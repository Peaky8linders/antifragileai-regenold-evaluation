"""CRAG-style corrective verification & NLI citation grounding (plan §6, §8).

Provides:
  - `EntailmentScorer` ABC interface
  - `LexicalEntailmentScorer` (zero-latency IDF coverage proxy)
  - `NLIEntailmentScorer` (`cross-encoder/nli-deberta-v3-large` neural cross-encoder)
  - `CragThresholds` (keep, abstain thresholds)
"""

from __future__ import annotations

import math
import os
from abc import ABC, abstractmethod
from collections import Counter
from dataclasses import dataclass
from typing import Any

from app.engines.retrieval_stack import tokenize

__all__ = [
    "EntailmentScorer",
    "LexicalEntailmentScorer",
    "NLIEntailmentScorer",
    "CragThresholds",
    "DEFAULT_NLI_MODEL",
]

DEFAULT_NLI_MODEL = "cross-encoder/nli-deberta-v3-large"
_DEFAULT_ENTAIL_INDEX = 1


def _softmax(xs: list[float]) -> list[float]:
    if not xs:
        return []
    m = max(xs)
    exps = [math.exp(x - m) for x in xs]
    total = sum(exps)
    if total == 0.0:
        return [1.0 / len(xs)] * len(xs)
    return [e / total for e in exps]


class EntailmentScorer(ABC):
    """Scores how strongly a premise (provision text) supports a claim."""

    name: str = "entailment"

    @abstractmethod
    def score(self, claim: str, premise: str) -> float:
        raise NotImplementedError

    def score_batch(self, claim: str, premises: list[str]) -> list[float]:
        return [self.score(claim, p) for p in premises]


class LexicalEntailmentScorer(EntailmentScorer):
    """IDF-weighted coverage of the claim by the premise (zero latency)."""

    def __init__(self, provisions: list[Any]) -> None:
        docs = [
            tokenize(getattr(p, "text", None) or str(p.get("text", ""))) for p in provisions
        ]
        n = len(docs)
        df: Counter[str] = Counter()
        for toks in docs:
            df.update(set(toks))
        self._idf: dict[str, float] = {
            t: math.log((1 + n) / (1 + d)) + 1.0 for t, d in df.items()
        }
        self.name = "lexical-coverage"

    def score(self, claim: str, premise: str) -> float:
        claim_terms = set(tokenize(claim))
        if not claim_terms:
            return 0.0
        weights = {t: self._idf.get(t, 1.0) for t in claim_terms}
        total = sum(weights.values())
        if total == 0.0:
            return 0.0
        premise_terms = set(tokenize(premise))
        covered = sum(w for t, w in weights.items() if t in premise_terms)
        return covered / total


class NLIEntailmentScorer(EntailmentScorer):
    """Sentence-pair NLI entailment via CrossEncoder."""

    def __init__(
        self,
        model_name: str = DEFAULT_NLI_MODEL,
        *,
        model=None,
        batch_size: int = 16,
        entail_index: int | None = None,
        apply_softmax: bool = True,
    ) -> None:
        self.model_name = model_name
        self.batch_size = batch_size
        self.apply_softmax = apply_softmax
        self._model = model
        self._model_loaded = model is not None
        self._entail_index = (
            entail_index
            if entail_index is not None
            else _DEFAULT_ENTAIL_INDEX
        )
        self.name = f"nli:{model_name}"

    @staticmethod
    def _load(model_name: str):
        try:
            from sentence_transformers import CrossEncoder
            return CrossEncoder(model_name)
        except Exception as e:
            return None

    @staticmethod
    def _resolve_entail_index(model, default: int) -> int:
        if model is None:
            return default
        config = getattr(model, "config", None)
        id2label = getattr(config, "id2label", None) if config else None
        if isinstance(id2label, dict):
            for idx, label in id2label.items():
                if str(label).lower() in {"entailment", "entails"}:
                    return int(idx)
        return default

    def score(self, claim: str, premise: str) -> float:
        return self.score_batch(claim, [premise])[0]

    def score_batch(self, claim: str, premises: list[str]) -> list[float]:
        if not premises:
            return []

        # 1. Remote GPU / CPU Service Check (HuggingFace TEI / Railway endpoint)
        explicit_base = (
            os.getenv("NLI_API_BASE")
            or os.getenv("TEI_API_BASE")
            or os.getenv("REGENOLD_NLI_API")
        )
        api_bases = [explicit_base] if explicit_base else [
            "http://text-embeddings-inference.railway.internal:8080",
            "http://text-embeddings-inference.railway.internal",
            "http://127.0.0.1:8080",
        ]

        import httpx
        for api_base in api_bases:
            if not api_base:
                continue
            # Try payload formats (with and without model param for standard TEI)
            payloads = [
                {"query": claim, "texts": premises},
                {"query": claim, "texts": premises, "model": self.model_name},
            ]
            for payload in payloads:
                try:
                    resp = httpx.post(
                        f"{api_base.rstrip('/')}/rerank",
                        json=payload,
                        timeout=2.5,
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        # TEI rerank output format: [{"index": 0, "score": 0.95}, ...]
                        if isinstance(data, list):
                            indexed_scores = {
                                item.get("index", i): item.get("score", 0.0)
                                for i, item in enumerate(data)
                            }
                            return [indexed_scores.get(i, 0.0) for i in range(len(premises))]
                except Exception:
                    continue  # Try next payload or base

        # 2. In-Process Model Fallback (Lazy loaded)
        if not self._model_loaded:
            self._model = self._load(self.model_name)
            self._model_loaded = True
            if self._model is not None:
                self._entail_index = self._resolve_entail_index(self._model, self._entail_index)

        if self._model is None:
            return [0.0] * len(premises)

        pairs = [[premise, claim] for premise in premises]
        try:
            raw = self._model.predict(pairs, batch_size=self.batch_size)
        except Exception:
            return [0.0] * len(premises)

        out: list[float] = []
        for row in raw:
            probs = _softmax(list(row)) if self.apply_softmax else list(row)
            out.append(float(probs[self._entail_index]) if self._entail_index < len(probs) else 0.0)
        return out


@dataclass(frozen=True)
class CragThresholds:
    """CRAG keep and abstain thresholds."""

    keep: float = 0.0
    abstain: float = 0.0
