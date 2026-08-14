"""R334 — every ENGINE-level env flag must be part of the engine cache identity.

Why this file exists, in one sentence: an engine flag missing from
``_engine_cache_key`` makes an in-process A/B measure NOTHING, because the
branch arm is served the baseline arm's cached ``GraphRAGResponse``.

That is not hypothetical. R326 (``REGENOLD_GRAPH_VECTOR_RECALL``), R327
(``REGENOLD_GRAPH_SEMANTIC_LAYERS``) and three R329 reranker placements each
shipped a clean ``+0.0000`` A/B on a feature that never executed, and R327's
50-row paired run returned byte-identical answers AND byte-identical reference
lists on all 50 rows — while arm B averaged 1,096 ms against arm A's 16,642 ms,
i.e. every row was a cache hit and Stage-2 never re-ran. "Byte-identical" and
"inert" are the same picture.

Three properties are asserted here:

1. Each registered engine flag CHANGES the key when flipped (it fires).
2. Route-level flags do NOT change the key (the asymmetry is preserved — route
   post-processing re-runs on every cache hit, so folding route flags in would
   only shatter the cache and destroy the paired A/B the key exists to enable).
3. DRIFT GUARD: every ``REGENOLD_*`` / ``P2P_*`` env var read anywhere under
   ``app/engines/`` is either in the key or in an explicit, justified exemption
   list. This is the test that stops the list rotting again — adding a new
   engine flag without registering it fails here, by name.
"""
from __future__ import annotations

import pathlib
import re

import pytest

from app.routes.regenold import _engine_cache_key

_Q = "What are the transparency obligations for a hospital chatbot?"


def _key() -> str:
    return _engine_cache_key(_Q, None, 0, False)


# Flags R334 added. Each is read inside the engine and moves GraphRAGResponse.
R334_ADDED = [
    "REGENOLD_CURATED_STAGE2_SKIP",
    "REGENOLD_DEFINITIONAL_STAGE2_SKIP",
    "REGENOLD_STAGE2_ANSWER_HEADROOM",
    "REGENOLD_COMPLEX_GATE_WIDE",
    "REGENOLD_COMPLEX_SENTENCE_CAP",
    "REGENOLD_GRAPH_EXPANSION",
    "REGENOLD_FUSION_MIN_CANDIDATES",
    "REGENOLD_FUSION_TIMEOUT",
    "REGENOLD_PPR_DAMPING",
    "REGENOLD_PPR_MAX_ITER",
    "REGENOLD_QA_LEAD_RANK",
    "REGENOLD_ROLE_DUTY_ZRF",
    "REGENOLD_NLI_API",
]

# Read under app/engines/ but consumed from the ROUTE, so deliberately NOT in
# the key. `clara_logic.analyse` is called from routes/regenold.py at the
# Component-D stage; route post-processing re-runs on every cache hit.
ROUTE_LEVEL_EXEMPT = {
    "REGENOLD_CLARA_MODEL",
    "REGENOLD_CLARA_TIMEOUT",
    "REGENOLD_CLARA_FAILURE_THRESHOLD",
    "REGENOLD_CLARA_FAILURE_WINDOW",
}

# Folded into the key by a dedicated component rather than the engine_flags
# tuple, so the textual scan below would otherwise report a false positive.
KEYED_ELSEWHERE = {
    "P2P_GRAPH_RAG_PROVIDER",   # -> provider_bit
}


@pytest.mark.parametrize("flag", R334_ADDED)
def test_engine_flag_changes_the_cache_key(flag, monkeypatch):
    """A registered engine flag must FIRE — flipping it must move the key.

    This is the fire check. A flag that fails here is one whose A/B would
    report +0.0000 and mean nothing.
    """
    monkeypatch.delenv(flag, raising=False)
    before = _key()
    monkeypatch.setenv(flag, "9")
    assert _key() != before, (
        f"{flag} is read inside the engine but does not change the engine cache "
        f"key. An in-process A/B over it measures NOTHING: the branch arm is "
        f"served the baseline arm's cached GraphRAGResponse."
    )


@pytest.mark.parametrize("flag", sorted(ROUTE_LEVEL_EXEMPT))
def test_route_level_flag_does_not_change_the_cache_key(flag, monkeypatch):
    """The asymmetry is load-bearing, so assert it in both directions.

    Route flags must stay OUT: the route re-runs on every cache hit, so they
    cannot serve a stale answer, and folding them in would shatter the cache
    and destroy the paired A/B.
    """
    monkeypatch.delenv(flag, raising=False)
    before = _key()
    monkeypatch.setenv(flag, "9")
    assert _key() == before, (
        f"{flag} is consumed by ROUTE post-processing, which re-runs on every "
        f"cache hit. Folding it into the engine cache key only shatters the "
        f"cache and breaks the paired A/B."
    )


def _keyed_flags() -> set[str]:
    src = pathlib.Path("app/routes/regenold.py").read_text(encoding="utf-8")
    m = re.search(r'engine_flags = ":"\.join\((.*?)\n    \)\n', src, re.DOTALL)
    assert m, "could not locate the engine_flags tuple in _engine_cache_key"
    return set(re.findall(r'"([A-Z0-9_]+)"', m.group(1)))


def _engine_env_reads() -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for path in pathlib.Path("app/engines").rglob("*.py"):
        text = path.read_text(encoding="utf-8", errors="replace")
        for var in re.findall(
            r'os\.(?:getenv|environ\.get)\(\s*["\']([A-Z0-9_]+)["\']', text
        ):
            out.setdefault(var, set()).add(path.as_posix())
    return out


def test_no_unregistered_engine_flag_drifts_in():
    """DRIFT GUARD — the test that stops this list rotting again.

    Every ``REGENOLD_*`` / ``P2P_*`` env var read under ``app/engines/`` must be
    either in the cache key or explicitly exempted above. A new engine flag
    added without registering it fails here BY NAME, with the file that reads
    it, rather than silently producing an inert A/B six rounds later.
    """
    keyed = _keyed_flags()
    known = keyed | ROUTE_LEVEL_EXEMPT | KEYED_ELSEWHERE
    unregistered = {
        var: files
        for var, files in _engine_env_reads().items()
        if var.startswith(("REGENOLD_", "P2P_")) and var not in known
    }
    assert not unregistered, (
        "Env vars read inside app/engines/ but absent from _engine_cache_key:\n"
        + "\n".join(
            f"  {var}  ({', '.join(sorted(files))})"
            for var, files in sorted(unregistered.items())
        )
        + "\n\nEither add each to the engine_flags tuple in "
        "app/routes/regenold.py::_engine_cache_key, or — if it is consumed by "
        "ROUTE post-processing rather than the engine — add it to "
        "ROUTE_LEVEL_EXEMPT in this file with a one-line reason."
    )
