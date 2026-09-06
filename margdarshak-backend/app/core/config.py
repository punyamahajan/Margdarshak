from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Margdarshak Voice-AI Placement Hotline"
    environment: str = "development"
    log_level: str = "INFO"

    database_url: str
    redis_url: str
    agora_app_id: str
    agora_app_certificate: SecretStr
    agora_customer_id: str = ""
    agora_customer_secret: SecretStr = SecretStr("")
    agora_ai_agent: str
    agora_agent_rtc_uid: int = 1
    agora_convo_ai_base_url: str = (
        "https://api.agora.io/api/conversational-ai-agent/v2/projects"
    )
    agora_token_ttl_seconds: int = 3600
    triage_session_ttl_seconds: int = 86400
    expiry_worker_interval_seconds: int = 60

    # Query deduplication / routing agent (Gemini preferred; OpenAI as fallback).
    gemini_api_key: SecretStr = SecretStr("")
    openai_api_key: SecretStr = SecretStr("")
    llm_provider: str = "auto"
    gemini_model: str = "gemini-flash-latest"
    openai_model: str = "gpt-4o-mini"
    query_similarity_threshold: float = 0.75

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
