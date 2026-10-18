"""Admin-only secure configuration for the Shopee integration."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, SecretStr
from starlette.concurrency import run_in_threadpool

from apps.api.auth import current_user

router = APIRouter(prefix='/api/v1/shopee', tags=['shopee'])


class ShopeeCredentials(BaseModel):
    app_id: str = Field(min_length=1, max_length=128)
    app_secret: SecretStr = Field(min_length=1, max_length=512)


async def invoke(function, *args):
    try:
        return await run_in_threadpool(function, *args)
    except PermissionError:
        raise HTTPException(403, 'Acesso negado') from None
    except ValueError as error:
        raise HTTPException(422, str(error)) from None


@router.get('/credentials')
async def credential_status(request: Request, organization_id: UUID, user=Depends(current_user)):
    return await invoke(request.app.state.shopee_config.status, user['id'], organization_id)


@router.put('/credentials')
async def save_credentials(request: Request, organization_id: UUID, body: ShopeeCredentials, user=Depends(current_user)):
    result = await invoke(
        request.app.state.shopee_config.save,
        user['id'], organization_id, body.app_id, body.app_secret.get_secret_value(),
    )
    return result
