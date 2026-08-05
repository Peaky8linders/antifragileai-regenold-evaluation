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
        # R290 — default corrected "0" -> "1". R110.1 baked the
        # Sufficient-Context gate ON as the CODE default (Railway dashboard
        # variables override railway.toml, so the toml entry alone was not
        # reaching production); ``sufficient_context.sufficient_context_enabled()``
        # returns True when unset. Verified empirically.
        return env_enabled("REGENOLD_SUFFICIENT_CONTEXT", "1")

    @property
    def stage2_provider_enabled(self) -> bool:
        # R290 — delegate to the LIVE multi-branch provider gate. This is NOT
        # a simple boolean env: it keys off P2P_GRAPH_RAG_PROVIDER plus
        # whether a key/wrapper is wired (cli->False, groq->groq_enabled,
        # gemini->gemini_enabled, anthropic->api_key present, auto->wrapper).
        from app.engines._graph_rag_impl import _stage2_provider_enabled

        return _stage2_provider_enabled()

    @property
    def stage2_polish_enabled(self) -> bool:
        # R290 — canonical env name is P2P_GRAPH_RAG_ENABLE_STAGE2.
        # This is the master ON/OFF switch (distinct from stage2_provider_enabled
        # which checks whether a provider is actually wired).
        return env_enabled("P2P_GRAPH_RAG_ENABLE_STAGE2", "1")

    @property
    def stage2_simple_skip_enabled(self) -> bool:
        # R290 — canonical env name is REGENOLD_STAGE2_SIMPLE_SKIP. Must stay
        # default OFF: R129 measured the simple-skip regressing refs 0.75 -> 0.47.
        return env_enabled("REGENOLD_STAGE2_SIMPLE_SKIP", "0")

    @property
    def answer_v2_enabled(self) -> bool:
        return env_enabled("REGENOLD_GRAPH_RAG_V2", "1")

    @property
    def verify_verdict_enabled(self) -> bool:
        # R290 — default "0". R285 explicitly REVERTED this flag to 0: it was
        # flipped on with no A/B, which its own docstring forbids. Leaving the
        # default at "1" here would silently re-apply the exact change R285
        # reverted the moment anything reads this config.
        return env_enabled("REGENOLD_VERIFY_VERDICT", "0")

    @property
    def lower_risk_verdicts_enabled(self) -> bool:
        return env_enabled("REGENOLD_LOWER_RISK_VERDICTS", "1")

    @property
    def multi_article_entities_enabled(self) -> bool:
        return env_enabled("REGENOLD_MULTI_ARTICLE_ENTITIES", "1")


config = GraphRAGConfig()
