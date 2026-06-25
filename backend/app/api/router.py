from fastapi import APIRouter

from app.api.v1 import agent_callbacks, health, llm_providers, repos, reviews, webhooks

api_router = APIRouter(prefix="/api")
v1_router = APIRouter(prefix="/v1")
v1_router.include_router(health.router, tags=["health"])
v1_router.include_router(reviews.router, prefix="/reviews", tags=["reviews"])
v1_router.include_router(
    llm_providers.router,
    prefix="/settings/llm-providers",
    tags=["llm-providers"],
)
v1_router.include_router(
    repos.router,
    prefix="/settings/repos",
    tags=["repos"],
)
v1_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
v1_router.include_router(agent_callbacks.router, prefix="/agent", tags=["agent"])
api_router.include_router(v1_router)
