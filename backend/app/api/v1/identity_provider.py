import asyncpg
from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.dependencies import require_org_action_dep
from app.dependencies import get_conn
from app.rbac.catalog import ActionKey
from app.schemas.identity_provider import (
    IdentityProviderResponse,
    IdentityProviderUpsert,
    SamlSpCertUpload,
)
from app.services.identity_provider import (
    delete_identity_provider,
    get_identity_provider,
    upload_saml_sp_cert,
    upsert_identity_provider,
)

router = APIRouter()


@router.get("", response_model=IdentityProviderResponse)
async def get_idp_settings(
    conn: asyncpg.Connection = Depends(get_conn),
    _admin=Depends(require_org_action_dep(ActionKey.SETTINGS_SSO_READ)),
) -> IdentityProviderResponse:
    row = await get_identity_provider(conn)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not configured",
        )
    return row


@router.put("", response_model=IdentityProviderResponse)
async def put_idp_settings(
    payload: IdentityProviderUpsert,
    conn: asyncpg.Connection = Depends(get_conn),
    _admin=Depends(require_org_action_dep(ActionKey.SETTINGS_SSO_UPDATE)),
) -> IdentityProviderResponse:
    try:
        return await upsert_identity_provider(conn, payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_idp_settings(
    conn: asyncpg.Connection = Depends(get_conn),
    _admin=Depends(require_org_action_dep(ActionKey.SETTINGS_SSO_UPDATE)),
) -> None:
    await delete_identity_provider(conn)


@router.put("/saml/cert", response_model=IdentityProviderResponse)
async def put_saml_sp_cert(
    payload: SamlSpCertUpload,
    conn: asyncpg.Connection = Depends(get_conn),
    _admin=Depends(require_org_action_dep(ActionKey.SETTINGS_SSO_UPDATE)),
) -> IdentityProviderResponse:
    try:
        return await upload_saml_sp_cert(
            conn,
            sp_cert=payload.sp_cert,
            sp_private_key=payload.sp_private_key,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
