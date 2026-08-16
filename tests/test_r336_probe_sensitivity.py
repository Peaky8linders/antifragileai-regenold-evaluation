"""R336 — `dynamic_ab` must not report INERT until the probe has PROVEN it
could have observed the change.

The fire check answers "did the lever move anything?". It does not answer
"could these rows have shown me if it had?", and those have opposite remedies:
INERT means fix the feature, BLIND_PROBE means fix the rows. Conflating them
sends you to debug something that is not broken — which happened three times in
one session before the cause was pinned down.

The cause is question-dependent short-circuiting, measured in-process:

    REGENOLD_BM25_FALLBACK_K=2  FIRES  on an oblique question   (15 refs)
    REGENOLD_BM25_FALLBACK_K=2  inert  on a definitional one    (1 ref)

The definitional row resolves via a direct KB obligation lookup and never
reaches BM25, the graph, or the router — so a curated-heavy pool is blind to
every retrieval lever by construction.

These tests stub the engine out entirely (`_run_rows`), so they assert the GATE
logic rather than any model behaviour, and run in milliseconds.
"""
from __future__ import annotations

import pytest

from evals.harness import dynamic_ab as D
from evals.harness.probe_set import ProbeRow


def _rows(n: int = 4) -> list[ProbeRow]:
    return [
        ProbeRow(
            id=f"p{i}", source="unit", category="c", is_multiturn=False,
            messages=[{"role": "user", "content": f"q{i}"}],
            expected_refs=["Article 6"], expected_keywords=["high-risk"],
            gold_answer="gold",
        )
        for i in range(n)
    ]


# ── resolve_control ──────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("flag", "expected_layer"),
    [
        ("REGENOLD_CURATED_STAGE2_SKIP", "stage2"),
        ("REGENOLD_COMPLEX_GATE_WIDE", "stage2"),
        ("REGENOLD_KG_MAX_REFS", "graph"),
        ("REGENOLD_GRAPH_SEMANTIC_LAYERS", "graph"),
        ("REGENOLD_PPR_DAMPING", "graph"),
        ("REGENOLD_ENTITY_BOOST", "retrieval"),
        ("REGENOLD_SOMETHING_UNKNOWN", "retrieval"),
    ],
)
def test_control_layer_is_inferred_from_the_branch_flag(flag, expected_layer):
    """A retrieval control cannot prove a Stage-2 probe is sensitive, so the
    control must be layer-matched to the lever under test."""
    layer, env = D.resolve_control({flag: "1"})
    assert layer == expected_layer
    assert env == dict([D._CONTROL_FLAGS[expected_layer]])


def test_control_never_collides_with_the_flag_under_test():
    """Flipping the same var in both arms would make the control trivially fire
    (or trivially not) for reasons unrelated to probe sensitivity."""
    env_name = D._CONTROL_FLAGS["retrieval"][0]
    layer, env = D.resolve_control({env_name: "9"})
    assert env_name not in env, "control must not reuse the branch's own flag"
    assert layer != "retrieval"


def test_control_is_none_when_every_candidate_is_under_test():
    branch = {name: "0" for name, _ in D._CONTROL_FLAGS.values()}
    assert D.resolve_control(branch) is None


# ── probe_sensitivity_check ──────────────────────────────────────────────


def _stub_run_rows(monkeypatch, *, control_moves: bool):
    """Stub the engine: the lever NEVER moves anything; the control moves rows
    only when `control_moves` — which is exactly the BLIND_PROBE vs INERT fork.
    """
    ctrl_env = D._CONTROL_FLAGS["retrieval"][0]

    def fake(rows, arm_env, **kw):
        is_control = ctrl_env in (arm_env or {})
        out = []
        for r in rows:
            refs = ["Article 6"]
            if is_control and control_moves:
                refs = ["Article 6", "Article 99"]
            out.append({"id": r.id, "pred_answer": "a", "pred_refs": refs,
                        "row": r, "latency_ms": 1.0})
        return out

    monkeypatch.setattr(D, "_run_rows", fake)


def test_sensitivity_check_reports_blind_when_control_cannot_move_the_rows(monkeypatch):
    _stub_run_rows(monkeypatch, control_moves=False)
    rows = _rows()
    base = D._run_rows(rows, {}, local=True, endpoint=None, api_key=None, timeout=1)
    got = D.probe_sensitivity_check(
        rows, base, {D._CONTROL_FLAGS["retrieval"][0]: "2"},
        local=True, endpoint=None, api_key=None, timeout=1)
    assert got["sensitive"] is False
    assert got["rows_moved"] == 0


def test_sensitivity_check_reports_sensitive_when_control_moves_the_rows(monkeypatch):
    _stub_run_rows(monkeypatch, control_moves=True)
    rows = _rows()
    base = D._run_rows(rows, {}, local=True, endpoint=None, api_key=None, timeout=1)
    got = D.probe_sensitivity_check(
        rows, base, {D._CONTROL_FLAGS["retrieval"][0]: "2"},
        local=True, endpoint=None, api_key=None, timeout=1)
    assert got["sensitive"] is True
    assert got["rows_moved"] == len(rows)


# ── the gate ─────────────────────────────────────────────────────────────


def _run_gate(monkeypatch, *, control_moves: bool):
    monkeypatch.setattr(D, "load_probe_set", lambda **kw: _rows(4))
    _stub_run_rows(monkeypatch, control_moves=control_moves)
    return D.run(
        branch_env={"REGENOLD_ENTITY_BOOST": "0"}, label="unit",
        max_rows=4, batch=2, local=True, endpoint=None, api_key=None,
        timeout=1, null_band=0.01, seed=1, emit=lambda *_: None,
    )


def test_flat_lever_on_a_blind_probe_is_BLIND_PROBE_not_INERT(monkeypatch):
    """The regression this file exists for. Same flat lever, blind rows: the
    verdict must point at the ROWS, and must not be reported as a finding about
    the feature."""
    res = _run_gate(monkeypatch, control_moves=False)
    assert res["verdict"] == "BLIND_PROBE"
    assert res["sensitivity"]["sensitive"] is False
    assert "axes" not in res, "a blind probe must not produce an axis table"


def test_flat_lever_on_a_sensitive_probe_is_a_real_INERT(monkeypatch):
    """Same flat lever, rows PROVEN able to see the layer: now INERT is a real
    finding about the lever, and the evidence is attached."""
    res = _run_gate(monkeypatch, control_moves=True)
    assert res["verdict"] == "INERT"
    assert res["sensitivity"]["sensitive"] is True
    assert res["sensitivity"]["rows_moved"] > 0
    assert "axes" not in res


def test_the_two_verdicts_are_distinguishable(monkeypatch):
    """Belt and braces: the fork must actually fork. If both branches returned
    the same verdict this whole file would be decorative."""
    blind = _run_gate(monkeypatch, control_moves=False)["verdict"]
    real = _run_gate(monkeypatch, control_moves=True)["verdict"]
    assert blind != real, "BLIND_PROBE and INERT must not collapse together"
