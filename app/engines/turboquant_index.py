"""Windows-friendly dense retrieval via TurboQuant (Zandieh et al., ICLR 2026).

Companion to :mod:`app.engines.vector_rerank` — that module is Linux-only
(turbovec ships no Windows wheel); this module is the **pure-NumPy**
TurboQuant path. Same compression algorithm, same recall, no Rust toolchain.

## Architecture (Round 31 — High-Precision RAG Architecture PDF, Layer D)

The High-Precision RAG whitepaper calls for a *Two-Step Hybrid Retrieval Core*
fusing BM25 sparse with a dense vector index. The Round-25..28 pipeline
already nails the sparse side (`app.data.kb_search`). The missing half is the
dense side. We close it with:

1. **TF-IDF document vectors** over the existing BM25 corpus (≈350 docs:
   KB summaries + ontology + EUR-Lex prose + Art. 3 definitions).
2. **Truncated SVD projection** to 128 dimensions — NumPy-only, the
   doc-term matrix is ~350×3000 so a full SVD is sub-100ms one-shot.
3. **TurboQuant 4-bit quantization** (`turboquant.TurboQuant`) — the
   Google-Research codebook-free codec the user requested.
4. **Brute-force inner-product search** — at 350 vectors the lack of an
   ANN structure is irrelevant; the scan is sub-millisecond.

When `turboquant` is **not installed**, the module falls back to
**plain float32** vectors with the same public API. When it IS installed, we
compress to 4-bit and use `TurboQuant.inner_product()`. Either way the
caller sees the same `dense_top_k(question, k)` surface.

## Integration

* :func:`dense_top_k` is the public retrieval call. The route + engine fuse
  its output with BM25 ranks via Reciprocal Rank Fusion in
  :func:`app.data.kb_search.top_articles_by_relevance_hybrid`.
* :func:`is_enabled` is the cheap env-gate. Default ON; set
  ``REGENOLD_TURBOQUANT_DENSE=0`` to disable (e.g. to reproduce a
  deterministic BM25-only benchmark run).

## Why not Voyage-3-Large / Jina-Embeddings-V3 (per the whitepaper)?

Both are network calls — Voyage is API-billed, Jina v3 requires
sentence-transformers (~2 GB torch wheel). Either would break the
Windows-dev guarantee and inflate the Railway cold-start. TF-IDF + SVD is
the deterministic stdlib-only path that buys us the *paraphrase* match BM25
misses (e.g. "manipulative" → Art. 5 even when the query says
"covertly influencing") without an external model.

The whitepaper's F1 numbers (0.87 prohibited / 0.85 high-risk) come from
the **fusion** of sparse + dense + reranker, not the model choice. Our
sparse path already covers what the whitepaper's BM25 step does; adding
the dense path closes the recall gap on paraphrased queries.
"""
from __future__ import annotations

import hashlib
import logging
import os
import threading
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np  # type: ignore

logger = logging.getLogger(__name__)


_ENV_FLAG = "REGENOLD_TURBOQUANT_DENSE"
_PROJECTION_DIM = 128
_QUANT_BIT_WIDTH = 4
# Random projection seed — fixed for reproducibility. Changing this would
# require a re-index but the BM25 deterministic fallback still works.
_INDEX_SEED = 20260515


def is_enabled() -> bool:
    """True unless the env-gate is explicitly disabled. Cheap to call (no import cost)."""
    val = os.getenv(_ENV_FLAG, "1").strip().lower()
    return val not in ("0", "false", "no", "off")


def is_compressed_available() -> bool:
    """True iff the optional ``turboquant`` package is importable.

    Module-level for cheap test-time access; the real check is gated
    further inside :class:`_DenseIndex` so an import error degrades the
    feature instead of crashing the route. Used by tests + telemetry.
    """
    try:
        import turboquant  # noqa: F401 — probe-only import
    except Exception:  # noqa: BLE001 — any failure → no compression
        return False
    return True


# ``id(bm25) -> (strong ref to that index, its digest)``. See _corpus_identity.
# Tiny by construction: kb_search memoises exactly two corpora.
_IDENTITY_MEMO: dict[int, tuple[object, str]] = {}
_MAX_MEMOISED_IDENTITIES = 8


