"""Minimal settings module — Regenold + GraphRAG + Mistral.

Trimmed-down extract of CodexAI's full ``app/config.py``. Only the
sub-settings the Regenold pipeline + Graph-RAG engine actually read are
preserved. Adding new options outside this scope is intentional — keep
this file small so partners auditing the bundle can read it in one pass.
"""
from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class GraphRAGSettings(BaseSettings):
    """LLM config for the Graph-RAG engine."""

    model_config = SettingsConfigDict(env_prefix="P2P_GRAPH_RAG_", extra="ignore")

    api_key: SecretStr | None = None
    model: str = "claude-sonnet-4-6"
    max_tokens: int = 1024
    temperature: float = 0.0


class RegenoldSettings(BaseSettings):
    """Regenold partner-tier auth + rate-limit settings."""

    model_config = SettingsConfigDict(env_prefix="P2P_REGENOLD_", extra="ignore")

    api_key: SecretStr | None = None
    """Optional. When set, callers with a matching X-Regenold-Api-Key
    header get the privileged 60/min rate-limit bucket.
    """


class MistralSettings(BaseSettings):
    """Mistral provider config (read on every call so a Railway env-var
    rebind takes effect immediately)."""

    model_config = SettingsConfigDict(env_prefix="MISTRAL_", extra="ignore")

    api_key: SecretStr | None = None
    timeout_seconds: float = 30.0
    max_retries: int = 1


class RateLimitSettings(BaseSettings):
    """slowapi limiter knobs."""

    model_config = SettingsConfigDict(env_prefix="P2P_RATELIMIT_", extra="ignore")

    storage_uri: str = "memory://"
    default_limit: str = "100/minute"


class AppSettings(BaseSettings):
    """Top-level container — sub-settings are eagerly instantiated."""

    model_config = SettingsConfigDict(env_prefix="P2P_", extra="ignore")

    graph_rag: GraphRAGSettings = Field(default_factory=GraphRAGSettings)
    regenold: RegenoldSettings = Field(default_factory=RegenoldSettings)
    mistral: MistralSettings = Field(default_factory=MistralSettings)
    rate_limit: RateLimitSettings = Field(default_factory=RateLimitSettings)

    version: str = "0.1.0"


settings = AppSettings()
