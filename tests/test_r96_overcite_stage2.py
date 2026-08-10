"""R96 regression tests.

Two fixes derived from the r95-live representative-100 + LLM-judge run
(production = verbatim R94 + R95-P0/P1, never previously live-judged
together):

* **Fix #1 (R97 superseded)** — R96 short-circuited
  ``_stage2_polish_enabled`` OFF whenever verbatim was on. R97 decoupled
  that: the gate is now pure ``P2P_GRAPH_RAG_ENABLE_STAGE2`` and the
  verbatim-vs-synthesis decision moved into the answer router (see
  ``tests/test_r97_answer_router.py``). The tests below now pin the R97
  contract: ``_stage2_polish_enabled`` ignores verbatim.

* **Fix #2** — the historical HRAIS-listing ref-budget lift no longer
  fires on multi-turn finals. r95-live showed limited-risk multi-turn
  systems (rule-based advisor, usage-prediction tool) getting the full
  22-article high-risk chain dumped on small-gold rows (mt_042 pred=22
  gold=3), tanking the refs-precision axis. Ordinary scenarios now use five;
  explicit single-turn exhaustive lists have a bounded 12-reference exception.
"""
from __future__ import annotations

import json

from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.config import settings
from app.engines.graph_rag import _stage2_polish_enabled
from app.main import app


# ─── Fix #1 (R97 contract) — gate decoupled from verbatim ────────────────────


class TestStage2VerbatimShortCircuit:
    """R97 — ``_stage2_polish_enabled`` is now the pure master env gate
    (``P2P_GRAPH_RAG_ENABLE_STAGE2``); the verbatim coupling moved to the
    answer router. These tests pin the decoupling so a future revert to the
    R96 verbatim short-circuit is loud."""

    def test_verbatim_on_does_not_disable_master_gate(self, monkeypatch) -> None:
        """R97: verbatim ON no longer forces the gate OFF — the router
        decides per-request. Master ON → gate ON regardless of verbatim."""
        monkeypatch.setenv("REGENOLD_VERBATIM_ANSWER", "1")
        monkeypatch.setenv("P2P_GRAPH_RAG_ENABLE_STAGE2", "1")
        assert _stage2_polish_enabled() is True

    def test_verbatim_default_on_does_not_disable_master_gate(self, monkeypatch) -> None:
        """Unset verbatim (defaults ON) → gate still ON when master ON."""
        monkeypatch.delenv("REGENOLD_VERBATIM_ANSWER", raising=False)
        monkeypatch.setenv("P2P_GRAPH_RAG_ENABLE_STAGE2", "1")
        assert _stage2_polish_enabled() is True

    def test_verbatim_off_master_on(self, monkeypatch) -> None:
        """Verbatim OFF + master ON → gate ON (unchanged)."""
        monkeypatch.setenv("REGENOLD_VERBATIM_ANSWER", "0")
        monkeypatch.setenv("P2P_GRAPH_RAG_ENABLE_STAGE2", "1")
        assert _stage2_polish_enabled() is True

    def test_master_off_stays_off(self, monkeypatch) -> None:
        """Master OFF → gate OFF regardless of verbatim (no resurrection)."""
        monkeypatch.setenv("REGENOLD_VERBATIM_ANSWER", "1")
        monkeypatch.setenv("P2P_GRAPH_RAG_ENABLE_STAGE2", "0")
        assert _stage2_polish_enabled() is False
        monkeypatch.setenv("REGENOLD_VERBATIM_ANSWER", "0")
        assert _stage2_polish_enabled() is False


# ─── Fix #2 — HRAIS-listing 22-lift gated off for multi-turn ──────────────────


def _client() -> TestClient:
    return TestClient(app)


_MT_HRAIS_LISTING = [
    {
        "role": "user",
        "content": (
            "We are a provider offering a CV-screening AI used to rank job "
            "applicants for recruitment — a high-risk AI system under Annex III."
        ),
    },
    {
        "role": "assistant",
        "content": (
            "This system is high-risk under Annex III point 4. Article 6 "
            "governs the classification and the Chapter III obligations apply."
        ),
    },
    {
        "role": "user",
        "content": "Which articles set out all the obligations that apply to us?",
    },
]


