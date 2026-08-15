"""R329 — cross-encoder reranking of candidate provisions (Cohere Rerank).

WHY THIS EXISTS
===============

The live HARD measurement (``docs/R329-SCORECARD-VS-FRONTIER.md``, grounded
Sonnet-5 judge, n=40) put reference **precision at 0.653** against recall 0.879.
Every sampled failure was an EXTRA reference, never a missing one:

    "over-citation of inapplicable transparency and product-safety provisions"
    "over-cited log-retention provision (Art 19) not tied to competent-authority
     documentation"

That is not a count problem. Only 2 of 40 rows exceeded 5 references — the mean
was 3.30. The damage is ~1.1 WRONG references inside an otherwise reasonable
set, and no count clamp can fix it: a cut cannot know *which* of three refs is
wrong. It is a ranking problem, which is why the five refuted trimmer families
(``.planning/R318-PLAN.md`` §1) all failed — they attacked the count.

WHY A MANAGED RERANKER, AND WHY THIS ONE
========================================

``AGENTS.md`` forbids PyTorch / heavy neural models in the runtime path, and
Railway is CPU-only. That constraint killed every previous reranker attempt here
(R32 built, R46 deleted as bench-negative; ``bge-reranker-large`` is torch+GPU).
A hosted cross-encoder sidesteps it entirely — no local model, no new heavy
dependency, one bounded HTTP call.

AWS Bedrock hosts the same class of model and would have kept inference inside
``eu-central-1``. It is NOT used here for a measured reason: Bedrock's Rerank API
lives in ``bedrock-agent-runtime``, which requires SigV4 and rejects the
``AWS_BEARER_TOKEN_BEDROCK`` API-key this deployment holds::

    ClientError IncompleteSignatureException: Authorization header requires
    'Credential' / 'Signature' / 'SignedHeaders' parameters

Both ``amazon.rerank-v1:0`` and ``cohere.rerank-v3-5:0`` ARE available in
``eu-central-1`` (verified; ``eu-west-1`` has neither), so the Bedrock path
becomes preferable the moment IAM credentials with ``bedrock:Rerank`` exist.
See ``.planning/R329-PLAN-RANKER-AND-OVERCITATION.md`` §2.3.

⚠ **Data-protection note.** This module sends the user's question and verbatim
EU AI Act provision text to Cohere. The Act text is public law; the question is
partner input. For an EU AI Act compliance product that is a residency decision
the operator must make deliberately — which is why this ships **default OFF**
and why the Bedrock path is the preferred destination.

DESIGN — REORDER ONLY, NEVER DROP
=================================

:func:`rerank_references` returns a PERMUTATION of its input. It never removes,
never adds, never rewrites a reference. That is deliberate and load-bearing:
R142.1 lost a live pairwise 11-0 (refs p=0.001) by dropping a gold reference.

The cut stays with the already-validated R281 ``adaptive_ref_clamp``
(``app/routes/regenold.py:4416``), which trims from the TAIL against a
per-question budget and measured +1.17pp with its own gold guard. This module
supplies the ORDER; that pass supplies the CUT. Composed, a wrong reference is
moved to the tail and then removed by a mechanism that already has a gold-drop
guard — neither half is a new trimmer family.

Fail-soft everywhere: any error, timeout, missing key or malformed response
returns the input order UNCHANGED. A reranker outage must never alter the
reference set.
"""
from __future__ import annotations

import logging
import os
import threading
from collections.abc import Sequence
from typing import Any

import httpx

logger = logging.getLogger(__name__)

__all__ = [
    "rerank_enabled",
    "rerank_documents",
    "rerank_pool",
    "rerank_references",
    "rerank_query_context",
    "build_kg_candidate_pool",
    "rerank_stats",
    "reset_rerank_stats",
]

#: R347 — hybrid-RAG candidate supplementation: the parse-level rerank may
#: rank the keyword entities TOGETHER with their 1-hop CROSS_REFERENCES
#: neighbours from the KG taxonomy (see :func:`build_kg_candidate_pool`), so
#: a genuinely cross-referenced provision can be promoted ahead of a keyword
#: hit. DEFAULT OFF — the A/B decides; the R340 permutation-only contract is
#: the baseline behaviour.
_RERANK_KG_ENV = "REGENOLD_RERANK_KG_CANDIDATES"


