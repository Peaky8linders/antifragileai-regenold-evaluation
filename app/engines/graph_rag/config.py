"""Configuration & Feature Flag Manager for Graph RAG Engine."""

from __future__ import annotations

import os


def env_enabled(name: str, default: str = "0") -> bool:
    """Helper to check truthy environment variables."""
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "on")


class GraphRAGConfig:
    """Centralized config container for Graph RAG pipeline switches."""

    @property
    def logic_rag_enabled(self) -> bool:
        return env_enabled("REGENOLD_LOGIC_RAG", "1")

    @property
    def medtech_enabled(self) -> bool:
        return env_enabled("REGENOLD_MEDTECH", "1")

    @property
    def sufficient_context_enabled(self) -> bool:
        return env_enabled("REGENOLD_SUFFICIENT_CONTEXT", "0")

    @property
    def stage2_provider_enabled(self) -> bool:
        return env_enabled("STAGE2_PROVIDER_ENABLED", "1")

    @property
    def stage2_polish_enabled(self) -> bool:
        return env_enabled("STAGE2_POLISH_ENABLED", "1")

    @property
    def stage2_simple_skip_enabled(self) -> bool:
        return env_enabled("STAGE2_SIMPLE_SKIP_ENABLED", "0")

    @property
    def answer_v2_enabled(self) -> bool:
        return env_enabled("REGENOLD_GRAPH_RAG_V2", "1")

    @property
    def verify_verdict_enabled(self) -> bool:
        return env_enabled("REGENOLD_VERIFY_VERDICT", "1")

    @property
    def lower_risk_verdicts_enabled(self) -> bool:
        return env_enabled("REGENOLD_LOWER_RISK_VERDICTS", "1")

    @property
    def multi_article_entities_enabled(self) -> bool:
        return os.environ.get(
            "REGENOLD_MULTI_ARTICLE_ENTITIES", "1"
        ).strip().lower() not in {"0", "false", "no", "off"}


config = GraphRAGConfig()
