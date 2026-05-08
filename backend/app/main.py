from __future__ import annotations

import time
import uuid
from collections.abc import Callable
from typing import Any

import httpx
import structlog
from fastapi import Depends, FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.v1.router import custom_router, health_router, openai_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.core.security import require_api_key


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable[[Request], Any]) -> Response:
        request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
        start = time.perf_counter()

        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        request_body_bytes: bytes | None = None
        if settings.log_request_body:
            try:
                request_body_bytes = await request.body()
            except Exception:
                request_body_bytes = None

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            structlog.get_logger().exception("request_failed", duration_ms=duration_ms)
            structlog.contextvars.clear_contextvars()
            raise

        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        response.headers["X-Request-Id"] = request_id

        event: dict[str, Any] = {
            "status_code": response.status_code,
            "duration_ms": duration_ms,
            "client_host": getattr(request.client, "host", None),
        }
        if request_body_bytes is not None:
            try:
                event["request_body"] = request_body_bytes.decode("utf-8", errors="replace")
            except Exception:
                event["request_body"] = "<unavailable>"

        structlog.get_logger().info(
            "request",
            **event,
        )
        structlog.contextvars.clear_contextvars()
        return response


def create_app() -> FastAPI:
    configure_logging(settings.log_level)

    app = FastAPI(title=settings.app_name)
    app.add_middleware(RequestLoggingMiddleware)

    app.include_router(health_router)
    app.include_router(openai_router, dependencies=[Depends(require_api_key)])
    app.include_router(custom_router, dependencies=[Depends(require_api_key)])

    @app.exception_handler(httpx.HTTPError)
    async def httpx_error_handler(_: Request, exc: httpx.HTTPError):
        return JSONResponse(status_code=502, content={"detail": "Upstream request failed", "error": str(exc)})

    return app


app = create_app()

