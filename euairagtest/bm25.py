"""BM25F lexical retriever with article-number field boosting for the EU AI Act
corpus.

BM25F extends Okapi BM25 to structured (multi-field) documents: each field is
length-normalised independently, then the per-field weighted term frequencies are
combined before the BM25 saturation function is applied once on the aggregate.
The ``heading`` field carries the structural identity derived from
``Provision.citation`` (e.g. ``"Art. 6(2)"`` for ``art_6__para_2``) and is given
a higher weight than the body text so a query that mentions an article number
directly boosts the matching provision.

This retriever is lexical, not dense.  Expected outcome: it should sit near the
~0.30 soft-F1 lexical ceiling already demonstrated by TF-IDF and LSA, possibly
with a mild improvement when queries contain explicit article references (the
one structured-field signal TF-IDF bag-of-words cannot exploit).  The result is
an honest data point regardless of direction.
"""

from __future__ import annotations

import math
from collections import Counter
from typing import Sequence

try:
    from .models import Provision
except (ImportError, ValueError):
    from ..models import Provision
from .retrieval import _STOP, _TOKEN_RE, Retriever

__all__ = ["Bm25Retriever"]


def _bm25_tokenize(text: str) -> list[str]:
    """Tokenize like ``retrieval.tokenize`` but keep all-digit tokens of any length.

    The shared tokenizer drops every token of length <= 2, which silently
    discards the article numbers 1-99 — exactly the article-number signal the
    ``heading`` field exists to boost. Here a run of digits is kept regardless of
    length (so "6" and "50" survive), while non-digit tokens keep the same
    length-> 2 and stopword filters so body/heading statistics stay aligned with
    the rest of the harness.
    """
    out: list[str] = []
    for t in _TOKEN_RE.findall(text.lower()):
        if t.isdigit():
            out.append(t)
        elif len(t) > 2 and t not in _STOP:
            out.append(t)
    return out


class Bm25Retriever(Retriever):
    """Okapi BM25F over two fields per provision.

    Fields
    ------
    body
        ``provision.text`` — the substantive prose, weight 1.0.
    heading
        A short structural-identity string built from ``provision.citation``
        (e.g. ``"Art. 6(2)"``).  Falls back to ``"article N"`` when the
        citation is empty but ``provision.article`` is set; empty otherwise.
        Default weight 2.0 so a query term that appears in a provision's own
        article-number token boosts that provision above body-only matches.

    BM25F formula (per query term *t*, per document *d*)
    ----------------------------------------------------
    Accumulate a weighted term frequency across fields::

        wtf(t, d) = Σ_f  weight_f * tf(t, f) / (1 - b + b * |f| / avglen_f)

    then apply saturation once on the combined score::

        score(t, d) = idf(t) * wtf(t, d) * (k1 + 1) / (wtf(t, d) + k1)

    Document score = Σ_t score(t, d) over all query terms.

    IDF uses the same smoothed formula as ``TfidfRetriever``::

        idf(t) = log((1 + N) / (1 + df(t))) + 1.0

    which is always positive (unseen query terms contribute 0).
    """

    def __init__(
        self,
        provisions: Sequence[Provision],
        *,
        k1: float = 1.5,
        b: float = 0.75,
        field_weights: dict[str, float] | None = None,
    ) -> None:
        self._k1 = k1
        self._b = b
        self._field_weights: dict[str, float] = field_weights or {
            "body": 1.0,
            "heading": 2.0,
        }

        # --- tokenise both fields for every provision -----------------------
        self._ids: list[str] = []
        # body_toks[i] / heading_toks[i] are the token lists for provision i
        body_toks: list[list[str]] = []
        heading_toks: list[list[str]] = []

        for p in provisions:
            self._ids.append(p.provision_id)
            body_toks.append(_bm25_tokenize(p.text))
            heading_toks.append(_bm25_tokenize(_heading(p)))

        n = len(provisions)

        # --- per-field average length ---------------------------------------
        self._avglen: dict[str, float] = {
            "body": _safe_avg(len(t) for t in body_toks),
            "heading": _safe_avg(len(t) for t in heading_toks),
        }

        # --- document-frequency table (global, across all terms) -----------
        df: Counter[str] = Counter()
        for bt, ht in zip(body_toks, heading_toks):
            df.update(set(bt) | set(ht))

        # smoothed idf — always positive, mirrors TfidfRetriever exactly
        self._idf: dict[str, float] = {
            t: math.log((1 + n) / (1 + d)) + 1.0 for t, d in df.items()
        }

        # --- pre-compute per-doc BM25F building blocks ---------------------
        # Store: list of dicts  {term -> wtf}  (weighted-tf, already length-norm'd)
        self._wtf_docs: list[dict[str, float]] = []
        for bt, ht in zip(body_toks, heading_toks):
            self._wtf_docs.append(
                self._build_wtf(
                    {"body": Counter(bt), "heading": Counter(ht)},
                    {"body": len(bt), "heading": len(ht)},
                )
            )

    # -----------------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------------

    def _build_wtf(
        self,
        tf_per_field: dict[str, Counter[str]],
        len_per_field: dict[str, int],
    ) -> dict[str, float]:
        """Return {term -> wtf} for one document."""
        acc: dict[str, float] = {}
        for fname, weight in self._field_weights.items():
            tf_map = tf_per_field.get(fname, Counter())
            field_len = len_per_field.get(fname, 0)
            avglen = self._avglen.get(fname, 1.0)
            norm = 1.0 - self._b + self._b * field_len / max(avglen, 1e-9)
            for term, freq in tf_map.items():
                contrib = weight * freq / norm
                acc[term] = acc.get(term, 0.0) + contrib
        return acc

    def _bm25_score(self, wtf: float, idf: float) -> float:
        """Apply BM25 saturation once on the combined wtf."""
        k1 = self._k1
        return idf * wtf * (k1 + 1.0) / (wtf + k1)

    # -----------------------------------------------------------------------
    # Retriever interface
    # -----------------------------------------------------------------------

    def search(self, query: str, k: int) -> list[str]:
        return [pid for pid, _ in self.search_scored(query, k)]

    def search_scored(self, query: str, k: int) -> list[tuple[str, float]]:
        q_terms = _bm25_tokenize(query)
        if not q_terms:
            return []

        # keep only query terms that appear in the corpus
        q_idf = {t: self._idf[t] for t in q_terms if t in self._idf}
        if not q_idf:
            return []

        scored: list[tuple[float, str]] = []
        for pid, wtf_doc in zip(self._ids, self._wtf_docs):
            doc_score = 0.0
            for term, idf in q_idf.items():
                wtf = wtf_doc.get(term, 0.0)
                if wtf > 0.0:
                    doc_score += self._bm25_score(wtf, idf)
            if doc_score > 0.0:
                scored.append((doc_score, pid))

        # deterministic: score descending, then provision_id ascending for ties
        scored.sort(key=lambda s: (-s[0], s[1]))
        return [(pid, score) for score, pid in scored[:k]]


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _heading(p: Provision) -> str:
    """Return the heading string for the heading field.

    Priority:
    1. ``provision.citation`` if non-empty.
    2. ``"article N"`` when citation is empty but ``provision.article`` is set.
    3. Empty string otherwise (heading field contributes nothing).
    """
    if p.citation:
        return p.citation
    if p.article is not None:
        return f"article {p.article}"
    return ""


def _safe_avg(lengths) -> float:
    """Return the mean of an iterable of lengths; 1.0 if empty."""
    total = 0
    count = 0
    for v in lengths:
        total += v
        count += 1
    return total / count if count else 1.0