def rerank_kg_candidates_enabled() -> bool:
    """``REGENOLD_RERANK_KG_CANDIDATES`` — **DEFAULT OFF**, fresh read per call.

    Only meaningful when ``REGENOLD_COHERE_RERANK=1``: the KG expansion is
    applied to the pool the cross-encoder ranks, never to a gate-off parse.
    """
    return (
        os.getenv(_RERANK_KG_ENV, "0").strip().lower()
        in _TRUTHY
    )

COHERE_RERANK_URL = "https://api.cohere.com/v2/rerank"

_ENV_GATE = "REGENOLD_COHERE_RERANK"
_ENV_MODEL = "REGENOLD_COHERE_RERANK_MODEL"
_DEFAULT_MODEL = "rerank-v3.5"
_TRUTHY = frozenset({"1", "true", "yes", "on"})

#: Latency is a SCORED axis (Speed, 61.7% — our second-worst) and live p50 is
#: already ~57 s, so this call must be tightly bounded and must fail open.
_CLIENT_TIMEOUT = httpx.Timeout(6.0, connect=2.0)

_CLIENT_LOCK = threading.Lock()
_CLIENT: httpx.Client | None = None

# ── Call instrumentation (R331) ──────────────────────────────────────────────
#
# R329 tried three placements for this reranker. All three looked correct in
# the diff and all three made **ZERO calls**: two sat behind gates that never
# opened (``kb_search.top_articles_by_relevance`` is reached only when
# ``_deterministic_parse`` extracted no entities — see ``_graph_rag_impl.py``
# ``if not entities:`` at :2270), and the "budget cut" the third was routed
# through was already within budget. The A/B read +0.0000 on every axis, which
# is indistinguishable from "the lever does not work".
#
# Byte-identical output is what an INERT feature looks like. A number read off
# an unproven placement measures nothing, so every placement must assert
# ``rerank_stats()["attempts"] > 0`` before any A/B result is believed.
_STATS_LOCK = threading.Lock()
_STATS: dict[str, int] = {"attempts": 0, "reordered": 0, "failed": 0, "noop": 0}


def rerank_stats() -> dict[str, int]:
    """Snapshot of the call counters.

    ``attempts``  — network calls actually issued to Cohere.
    ``reordered`` — :func:`rerank_references` calls that CHANGED the order.
    ``failed``    — attempts that fell back to the input order.
    ``noop``      — attempts that returned the input order unchanged.

    ``attempts == 0`` means the feature never ran; treat any downstream metric
    as UNMEASURED, not as evidence of no effect.
    """
    with _STATS_LOCK:
        return dict(_STATS)


def reset_rerank_stats() -> None:
    """Zero the counters — per-arm reset for an A/B harness."""
    with _STATS_LOCK:
        for key in _STATS:
            _STATS[key] = 0


def _bump(field: str) -> None:
    with _STATS_LOCK:
        _STATS[field] = _STATS.get(field, 0) + 1


def _get_client() -> httpx.Client:
    """Module-level pooled client (R112 pattern — avoids per-call TLS setup)."""
    global _CLIENT
    client = _CLIENT
    if client is not None:
        return client
    with _CLIENT_LOCK:
        if _CLIENT is None:
            _CLIENT = httpx.Client(
                timeout=_CLIENT_TIMEOUT,
                limits=httpx.Limits(max_connections=4, max_keepalive_connections=2),
            )
        return _CLIENT


def rerank_enabled() -> bool:
    """``REGENOLD_COHERE_RERANK`` — **DEFAULT OFF**, fresh env read per call.

    Default OFF for three independent reasons, any one of which is sufficient:

    * it is unmeasured on this corpus (R325 measured that nothing beat the
      engine's own ``rank``, AUC 0.703 — though with a *lexical* reranker, not a
      cross-encoder, so this is a genuinely different arm);
    * it adds external egress of partner questions (see the module docstring);
    * this repo has just paid for an ungated default-ON retrieval change
      (R329 HyPA: Ref Conciseness −0.209).

    Fresh read per call (R263.2) so ``evals/harness/easyhard_ab.py`` can flip it
    between in-process arms.
    """
    if os.getenv(_ENV_GATE, "0").strip().lower() not in _TRUTHY:
        return False
    return bool(os.getenv("COHERE_API_KEY", "").strip())


