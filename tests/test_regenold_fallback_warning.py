"""Degraded-mode competition-wire schema regression guards.

When Stage-2 LLM synthesis (Claude Max via the Cloudflare tunnel) is
attempted but the wrapper call fails — tunnel down, Claude Max auth
expired, 429 exhaustion, network error, or structural truncation — the
engine ships the deterministic Stage-1 answer and sets
``graph_stats["stage2_call_failed"] = True`` (see
``app/engines/graph_rag.py`` ~line 6427).

The competition contract always has exactly ``reasoning``, ``answer`` and
``references``. Degradation stays observable in server logs/opt-in telemetry,
never through a fourth default-wire key.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.config import settings
from app.main import app
from app.models import CitationNode, GraphRAGResponse


def _client() -> TestClient:
    return TestClient(app)


def _messages(content: str) -> list[dict[str, str]]:
    return [{"role": "user", "content": content}]


def _headers() -> dict[str, str]:
    return {"X-Regenold-Api-Key": "regenold-test-key"}


@pytest.fixture(autouse=True)
def _configure_key_and_clear_cache():
    """Valid partner key + a clean engine LRU between tests.

    The route's ``_ENGINE_CACHE`` keys on ``(question, system_context, …)``;
    clearing it keeps a mocked engine return value from being masked by a
    prior test's cached blob under the same key.
    """
    settings.regenold.api_key = SecretStr("regenold-test-key")
    from app.routes.regenold import _ENGINE_CACHE  # noqa: PLC0415

    with _ENGINE_CACHE._lock:  # type: ignore[attr-defined]
        _ENGINE_CACHE._data.clear()  # type: ignore[attr-defined]
    yield


def _cited_response(
    *, stage2_call_failed: bool, answer: str | None = None
) -> GraphRAGResponse:
    """A healthy, cited answer — optionally flagged as a Stage-2 fallback.

    ``stage2_call_failed=True`` mimics the exact engine state after the
    wrapper call fails and the deterministic Stage-1 answer is shipped.
    ``stage2_call_failed=False`` (with ``stage2_landed=True``) mimics a
    normal, fully-polished answer.
    """
    return GraphRAGResponse(
        answer=answer or (
            "Article 13 requires high-risk AI providers to design "
            "transparency mechanisms so deployers can interpret outputs."
        ),
        citations=[
            CitationNode(
                node_type="Article",
                node_id="art-13",
                text="Transparency obligations.",
                article_ref="Art. 13",
            ),
        ],
        confidence=0.7,
        graph_stats={
            "nodes_traversed": 2,
            "stage2_call_failed": stage2_call_failed,
            "stage2_landed": not stage2_call_failed,
        },
    )


class TestFallbackSchemaWire:
    """Healthy and degraded answers have the same exact default schema."""

    def test_fallback_has_exact_three_field_schema(self) -> None:
        resp = _cited_response(stage2_call_failed=True)
        with patch(
            "app.routes.regenold.ask_compliance_question", return_value=resp
        ):
            r = _client().post(
                "/api/v1/regenold/eu-ai-act/ask",
                headers=_headers(),
                json=_messages("What does Article 13 require?"),
            )
        assert r.status_code == 200, r.json()
        body = r.json()
        assert set(body) == {"reasoning", "answer", "references"}
        assert isinstance(body["reasoning"], str)
        assert body["answer"], "answer must survive the fallback"
        assert body["references"], "references must survive the fallback"

    def test_no_warning_key_on_healthy_response(self) -> None:
        """The happy path must be byte-identical: NO ``warning`` key."""
        resp = _cited_response(stage2_call_failed=False)
        with patch(
            "app.routes.regenold.ask_compliance_question", return_value=resp
        ):
            r = _client().post(
                "/api/v1/regenold/eu-ai-act/ask",
                headers=_headers(),
                json=_messages("What does Article 13 require?"),
            )
        assert r.status_code == 200, r.json()
        body = r.json()
        assert set(body) == {"reasoning", "answer", "references"}

    def test_fallback_telemetry_does_not_add_warning(self) -> None:
        resp = _cited_response(stage2_call_failed=True)
        with patch(
            "app.routes.regenold.ask_compliance_question", return_value=resp
        ):
            r = _client().post(
                "/api/v1/regenold/eu-ai-act/ask?include_telemetry=true",
                headers=_headers(),
                json=_messages("What does Article 13 require?"),
            )
        assert r.status_code == 200, r.json()
        body = r.json()
        assert "warning" not in body
        assert "confidence" in body, "telemetry block must still be present"

    def test_landed_stage2_answer_is_uncapped_by_default(self) -> None:
        """R327 — ``REGENOLD_ANSWER_NO_CAP`` is default ON, per hard rule #2.

        An uncommitted pass flipped ``REGENOLD_ANSWER_NO_CAP`` to ``0`` and
        ``REGENOLD_STAGE2_CONCISENESS_BACKSTOP`` to ``1``, then pinned a
        four-sentence ceiling here. Turning the uncap off re-enables the soft CHAR
        cap as well as the sentence cap, and hard rule #2 is explicit: "Any cap
        must be SENTENCE-only: the char cap deletes verdict-first leads."
        Answer-Conciseness is also the ONE rubric axis we lead (zero headroom), so
        a live length change needs ``ab_judge`` first.

        A cap remains reachable via ``REGENOLD_MAX_ANSWER_SENTENCES`` — see below.
        """
        from app.integrations.regenold.models import _split_sentences

        long_answer = " ".join(
            f"Article 13 requirement {i} remains applicable."
            for i in range(1, 8)
        )
        resp = _cited_response(stage2_call_failed=False, answer=long_answer)
        with patch(
            "app.routes.regenold.ask_compliance_question", return_value=resp
        ):
            r = _client().post(
                "/api/v1/regenold/eu-ai-act/ask",
                headers=_headers(),
                json=_messages("Explain the ordinary Article 13 duty."),
            )
        assert r.status_code == 200, r.json()
        answer = r.json()["answer"]
        assert len(_split_sentences(answer)) > 4, (
            f"the uncap must be ON by default; got {answer!r}"
        )
        assert answer.rstrip().endswith((".", "!", "?")), answer

    def test_sentence_only_cap_remains_available(
        self, monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """A SENTENCE-only bound is the hard-rule-#2-compliant way to shorten."""
        from app.integrations.regenold.models import _split_sentences

        monkeypatch.setenv("REGENOLD_MAX_ANSWER_SENTENCES", "4")
        long_answer = " ".join(
            f"Article 13 requirement {i} remains applicable."
            for i in range(1, 8)
        )
        resp = _cited_response(stage2_call_failed=False, answer=long_answer)
        with patch(
            "app.routes.regenold.ask_compliance_question", return_value=resp
        ):
            r = _client().post(
                "/api/v1/regenold/eu-ai-act/ask",
                headers=_headers(),
                json=_messages("Explain the ordinary Article 13 duty."),
            )
        assert r.status_code == 200, r.json()
        answer = r.json()["answer"]
        assert len(_split_sentences(answer)) <= 4, answer
        assert answer.rstrip().endswith((".", "!", "?")), answer


class TestCompetitionResponseModel:
    """Pydantic-level schema is strict and reasoning is always a string."""

    def test_default_model_has_exact_three_fields(self) -> None:
        from app.integrations.regenold.models import RegenoldAskResponse

        out = RegenoldAskResponse(answer="x", references=["Article 13"])
        dumped = out.model_dump(exclude_none=True)
        assert dumped == {
            "answer": "x",
            "references": ["Article 13"],
            "reasoning": "",
        }

    def test_unknown_warning_field_is_rejected(self) -> None:
        from app.integrations.regenold.models import RegenoldAskResponse
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            RegenoldAskResponse(answer="x", warning="degraded")
