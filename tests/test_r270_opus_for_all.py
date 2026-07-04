"""R270 — opus-for-all env knob (default OFF; ab_judge WASH, not shipped ON).

The live pairwise ab_judge (paper_st_v4, n=6, position-swapped, Sonnet-4-6
judge, 2026-07-04) found routing standard Stage-2 to Opus 4.8 a statistical
wash: correctness/refs leaned branch 1-0 (5 ties), conciseness leaned baseline
3-2, tone leaned baseline 2-0 — nothing near significance and a slight lean
AGAINST the rubric's conciseness/tone axes. So the knob ships **default OFF**
(prod stays Sonnet-5 standard / Opus-4.8 complex). These tests pin that default
and the cache-key doctrine so a future flip is deliberate, not silent.
"""
import importlib
import os

import pytest

os.environ.setdefault("P2P_GRAPH_RAG_PROVIDER", "cli")


@pytest.fixture(autouse=True)
def _clean_env():
    saved = os.environ.get("REGENOLD_OPUS_FOR_ALL")
    os.environ.pop("REGENOLD_OPUS_FOR_ALL", None)
    yield
    if saved is None:
        os.environ.pop("REGENOLD_OPUS_FOR_ALL", None)
    else:
        os.environ["REGENOLD_OPUS_FOR_ALL"] = saved


def _g():
    from app.engines import graph_rag
    return graph_rag


def test_opus_for_all_default_off():
    """Unset REGENOLD_OPUS_FOR_ALL -> disabled (prod = Sonnet-5 standard)."""
    assert _g()._opus_for_all_enabled() is False


@pytest.mark.parametrize("val,expect", [
    ("1", True), ("true", True), ("YES", True), ("On", True),
    ("0", False), ("false", False), ("", False), ("no", False),
])
def test_opus_for_all_toggle(val, expect):
    os.environ["REGENOLD_OPUS_FOR_ALL"] = val
    assert _g()._opus_for_all_enabled() is expect


def test_opus_for_all_in_engine_cache_key():
    """R30/R56/R79 doctrine — the flag flips the Stage-2 answer MODEL, so it
    must be part of the cache identity (else OFF/ON blobs cross-contaminate)."""
    from app.routes import regenold as route
    q, ctx = "What does Article 13 require?", None
    os.environ.pop("REGENOLD_OPUS_FOR_ALL", None)
    k_off = route._engine_cache_key(q, ctx)
    os.environ["REGENOLD_OPUS_FOR_ALL"] = "1"
    k_on = route._engine_cache_key(q, ctx)
    assert k_off != k_on
