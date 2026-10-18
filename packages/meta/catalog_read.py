"""Read-only bounded Instagram catalog queries, fixed host and cursor pagination."""
import httpx
from packages.meta.token_lifecycle import checked_payload,TokenLifecycleError


def read_collection(settings,token,path,fields,max_pages=3):
    if not all(part.isdigit() or part in ('media','comments') for part in path.split('/')):
        raise ValueError('Invalid provider path')
    items=[];after=None;more=False
    try:
        with httpx.Client(timeout=httpx.Timeout(15,connect=5),follow_redirects=False,transport=httpx.HTTPTransport(retries=0)) as client:
            for _ in range(max_pages):
                params={'fields':fields,'limit':25}
                if after:params['after']=after
                body=checked_payload(client.get('https://graph.instagram.com/'+settings.meta_api_version+'/'+path,params=params,headers={'Authorization':'Bearer '+token}))
                page=body.get('data')
                if not isinstance(page,list) or not all(isinstance(item,dict) for item in page):raise TokenLifecycleError('invalid_response')
                items.extend(page)
                pagination=body.get('paging',{})
                after=pagination.get('cursors',{}).get('after')
                more=bool(pagination.get('next') and after)
                if not more:break
        return items,more
    except httpx.HTTPError:raise TokenLifecycleError('provider_unavailable') from None


def media(settings,snapshot):
    return read_collection(settings,snapshot['token'],snapshot['ig_user_id']+'/media','id,caption,permalink,media_type,timestamp')


def comments(settings,snapshot,media_id):
    owned,_=media(settings,snapshot)
    if not any(str(item.get('id'))==media_id for item in owned):raise ValueError('Publicação não encontrada entre as até 75 mídias próprias consultadas. Sincronize e selecione uma mídia recente.')
    return read_collection(settings,snapshot['token'],media_id+'/comments','id,from,text,timestamp,parent_id,hidden')


def media_page(settings,snapshot,after=None):
    """One bounded provider page. Caller keeps the next cursor encrypted, scoped to account."""
    if not str(snapshot['ig_user_id']).isdigit():raise ValueError('Invalid account identity')
    if after is not None and (not isinstance(after,str) or not 1<=len(after)<=4096):raise ValueError('Invalid media cursor')
    params={'fields':'id,caption,permalink,media_type,media_product_type,media_url,thumbnail_url,timestamp','limit':25}
    if after:params['after']=after
    try:
        with httpx.Client(timeout=httpx.Timeout(15,connect=5),follow_redirects=False,transport=httpx.HTTPTransport(retries=0)) as client:
            body=checked_payload(client.get('https://graph.instagram.com/'+settings.meta_api_version+'/'+snapshot['ig_user_id']+'/media',params=params,headers={'Authorization':'Bearer '+snapshot['token']}))
        items=body.get('data')
        if not isinstance(items,list) or not all(isinstance(item,dict) for item in items):raise TokenLifecycleError('invalid_response')
        paging=body.get('paging') or {}
        cursor=(paging.get('cursors') or {}).get('after') if paging.get('next') else None
        if cursor is not None and (not isinstance(cursor,str) or not 1<=len(cursor)<=4096 or cursor==after):raise TokenLifecycleError('invalid_response')
        return items,cursor
    except httpx.HTTPError:raise TokenLifecycleError('provider_unavailable') from None
