from __future__ import annotations

from dataclasses import dataclass

from prometheus_client import Counter
from starlette.requests import Request


wrapper_requests_total = Counter(
    "wrapper_requests_total",
    "Total HTTP requests handled by the FastAPI wrapper.",
    labelnames=("route", "method", "status_code"),
)

wrapper_inference_success_total = Counter(
    "wrapper_inference_success_total",
    "Successful inference requests handled by the wrapper (HTTP 2xx).",
    labelnames=("route", "method"),
)

wrapper_inference_error_total = Counter(
    "wrapper_inference_error_total",
    "Inference errors handled by the wrapper (HTTP >= 400), classified by error_type.",
    labelnames=("route", "method", "status_code", "error_type"),
)


@dataclass(frozen=True)
class RequestLabels:
    route: str
    method: str


def is_inference_route(route: str) -> bool:
    # Per plan: count inference endpoints only (exclude /health, /metrics, etc.)
    return route.startswith("/v1/") or route.startswith("/api/v1/")


def get_route_label(request: Request) -> str:
    route_obj = request.scope.get("route")
    path = getattr(route_obj, "path", None)
    if isinstance(path, str) and path:
        return path
    return request.url.path


def classify_error_type(method: str, status_code: int, route: str) -> str:
    if method.upper() == "OPTIONS":
        return "cors_preflight_or_cors_block"

    if status_code == 401:
        return "auth_missing_or_invalid"
    if status_code == 413:
        return "request_too_large"
    if status_code == 415:
        return "unsupported_media_type"
    if status_code == 422:
        return "validation_error"
    if status_code == 404:
        return "not_found"
    if status_code == 405:
        return "method_not_allowed"
    if status_code == 400:
        return "invalid_json"
    if status_code == 502 and is_inference_route(route):
        return "upstream_unavailable"
    if status_code >= 500:
        return "internal_error"

    return "other"

