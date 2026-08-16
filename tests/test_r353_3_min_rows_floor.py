"""R353.3 — the ``--min-rows`` floor on the adaptive stop.

A small ``--batch`` is how a live A/B checkpoints often (the sidecar lands
after every batch), but the adaptive-stop check at ``batch * 2`` fires on a
NULL-heavy sample and aborts a lever that needs more rows to show signal.
``--min-rows`` is the floor: keep running until at least that many rows even
if every axis resolves NULL; only stop early past the floor on a clear
WIN/LOSS verdict.
"""
from __future__ import annotations

from evals.harness import dynamic_ab as D


def _row(rid: str, answer: str = "x", refs: list[str] | None = None) -> dict:
    refs = refs or ["Article 5"]
    return {"id": rid, "source": "s", "pred_answer": answer,
            "pred_refs": refs, "error": None,
            "scores": {"ref_loose": 0.5, "ref_strict": 0.5, "ref_conc": 0.5,
                       "kw_recall": 0.5, "gold_dropped_head": 0.0,
                       "gold_dropped_exact": 0.0, "answer_chars": 1.0,
                       "n_refs": 1.0}}


def _null_analyse(base, brch, *, null_band):
    """Every axis a tight NULL — the sample that used to abort the run."""
    return {"axes": {ax: {"verdict": "NULL", "delta": 0.0, "ci_lo": -0.001,
                          "ci_hi": 0.001, "n_pairs": len(base)}
                     for ax in ("ref_loose", "ref_strict", "ref_conc",
                                "kw_recall", "gold_dropped_head",
                                "gold_dropped_exact", "ans_corr", "ref_corr",
                                "cite_faith", "ans_conc")},
            "gold": {"baseline": {"gold_dropped_head": 0.0,
                                  "gold_dropped_exact": 0.0},
                     "branch": {"gold_dropped_head": 0.0,
                                "gold_dropped_exact": 0.0},
                     "delta": 0.0}}


def _win_analyse(base, brch, *, null_band):
    res = _null_analyse(base, brch, null_band=null_band)
    res["axes"]["ref_loose"] = {"verdict": "WIN", "delta": 0.05,
                                "ci_lo": 0.01, "ci_hi": 0.09,
                                "n_pairs": len(base)}
    return res


def test_floor_prevents_early_abort_on_null_sample(monkeypatch):
    """batch=8, min_rows=30: NULL at n=16 must NOT stop the run."""
    monkeypatch.setattr(D, "_run_rows", lambda chunk, env, **kw: [
        _row(str(i)) for i in range(len(chunk))])
    monkeypatch.setattr(D, "load_probe_set",
                        lambda sources=None: [type("P", (), {"id": str(i),
                                                             "source": "s",
                                                             "live_question": "q",
                                                             "category": "c",
                                                             "gold_answer": ""})()
                                              for i in range(40)])
    monkeypatch.setattr(D, "fire_check",
                        lambda a, b: {"fired": True, "any_changed": 1,
                                      "refs_changed": 0, "answers_changed": 1,
                                      "errored": 0, "common": len(a),
                                      "changed_ids": ["0"]})
    monkeypatch.setattr(D, "_analyse", _null_analyse)
    monkeypatch.setattr(D, "_write_sidecar", lambda *a, **k: None)

    res = D.run(branch_env={"REGENOLD_MIN_ROWS_TEST": "1"}, label="t",
                max_rows=40, batch=8, local=True, endpoint=None,
                api_key=None, timeout=10, null_band=0.01, seed=1,
                min_rows=30, judge_model=None)
    # NULL at n=16 (batch*2) did not abort — ran to the first batch past the
    # floor (32 >= 30) before the NULL axes resolved the run.
    assert res["n"] == 32
    assert res["stop_reason"] == "resolved"


def test_floor_still_allows_early_stop_on_win_past_floor(monkeypatch):
    """Past the floor, a resolved WIN must still stop the run early."""
    monkeypatch.setattr(D, "_run_rows", lambda chunk, env, **kw: [
        _row(str(i)) for i in range(len(chunk))])
    monkeypatch.setattr(D, "load_probe_set",
                        lambda sources=None: [type("P", (), {"id": str(i),
                                                             "source": "s",
                                                             "live_question": "q",
                                                             "category": "c",
                                                             "gold_answer": ""})()
                                              for i in range(40)])
    monkeypatch.setattr(D, "fire_check",
                        lambda a, b: {"fired": True, "any_changed": 1,
                                      "refs_changed": 0, "answers_changed": 1,
                                      "errored": 0, "common": len(a),
                                      "changed_ids": ["0"]})
    monkeypatch.setattr(D, "_analyse", _win_analyse)
    monkeypatch.setattr(D, "_write_sidecar", lambda *a, **k: None)

    res = D.run(branch_env={"REGENOLD_MIN_ROWS_TEST": "1"}, label="t",
                max_rows=40, batch=8, local=True, endpoint=None,
                api_key=None, timeout=10, null_band=0.01, seed=1,
                min_rows=10, judge_model=None)
    # At n=16 (>= max(16, 10)) all axes resolve → early stop.
    assert res["n"] == 16
    assert res["stop_reason"] == "resolved"


def test_default_floor_zero_keeps_old_behavior(monkeypatch):
    """min_rows=0 (default) must reproduce the old batch*2 abort."""
    monkeypatch.setattr(D, "_run_rows", lambda chunk, env, **kw: [
        _row(str(i)) for i in range(len(chunk))])
    monkeypatch.setattr(D, "load_probe_set",
                        lambda sources=None: [type("P", (), {"id": str(i),
                                                             "source": "s",
                                                             "live_question": "q",
                                                             "category": "c",
                                                             "gold_answer": ""})()
                                              for i in range(40)])
    monkeypatch.setattr(D, "fire_check",
                        lambda a, b: {"fired": True, "any_changed": 1,
                                      "refs_changed": 0, "answers_changed": 1,
                                      "errored": 0, "common": len(a),
                                      "changed_ids": ["0"]})
    monkeypatch.setattr(D, "_analyse", _null_analyse)
    monkeypatch.setattr(D, "_write_sidecar", lambda *a, **k: None)

    res = D.run(branch_env={"REGENOLD_MIN_ROWS_TEST": "1"}, label="t",
                max_rows=40, batch=8, local=True, endpoint=None,
                api_key=None, timeout=10, null_band=0.01, seed=1,
                min_rows=0, judge_model=None)
    # Old behavior: NULL at n=batch*2 aborts immediately.
    assert res["n"] == 16
    assert res["stop_reason"] == "resolved"
