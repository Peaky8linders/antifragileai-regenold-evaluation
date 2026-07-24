"""Latent Semantic Analysis retriever -- an OFFLINE "semantic" seeder.

Honest labelling (same discipline as ``retrieval.py`` calling TF-IDF "lexical,
not dense"): this is **classical LSA** -- a truncated SVD over the TF-IDF
term-document matrix (Deerwester et al. 1990) -- **not** a neural dense embedder.
It needs no model download and no network, only numpy, so it runs anywhere the
rest of the harness runs. Its one property TF-IDF lacks: two provisions that
share *no* surface terms can still score > 0 if they load on the same latent
topics (synonymy / co-occurrence). That is exactly the property we want to test
as a graph **seeder** on cross-reference / multi-hop questions, where the query
vocabulary rarely matches the target provision verbatim.

A neural dense embedder (Qwen3-Embedding / voyage-law-2, plan §9) is the stronger
drop-in and belongs behind the same :class:`Retriever` ABC + an optional-dep gate
(cf. ``llm.py``); it is not runnable offline here. LSA is the runnable-now proxy,
and -- being deterministic (seeded randomized SVD + sign canonicalisation) -- it
keeps the whole retrieval surface reproducible and CI-testable with zero models.
"""

from __future__ import annotations

import math
from collections import Counter

try:
    from .models import Provision
except (ImportError, ValueError):
    from ..models import Provision
from .retrieval import Retriever, tokenize

try:  # numpy is guaranteed via pyarrow, but gate anyway so the failure is legible
    import numpy as np
except ImportError:  # pragma: no cover - numpy is always present in practice
    np = None  # type: ignore[assignment]

__all__ = ["LsaRetriever"]


def _randomized_svd(A, k: int, *, n_oversamples: int = 10, n_iter: int = 4, seed: int = 0):
    """Deterministic truncated SVD (Halko et al. 2011), the method sklearn's
    ``TruncatedSVD`` uses. O(m*n*k) rather than the O(m*n*min(m,n)) of a full SVD
    -- seconds, not minutes, on the ~1.3k x ~2.8k corpus matrix. Seeded + power-
    iterated for a stable, accurate top-k subspace."""
    rng = np.random.default_rng(seed)
    m, n = A.shape
    p = min(k + n_oversamples, n)
    Y = A @ rng.standard_normal((n, p))
    for _ in range(n_iter):  # power iterations sharpen the range approximation
        Q, _ = np.linalg.qr(A @ (A.T @ Y))
        Y = Q
    Q, _ = np.linalg.qr(Y)
    B = Q.T @ A
    Ub, s, Vt = np.linalg.svd(B, full_matrices=False)
    return (Q @ Ub)[:, :k], s[:k], Vt[:k]


class LsaRetriever(Retriever):
    """TF-IDF -> truncated-SVD latent space; cosine ranking in that space.

    Ranks by cosine similarity between the query's latent vector and each
    provision's latent vector. ``search_scored`` returns those cosines directly
    (in [-1, 1]; only positive matches are emitted), so it drops straight into
    :class:`GraphExpansionRetriever` as a semantic seeder alongside TF-IDF.
    """

    def __init__(
        self,
        provisions: list[Provision],
        *,
        n_components: int = 200,
        min_df: int = 2,
        seed: int = 0,
    ) -> None:
        if np is None:  # pragma: no cover - defensive; numpy ships with pyarrow
            raise RuntimeError(
                "LsaRetriever needs numpy. Install it (it ships with the base deps "
                "via pyarrow) or `pip install 'euaiact-graphrag[lsa]'`."
            )
        self._ids: list[str] = [p.provision_id for p in provisions]
        docs = [tokenize(p.text) for p in provisions]
        n = len(docs)

        df: Counter[str] = Counter()
        for toks in docs:
            df.update(set(toks))
        # document-frequency floor: drop hapax terms -> denoise + shrink the matrix
        vocab = sorted(t for t, d in df.items() if d >= min_df)
        self._vocab: dict[str, int] = {t: i for i, t in enumerate(vocab)}
        self._idf: dict[str, float] = {
            t: math.log((1 + n) / (1 + df[t])) + 1.0 for t in vocab
        }

        # dense TF-IDF matrix (docs x terms), L2-normalised rows
        X = np.zeros((n, len(vocab)), dtype=np.float64)
        for r, toks in enumerate(docs):
            for t, c in Counter(toks).items():
                j = self._vocab.get(t)
                if j is not None:
                    X[r, j] = c * self._idf[t]
        X /= np.clip(np.linalg.norm(X, axis=1, keepdims=True), 1e-12, None)

        k = max(1, min(n_components, min(X.shape) - 1)) if min(X.shape) > 1 else 1
        U, s, Vt = _randomized_svd(X, k, seed=seed)
        # sign canonicalisation: fix each component's sign by its largest-|value|
        # entry, so the embedding (hence the ranking) is reproducible run-to-run.
        for i in range(Vt.shape[0]):
            j = int(np.argmax(np.abs(Vt[i])))
            if Vt[i, j] < 0:
                Vt[i] *= -1
                U[:, i] *= -1
        self._components = Vt  # (k, |vocab|): term-space -> latent
        doc_emb = U * s  # (n, k) provisions in latent space
        self._doc_emb = doc_emb / np.clip(
            np.linalg.norm(doc_emb, axis=1, keepdims=True), 1e-12, None
        )

    def _embed_query(self, query: str):
        vec = np.zeros(len(self._vocab), dtype=np.float64)
        hit = False
        for t, c in Counter(tokenize(query)).items():
            j = self._vocab.get(t)
            if j is not None:
                vec[j] = c * self._idf[t]
                hit = True
        if not hit:
            return None  # no in-vocabulary term -> nothing to project
        vec /= np.clip(np.linalg.norm(vec), 1e-12, None)
        latent = self._components @ vec
        norm = float(np.linalg.norm(latent))
        if norm == 0.0:
            return None
        return latent / norm

    def search(self, query: str, k: int) -> list[str]:
        return [pid for pid, _ in self.search_scored(query, k)]

    def search_scored(self, query: str, k: int) -> list[tuple[str, float]]:
        q = self._embed_query(query)
        if q is None:
            return []
        sims = self._doc_emb @ q  # cosine in latent space (rows already unit-norm)
        # deterministic: score desc, then provision_id for ties
        order = sorted(range(len(self._ids)), key=lambda i: (-float(sims[i]), self._ids[i]))
        out: list[tuple[str, float]] = []
        for i in order[:k]:
            score = float(sims[i])
            if score > 0:
                out.append((self._ids[i], score))
        return out