def rerank_documents(
    query: str,
    documents: Sequence[str],
    *,
    top_n: int | None = None,
) -> list[tuple[int, float]] | None:
    """Return ``[(original_index, relevance_score), ...]`` best-first.

    Returns ``None`` on ANY failure so callers can keep their input order.
    Never raises.
    """
    if not rerank_enabled():
        return None
    docs = [str(d) for d in documents if str(d).strip()]
    if len(docs) < 2 or not str(query).strip():
        # Nothing to reorder — do not pay a network round-trip.
        return None

    key = os.getenv("COHERE_API_KEY", "").strip()
    model = os.getenv(_ENV_MODEL, "").strip() or _DEFAULT_MODEL
    payload: dict[str, Any] = {
        "model": model,
        "query": str(query),
        "documents": list(docs),
        "top_n": int(top_n) if top_n else len(docs),
    }
    _bump("attempts")
    try:
        resp = _get_client().post(
            COHERE_RERANK_URL,
            json=payload,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
        )
        if resp.status_code != 200:
            logger.debug(
                "cohere_rerank: http %s (%s)", resp.status_code, resp.text[:160]
            )
            _bump("failed")
            return None
        body = resp.json()
    except Exception as exc:  # noqa: BLE001 — fail open, never break the answer
        logger.debug("cohere_rerank: call failed: %s", exc)
        _bump("failed")
        return None

    try:
        out: list[tuple[int, float]] = []
        for item in body.get("results") or []:
            idx = item.get("index")
            score = item.get("relevance_score")
            if isinstance(idx, int) and 0 <= idx < len(docs):
                out.append((idx, float(score) if score is not None else 0.0))
        if not out:
            _bump("failed")
            return None
        return out
    except Exception as exc:  # noqa: BLE001
        logger.debug("cohere_rerank: malformed response: %s", exc)
        _bump("failed")
        return None


def rerank_query_context(
    *, intent: str = "", risk_context: str = "", dimension_hint: str = ""
) -> str:
    """R347 — deterministic rerank-query enrichment from the parse's own labels.

    A bare question string is a weak discriminator for a cross-encoder: the
    classifier already KNOWS the question is a ``prohibited_practice`` ask
    about a ``high``-risk system — telling the reranker the same in domain
    terms focuses its relevance signal. No LLM call; a few tokens.

    Returns a short ``"; ".join`` (e.g. ``"risk: high; intent: prohibited
    practice"``) that callers append to the rerank query. Empty string when
    nothing is available — the query stays exactly the question.
    """
    parts: list[str] = []
    if risk_context:
        parts.append(f"risk: {str(risk_context).strip().lower()}")
    if intent:
        parts.append(
            f"intent: {str(intent).strip().lower().replace('_', ' ')}"
        )
    if dimension_hint:
        parts.append(
            f"focus: {str(dimension_hint).strip().lower().replace('_', ' ')}"
        )
    return "; ".join(parts)


def build_kg_candidate_pool(
    references: Sequence[str],
    *,
    max_extra: int = 8,
    per_ref: int = 3,
) -> list[str]:
    """R347 — ``references`` + deduplicated 1-hop CROSS_REFERENCES neighbours.

    The KG/taxonomy lever: each candidate's own cross-reference adjacency
    (incoming AND outgoing on the embedded undirected graph; the canonical
    ``kb_xrefs.cross_refs`` adjacency when the embedded backend is not
    selected) is appended to the pool, so the cross-encoder can PROMOTE a
    genuinely cross-referenced provision that the keyword map never saw —
    instead of only re-ordering a keyword-picked set.

    Appends only, deduplicated, capped at ``max_extra`` (a hub article like
    Art. 16 would otherwise flood the pool). The caller adopts the result
    only when the rerank call SUCCEEDED (see :func:`rerank_pool`'s ok bit),
    so a failure never leaks neighbours into the reference set. Never raises.
    """
    base = [r for r in (references or [])]
    extra: list[str] = []
    try:
        # Prefer the embedded graph (undirected — includes refs that POINT AT
        # our anchors, the "why is this relevant" signal); fall back to the
        # outgoing-only kb_xrefs adjacency when the neo4j backend is selected.
        from app.graph.embedded_graph import (  # noqa: PLC0415
            embedded_backend_selected,
            get_embedded_graph,
        )

        neighbors_of: Any = None
        if embedded_backend_selected():
            try:
                g = get_embedded_graph()
                if g.enabled:
                    neighbors_of = g.neighbors
            except Exception:  # noqa: BLE001
                neighbors_of = None
        if neighbors_of is None:
            from functools import partial  # noqa: PLC0415

            from app.data.kb_xrefs import cross_refs  # noqa: PLC0415

            neighbors_of = partial(cross_refs, limit=per_ref)

        for ref in base:
            try:
                nbs = neighbors_of(ref)
            except Exception:  # noqa: BLE001 — one bad ref must not kill the pool
                continue
            for nb in nbs:
                if nb not in base and nb not in extra:
                    extra.append(nb)
                    if len(extra) >= max_extra:
                        return base + extra
    except Exception:  # noqa: BLE001 — KG expansion must never break parse
        return base
    return base + extra


