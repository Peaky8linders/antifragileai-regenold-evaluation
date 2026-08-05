"""Baseline protocol + runner for the §8 evaluation.

A baseline maps a benchmark item to a list of citation strings. The runner
collects those into the ``{item_id: [citation, ...]}`` JSON that
``eu-ai-act-benchmark/scorer.py`` consumes -- so any baseline (naive retrieval,
frontier LLM, or a future full GraphRAG system) is scored by the exact same
harness on the exact same footing.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path

__all__ = ["Baseline", "question_text", "run_baseline", "write_predictions"]


def question_text(item: dict) -> str:
    """Flatten a benchmark item into a single query string: the question plus any
    structured scenario fields (role / system_type / intended_use / …)."""
    parts = [item.get("question", "")]
    scenario = item.get("scenario")
    if isinstance(scenario, dict):
        for key in ("role", "system_type", "intended_use", "input_data", "domain"):
            val = scenario.get(key)
            if val:
                parts.append(f"{key}: {val}")
    return "\n".join(p for p in parts if p)


class Baseline(ABC):
    """A system under evaluation. Implementations hold whatever state they need
    (a retriever index, an LLM client, …) and turn one item into citations."""

    #: short identifier used in prediction-file provenance / logs
    name: str = "baseline"

    @abstractmethod
    def predict(self, item: dict) -> list[str]:
        """Return the citation strings this system would cite for ``item``
        (eid or human form; may be empty to abstain)."""
        raise NotImplementedError


def run_baseline(baseline: Baseline, items: list[dict]) -> dict[str, list[str]]:
    """Run ``baseline`` over every item, returning ``{item_id: [citation, ...]}``."""
    return {item["id"]: list(baseline.predict(item)) for item in items}


def write_predictions(path: Path, predictions: dict[str, list[str]]) -> None:
    """Write predictions as the JSON the scorer expects (deterministic key order)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {k: predictions[k] for k in sorted(predictions)}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
