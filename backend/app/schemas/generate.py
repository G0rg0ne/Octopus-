from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    model: str = Field(min_length=1)
    prompt: str = Field(min_length=1)

    max_tokens: int = Field(default=256, ge=1, le=4096)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    top_p: float = Field(default=1.0, ge=0.0, le=1.0)
    stop: str | list[str] | None = None


class GenerateResponse(BaseModel):
    model: str
    text: str
    finish_reason: str | None = None
    usage: dict[str, Any] | None = None


class StreamEvent(BaseModel):
    event: Literal["token", "done", "error"]
    data: dict[str, Any]

