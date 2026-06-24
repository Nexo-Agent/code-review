from fastapi import APIRouter

from app.api.v1 import examples, health

api_router = APIRouter(prefix="/api")
v1_router = APIRouter(prefix="/v1")
v1_router.include_router(health.router, tags=["health"])
v1_router.include_router(examples.router, prefix="/examples", tags=["examples"])
api_router.include_router(v1_router)
