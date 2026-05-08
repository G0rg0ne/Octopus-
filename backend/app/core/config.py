from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "octopus-api-gateway"
    log_level: str = "INFO"

    vllm_base_url: str = "http://localhost:8000"
    api_key: str = "dev-key"
    require_api_key_on_health: bool = False

    log_request_body: bool = False


settings = Settings()

