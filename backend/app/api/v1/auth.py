import logging

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse

from app.auth.dependencies import (
    SESSION_COOKIE,
    AuthContext,
    get_auth_context,
    get_current_user,
)
from app.auth.oidc import build_authorization_url, exchange_code
from app.auth.session import create_session, destroy_session
from app.config import get_code_review_settings
from app.dependencies import get_conn
from app.repositories.users import UserRepository
from app.schemas.auth import MeResponse, UserResponse
from app.services.teams import list_users

logger = logging.getLogger(__name__)

router = APIRouter()


def _user_response(user) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        is_org_admin=user.is_org_admin,
        created_at=user.created_at,
    )


def _resolve_redirect(state: str | None, frontend_url: str) -> str:
    if not state:
        return frontend_url
    if state.startswith("http://") or state.startswith("https://"):
        return state
    base = frontend_url.rstrip("/")
    if state.startswith("/"):
        return f"{base}{state}"
    return state


@router.get("/me", response_model=MeResponse)
async def get_me(
    auth: AuthContext = Depends(get_auth_context),
) -> MeResponse:
    return MeResponse(
        user=_user_response(auth.user),
        team_ids=auth.accessible_team_ids,
        auth_enabled=auth.auth_enabled,
    )


@router.get("/users", response_model=list[UserResponse])
async def get_users(
    user=Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_conn),
) -> list[UserResponse]:
    if not user.is_org_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return await list_users(conn)


@router.get("/login")
async def login(request: Request) -> RedirectResponse:
    settings = get_code_review_settings()
    if not settings.auth_enabled:
        return RedirectResponse(url=settings.frontend_url)
    state = request.query_params.get("return_to", settings.frontend_url)
    url = await build_authorization_url(state=state)
    return RedirectResponse(url=url)


@router.get("/callback")
async def callback(
    request: Request,
    response: Response,
    code: str | None = None,
    state: str | None = None,
    conn: asyncpg.Connection = Depends(get_conn),
) -> RedirectResponse:
    settings = get_code_review_settings()
    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing code",
        )

    userinfo = await exchange_code(code)
    sub = userinfo.get("sub")
    email = userinfo.get("email", "")
    name = userinfo.get("name", "")
    if not sub or not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OIDC userinfo",
        )

    user_repo = UserRepository(conn)
    existing = await user_repo.get_by_oidc_sub(sub)
    is_org_admin = False
    if existing is None:
        admin_count = await user_repo.count_org_admins()
        bootstrap_email = settings.bootstrap_org_admin_email.strip().lower()
        if admin_count == 0 or (
            bootstrap_email and email.strip().lower() == bootstrap_email
        ):
            is_org_admin = True

    user = await user_repo.upsert_oidc_user(
        oidc_sub=sub,
        email=email,
        name=name or email,
        is_org_admin=is_org_admin if existing is None else existing.is_org_admin,
    )

    session_id = await create_session(user_id=user.id)
    redirect_url = _resolve_redirect(state, settings.frontend_url)
    redirect = RedirectResponse(url=redirect_url, status_code=302)
    redirect.set_cookie(
        key=SESSION_COOKIE,
        value=session_id,
        httponly=True,
        secure=settings.auth_enabled and "localhost" not in settings.frontend_url,
        samesite="lax",
        max_age=settings.session_ttl_seconds,
    )
    return redirect


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
) -> Response:
    cookie = request.cookies.get(SESSION_COOKIE)
    if cookie:
        await destroy_session(cookie)
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(SESSION_COOKIE)
    return response
