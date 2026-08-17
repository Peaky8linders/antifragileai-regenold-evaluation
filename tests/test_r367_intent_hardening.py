"""R367 — intent-detection hardening tests.

Pins the four optimisations shipped in R367 (operator review of the
intent layer against proven hybrid-RAG routing practice):

1. **Dead bridging key fixed** — ``BRIDGING_NODES`` previously keyed on
   ``high_risk_annex_i`` which is NOT an intent label, so an
   ``annex_harmonisation_law`` (Annex I) intent never seeded the
   MDR/Machinery cross-framework context. The key now matches the real
   label.
2. **Cache key is prompt-versioned** — a prompt edit invalidates cached
   intents instead of serving stale label distributions.
3. **Intent provider chain is Groq → Gemini → Mistral → wrapper** —
   the operator directive keeps the intent providers ON; the chain is
   wired so a Groq outage degrades to Gemini/Mistral before the wrapper.
4. **Prompt calibration matches the engine gates** — the classifier is
   told the real 0.7 (narrow) / 0.85 (promote) thresholds and to keep
   ``reasoning`` short so the 250-token JSON never truncates.

All tests are pure-stdlib / no-network.
"""

from __future__ import annotations

import hashlib

from app.llm import intent_classifier as ic


class TestBridgingNodes:
    def test_annex_harmonisation_law_bridges_sectoral_law(self) -> None:
        """Annex-I intent must seed the MDR/Machinery cross-framework context."""
        assert "annex_harmonisation_law" in ic.BRIDGING_NODES
        nodes = ic.BRIDGING_NODES["annex_harmonisation_law"]
        assert any("MDR" in n or "Medical Device" in n for n in nodes)
        assert any("Machinery" in n for n in nodes)

    def test_every_bridging_key_is_a_real_intent_label(self) -> None:
        """No dead keys: every bridging entry must be emittable by the taxonomy."""
        labels = set(ic.INTENT_LABELS)
        for key in ic.BRIDGING_NODES:
            assert key in labels, (
                f"BRIDGING_NODES key {key!r} is not an intent label — "
                "the bridging context can never fire"
            )

    def test_old_dead_key_removed(self) -> None:
        assert "high_risk_annex_i" not in ic.BRIDGING_NODES


class TestCacheKeyPromptVersioning:
    def test_cache_key_embeds_prompt_hash(self) -> None:
        k = ic._cache_key("What is Art. 13?", "test-model")
        assert len(k) == 64
        # The prompt hash must be part of the input (deterministic check:
        # keying on the hash means a prompt change yields a different key).
        assert ic._prompt_hash()  # non-empty
        assert k != hashlib.sha256(b"test-model\x00what is art. 13?").hexdigest()

    def test_prompt_change_invalidates_cache(self, monkeypatch) -> None:
        """A prompt edit must produce a different cache key for the same Q+model."""
        before = ic._cache_key("Is a chatbot high-risk?", "m")
        # Simulate a prompt change by altering the module prompt and clearing
        # the lazy hash.
        old_prompt = ic._SYSTEM_PROMPT
        ic._SYSTEM_PROMPT = old_prompt + "\nR367 test append."
        ic._PROMPT_HASH = None
        try:
            after = ic._cache_key("Is a chatbot high-risk?", "m")
            assert before != after
        finally:
            ic._SYSTEM_PROMPT = old_prompt
            ic._PROMPT_HASH = None


class TestProviderChain:
    def test_chain_includes_gemini_and_mistral(self) -> None:
        """The intent chain must contain Gemini + Mistral tiers (directive)."""
        import inspect

        src = inspect.getsource(ic._resolve_intent_provider)
        assert "is_gemini_provider_enabled" in src
        assert "is_mistral_provider_enabled" in src
        assert "get_gemini_provider" in src
        assert "get_mistral_provider" in src
        # Order: Groq first, then Gemini, then Mistral, wrapper last.
        assert src.index("is_groq_intent_provider_enabled") < src.index("is_gemini_provider_enabled") < src.index(
            "is_mistral_provider_enabled"
        ) < src.index("is_openai_wrapper_enabled")

    def test_chain_fallback_walks_all_tiers(self, monkeypatch) -> None:
        """classify_intent must iterate the whole chain on failure."""
        import inspect

        src = inspect.getsource(ic.classify_intent)
        assert "_intent_chain" in src
        # The old Groq→wrapper-only hop is gone.
        assert "falling back to Sonnet" not in src


class TestPromptCalibration:
    def test_prompt_documents_engine_gates(self) -> None:
        assert "0.7" in ic._SYSTEM_PROMPT
        assert "0.85" in ic._SYSTEM_PROMPT
        assert "single most-load-bearing article" in ic._SYSTEM_PROMPT

    def test_prompt_caps_reasoning_length(self) -> None:
        assert "one short sentence" in ic._SYSTEM_PROMPT
        assert "20 words" in ic._SYSTEM_PROMPT