def _corpus_identity(bm25: object) -> str:
    """Fingerprint the BM25 corpus this dense index is joined against.

    R338 [I2] — ``_DenseIndex._bm25_idx_map`` stores **raw positions** into the
    BM25 corpus, not stable ids, and ``dense_top_k`` dereferences
    ``bm25.article_refs[orig_idx]`` to label every hit. So the map is only
    meaningful against the *exact* corpus it was built from. Since ``938933a``
    the corpus is configuration-dependent — ``REGENOLD_ONTOLOGY_RISK_DOCS``
    swings it 345 ↔ 373 docs, and because ``_build_ontology_docs`` is emitted in
    the MIDDLE of the corpus (kb → ontology → corpus → definitions) the gate
    shifts every later document by 28. Measured on this repo, one process that
    built with the gate ON and then flipped it OFF answered
    "serious incident reporting deadline" with ``Art. 111`` at the identical
    0.8224 score that ``Art. 73`` had held — no IndexError, no log line, just a
    relabelled ranking.

    The fingerprint therefore covers everything the join depends on:

    * ``n_docs`` — the array length the positions index into;
    * ``avg_doc_len`` — cheap proof the BM25 statistics were rebuilt too (IDF
      and length normalisation move for *every* pre-existing doc when the
      corpus changes size);
    * a digest of the parallel ``(article_ref, source)`` arrays — the actual
      labels, so a same-size REORDER is caught as well as a resize.

    Memoised by OBJECT IDENTITY, not by value: ``kb_search._build_index_cached``
    is an ``lru_cache``, so each corpus is one long-lived frozen dataclass and
    the same object comes back for the same gate. Measured, the digest itself is
    **174 µs** over 373 docs — negligible against a live request but a third of
    a 509 µs ``dense_top_k`` on the deterministic path, which a full offline
    bench calls tens of thousands of times. The memo holds a strong reference to
    the index alongside its digest so ``id()`` cannot be recycled onto a
    different object underneath us; ``_BM25Index`` is frozen with tuple fields,
    so a cached digest cannot go stale by mutation.
    """
    memo_key = id(bm25)
    memo = _IDENTITY_MEMO.get(memo_key)
    if memo is not None and memo[0] is bm25:
        return memo[1]

    refs = getattr(bm25, "article_refs", ())
    sources = getattr(bm25, "sources", ())
    h = hashlib.blake2s(digest_size=8)
    for ref, src in zip(refs, sources):
        h.update(str(ref).encode("utf-8", "replace"))
        h.update(b"\x1f")
        h.update(str(src).encode("utf-8", "replace"))
        h.update(b"\x1e")
    n_docs = len(getattr(bm25, "docs", ()))
    avg_len = float(getattr(bm25, "avg_doc_len", 0.0) or 0.0)
    identity = f"n{n_docs}:avg{avg_len:.4f}:{h.hexdigest()}"
    if len(_IDENTITY_MEMO) >= _MAX_MEMOISED_IDENTITIES:
        _IDENTITY_MEMO.clear()
    _IDENTITY_MEMO[memo_key] = (bm25, identity)
    return identity


@dataclass(frozen=True)
class _DenseSearchHit:
    """One result from :meth:`_DenseIndex.search`.

    ``doc_idx`` is parallel to the underlying BM25 index — so a consumer
    can join with :func:`app.data.kb_search._build_index().article_refs`
    to map the hit back to ``"Art. N"`` form. ``score`` is the dot
    product between the unit-norm query vector and the (de-quantized)
    document vector — for unit vectors that's exactly cosine similarity.
    """

    doc_idx: int
    score: float


