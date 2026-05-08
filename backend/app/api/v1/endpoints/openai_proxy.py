from __future__ import annotations

import time
from typing import Any

import httpx
import structlog
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse

from app.core.config import settings

router = APIRouter()


async def _proxy_json(body: Any, upstream_path: str, content_type: str | None) -> Response:
    if (content_type or "").split(";")[0].strip().lower() != "application/json":
        return JSONResponse(status_code=415, content={"detail": "Content-Type must be application/json"})

    upstream_url = f"{settings.vllm_base_url}{upstream_path}"
    upstream_start = time.perf_counter()

    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
        resp = await client.post(upstream_url, json=body)

    structlog.get_logger().info(
        "upstream",
        upstream_path=upstream_path,
        upstream_status=resp.status_code,
        upstream_latency_ms=round((time.perf_counter() - upstream_start) * 1000, 2),
    )
    return Response(content=resp.content, status_code=resp.status_code, media_type=resp.headers.get("content-type"))


async def _proxy_streaming(body: Any, upstream_path: str) -> StreamingResponse:
    upstream_url = f"{settings.vllm_base_url}{upstream_path}"
    upstream_start = time.perf_counter()

    async def gen():
        async with httpx.AsyncClient(timeout=httpx.Timeout(None)) as client:
            async with client.stream("POST", upstream_url, json=body) as r:
                structlog.get_logger().info(
                    "upstream_stream_open",
                    upstream_path=upstream_path,
                    upstream_status=r.status_code,
                    upstream_latency_ms=round((time.perf_counter() - upstream_start) * 1000, 2),
                )
                async for chunk in r.aiter_raw():
                    if chunk:
                        yield chunk

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.get("/v1/models")
async def list_models() -> Response:
    upstream_url = f"{settings.vllm_base_url}/v1/models"
    upstream_start = time.perf_counter()
    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
        resp = await client.get(upstream_url)

    structlog.get_logger().info(
        "upstream",
        upstream_path="/v1/models",
        upstream_status=resp.status_code,
        upstream_latency_ms=round((time.perf_counter() - upstream_start) * 1000, 2),
    )
    return Response(content=resp.content, status_code=resp.status_code, media_type=resp.headers.get("content-type"))


@router.post("/v1/completions")
async def completions(request: Request) -> Response:
    body: Any = await request.json()
    stream = bool(body.get("stream"))
    if stream:
        return await _proxy_streaming(body, "/v1/completions")
    return await _proxy_json(body, "/v1/completions", request.headers.get("content-type"))


@router.post("/v1/chat/completions")
async def chat_completions(request: Request) -> Response:
    body: Any = await request.json()
    stream = bool(body.get("stream"))
    if stream:
        return await _proxy_streaming(body, "/v1/chat/completions")
    return await _proxy_json(body, "/v1/chat/completions", request.headers.get("content-type"))

