"""Naive retrieval over the provision corpus -- the retrieval half of the §8
"naive RAG (no graph)" baseline.

A pure-Python TF-IDF cosine retriever, behind a ``Retriever`` interface so a
*dense* embedder (Qwen3-Embedding / voyage-law-2, per plan §9) drops in later
without touching the baseline that consumes it. TF-IDF is lexical, not dense;
it stands in until the embedding libraries (sentence-transformers/torch) and a
GPU/API are available. Labelled honestly so nobody reads a lexical number as a
dense one.

No third-party dependencies (numpy is avoidable at this corpus size).
"""

from __future__ import annotations

import math
import re
from abc import ABC, abstractmethod
from collections import Counter

from ..models import Provision

__all__ = ["Retriever", "TfidfRetriever", "tokenize"]

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOP = frozenset(
    "the a an of to and or in on for is are be as by with that this which shall "
    "may not it its their such where when who whom under pursuant referred".split()
)


def tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN_RE.findall(text.lower()) if len(t) > 2 and t not in _STOP]


def _l2_normalize(vec: dict[str, float]) -> dict[str, float]:
    norm = math.sqrt(sum(w * w for w in vec.values()))
    if norm == 0:
        return vec
    return {t: w / norm for t, w in vec.items()}


class Retriever(ABC):
    """Maps a query to a ranked list of provision_ids. Swap TF-IDF for a dense
    embedder by implementing this one method."""

    @abstractmethod
    def search(self, query: str, k: int) -> list[str]:
        raise NotImplementedError

    def search_scored(self, query: str, k: int) -> list[tuple[str, float]]:
        """Ranked ``(provision_id, score)`` pairs. Default: rank-reciprocal scores
        over :meth:`search`, so any retriever composes with graph expansion /
        score-thresholded abstention even if it can't expose a native score."""
        return [(pid, 1.0 / (i + 1)) for i, pid in enumerate(self.search(query, k))]


class TfidfRetriever(Retriever):
    def __init__(self, provisions: list[Provision]) -> None:
        self._ids: list[str] = []
        tokenized: list[list[str]] = []
        for p in provisions:
            self._ids.append(p.provision_id)
            tokenized.append(tokenize(p.text))

        n = len(tokenized)
        df: Counter[str] = Counter()
        for toks in tokenized:
            df.update(set(toks))
        # smoothed idf, always positive
        self._idf: dict[str, float] = {
            t: math.log((1 + n) / (1 + d)) + 1.0 for t, d in df.items()
        }
        self._doc_vecs: list[dict[str, float]] = [self._vectorize(toks) for toks in tokenized]

    def _vectorize(self, toks: list[str]) -> dict[str, float]:
        tf = Counter(toks)
        vec = {t: c * self._idf.get(t, 0.0) for t, c in tf.items() if self._idf.get(t, 0.0)}
        return _l2_normalize(vec)

    def search(self, query: str, k: int) -> list[str]:
        return [pid for pid, _ in self.search_scored(query, k)]

    def search_scored(self, query: str, k: int) -> list[tuple[str, float]]:
        qvec = self._vectorize(tokenize(query))
        if not qvec:
            return []
        scored: list[tuple[float, str]] = []
        for pid, dvec in zip(self._ids, self._doc_vecs):
            # cosine == dot product of the two L2-normalised sparse vectors
            small, big = (qvec, dvec) if len(qvec) <= len(dvec) else (dvec, qvec)
            score = sum(w * big.get(t, 0.0) for t, w in small.items())
            if score > 0:
                scored.append((score, pid))
        # deterministic: sort by score desc, then provision_id for ties
        scored.sort(key=lambda s: (-s[0], s[1]))
        return [(pid, score) for score, pid in scored[:k]]
