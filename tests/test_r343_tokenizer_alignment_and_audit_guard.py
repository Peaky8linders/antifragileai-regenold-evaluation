"""R343 — canonical dense-lane tokenizer + audit-write None guard.

Two review suggestions fixed together:

**S1 — tokenizer divergence.** The SVD assets are built with the canonical
``kb_search._tokenize`` (``scripts/build_embeddings_index.py``), but the
runtime query tokeniser was a VENDORED copy that had drifted: the digit rule
(build keeps only 4-digit numbers like ``2025``; the vendored copy kept 1-3
digit numbers that NEVER exist in the index vocab) AND the stopword set
(vendored lacked ``doing/done/into/onto/without``, had ``if``). Query-time
tokenisation now IS the canonical function — vocab alignment by construction.

**S7 — audit-write silent loss.** ``_build_scope_refusal_response`` and the
in-scope audit write sliced ``scope.verdict.evidence[:200]`` unguarded; a
``None`` evidence (alternate verdict construction paths) raised TypeError
INSIDE the broad except and silently dropped the WHOLE audit record — a
regulatory-trail integrity hole. Both sites now guard with
``(evidence or "")[:200]``.
"""

from __future__ import annotations

from unittest.mock import Mock

from app.data.kb_search import _tokenize as _kb_tokenize
from app.engines import embeddings_index as E
from app.evidence.store import EvidenceEntryType, get_evidence_store
from app.integrations.regenold.scope import (
    ConversationVerdict,
    ScopeReason,
    ScopeVerdict,
)
from app.routes.regenold import _build_scope_refusal_response

# ─── S1: canonical tokenizer ────────────────────────────────────────────────


def test_query_tokenizer_is_the_canonical_build_tokenizer():
    """The assets are built with ``kb_search._tokenize``; query-time MUST be
    the same function object — a vendored copy is how the drift happened."""
    assert E._tokenize is _kb_tokenize


def test_digit_tokens_align_with_index_vocab():
    """The vendored copy emitted 1-3 digit tokens (``10``) that never exist
    in the index vocab; the canonical rule keeps only 4-digit years, which is
    exactly what the build put in the vocab."""
    assert _kb_tokenize("Art. 10 and 2025 obligations") == ["2025"]
    assert E._tokenize("Art. 10 and 2025 obligations") == ["2025"]
    assert "10" not in E._tokenize("Article 10 technical documentation")
    assert "2026" in E._tokenize("the 2026 conformity review")
    # A 5-digit number is dropped on both sides — never a phantom token.
    assert "10000" not in E._tokenize("a fine of 10000 euro")


def test_stopwords_align_with_canonical():
    """The vendored stopword set differed (lacked doing/done/into/onto/
    without, had if) — token equality across a prose sample pins the shared
    set end-to-end."""
    sample = (
        "Providers doing post-market monitoring shall ensure that obligations "
        "into the review are without prejudice, done properly, onto the record."
    )
    assert E._tokenize(sample) == _kb_tokenize(sample)


# ─── S7: audit write survives None evidence ─────────────────────────────────


def _verdict_with_none_evidence() -> ConversationVerdict:
    return ConversationVerdict(
        verdict=ScopeVerdict(
            in_scope=False,
            reason=ScopeReason.EMPTY_OR_NONSENSE,
            evidence=None,  # the alternate-path None that killed the record
        ),
        anchor_articles=(),
        history_unknown_articles=(),
        live_question="What is the airspeed of an unladen swallow?",
    )


def test_refusal_audit_write_survives_none_evidence():
    """S7 — with ``evidence=None`` the audit record MUST still be written
    (pre-fix: TypeError inside the broad except dropped the whole record)."""
    from app.evidence.store import reset_evidence_store_for_tests  # noqa: PLC0415

    reset_evidence_store_for_tests()
    store = get_evidence_store()
    before = store.count()

    out = _build_scope_refusal_response(
        scope=_verdict_with_none_evidence(),
        include_telemetry=True,
        request=Mock(),
        api_key=None,
        question="What is the airspeed of an unladen swallow?",
        system_context=None,
        history_turns=[],
    )

    # The record landed.
    entries = list(store.get_chain(entry_type=EvidenceEntryType.regenold_question.value))
    assert len(entries) == before + 1
    payload = entries[0].payload
    assert payload["scope_evidence"] == ""  # the None was clamped, not fatal
    assert payload["scope_reason"] == ScopeReason.EMPTY_OR_NONSENSE.value
    assert out.answer  # the refusal itself is unaffected
