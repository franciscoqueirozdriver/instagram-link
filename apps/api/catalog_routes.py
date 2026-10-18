from datetime import datetime,timezone
from typing import List,Optional
from uuid import UUID
from fastapi import APIRouter,Depends,HTTPException,Request,Query
from pydantic import BaseModel,Field
from starlette.concurrency import run_in_threadpool
from apps.api.auth import current_user
from apps.api.catalog import ConflictError,PublicationInUse
from packages.domain.campaigns import assess_comment,match_rules,render_message
from packages.meta.catalog_read import media,media_page,comments
from packages.meta.token_lifecycle import TokenLifecycleError
from packages.meta.oauth import SCOPES

router=APIRouter(prefix='/api/v1/catalog')


class Link(BaseModel):
    label:str=Field(min_length=1,max_length=80)
    url:str=Field(min_length=1,max_length=2048)


class Product(BaseModel):
    name:str=Field(min_length=1,max_length=160)
    description:str=Field(default='',max_length=3000)
    links:List[Link]=Field(min_length=1,max_length=5)
    active:bool=True
    expected_version:Optional[int]=Field(default=None,ge=1)


class Campaign(BaseModel):
    name:str=Field(min_length=1,max_length=160)
    publication_id:UUID
    product_id:UUID
    include:List[str]
    exclude:List[str]=[]
    ignore_accents:bool=False
    template:str=Field(min_length=1,max_length=4000)
    expected_version:Optional[int]=Field(default=None,ge=1)


class Review(BaseModel):
    expected_version:int=Field(ge=1)
    positive:str=Field(min_length=1,max_length=1000)
    negative:str=Field(min_length=1,max_length=1000)


async def invoke(function,*args,**kwargs):
    try:return await run_in_threadpool(function,*args,**kwargs)
    except PermissionError:raise HTTPException(403,'Acesso negado') from None
    except PublicationInUse:raise HTTPException(409,'Esta publicação já possui uma automação. Atualize a lista e abra a existente.') from None
    except ConflictError:raise HTTPException(409,'Este registro mudou. Atualize os dados antes de salvar.') from None
    except ValueError as error:raise HTTPException(422,str(error)) from None
    except TokenLifecycleError as error:
        raise HTTPException(409 if error.reason in ('reconnect_required','permission_denied') else 502,'Instagram indisponível ou autorização insuficiente. Confira a conexão da conta.') from None


@router.get('/products')
async def products(request:Request,organization_id:UUID,user=Depends(current_user)):
    return {'items':await invoke(request.app.state.catalog.products,user['id'],organization_id)}


@router.post('/products')
async def create_product(request:Request,organization_id:UUID,body:Product,user=Depends(current_user)):
    return await invoke(request.app.state.catalog.save_product,user['id'],organization_id,body.model_dump())


@router.put('/products/{product_id}')
async def update_product(request:Request,organization_id:UUID,product_id:UUID,body:Product,user=Depends(current_user)):
    return await invoke(request.app.state.catalog.save_product,user['id'],organization_id,body.model_dump(),product_id)


@router.delete('/products/{product_id}')
async def archive_product(request:Request,organization_id:UUID,product_id:UUID,expected_version:int,user=Depends(current_user)):
    return await invoke(request.app.state.catalog.archive_product,user['id'],organization_id,product_id,expected_version)


@router.get('/publications')
async def publications(request:Request,organization_id:UUID,account_id:UUID,cursor:Optional[str]=Query(default=None,max_length=4096),limit:int=Query(default=12,ge=1,le=25),user=Depends(current_user)):
    return await invoke(request.app.state.catalog.publications_page,user['id'],organization_id,account_id,cursor,limit)


async def snapshot(request,user,org,account):
    store=request.app.state.catalog
    def get():
        with store.connect() as c:row=store.account(c,user,org,account)
        if row['connection_status']!='connected' or not row['expires_at'] or row['expires_at']<=datetime.now(timezone.utc):
            raise ValueError('Reconecte a conta antes de consultar o Instagram')
        if not set(SCOPES).issubset(set(row['scopes'])):raise ValueError('Há permissões obrigatórias ausentes')
        result=request.app.state.accounts.credential_snapshot(account)
        if not result:raise ValueError('Credencial não disponível')
        return result
    return await invoke(get)


async def provider_read(request,snap,function,*args):
    try:return await run_in_threadpool(function,request.app.state.settings,snap,*args)
    except TokenLifecycleError as error:
        await run_in_threadpool(request.app.state.accounts.apply_token_health,snap,error.reason)
        raise HTTPException(409 if error.reason in ('reconnect_required','permission_denied') else 502,'Não foi possível consultar o Instagram. Confira a conexão e tente novamente.') from None
    except ValueError as error:raise HTTPException(422,str(error)) from None


class MediaSync(BaseModel):
    load_more:bool=False


@router.post('/publications/sync')
async def sync(request:Request,organization_id:UUID,account_id:UUID,body:MediaSync=MediaSync(),user=Depends(current_user)):
    snap=await snapshot(request,user['id'],organization_id,account_id)
    store=request.app.state.catalog
    state=await invoke(store.sync_state,user['id'],organization_id,account_id)
    if body.load_more and state['synced_at'] and not state['after']:return {'count':0,'partial':False}
    after=state['after'] if body.load_more else None
    items,next_after=await provider_read(request,snap,media_page,after)
    await invoke(store.save_publications,user['id'],organization_id,account_id,items,sync_state=state,next_after=next_after)
    return {'count':len(items),'partial':bool(next_after)}


@router.get('/campaigns')
async def campaigns(request:Request,organization_id:UUID,account_id:UUID,user=Depends(current_user)):
    return {'items':await invoke(request.app.state.catalog.campaigns,user['id'],organization_id,account_id)}