def _notes_from_reasoning(body: dict) -> list[str]:
    raw = body.get("reasoning")
    if not raw or not isinstance(raw, str):
        return []
    try:
        return list(json.loads(raw).get("notes") or [])
    except Exception:
        return []


class TestHraisListingMultiturnBudget:
    def test_multiturn_hrais_listing_does_not_lift_to_22(self, monkeypatch) -> None:
        """A multi-turn final must not take the 22-ref listing lift.

        R327 — the assertion is that the LIFT does not fire (R87-B/P3: the
        multi-turn final is a summary, so the 22-lift bulk-dumped the chain). The
        surviving budget is the ordinary SCENARIO budget of 10, not 5: an
        uncommitted pass collapsed every scenario budget to ``MAX_REFERENCES``,
        which is the top-N clamp family CLAUDE.md records as destroying 421 gold
        on scenarios (davidath scenario gold averages 9.88 refs/row).
        """
        monkeypatch.setenv("REGENOLD_HRAIS_LISTING_BUDGET", "1")
        settings.regenold.api_key = SecretStr("regenold-test-key")
        c = _client()
        r = c.post(
            "/api/v1/regenold/eu-ai-act/ask?include_reasoning=true",
            headers={"X-Regenold-Api-Key": "regenold-test-key"},
            json=_MT_HRAIS_LISTING,
        )
        assert r.status_code == 200, r.json()
        body = r.json()
        notes = _notes_from_reasoning(body)
        assert not any("hrais_listing_budget_lift" in n for n in notes), (
            f"22-lift must not fire on multi-turn; notes={notes}"
        )
        assert len(body.get("references") or []) <= 10, body.get("references")

    def test_single_turn_explicit_listing_has_bounded_exception(
        self, monkeypatch
    ) -> None:
        monkeypatch.setenv("REGENOLD_HRAIS_LISTING_BUDGET", "1")
        settings.regenold.api_key = SecretStr("regenold-test-key")
        r = _client().post(
            "/api/v1/regenold/eu-ai-act/ask?include_reasoning=true",
            headers={"X-Regenold-Api-Key": "regenold-test-key"},
            json=[{
                "role": "user",
                "content": (
                    "We are a provider of a high-risk CV-screening AI under "
                    "Annex III. List every article that sets out all applicable "
                    "obligations."
                ),
            }],
        )
        assert r.status_code == 200, r.json()
        body = r.json()
        notes = _notes_from_reasoning(body)
        # R327 — the measured R87-B/P1 lift target is 22 (r86-live-postship: every
        # multi-turn HRAIS row was hitting the 10-ref cap against gold carrying
        # the full obligation chain). The 12-ref ceiling is available as an
        # opt-in via REGENOLD_MINIMAL_REF_BUDGET — see the test below.
        assert any("hrais_listing_budget_lift=10->22" in n for n in notes), notes
        assert len(body.get("references") or []) <= 22, body.get("references")

    def test_minimal_ref_budget_opt_in_bounds_the_listing_exception(
        self, monkeypatch
    ) -> None:
        """``REGENOLD_MINIMAL_REF_BUDGET=1`` bounds the lift to 12.

        The tighter budget stays reachable so ``evals.harness.easyhard_ab`` can
        A/B it OFF<->ON and report ``gold_dropped`` (hard rule #8) before anyone
        considers making it the default.
        """
        monkeypatch.setenv("REGENOLD_HRAIS_LISTING_BUDGET", "1")
        monkeypatch.setenv("REGENOLD_MINIMAL_REF_BUDGET", "1")
        settings.regenold.api_key = SecretStr("regenold-test-key")
        r = _client().post(
            "/api/v1/regenold/eu-ai-act/ask?include_reasoning=true",
            headers={"X-Regenold-Api-Key": "regenold-test-key"},
            json=[{
                "role": "user",
                "content": (
                    "We are a provider of a high-risk CV-screening AI under "
                    "Annex III. List every article that sets out all applicable "
                    "obligations."
                ),
            }],
        )
        assert r.status_code == 200, r.json()
        body = r.json()
        notes = _notes_from_reasoning(body)
        assert any("hrais_listing_budget_lift=5->12" in n for n in notes), notes
        assert len(body.get("references") or []) <= 12, body.get("references")
