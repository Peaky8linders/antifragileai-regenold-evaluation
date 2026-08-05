"""Dense-embedding retrieval behind the ``Retriever`` ABC -- the API route
around local torch.

This is the REAL neural-dense semantic-seed slot that ``LsaRetriever`` only
proxied with classical SVD. A ``DenseRetriever`` takes an injected ``embedder``
(exposing ``.embed(texts: list[str]) -> list[list[float]]``) so that
voyage-law-2, Qwen3-Embedding, or any other embeddings API drops in without
touching this module.

No third-party import at module load time -- the embedder is injected by the
caller. If ``embedder is None`` we raise a clear ``RuntimeError`` so the caller
knows exactly what to wire up.

Honesty gating (same discipline as the rest of the harness):
  * No local model load at import time -- zero extra deps unless the caller
    wires in an API embedder.
  * If ``embedder`` is not provided we raise rather than fabricating embeddings.
  * All similarity computation is pure-Python dot of L2-normalised vectors --
    no numpy, consistent with the repo-wide constraint.
"""

from __future__ import annotations

import math
from typing import Any, Protocol, runtime_checkable

try:
    from .models import Provision
except (ImportError, ValueError):
    from ..models import Provision
from .retrieval import Retriever

__all__ = ["DenseRetriever", "Embedder"]


@runtime_checkable
class Embedder(Protocol):
    """Minimal protocol for an embeddings API client.

    Any object with this single method -- voyage-law-2 wrapper, a test stub, an
    OpenAI-compatible client shim -- satisfies it without subclassing.
    """

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one float vector per input text. All vectors must have the
        same dimension. The caller L2-normalises them, so raw or pre-normalised
        vectors both work."""
        ...


def _l2_normalize_vec(vec: list[float]) -> list[float]:
    """L2-normalise a dense float vector in pure Python. Returns a zero vector
    unchanged (cannot normalise a zero vector; cosine is undefined there)."""
    norm = math.sqrt(sum(x * x for x in vec))
    if norm == 0.0:
        return vec
    return [x / norm for x in vec]


def _dot(a: list[float], b: list[float]) -> float:
    """Dot product of two same-length float vectors (pure Python, no numpy)."""
    return sum(x * y for x, y in zip(a, b))


class DenseRetriever(Retriever):
    """Dense-embedding retrieval over the provision corpus via an injected API
    embedder (the neural semantic-seed slot; no local torch required).

    At construction time all provision texts are embedded once via ``embedder``
    and cached as L2-normalised vectors. ``search_scored`` embeds the query,
    cosines it against every cached provision vector (pure-Python dot of
    L2-normalised vectors), and returns the top-k ``(provision_id, score)``
    pairs sorted by score descending, then provision_id for deterministic ties.

    Inject any object exposing ``.embed(texts: list[str]) -> list[list[float]]``
    -- a voyage-law-2 API wrapper, Qwen3-Embedding, or a deterministic test
    stub. Passing ``embedder=None`` raises a ``RuntimeError`` immediately so the
    caller is never silently given a broken retriever.
    """

    def __init__(
        self,
        provisions: list[Provision],
        embedder: Any | None,
    ) -> None:
        if embedder is None:
            raise RuntimeError(
                "DenseRetriever requires an embedder (an object with "
                "`.embed(texts) -> list[list[float]]`). Inject a voyage-law-2 "
                "API wrapper, a Qwen3-Embedding client, or any compatible shim. "
                "No local model is bundled -- this is the API-route dense retriever."
            )
        self._embedder = embedder
        self._ids: list[str] = [p.provision_id for p in provisions]

        if provisions:
            raw = embedder.embed([p.text for p in provisions])
            self._doc_vecs: list[list[float]] = [_l2_normalize_vec(v) for v in raw]
        else:
            self._doc_vecs = []

    def search(self, query: str, k: int) -> list[str]:
        return [pid for pid, _ in self.search_scored(query, k)]

    def search_scored(self, query: str, k: int) -> list[tuple[str, float]]:
        """Embed the query, cosine vs cached doc vectors, return top-k results.

        Returns ``[]`` for an empty corpus or an empty query (a zero query
        vector has no meaningful cosine against anything).
        """
        if not self._doc_vecs or not query:
            return []
        raw_q = self._embedder.embed([query])
        qvec = _l2_normalize_vec(raw_q[0])
        # If the query embedded as all-zeros, cosine is undefined -> no results
        if all(x == 0.0 for x in qvec):
            return []
        scored: list[tuple[float, str]] = []
        for pid, dvec in zip(self._ids, self._doc_vecs):
            score = _dot(qvec, dvec)
            if score > 0.0:
                scored.append((score, pid))
        # deterministic: score desc, then provision_id for ties
        scored.sort(key=lambda s: (-s[0], s[1]))
        return [(pid, score) for score, pid in scored[:k]]