class _DenseIndex:
    """Lazy-loaded, process-singleton dense index over the BM25 corpus.

    Construction:

    1. Pull ``(article_refs, docs)`` from
       :func:`app.data.kb_search._build_index`.
    2. Build a TF-IDF doc-term matrix in NumPy.
    3. Project to 128-d via SVD (stable thanks to the
       `_INDEX_SEED` random-state determinism in numpy ≥ 2.0).
    4. L2-normalise each doc vector.
    5. Quantize via :class:`turboquant.TurboQuant` if available;
       otherwise keep plain float32 vectors with the same dot-product API.

    Search:

    1. Tokenise the query via :func:`app.data.kb_search._tokenize`.
    2. Build a sparse TF-IDF query vector against the same vocab.
    3. Project via the cached SVD V_T matrix.
    4. L2-normalise and dot against every doc vector — top-k by score.

    Thread-safety: ``_setup`` is guarded by a re-entrant lock; the
    one-shot build is idempotent.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._loaded = False
        self._failed = False
        # Populated after _setup():
        self._vocab: dict[str, int] = {}
        self._idf: np.ndarray | None = None
        self._mean_doc_vec: np.ndarray | None = None  # unused after r31 rewrite
        self._v_t: np.ndarray | None = None  # SVD V_T (dim × vocab)
        self._doc_vecs_dense: np.ndarray | None = None  # plain fallback
        self._compressed: object | None = None  # turboquant CompressedVectors
        self._quantizer: object | None = None  # turboquant TurboQuant
        self._num_docs: int = 0
        self._compression_active: bool = False
        self._use_external: bool = False
        # Map filtered dense index → original BM25 doc index (for the
        # article_ref join). Populated after _setup().
        self._bm25_idx_map: list[int] = []
        # R338 [I2] — fingerprint of the BM25 corpus the positions above index
        # into. ``None`` until _build() runs. :func:`_resolve_index` compares it
        # against the LIVE corpus on every call and swaps in a different
        # instance rather than letting a stale map relabel dense hits.
        self._corpus_id: str | None = None

    # --- lifecycle ------------------------------------------------------
    def _setup(self) -> bool:
        if self._loaded:
            return True
        if self._failed:
            return False
        with self._lock:
            if self._loaded:
                return True
            if self._failed:
                return False
            try:
                self._build()
                self._loaded = True
                return True
            except Exception as exc:  # noqa: BLE001 — graceful degrade
                logger.info(
                    "turboquant_index: dense path unavailable. reason=%s",
                    exc,
                )
                self._failed = True
                return False

    def _build(self) -> None:
        # Heavy imports stay inside _build so module import is free.
        import json  # noqa: PLC0415
        from pathlib import Path  # noqa: PLC0415

        import numpy as np  # noqa: PLC0415

        # R338 [I2] — stamp the corpus this build is bound to BEFORE any of the
        # three build paths run. Every one of them resolves the corpus through
        # ``kb_search._build_index()``, which reads
        # ``REGENOLD_ONTOLOGY_RISK_DOCS`` fresh and is memoised per gate value
        # (``lru_cache(maxsize=2)``), so all of them see this same object within
        # this call. Stamping it here means the identity always describes the
        # corpus the vectors were ACTUALLY built from — not an assumption about
        # what the env said afterwards.
        from app.data.kb_search import _build_index as _kb_build_index  # noqa: PLC0415

        self._corpus_id = _corpus_identity(_kb_build_index())

        self._use_external = False
        loaded_external = False

        # 1. Prioritize external high-dimensional embeddings (Cohere/OpenAI) if keys are present
        try:
            from app.engines import external_embeddings  # noqa: PLC0415
            if external_embeddings.is_available():
                from app.data.kb_search import _build_index  # noqa: PLC0415
                bm25 = _build_index()
                n_total = len(bm25.docs)
                if n_total == 0:
                    raise RuntimeError("BM25 corpus is empty")

                keep_doc_idx = [i for i in range(n_total) if bm25.sources[i] != "definition"]
                self._bm25_idx_map = list(keep_doc_idx)
                raw_texts = [" ".join(bm25.docs[orig_i]) for orig_i in self._bm25_idx_map]

                logger.info("turboquant_index: requesting external embeddings for n=%d documents...", len(raw_texts))
                ext_vecs = external_embeddings.get_embedding(raw_texts, is_query=False)
                if ext_vecs is not None:
                    # Normalise to unit vectors
                    norms = np.linalg.norm(ext_vecs, axis=1, keepdims=True)
                    norms = np.where(norms < 1e-9, 1.0, norms)
                    self._doc_vecs_dense = (ext_vecs / norms).astype(np.float32)
                    self._use_external = True
                    self._num_docs = len(self._bm25_idx_map)
                    loaded_external = True
                    logger.info(
                        "turboquant_index: successfully loaded external embeddings dim=%d",
                        self._doc_vecs_dense.shape[1],
                    )
                else:
                    logger.warning("turboquant_index: external embeddings returned None, falling back to SVD path")
        except Exception as exc:  # noqa: BLE001 — fallback to SVD
            logger.warning("turboquant_index: external embeddings build failed, falling back. reason=%s", exc)

        loaded_precomputed = False

        # 2. Try to load pre-computed SVD assets from disk if external is not active/failed
        if not loaded_external:
            assets_path = Path(__file__).resolve().parent / "_assets" / "turboquant_precomputed.npz"
            if assets_path.exists():
                try:
                    data = np.load(assets_path)
                    self._vocab = json.loads(str(data["vocab_json"]))
                    self._idf = data["idf"].astype(np.float32)
                    self._mean_doc_vec = None
                    self._v_t = data["v_t"].astype(np.float32)
                    self._bm25_idx_map = list(data["bm25_idx_map"].astype(int))
                    doc_vecs = data["doc_vecs_dense"].astype(np.float32)

                    # ── Staleness guard ──────────────────────────────────
                    # ``bm25_idx_map`` stores POSITIONS in the BM25 corpus,
                    # not stable ids. If the KB gains, loses or reorders a
                    # document, every stored position silently addresses a
                    # DIFFERENT article: dense retrieval then returns
                    # confidently wrong article refs with no error anywhere.
                    # Verify the map still describes the live corpus, and
                    # fall through to the on-the-fly build if it does not —
                    # slower, but correct.
                    from app.data.kb_search import _build_index  # noqa: PLC0415

                    _bm25 = _build_index()
                    _live_keep = [
                        i for i in range(len(_bm25.docs))
                        if _bm25.sources[i] != "definition"
                    ]
                    if list(self._bm25_idx_map) != _live_keep:
                        raise RuntimeError(
                            "precomputed bm25_idx_map is stale: asset maps "
                            f"{len(self._bm25_idx_map)} docs, live corpus has "
                            f"{len(_live_keep)} non-definition docs "
                            f"(corpus size {len(_bm25.docs)}). "
                            "Re-run scripts/build_turboquant_precomputed.py."
                        )
                    if doc_vecs.shape[0] != len(self._bm25_idx_map):
                        raise RuntimeError(
                            f"precomputed asset inconsistent: {doc_vecs.shape[0]} "
                            f"vectors vs {len(self._bm25_idx_map)} mapped docs"
                        )

                    self._doc_vecs_dense = doc_vecs
                    self._num_docs = len(self._bm25_idx_map)
                    loaded_precomputed = True
                    logger.info("turboquant_index: successfully loaded precomputed SVD assets from disk")
                except Exception as exc:  # noqa: BLE001 — fallback to on-the-fly build
                    logger.warning("turboquant_index: failed to load precomputed SVD assets from disk, falling back. reason=%s", exc)

        # 3. Calculate SVD on-the-fly as final fail-safe fallback
        if not loaded_external and not loaded_precomputed:
            from app.data.kb_search import _build_index  # noqa: PLC0415

            bm25 = _build_index()
            n_total = len(bm25.docs)
            if n_total == 0:
                raise RuntimeError("BM25 corpus is empty")

            # Exclude the per-definition virtual docs (~68 rows keyed by
            # ``Art. 3``). They have their own deterministic path
            # (:func:`app.engines.sentence_index.select_definition_sentence`)
            # and they pollute dense ranks because they're short, term-dense,
            # and almost every term in the AI Act appears in at least one
            # definition. Including them collapsed every query to Art. 3 in
            # smoke testing. The dense index is for retrieval-rerank of
            # *substantive* obligation / scope clauses — definitions can
            # stay deterministic.
            keep_doc_idx: list[int] = [
                i for i in range(n_total) if bm25.sources[i] != "definition"
            ]
            n_docs = len(keep_doc_idx)
            if n_docs == 0:
                raise RuntimeError("dense corpus is empty after filter")
            # Map filtered index → original index (so search() can return
            # the original BM25 doc_idx for the article-ref join).
            self._bm25_idx_map = list(keep_doc_idx)

            # Build vocabulary from tokens that appear in ≥ 2 documents
            # (drops typo-only tokens that don't generalise). The hapax-cut
            # filters about 30% of the vocabulary surface and tightens SVD
            # signal density.
            df_count: dict[str, int] = {}
            for i in keep_doc_idx:
                for term in set(bm25.docs[i]):
                    df_count[term] = df_count.get(term, 0) + 1
            vocab_terms = sorted([t for t, c in df_count.items() if c >= 2])
            if not vocab_terms:
                raise RuntimeError("no shared vocabulary")
            vocab = {t: i for i, t in enumerate(vocab_terms)}
            V = len(vocab)

            # Build sparse-on-paper, dense-in-numpy doc-term TF matrix.
            # n_docs ≤ ~300, |V| ≤ ~2500 → ~750k float32 cells ≈ 3 MB. Fine.
            tf = np.zeros((n_docs, V), dtype=np.float32)
            for new_i, orig_i in enumerate(keep_doc_idx):
                for term in bm25.docs[orig_i]:
                    j = vocab.get(term)
                    if j is not None:
                        tf[new_i, j] += 1.0

            # Standard IDF: log((N + 1) / (df + 1)) + 1 (smoothed sklearn-style).
            df = np.zeros(V, dtype=np.float32)
            for j, term in enumerate(vocab_terms):
                df[j] = df_count.get(term, 0)
            idf = np.log((n_docs + 1.0) / (df + 1.0)) + 1.0

            # TF-IDF = (1 + log(tf)) * idf with log-TF damping. Pure log
            # would NaN on tf=0; the np.where keeps zeros.
            with np.errstate(divide="ignore"):
                log_tf = np.where(tf > 0, 1.0 + np.log(tf), 0.0)
            tfidf = log_tf * idf  # (n_docs, V)

            # **Row-normalise to unit length BEFORE SVD.** Row-norm + raw SVD gives cosine-
            # aligned doc vectors where length variation doesn't dominate.
            row_norms = np.linalg.norm(tfidf, axis=1, keepdims=True)
            row_norms = np.where(row_norms < 1e-9, 1.0, row_norms)
            tfidf_unit = tfidf / row_norms

            # Truncated SVD: U Σ V^T = X. We take the top _PROJECTION_DIM
            # right singular vectors as the projection basis. NumPy ≥ 2.0
            # ``np.linalg.svd`` is deterministic when input is fixed.
            # full_matrices=False yields the thin SVD in ~50 ms here.
            u, s, vt = np.linalg.svd(tfidf_unit, full_matrices=False)
            k = min(_PROJECTION_DIM, vt.shape[0])
            # Doc embeddings: U[:, :k] * Σ[:k] gives the projection of each
            # original row onto the top-k right singular vectors.
            doc_vecs = (u[:, :k] * s[:k][np.newaxis, :]).astype(np.float32)
            # Normalise rows to unit length so dot product == cosine.
            norms = np.linalg.norm(doc_vecs, axis=1, keepdims=True)
            # Guard the very rare zero-norm doc — shouldn't happen given
            # the df ≥ 2 filter but defensive nonetheless.
            norms = np.where(norms < 1e-9, 1.0, norms)
            doc_vecs = doc_vecs / norms

            # Cache the projection basis + IDF + vocab for query-time use.
            # Note: NO mean to subtract — we kept tfidf_unit raw.
            self._vocab = vocab
            self._idf = idf.astype(np.float32)
            self._mean_doc_vec = None
            self._v_t = vt[:k].astype(np.float32)  # (k, V)
            self._num_docs = n_docs
            self._doc_vecs_dense = doc_vecs.astype(np.float32)

        k = self._doc_vecs_dense.shape[1]
        n_docs = self._num_docs

        try:
            import turboquant  # noqa: PLC0415

            # Outlier-Aware Mixed Precision (Zandieh et al., ICLR 2026 / Layer D of CLARA whitepaper)
            # Targets high channel variance by quantizing outlier channels at higher precision.
            # Expose as environment variables to allow production tuning.
            outlier_channels = int(os.getenv("REGENOLD_TURBOQUANT_OUTLIER_CHANNELS", "13"))
            outlier_bw = int(os.getenv("REGENOLD_TURBOQUANT_OUTLIER_BIT_WIDTH", "4")) if outlier_channels > 0 else None

            quantizer = turboquant.TurboQuant(
                dim=k,
                bit_width=_QUANT_BIT_WIDTH,
                mode="inner_product",
                seed=_INDEX_SEED,
                outlier_channels=outlier_channels,
                outlier_bit_width=outlier_bw,
            )
            # turboquant's quantize() expects float64.
            compressed = quantizer.quantize(self._doc_vecs_dense.astype(np.float64))
            self._quantizer = quantizer
            self._compressed = compressed
            self._compression_active = True
            logger.info(
                "turboquant_index: built dense index n=%d k=%d "
                "compressed=True bits=%d outliers=%d outlier_bw=%s",
                n_docs, k, _QUANT_BIT_WIDTH, outlier_channels, outlier_bw,
            )
        except Exception as exc:  # noqa: BLE001 — degrade silently
            self._compression_active = False
            logger.info(
                "turboquant_index: built dense index n=%d k=%d "
                "compressed=False reason=%s",
                n_docs, k, exc,
            )

    # --- query ----------------------------------------------------------
    def _embed_query(self, question: str) -> np.ndarray | None:
        """Embed the question into the same 128-d unit-norm subspace."""
        if not self._setup():
            return None
        import numpy as np  # noqa: PLC0415

        if self._use_external:
            try:
                from app.engines import external_embeddings  # noqa: PLC0415
                q_emb = external_embeddings.get_embedding(question, is_query=True)
                if q_emb is not None:
                    q_norm = np.linalg.norm(q_emb)
                    if q_norm > 1e-9:
                        return (q_emb / q_norm).astype(np.float32)
                return None
            except Exception as exc:  # noqa: BLE001
                logger.warning("turboquant_index: external query embedding failed. reason=%s", exc)
                return None

        from app.data.kb_search import _tokenize  # noqa: PLC0415

        tokens = _tokenize(question)
        if not tokens:
            return None
        # Sparse TF row over the same vocab.
        V = len(self._vocab)
        tf = np.zeros(V, dtype=np.float32)
        for tok in tokens:
            j = self._vocab.get(tok)
            if j is not None:
                tf[j] += 1.0
        if not tf.any():
            return None

        idf = self._idf
        assert idf is not None
        with np.errstate(divide="ignore"):
            log_tf = np.where(tf > 0, 1.0 + np.log(tf), 0.0)
        q_tfidf = log_tf * idf  # (V,)
        # Row-normalise the query the same way docs are normalised
        # (see _build — we use raw SVD on row-normalised TF-IDF).
        q_norm = np.linalg.norm(q_tfidf)
        if q_norm < 1e-9:
            return None
        q_unit = q_tfidf / q_norm

        # Project via V^T. v_t is shape (k, V), so V^T x = (k,).
        v_t = self._v_t
        assert v_t is not None
        q_proj = v_t @ q_unit  # (k,)
        norm = np.linalg.norm(q_proj)
        if norm < 1e-9:
            return None
        return (q_proj / norm).astype(np.float32)

    def search(self, question: str, *, k: int = 5) -> list[_DenseSearchHit]:
        """Top-k doc indices by inner product with the question."""
        if not self._setup():
            return []
        emb = self._embed_query(question)
        if emb is None:
            return []
        import numpy as np  # noqa: PLC0415

        if self._compression_active and self._quantizer is not None and self._compressed is not None:
            # TurboQuant's inner_product takes a float64 query.
            scores = self._quantizer.inner_product(  # type: ignore[attr-defined]
                emb.astype(np.float64), self._compressed
            )
        else:
            doc_vecs = self._doc_vecs_dense
            assert doc_vecs is not None
            scores = doc_vecs @ emb  # (n_docs,)

        n = self._num_docs
        kk = min(k, n)
        if kk <= 0:
            return []
        # argpartition gets the top-k indices in O(n) instead of O(n log n);
        # we then sort just those k for stable output ordering.
        top_idx = np.argpartition(-scores, kk - 1)[:kk]
        top_idx = top_idx[np.argsort(-scores[top_idx])]
        return [
            _DenseSearchHit(doc_idx=int(i), score=float(scores[i]))
            for i in top_idx
        ]


# Process-wide singleton for the CURRENT corpus. Built on first use, kept alive
# for the worker. ⚠ Do not read this directly on a query path — go through
# :func:`_resolve_index`, which is what keeps it aligned with the live corpus.
_INDEX = _DenseIndex()

# R338 [I2] — one built index PER CORPUS IDENTITY, mirroring the canonical
# ``kb_search._build_index_cached(maxsize=2)`` one layer down: exactly the two
# corpora ``REGENOLD_ONTOLOGY_RISK_DOCS`` can produce, so an in-process A/B
# ping-ponging between the arms pays the SVD build once per arm rather than once
# per flip (measured: 539 ms to build the gate-OFF corpus, 0.3 ms for the return
# trip). Insertion-ordered and touched on use, so the eviction past
# ``_MAX_CACHED_INDEXES`` is LRU and can never drop the index being served.
_INDEX_BY_CORPUS: dict[str, _DenseIndex] = {}
_INDEX_LOCK = threading.RLock()
_MAX_CACHED_INDEXES = 2

# Observability. A silent rebuild and a silent staleness look identical from the
# outside, which is the whole reason this bug survived — so count both, expose
# them in :func:`index_diagnostics`, and log every switch at WARNING.
_CORPUS_SWITCHES = 0   # times the live corpus stopped matching the loaded index
_STALE_REBUILDS = 0    # of those, how many needed a fresh SVD build (cache miss)


def _resolve_index() -> tuple[_DenseIndex, object]:
    """Return ``(index, bm25)`` guaranteed to describe the SAME corpus.

    R338 [I2]. The old code read a **live, gate-resolved** ``_build_index()``
    for the article-ref join but a **frozen** ``_bm25_idx_map`` from a singleton
    with a ``_loaded`` latch, with a bounds check only against ``len(idx_map)``.
    Every position in that map that still fell inside the new corpus therefore
    resolved to a DIFFERENT article, silently. This is CLAUDE.md's canonical
    inert-A/B shape ("a module-level lru_cache outliving the flip makes the A/B
    inert even with the flag in ``_engine_cache_key``", R332) in its worse
    variant: the arms here do not read flat, they read *confidently wrong*, so
    ``dynamic_ab``'s fire check passes and it prints an axis table for a
    configuration that never existed.

    The fix is to stop trusting a memo that outlives the configuration: resolve
    the live corpus first, fingerprint it, and hand back the index built for
    THAT fingerprint — rebuilding if we have never seen it.

    Returning the ``bm25`` object as well is deliberate: the caller must join
    against the very object whose identity was checked, not re-resolve it and
    reopen the race by one call width.
    """
    global _INDEX, _CORPUS_SWITCHES, _STALE_REBUILDS

    from app.data.kb_search import _build_index  # noqa: PLC0415

    bm25 = _build_index()
    live_id = _corpus_identity(bm25)

    with _INDEX_LOCK:
        current = _INDEX
        # ``_corpus_id is None`` = never built; let _setup() stamp it. A built
        # index whose stamp still matches the live corpus is reused untouched —
        # the common case, and the one production always takes (env is fixed per
        # process, so this costs one fingerprint per query and nothing else).
        if current._corpus_id is not None and current._corpus_id != live_id:
            previous_id = current._corpus_id
            _CORPUS_SWITCHES += 1
            _INDEX_BY_CORPUS.setdefault(previous_id, current)
            cached = _INDEX_BY_CORPUS.get(live_id)
            if cached is None:
                _STALE_REBUILDS += 1
                cached = _DenseIndex()
                logger.warning(
                    "turboquant_index: BM25 corpus identity changed %s -> %s "
                    "(live corpus %d docs); the loaded dense index maps %d "
                    "positions into the OLD corpus, so REBUILDING rather than "
                    "relabelling its hits. switches=%d rebuilds=%d",
                    previous_id, live_id, len(bm25.docs),
                    len(current._bm25_idx_map), _CORPUS_SWITCHES, _STALE_REBUILDS,
                )
            else:
                logger.warning(
                    "turboquant_index: BM25 corpus identity changed %s -> %s; "
                    "swapping in the dense index already built for it. "
                    "switches=%d rebuilds=%d",
                    previous_id, live_id, _CORPUS_SWITCHES, _STALE_REBUILDS,
                )
            _INDEX = cached
            current = cached

        if not current._setup():
            return current, bm25

        if current._corpus_id is not None:
            # Move-to-end on touch, so the eviction below is LRU and can never
            # pick the index we are about to serve from.
            _INDEX_BY_CORPUS.pop(current._corpus_id, None)
            _INDEX_BY_CORPUS[current._corpus_id] = current
            while len(_INDEX_BY_CORPUS) > _MAX_CACHED_INDEXES:
                _INDEX_BY_CORPUS.pop(next(iter(_INDEX_BY_CORPUS)), None)

        return current, bm25


def _reset_index_cache() -> None:
    """Drop every built dense index. Test / harness hook.

    R338 [I2]. Poking ``_INDEX._loaded = False`` by hand — what
    ``tests/test_turboquant_index.py`` used to do — is no longer a complete
    reset: the instance the caller resets may not be the one
    :func:`_resolve_index` serves, because a previously-built index for the LIVE
    corpus can still be sitting in ``_INDEX_BY_CORPUS``. Reset both, or a test
    that re-configures the build (external embeddings, outlier channels) silently
    grades a cached index built under the old configuration.

    Note this is NOT the mechanism that keeps an in-process A/B honest — that is
    :func:`_resolve_index`, automatically, with no cooperation required from the
    harness. This hook exists for the narrower case of changing something the
    corpus fingerprint cannot see.
    """
    global _INDEX, _CORPUS_SWITCHES, _STALE_REBUILDS
    with _INDEX_LOCK:
        _INDEX_BY_CORPUS.clear()
        _INDEX = _DenseIndex()
        _CORPUS_SWITCHES = 0
        _STALE_REBUILDS = 0


def dense_top_k(question: str, *, k: int = 10) -> list[tuple[str, float]]:
    """Public retrieval call — returns ``(article_ref, score)`` pairs.

    Collapses multiple doc hits sharing the same article (KB + ontology
    + corpus + definition versions of the same Art. N) to one entry
    keyed by article ref, keeping the maximum score per ref. Returns
    the empty list when:

    * env-gate is explicitly off (``REGENOLD_TURBOQUANT_DENSE=0``)
    * the query has no in-vocab tokens
    * the index failed to build (corpus empty, numpy missing, etc.)

    Callers can safely treat empty as "dense path not available; use the
    BM25-only path." This module is purely additive — no consumer is
    forced to use it.
    """
    if not is_enabled():
        return []
    # R338 [I2] — resolve the index and the corpus TOGETHER. ``_resolve_index``
    # rebuilds when the live BM25 corpus is not the one the stored positions
    # index into, so the ``idx_map`` below can no longer address a corpus it was
    # not built from.
    index, bm25 = _resolve_index()
    # Over-fetch so the article-collapse below has room to pick distinct
    # articles even when multiple top docs share the same article ref.
    hits = index.search(question, k=max(k * 4, 20))
    if not hits:
        return []
    # Belt-and-braces: ``search()`` re-enters ``_setup``/``_build``, which touch
    # ``kb_search._build_index()`` again, so re-verify rather than assume. A
    # mismatch here means the corpus moved mid-query (only reachable from a
    # concurrent env mutation); fail LOUD and EMPTY — an absent dense fill costs
    # recall, a mislabelled one costs a wrong citation.
    if index._corpus_id is not None and index._corpus_id != _corpus_identity(bm25):  # noqa: SLF001
        logger.error(
            "turboquant_index: corpus identity moved during the query "
            "(index=%s live=%s); dropping the dense fill for this call.",
            index._corpus_id, _corpus_identity(bm25),  # noqa: SLF001
        )
        return []
    # Collapse FILTERED doc_idx → original BM25 doc_idx → article_ref.
    idx_map = index._bm25_idx_map  # noqa: SLF001 — module-internal singleton
    best: dict[str, float] = {}
    for hit in hits:
        # hit.doc_idx is in the FILTERED dense corpus; map back to BM25.
        if hit.doc_idx < 0 or hit.doc_idx >= len(idx_map):
            continue
        orig_idx = idx_map[hit.doc_idx]
        ref = bm25.article_refs[orig_idx]
        prev = best.get(ref)
        if prev is None or hit.score > prev:
            best[ref] = hit.score
    out = sorted(best.items(), key=lambda t: t[1], reverse=True)
    return out[:k]


def reciprocal_rank_fusion(
    bm25_refs: list[str],
    dense_refs: list[tuple[str, float]],
    *,
    rrf_k: int = 60,
    k: int = 5,
    bm25_weight: float = 1.0,
    dense_weight: float = 1.0,
) -> list[str]:
    """Fuse a BM25 ranking with the dense ranking via weighted RRF.

    **Currently a dormant tuning knob.** The Round-31 wire path uses
    :func:`additive_dense_fill` instead — symmetric RRF traded ~0.004
    Strict Ref for ~0.004 Strict Ans on the davidath benchmark (a wash)
    so we chose the precision-safer additive fill. RRF stays in the
    public surface because the recall vs precision trade-off is a
    parameter-tunable knob: a future round can switch
    ``kb_search.top_articles_by_relevance`` to RRF with
    ``bm25_weight=2.0, dense_weight=1.0`` to keep BM25 mostly
    dominant while letting the dense ranker reshape close-score ties.
    The tests in ``tests/test_turboquant_index.py`` exercise the math
    so the tuning surface is still verified.

    For each article ref ``r``, the fused score is::

        score(r) = w_bm25 / (rrf_k + rank_bm25(r))
                 + w_dense / (rrf_k + rank_dense(r))

    where the per-ranker term contributes only if that ranker placed
    ``r``. RRF (Cormack 2009) is the standard non-parametric fusion
    baseline — no score-normalisation needed, robust to scale
    differences between BM25 and cosine.

    The ``bm25_weight`` / ``dense_weight`` parameters tilt the fusion.
    Default 1.0 each = symmetric. Setting ``dense_weight < 1`` makes
    the dense path a *tie-breaker* rather than an equal-vote ranker —
    useful when BM25 is the ground-truth ranking and dense is a
    secondary signal that should only reshape close-score competitors.

    Returns the top-``k`` refs in fused-score order.
    """
    scores: dict[str, float] = {}
    for rank, ref in enumerate(bm25_refs, start=1):
        scores[ref] = scores.get(ref, 0.0) + bm25_weight / (rrf_k + rank)
    for rank, (ref, _) in enumerate(dense_refs, start=1):
        scores[ref] = scores.get(ref, 0.0) + dense_weight / (rrf_k + rank)
    if not scores:
        return []
    fused = sorted(scores.items(), key=lambda t: t[1], reverse=True)
    return [ref for ref, _ in fused[:k]]


def additive_dense_fill(
    bm25_refs: list[str],
    dense_refs: list[tuple[str, float]],
    *,
    k: int = 5,
) -> list[str]:
    """Purely additive fusion — never displace a BM25 winner.

    Returns the BM25 ranking as-is, then APPENDS dense-only refs (those
    BM25 didn't surface) until ``k`` is reached. This is the safer of
    the two fusion strategies: it can only ADD recall, never lose
    precision. Use when the benchmark shows the dense rerank trades
    precision for recall (Round 31 first cut found BM25 saturation
    means RRF re-shuffling slightly hurts Ref Correctness).

    The order of dense-only fills follows their dense rank.
    """
    out: list[str] = list(bm25_refs[:k])
    seen = set(out)
    for ref, _ in dense_refs:
        if len(out) >= k:
            break
        if ref in seen:
            continue
        out.append(ref)
        seen.add(ref)
    return out


def index_diagnostics() -> dict[str, object]:
    """Return build metadata for debug + telemetry routes.

    Triggers a lazy build on first call. Returns ``{"loaded": False}`` if
    the index failed to build.
    """
    # R338 [I2] — goes through _resolve_index so a diagnostics call made after
    # an in-process corpus flip reports the index that would actually SERVE the
    # next query, not the one that happened to be built first.
    index, _bm25 = _resolve_index()
    if not index._setup():  # noqa: SLF001 — module-internal singleton
        return {"loaded": False, "reason": "build_failed"}

    # Safely probe outlier metadata if compression is active
    outlier_channels = 0
    outlier_bw = None
    if index._compression_active and index._quantizer is not None:
        outlier_channels = getattr(index._quantizer, "_outlier_channels", 0)
        outlier_bw = getattr(index._quantizer, "_outlier_bit_width", None)

    return {
        "loaded": True,
        "num_docs": index._num_docs,  # noqa: SLF001
        "vocab_size": len(index._vocab),  # noqa: SLF001
        "projection_dim": _PROJECTION_DIM,
        "compression_active": index._compression_active,  # noqa: SLF001
        "bit_width": _QUANT_BIT_WIDTH if index._compression_active else None,  # noqa: SLF001
        "outlier_channels": outlier_channels,
        "outlier_bit_width": outlier_bw,
        "env_enabled": is_enabled(),
        "turboquant_available": is_compressed_available(),
        # R338 [I2] — corpus provenance. ``corpus_id`` is the fingerprint the
        # stored BM25 positions are valid against; the two counters make a
        # stale-identity rebuild observable, because a silent rebuild and a
        # silent staleness look the same from outside.
        "corpus_id": index._corpus_id,  # noqa: SLF001
        "corpus_switches": _CORPUS_SWITCHES,
        "stale_rebuilds": _STALE_REBUILDS,
        "cached_corpora": len(_INDEX_BY_CORPUS),
    }


__all__ = [
    "additive_dense_fill",
    "dense_top_k",
    "index_diagnostics",
    "is_compressed_available",
    "is_enabled",
    "reciprocal_rank_fusion",
]