def rerank_pool(
    question: str,
    references: Sequence[str],
    *,
    query_context: str = "",
    text_for: Any = None,
) -> tuple[list[str], bool]:
    """R347 — the permutation core with an explicit SUCCESS bit.

    Identical guarantees to :func:`rerank_references` (output is a
    PERMUTATION of the input, unresolved refs keep relative order, any
    failure returns the input unchanged), plus ``ok``:

    * ``ok=True``  — the cross-encoder answered; the output order is its
      verdict. ``ok`` is True even when the verdict equals the input order
      (a successful noop).
    * ``ok=False`` — gate off, no scorable pair, network/timeout/malformed
      failure, or the permutation invariant broke. The input stands.

    The bit lets a caller that EXPANDED the pool (e.g.
    :func:`build_kg_candidate_pool`) adopt the expanded result only on real
    success — a rerank outage must never change the reference set.

    ``query_context`` (see :func:`rerank_query_context`) is appended to the
    rerank query — the cross-encoder discriminates on domain terms.

    :param text_for: callable ``ref -> str | None`` supplying the verbatim
        text of a provision. Defaults to
        :func:`app.data.provision_text.get_provision_text`.
    """
    refs = [r for r in (references or [])]
    if len(refs) < 2:
        return list(refs), False
    if not rerank_enabled():
        return list(refs), False

    if text_for is None:
        try:
            from app.data.provision_text import (  # noqa: PLC0415
                get_provision_text,
            )

            text_for = get_provision_text
        except Exception:  # noqa: BLE001
            return list(refs), False

    # Only rows whose provision text resolves can be scored. Unresolved refs are
    # held aside and re-appended in their ORIGINAL relative order, so nothing is
    # lost and the transform stays a permutation.
    scorable: list[int] = []
    docs: list[str] = []
    for i, ref in enumerate(refs):
        try:
            txt = text_for(ref)
        except Exception:  # noqa: BLE001
            txt = None
        if txt and str(txt).strip():
            scorable.append(i)
            docs.append(str(txt).strip()[:4000])

    if len(scorable) < 2:
        return list(refs), False

    query = str(question).strip()
    ctx = (query_context or "").strip()
    if ctx:
        query = f"{query} — {ctx}"[:600]

    ranked = rerank_documents(query, docs)
    if not ranked:
        return list(refs), False

    seen: set[int] = set()
    ordered: list[str] = []
    for doc_idx, _score in ranked:
        if 0 <= doc_idx < len(scorable):
            orig = scorable[doc_idx]
            if orig not in seen:
                seen.add(orig)
                ordered.append(refs[orig])
    # Any scorable ref the API omitted, then every unscorable ref — both in
    # original order. This is what makes the result a permutation.
    for i, ref in enumerate(refs):
        if i in seen:
            continue
        if i in scorable and refs[i] in ordered and ordered.count(refs[i]) >= refs.count(refs[i]):
            continue
        ordered.append(ref)

    if sorted(ordered) != sorted(refs):  # pragma: no cover — invariant guard
        logger.debug("cohere_rerank: permutation invariant violated, keeping input")
        _bump("failed")
        return list(refs), False
    _bump("reordered" if ordered != list(refs) else "noop")
    return ordered, True


def rerank_references(
    question: str,
    references: Sequence[str],
    *,
    text_for: Any = None,
) -> list[str]:
    """Reorder ``references`` by cross-encoder relevance. **Never drops.**

    Thin wrapper over :func:`rerank_pool` keeping the historical signature;
    the guarantees are unchanged (permutation, unresolved refs keep relative
    order, any failure returns the input unchanged).
    """
    return rerank_pool(question, references, text_for=text_for)[0]
