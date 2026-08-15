"""R345 — dynamic_ab control-layer inference for the shipped levers.

``dynamic_ab._infer_control_layer`` picks which known-live control flag the
probe-sensitivity check flips to prove the rows can observe the branch's
layer at all. A lever misclassified as the wrong layer still runs, but its
sensitivity probe measures the wrong thing — for a Stage-2 prompt lever it
would flip a RETRIEVAL knob and learn nothing about whether the rows can
see prompt changes.

These tests pin the classification of every lever this repo ships, so a
future flag name cannot silently fall into the wrong probe:
* R340 rerank + R341 expansion are retrieval levers (the retrieval control);
* R345's ``REGENOLD_PROMPT_V2`` (the #24 Stage-2 prompt rebuild) is a
  stage2 lever (the stage2 control) — this was the misclassification R345
  fixed by adding the ``PROMPT`` hint.
"""

from __future__ import annotations

import pytest

from evals.harness.dynamic_ab import _infer_control_layer, resolve_control


@pytest.mark.parametrize(
    ("flag", "expected_layer"),
    [
        ("REGENOLD_QUERY_EXPANSION", "retrieval"),
        ("REGENOLD_COHERE_RERANK", "retrieval"),
        ("REGENOLD_PROMPT_V2", "stage2"),
        ("REGENOLD_BM25_FALLBACK_K", "retrieval"),
        ("REGENOLD_KG_CONTEXT", "graph"),
    ],
)
def test_layer_inference(flag: str, expected_layer: str) -> None:
    assert _infer_control_layer({flag: "1"}) == expected_layer


def test_prompt_v2_probes_the_stage2_control() -> None:
    """The V1-vs-V2 confirmatory A/B (#24) must probe sensitivity with the
    stage2 control, and the control must not be the branch's own var."""
    control = resolve_control({"REGENOLD_PROMPT_V2": "1"})
    assert control is not None
    layer, env = control
    assert layer == "stage2"
    assert env == {"P2P_GRAPH_RAG_ENABLE_STAGE2": "0"}


def test_rerank_and_expansion_probe_the_retrieval_control() -> None:
    for flag in ("REGENOLD_QUERY_EXPANSION", "REGENOLD_COHERE_RERANK"):
        control = resolve_control({flag: "1"})
        assert control is not None
        layer, env = control
        assert layer == "retrieval"
        assert env == {"REGENOLD_BM25_FALLBACK_K": "2"}