@router.post('/campaigns')
async def create_campaign(request:Request,organization_id:UUID,account_id:UUID,body:Campaign,user=Depends(current_user)):
    return await invoke(request.app.state.catalog.save_campaign,user['id'],organization_id,account_id,body.model_dump())


@router.put('/campaigns/{campaign_id}')
async def update_campaign(request:Request,organization_id:UUID,account_id:UUID,campaign_id:UUID,body:Campaign,user=Depends(current_user)):
    return await invoke(request.app.state.catalog.save_campaign,user['id'],organization_id,account_id,body.model_dump(),campaign_id)


@router.delete('/campaigns/{campaign_id}')
async def archive_campaign(request:Request,organization_id:UUID,account_id:UUID,campaign_id:UUID,expected_version:int,user=Depends(current_user)):
    return await invoke(request.app.state.catalog.archive_campaign,user['id'],organization_id,account_id,campaign_id,expected_version)


@router.post('/campaigns/{campaign_id}/prepare-pilot')
async def prepare(request:Request,organization_id:UUID,account_id:UUID,campaign_id:UUID,body:Review,user=Depends(current_user)):
    store=request.app.state.catalog
    campaign=await invoke(store.campaign,user['id'],organization_id,account_id,campaign_id)
    if campaign['version']!=body.expected_version:raise HTTPException(409,'Atualize a versão da campanha')
    if not match_rules(body.positive,campaign['rules'])[0] or match_rules(body.negative,campaign['rules'])[0]:
        raise HTTPException(422,'O teste positivo deve corresponder e o negativo deve ser excluído pelas regras')
    snap=await snapshot(request,user['id'],organization_id,account_id)
    publications=await invoke(store.publications,user['id'],organization_id,account_id)
    publication=next(item for item in publications if item['id']==campaign['publication_id'])
    rows,partial=await provider_read(request,snap,comments,publication['ig_media_id'])
    used=await invoke(store.prior_attempts,account_id)
    now=datetime.now(timezone.utc);seen=set()
    assessed=[assess_comment(row,campaign['rules'],now,campaign['created_at'],snap['ig_user_id'],used,seen) for row in sorted(rows,key=lambda r:r.get('timestamp',''))]
    review={'campaign_id':str(campaign_id),'version':campaign['version'],'account_id':str(account_id),
            'rendered_message':campaign['rendered_message'],'message_bytes':len(campaign['rendered_message'].encode()),
            'rules':campaign['rules'],'comments':assessed,'partial':partial,'reviewed_at':now.isoformat(),
            'test_cases':{'positive':body.positive,'negative':body.negative},
            'cutoff':campaign['created_at'].isoformat(),'positive_passed':True,'negative_passed':True,
            'eligible_count':sum(row['eligible'] for row in assessed),'sending_enabled':False,
            'blockers':['Envios globais pausados por decisão do operador.','Despachante de campanhas, reservas de frequência e orçamento ainda não liberados.','Revalidar comentário, janela, regra, pausa e deduplicação imediatamente antes de qualquer envio.'],
            'note':'Pré-elegibilidade para revisão. Não autoriza envio nem inclui retroativos. O corte deverá ser refeito na ativação; só comentários posteriores poderão entrar no piloto.'}
    saved=await invoke(store.save_review,user['id'],organization_id,account_id,campaign_id,campaign['version'],review)
    return {**review,'review_id':str(saved['id']),'expires_at':saved['expires_at']}


@router.get('/reviews')
async def reviews(request:Request,organization_id:UUID,account_id:UUID,user=Depends(current_user)):
    return {'items':await invoke(request.app.state.catalog.reviews,user['id'],organization_id,account_id),
            'audit':await invoke(request.app.state.catalog.audit_history,user['id'],organization_id,account_id)}


@router.get('/campaigns/{campaign_id}/versions')
async def versions(request:Request,organization_id:UUID,account_id:UUID,campaign_id:UUID,user=Depends(current_user)):
    return {'items':await invoke(request.app.state.catalog.versions,user['id'],organization_id,account_id,campaign_id)}


@router.get('/reviews/{review_id}')
async def review_detail(request:Request,organization_id:UUID,account_id:UUID,review_id:UUID,user=Depends(current_user)):
    return await invoke(request.app.state.catalog.review_detail,user['id'],organization_id,account_id,review_id)


class PauseCampaign(BaseModel):
    expected_version:int=Field(ge=1)


@router.post('/campaigns/{campaign_id}/pause')
async def pause_campaign(request:Request,organization_id:UUID,account_id:UUID,campaign_id:UUID,body:PauseCampaign,user=Depends(current_user)):
    return await invoke(request.app.state.catalog.pause_campaign,user['id'],organization_id,account_id,campaign_id,body.expected_version)


@router.post('/campaigns/{campaign_id}/simulate')
async def simulate(request:Request,organization_id:UUID,account_id:UUID,campaign_id:UUID,body:Review,user=Depends(current_user)):
    campaign=await invoke(request.app.state.catalog.campaign,user['id'],organization_id,account_id,campaign_id)
    if campaign['version']!=body.expected_version:raise HTTPException(409,'Atualize a versão da campanha')
    positive,positive_reason=match_rules(body.positive,campaign['rules'])
    negative,negative_reason=match_rules(body.negative,campaign['rules'])
    return {'positive':{'matched':positive,'reason':positive_reason},'negative':{'matched':negative,'reason':negative_reason},
            'valid':positive and not negative,'rendered_message':campaign['rendered_message'],
            'message_bytes':len(campaign['rendered_message'].encode()),'sending_enabled':False}
