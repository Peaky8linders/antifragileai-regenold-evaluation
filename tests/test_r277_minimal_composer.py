"""R277 arm C — the minimal-composer Stage-2 prompt variant.

Env ``REGENOLD_MINIMAL_COMPOSER`` (default OFF → the accreted
``ANSWER_GENERATE_SYSTEM``; ``=1`` → ``MINIMAL_COMPOSER_SYSTEM``). These
tests pin: the default is byte-identical; the resolver reads the env fresh
per call (ab_judge two-arm validity); and the minimal prompt carries every
load-bearing wire-contract invariant (citation form, third-person voice,
verdict-first, Digital-Omnibus exclusion, closed-set completeness, no
em-dashes/ellipses modelled in the prompt itself — the R108 lesson).

⚠ R340 made ``ANSWER_GENERATE_SYSTEM_V2`` the DEFAULT composition
(``_prompt_v2_enabled()``, env ``REGENOLD_PROMPT_V2``, default ``"1"``), and
``resolve_answer_system()`` consults it FIRST — before ``REGENOLD_MINIMAL_COMPOSER``
— so the V2 arm is unambiguous. The R277 composer branch is therefore reached
only on the V1 path, which ``REGENOLD_PROMPT_V2=0`` selects and which R340 kept
byte-identical. ``TestResolver`` pins that V1 branch explicitly; ``TestV2Default``
pins the new default beside it. Do NOT "fix" these back by deleting the pin.
"""
from __future__ import annotations

import pytest

from app.data.graph_rag_prompts import (
    ANSWER_GENERATE_SYSTEM,
    ANSWER_GENERATE_SYSTEM_V2,
    MINIMAL_COMPOSER_SYSTEM,
    resolve_answer_system,
)


class TestResolver:
    """The R277 arm-C branch, which lives on the V1 composition only."""

    @pytest.fixture(autouse=True)
    def _pin_v1_composition(self, monkeypatch):
        # R340 — V2 is the default and is checked FIRST in resolve_answer_system(),
        # so REGENOLD_MINIMAL_COMPOSER is only observable on the V1 path.
        # `=0` is R340's documented rollback and returns the V1 composition
        # byte-identical, which is exactly the prompt these cases were written for.
        monkeypatch.setenv("REGENOLD_PROMPT_V2", "0")

    def test_default_is_full_prompt(self, monkeypatch):
        """V1 path, composer unset ⇒ the accreted prompt, byte-identical."""
        monkeypatch.delenv("REGENOLD_MINIMAL_COMPOSER", raising=False)
        assert resolve_answer_system() == ANSWER_GENERATE_SYSTEM

    def test_off_values(self, monkeypatch):
        """V1 path (REGENOLD_PROMPT_V2=0, see the class fixture)."""
        for v in ("0", "false", "no", "off", ""):
            monkeypatch.setenv("REGENOLD_MINIMAL_COMPOSER", v)
            assert resolve_answer_system() == ANSWER_GENERATE_SYSTEM

    def test_on_values(self, monkeypatch):
        """V1 path (REGENOLD_PROMPT_V2=0, see the class fixture)."""
        for v in ("1", "true", "YES", " on "):
            monkeypatch.setenv("REGENOLD_MINIMAL_COMPOSER", v)
            assert resolve_answer_system() == MINIMAL_COMPOSER_SYSTEM

    def test_fresh_read_per_call(self, monkeypatch):
        """ab_judge arm-toggling validity: no import-time caching.

        V1 path (REGENOLD_PROMPT_V2=0, see the class fixture). The R340 selector
        is checked for the same property in ``TestV2Default`` below.
        """
        monkeypatch.setenv("REGENOLD_MINIMAL_COMPOSER", "0")
        assert resolve_answer_system() == ANSWER_GENERATE_SYSTEM
        monkeypatch.setenv("REGENOLD_MINIMAL_COMPOSER", "1")
        assert resolve_answer_system() == MINIMAL_COMPOSER_SYSTEM


