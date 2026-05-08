from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import generate, health, openai_proxy

health_router = APIRouter()
health_router.include_router(health.router, tags=["health"])

openai_router = APIRouter()
openai_router.include_router(openai_proxy.router, tags=["openai-proxy"])

custom_router = APIRouter()
custom_router.include_router(generate.router, prefix="/api/v1", tags=["generate"])

