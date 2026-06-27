import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.auth.dependencies import SESSION_COOKIE
from app.auth.session import create_session
from app.config import get_code_review_settings
from app.dependencies import get_conn
from app.schemas.auth import MeResponse, UserResponse
from app.schemas.install import InstallBootstrapRequest, InstallStatusResponse
from app.services.install import (
    SetupAlreadyCompletedError,
    bootstrap_install,
    get_install_status,
)

router = APIRouter()


def _user_response(user) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        is_org_admin=user.is_org_admin,
        created_at=user.created_at,
    )


def _set_session_cookie(response: Response, session_id: str) -> None:
    settings = get_code_review_settings()
    response.set_cookie(
        key=SESSION_COOKIE,
        value=session_id,
        httponly=True,
        secure=settings.auth_enabled and "localhost" not in settings.frontend_url,
        samesite="lax",
        max_age=settings.session_ttl_seconds,
    )


@router.get("/status", response_model=InstallStatusResponse)
async def install_status(
    conn: asyncpg.Connection = Depends(get_conn),
) -> InstallStatusResponse:
    return await get_install_status(conn)


@router.post("/bootstrap", response_model=MeResponse)
async def install_bootstrap(
    payload: InstallBootstrapRequest,
    response: Response,
    conn: asyncpg.Connection = Depends(get_conn),
) -> MeResponse:
    try:
        user = await bootstrap_install(conn, payload)
    except SetupAlreadyCompletedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Setup already completed",
        ) from exc

    session_id = await create_session(user_id=user.id)
    _set_session_cookie(response, session_id)

    settings = get_code_review_settings()
    return MeResponse(
        user=_user_response(user),
        team_ids=[],
        auth_enabled=settings.auth_enabled,
    )
