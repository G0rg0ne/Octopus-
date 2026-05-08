from __future__ import annotations

import json
import time
from typing import Any

import httpx
import structlog
from fastapi import APIRouter
from fastapi.responses import JSONResponse, StreamingResponse

from app.core.config import settings
from app.schemas.generate import GenerateRequest, GenerateResponse

router = APIRouter()


def _to_openai_completions_payload(req: GenerateRequest, stream: bool) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": req.model,
        "prompt": req.prompt,
        "max_tokens": req.max_tokens,
        "temperature": req.temperature,
        "top_p": req.top_p,
        "stream": stream,
    }
    if req.stop is not None:
        payload["stop"] = req.stop
    return payload


@router.post("/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest) -> GenerateResponse:
    upstream_url = f"{settings.vllm_base_url}/v1/completions"
    upstream_start = time.perf_counter()
    payload = _to_openai_completions_payload(req, stream=False)

    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
        resp = await client.post(upstream_url, json=payload)

    structlog.get_logger().info(
        "upstream",
        upstream_path="/v1/completions",
        upstream_status=resp.status_code,
        upstream_latency_ms=round((time.perf_counter() - upstream_start) * 1000, 2),
    )

    if resp.status_code >= 400:
        return JSONResponse(status_code=resp.status_code, content=resp.json())  # type: ignore[return-value]

    data = resp.json()
    text = ""
    finish_reason = None
    try:
        choice0 = (data.get("choices") or [None])[0] or {}
        text = choice0.get("text") or ""
        finish_reason = choice0.get("finish_reason")
    except Exception:
        text = ""

    return GenerateResponse(
        model=data.get("model") or req.model,
        text=text,
        finish_reason=finish_reason,
        usage=data.get("usage"),
    )


@router.post("/stream")
async def stream(req: GenerateRequest) -> StreamingResponse:
    upstream_url = f"{settings.vllm_base_url}/v1/completions"
    payload = _to_openai_completions_payload(req, stream=True)
    upstream_start = time.perf_counter()

    async def gen():
        async with httpx.AsyncClient(timeout=httpx.Timeout(None)) as client:
            async with client.stream("POST", upstream_url, json=payload) as r:
                structlog.get_logger().info(
                    "upstream_stream_open",
                    upstream_path="/v1/completions",
                    upstream_status=r.status_code,
                    upstream_latency_ms=round((time.perf_counter() - upstream_start) * 1000, 2),
                )

                async for raw_line in r.aiter_lines():
                    if not raw_line:
                        continue

                    line = raw_line.strip()
                    if not line.startswith("data:"):
                        continue

                    chunk = line[len("data:") :].strip()
                    if chunk == "[DONE]":
                        yield "event: done\ndata: {\"reason\":\"done\"}\n\n"
                        return

                    try:
                        obj = json.loads(chunk)
                        choice0 = (obj.get("choices") or [None])[0] or {}
                        token_text = choice0.get("text") or ""
                        yield f"event: token\ndata: {json.dumps({'text': token_text})}\n\n"
                    except Exception as e:
                        yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )

