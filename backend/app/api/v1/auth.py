import logging
from urllib.parse import urlparse

import asyncpg
from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response, status
from fastapi.responses import PlainTextResponse, RedirectResponse

from app.auth.dependencies import (
    SESSION_COOKIE,
    AuthContext,
    get_auth_context,
    get_current_user,
)
from app.auth.oidc import build_authorization_url, exchange_code
from app.auth.saml import (
    build_saml_auth,
    get_sp_metadata,
    process_acs_response,
)
from app.auth.session import create_session, destroy_session
from app.auth.state import consume_auth_state, create_auth_state
from app.config import get_code_review_settings
from app.dependencies import get_conn
from app.schemas.auth import MeResponse, UserResponse
from app.schemas.identity_provider import IdentityProviderPublicResponse
from app.schemas.install import LocalLoginRequest
from app.services.access_control import get_accessible_team_ids
from app.services.identity_provider import (
    extract_nested_claim,
    get_enabled_identity_provider,
    get_public_identity_provider,
    provision_user_from_claims,
)
from app.services.install import authenticate_local_user
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
    base = frontend_url.rstrip("/")
    allowed_origin = urlparse(base)
    if not state:
        return base
    if state.startswith("/"):
        return f"{base}{state}"
    if state.startswith("http://") or state.startswith("https://"):
        parsed = urlparse(state)
        if (
            parsed.scheme == allowed_origin.scheme
            and parsed.netloc == allowed_origin.netloc
        ):
            return state
    return base


def _apply_session_cookie(
    response: RedirectResponse,
    session_id: str,
) -> RedirectResponse:
    settings = get_code_review_settings()
    response.set_cookie(
        key=SESSION_COOKIE,
        value=session_id,
        httponly=True,
        secure=settings.auth_enabled and "localhost" not in settings.frontend_url,
        samesite="lax",
        max_age=settings.session_ttl_seconds,
    )
    return response


@router.get("/me", response_model=MeResponse)
async def get_me(
    auth: AuthContext = Depends(get_auth_context),
) -> MeResponse:
    return MeResponse(
        user=_user_response(auth.user),
        team_ids=auth.accessible_team_ids,
        auth_enabled=auth.auth_enabled,
    )


@router.get("/idp", response_model=IdentityProviderPublicResponse)
async def get_idp(
    conn: asyncpg.Connection = Depends(get_conn),
) -> IdentityProviderPublicResponse:
    return await get_public_identity_provider(conn)


@router.get("/users", response_model=list[UserResponse])
async def get_users(
    user=Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_conn),
) -> list[UserResponse]:
    if not user.is_org_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return await list_users(conn)


@router.get("/login")
async def login(
    request: Request,
    conn: asyncpg.Connection = Depends(get_conn),
) -> RedirectResponse:
    settings = get_code_review_settings()
    if not settings.auth_enabled:
        return RedirectResponse(url=settings.frontend_url)

    idp = await get_enabled_identity_provider(conn)
    if idp is None:
        return RedirectResponse(
            url=f"{settings.frontend_url.rstrip('/')}/login?error=idp_not_configured"
        )

    return_to = request.query_params.get("return_to", settings.frontend_url)
    redirect_target = _resolve_redirect(return_to, settings.frontend_url)
    state = await create_auth_state(return_to=redirect_target)

    if idp.protocol == "saml":
        auth = build_saml_auth(request, idp)
        url = auth.login(return_to=state)
        return RedirectResponse(url=url)

    url = await build_authorization_url(row=idp, state=state)
    return RedirectResponse(url=url)


