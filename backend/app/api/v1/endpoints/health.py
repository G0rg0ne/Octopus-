from __future__ import annotations

import time

import httpx
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.security import require_api_key

router = APIRouter()


@router.get("/health")
async def health(
    _: None = Depends(require_api_key) if settings.require_api_key_on_health else None,
):
    upstream_start = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(2.0)) as client:
            resp = await client.get(f"{settings.vllm_base_url}/v1/models")
        ok = resp.status_code == 200
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "degraded",
                "upstream": {
                    "status": "error",
                    "error": str(e),
                    "latency_ms": round((time.perf_counter() - upstream_start) * 1000, 2),
                },
            },
        )

    return {
        "status": "ok" if ok else "degraded",
        "upstream": {
            "status": "ok" if ok else "error",
            "latency_ms": round((time.perf_counter() - upstream_start) * 1000, 2),
            "status_code": resp.status_code,
        },
    }

