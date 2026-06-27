from fastapi import APIRouter

from app.api.v1 import (
    agent_callbacks,
    auth,
    health,
    identity_provider,
    install,
    llm_providers,
    org_repositories,
    repos,
    reviews,
    team_repos,
    teams,
    users,
    webhooks,
)

api_router = APIRouter(prefix="/api")
v1_router = APIRouter(prefix="/v1")
v1_router.include_router(health.router, tags=["health"])
v1_router.include_router(install.router, prefix="/install", tags=["install"])
v1_router.include_router(auth.router, prefix="/auth", tags=["auth"])
v1_router.include_router(reviews.router, prefix="/reviews", tags=["reviews"])
v1_router.include_router(
    org_repositories.router,
    prefix="/repositories",
    tags=["repositories"],
)
v1_router.include_router(users.router, prefix="/users", tags=["users"])
v1_router.include_router(teams.router, prefix="/teams", tags=["teams"])
v1_router.include_router(
    team_repos.router,
    prefix="/teams/{team_id}/repos",
    tags=["repos"],
)
v1_router.include_router(
    identity_provider.router,
    prefix="/settings/identity-provider",
    tags=["identity-provider"],
)
v1_router.include_router(
    llm_providers.router,
    prefix="/settings/llm-providers",
    tags=["llm-providers"],
)
v1_router.include_router(
    repos.router,
    prefix="/settings/repos",
    tags=["repos-legacy"],
)
v1_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
v1_router.include_router(agent_callbacks.router, prefix="/agent", tags=["agent"])
api_router.include_router(v1_router)