class TestV2Default:
    """R340 — the shipped default is the rebuilt prompt, and it wins outright.

    ``resolve_answer_system()`` checks ``_prompt_v2_enabled()`` before either
    R277/R281 flag, so on the default path neither flag can change the prompt.
    That is deliberate: it keeps the V1↔V2 A/B arms unambiguous.
    """

    def test_default_is_the_rebuilt_prompt(self, monkeypatch):
        monkeypatch.delenv("REGENOLD_PROMPT_V2", raising=False)
        monkeypatch.delenv("REGENOLD_MINIMAL_COMPOSER", raising=False)
        assert resolve_answer_system() == ANSWER_GENERATE_SYSTEM_V2

    def test_v2_outranks_the_minimal_composer_flag(self, monkeypatch):
        monkeypatch.setenv("REGENOLD_PROMPT_V2", "1")
        monkeypatch.setenv("REGENOLD_MINIMAL_COMPOSER", "1")
        assert resolve_answer_system() == ANSWER_GENERATE_SYSTEM_V2

    def test_v2_selector_is_read_fresh_per_call(self, monkeypatch):
        """Same R263.2 doctrine as the V1 flags: the V1↔V2 A/B toggles this
        between arms in one process, so an import-time read would make both
        arms identical."""
        monkeypatch.delenv("REGENOLD_MINIMAL_COMPOSER", raising=False)
        monkeypatch.setenv("REGENOLD_PROMPT_V2", "1")
        assert resolve_answer_system() == ANSWER_GENERATE_SYSTEM_V2
        monkeypatch.setenv("REGENOLD_PROMPT_V2", "0")
        assert resolve_answer_system() == ANSWER_GENERATE_SYSTEM
        monkeypatch.setenv("REGENOLD_PROMPT_V2", "1")
        assert resolve_answer_system() == ANSWER_GENERATE_SYSTEM_V2


class TestMinimalPromptInvariants:
    def test_materially_smaller(self):
        # The whole point: the composer is a whole-prompt REPLACEMENT that is a
        # small fraction of an accreted prompt (3,181 chars vs V1's 51,516).
        #
        # ⚠ R340 RE-BASED THIS FROM A RATIO TO AN ABSOLUTE CEILING. The old form
        # `< len(ANSWER_GENERATE_SYSTEM) / 8` silently asserted that the ANSWER
        # prompt stays ABOVE 25,448 chars, so it graded the wrong artefact: it
        # would read a shrinking system prompt as a regression, and the only way
        # to satisfy it would be to pad the prompt back up — reinstating exactly
        # the bloat the R340 rebuild removed (V2 is 16,146 chars). An absolute
        # bound states what this test actually means and holds against BOTH
        # compositions, which is why both are asserted below.
        assert len(MINIMAL_COMPOSER_SYSTEM) < 8_000
        assert len(MINIMAL_COMPOSER_SYSTEM) < len(ANSWER_GENERATE_SYSTEM)
        assert len(MINIMAL_COMPOSER_SYSTEM) < len(ANSWER_GENERATE_SYSTEM_V2)

    def test_wire_citation_format(self):
        for token in ('"Article 13"', '"Annex III"'):
            assert token in MINIMAL_COMPOSER_SYSTEM

    def test_third_person_voice(self):
        assert "third person" in MINIMAL_COMPOSER_SYSTEM

    def test_verdict_first(self):
        flat = " ".join(MINIMAL_COMPOSER_SYSTEM.split())
        assert "direct answer" in flat
        assert "first clause" in flat

    def test_omnibus_exclusion(self):
        # Benchmark cutoff: state of affairs at 1 May 2026; the Digital
        # Omnibus political agreement (7 May 2026) is out of scope.
        assert "Digital Omnibus" in MINIMAL_COMPOSER_SYSTEM
        assert "1 May 2026" in MINIMAL_COMPOSER_SYSTEM

    def test_closed_set_completeness(self):
        assert "every member" in MINIMAL_COMPOSER_SYSTEM

    def test_does_not_model_forbidden_punctuation(self):
        # R108: the prompt must not MODEL the punctuation the wire forbids.
        assert "—" not in MINIMAL_COMPOSER_SYSTEM  # em-dash
        assert "–" not in MINIMAL_COMPOSER_SYSTEM  # en-dash
        assert "…" not in MINIMAL_COMPOSER_SYSTEM  # ellipsis
        assert "..." not in MINIMAL_COMPOSER_SYSTEM

    def test_grounding_softened_not_removed(self):
        # Prefer supplied references, allow certain Act knowledge, keep the
        # citation-certainty bar (the anti-hallucination floor).
        assert "EU AI ACT REFERENCES" in MINIMAL_COMPOSER_SYSTEM
        assert "certain" in MINIMAL_COMPOSER_SYSTEM

    def test_good_only_exemplars(self):
        # GOOD-only examples (contrastive BAD examples model the forbidden
        # style and were dropped by design).
        assert "EXAMPLES:" in MINIMAL_COMPOSER_SYSTEM
        assert "BAD" not in MINIMAL_COMPOSER_SYSTEM


class TestCacheKey:
    def test_flag_in_engine_cache_key(self, monkeypatch):
        """R263.2 doctrine — the flag flips the engine answer, so the two
        ab_judge arms must produce distinct engine-cache keys."""
        from app.routes.regenold import _engine_cache_key

        monkeypatch.setenv("REGENOLD_MINIMAL_COMPOSER", "0")
        k_off = _engine_cache_key("q", None)
        monkeypatch.setenv("REGENOLD_MINIMAL_COMPOSER", "1")
        k_on = _engine_cache_key("q", None)
        assert k_off != k_on