@router.get("/callback")
async def callback(
    request: Request,
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

    return_to = await consume_auth_state(state or "")
    if return_to is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired state",
        )

    idp = await get_enabled_identity_provider(conn)
    if idp is None or idp.protocol != "oidc":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OIDC not configured",
        )

    userinfo = await exchange_code(row=idp, code=code)
    sub = extract_nested_claim(userinfo, idp.sub_claim) or str(userinfo.get("sub", ""))
    email = extract_nested_claim(userinfo, idp.email_claim) or str(
        userinfo.get("email", "")
    )
    name = extract_nested_claim(userinfo, idp.name_claim) or str(
        userinfo.get("name", "")
    )
    claims = {**userinfo, "sub": sub, "email": email, "name": name}

    try:
        user = await provision_user_from_claims(
            conn,
            protocol="oidc",
            issuer=idp.oidc_issuer or "",
            claims=claims,
            email_claim="email",
            name_claim="name",
            sub_claim="sub",
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    session_id = await create_session(user_id=user.id)
    redirect_url = _resolve_redirect(return_to, settings.frontend_url)
    redirect = RedirectResponse(url=redirect_url, status_code=302)
    return _apply_session_cookie(redirect, session_id)


@router.get("/saml/login")
async def saml_login(
    request: Request,
    conn: asyncpg.Connection = Depends(get_conn),
) -> RedirectResponse:
    settings = get_code_review_settings()
    if not settings.auth_enabled:
        return RedirectResponse(url=settings.frontend_url)

    idp = await get_enabled_identity_provider(conn)
    if idp is None or idp.protocol != "saml":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SAML not configured",
        )

    return_to = request.query_params.get("return_to", settings.frontend_url)
    redirect_target = _resolve_redirect(return_to, settings.frontend_url)
    state = await create_auth_state(return_to=redirect_target)
    auth = build_saml_auth(request, idp)
    url = auth.login(return_to=state)
    return RedirectResponse(url=url)


@router.post("/saml/acs")
async def saml_acs(
    request: Request,
    conn: asyncpg.Connection = Depends(get_conn),
    saml_response: str = Form(default="", alias="SAMLResponse"),
    relay_state: str = Form(default="", alias="RelayState"),
) -> RedirectResponse:
    settings = get_code_review_settings()
    idp = await get_enabled_identity_provider(conn)
    if idp is None or idp.protocol != "saml":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SAML not configured",
        )

    form = {"SAMLResponse": saml_response}
    if relay_state:
        form["RelayState"] = relay_state
    auth = build_saml_auth(request, idp, post_data=form)

    try:
        claims = process_acs_response(auth)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return_to = await consume_auth_state(relay_state) or settings.frontend_url
    sub = extract_nested_claim(claims, idp.sub_claim) or claims.get("sub", "")
    email = extract_nested_claim(claims, idp.email_claim) or claims.get("email", "")
    name = extract_nested_claim(claims, idp.name_claim) or claims.get("name", "")
    normalized = {**claims, "sub": sub, "email": email, "name": name}

    try:
        user = await provision_user_from_claims(
            conn,
            protocol="saml",
            issuer=idp.saml_idp_entity_id or "",
            claims=normalized,
            email_claim="email",
            name_claim="name",
            sub_claim="sub",
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    session_id = await create_session(user_id=user.id)
    redirect_url = _resolve_redirect(return_to, settings.frontend_url)
    redirect = RedirectResponse(url=redirect_url, status_code=302)
    return _apply_session_cookie(redirect, session_id)


@router.get("/saml/metadata")
async def saml_metadata(
    conn: asyncpg.Connection = Depends(get_conn),
) -> PlainTextResponse:
    from app.repositories.identity_providers import IdentityProviderRepository
    from app.repositories.organizations import OrganizationRepository

    org = await OrganizationRepository(conn).get_default()
    if org is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    idp = await IdentityProviderRepository(conn).get(org.id)
    if idp is None or idp.protocol != "saml":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    try:
        metadata = get_sp_metadata(idp)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return PlainTextResponse(
        content=metadata,
        media_type="application/samlmetadata+xml",
    )


def _set_json_session_cookie(response: Response, session_id: str) -> None:
    settings = get_code_review_settings()
    response.set_cookie(
        key=SESSION_COOKIE,
        value=session_id,
        httponly=True,
        secure=settings.auth_enabled and "localhost" not in settings.frontend_url,
        samesite="lax",
        max_age=settings.session_ttl_seconds,
    )


@router.post("/local/login", response_model=MeResponse)
async def local_login(
    payload: LocalLoginRequest,
    response: Response,
    conn: asyncpg.Connection = Depends(get_conn),
) -> MeResponse:
    user = await authenticate_local_user(
        conn,
        username=payload.username,
        password=payload.password,
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    session_id = await create_session(user_id=user.id)
    _set_json_session_cookie(response, session_id)
    settings = get_code_review_settings()
    team_ids = await get_accessible_team_ids(conn, user)
    return MeResponse(
        user=_user_response(user),
        team_ids=team_ids,
        auth_enabled=settings.auth_enabled,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
) -> Response:
    cookie = request.cookies.get(SESSION_COOKIE)
    if cookie:
        await destroy_session(cookie)
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(SESSION_COOKIE)
    return response
