"""R349 — the legal_v2 judge axes join the dynamic A/B as paired deltas.

The retrieval axes (ref_loose / ref_strict / ref_conc / kw_recall) measure
WHAT WAS RETRIEVED, not whether the ANSWER is right. The Regenold rubric
scores the answer itself — answer_correctness, reference_correctness,
citation_faithfulness, answer_conciseness — and those live in
``evals.judge.legal_v2``. R349 runs them per arm over the same rows (through
the same battle-tested caller plumbing) and reports them in the SAME axis
table as ``ans_corr`` / ``ref_corr`` / ``cite_faith`` / ``ans_conc``.

Load-bearing invariants pinned here:

* the paired delta is computed per row (pass=1 / fail=0), so a judge axis is
  as falsifiable as a retrieval axis — a branch that fails the judge reads as
  a LOSS, not as a prose note;
* a pair whose EITHER arm errors is SKIPPED (counted in ``n_skipped``), never
  counted as a pass or a fail — judge errors must not masquerade as answers;
* ``_judge_rows`` fails soft: a caller exception marks the whole pass with an
  ``error`` key, never raises into the A/B;
* the ``run()`` wiring merges the judge axes into the result (and records the
  judge provenance) when a judge model is configured.
"""

from __future__ import annotations

import pytest

from evals.harness import dynamic_ab as D
from evals.harness.probe_set import ProbeRow


def _probe(rid: str, answer_gold: str = "") -> ProbeRow:
    return ProbeRow(
        id=rid,
        source="s",
        category="c",
        is_multiturn=False,
        messages=({"role": "user", "content": f"question {rid}"},),
        expected_refs=("Article 5",),
        expected_keywords=("prohibition",),
        gold_answer=answer_gold,
    )


def _rec(rid: str, answer: str) -> dict:
    return {
        "id": rid, "source": "s", "pred_answer": answer,
        "pred_refs": ["Article 5"], "gold_refs": ["Article 5"],
        "error": None, "latency_ms": 1.0, "http_status": 200,
        "scores": {
            "ref_loose": 0.5, "ref_strict": 0.5, "ref_conc": 0.5,
            "kw_recall": 0.5, "gold_dropped_head": 0.0,
            "gold_dropped_exact": 0.0, "answer_chars": float(len(answer)),
            "n_refs": 1.0,
        },
    }


def _verdict_row(rid: str, verdict: str) -> dict:
    return {
        "id": rid,
        "category": "c",
        "verdicts": {
            ax: {"verdict": verdict, "_samples_n": 1}
            for ax, _label in D._JUDGE_AXES
        },
    }


def _patch_judge_row(monkeypatch, fn):
    """Patch ``legal_v2._judge_row`` — ``_judge_rows`` imports it lazily, so
    the patch is picked up at call time (no live LLM calls in these tests)."""
    import evals.judge.legal_v2 as L

    monkeypatch.setattr(L, "_judge_row", fn)


class TestJudgeAxes:
    def test_branch_worse_reads_as_loss(self, monkeypatch):
        """All four judge axes move against the branch → LOSS on every axis."""
        def _fake(r, caller, k):  # noqa: ARG001
            return _verdict_row(
                r["id"],
                "fail" if str(r["answer"] or "").startswith("b") else "pass",
            )

        _patch_judge_row(monkeypatch, _fake)
        # R350 — n must clear `_MIN_PAIRS_FOR_VERDICT`. This asserts the
        # DIRECTION of a resolved verdict, so it needs a population the harness
        # is willing to resolve; at 2 pairs the honest answer is now
        # UNDERPOWERED (see test_two_pairs_cannot_resolve below).
        ids = ["1", "2", "3", "4"]
        base = [_rec(i, f"a{i}") for i in ids]
        brch = [_rec(i, f"b{i}") for i in ids]
        probe_by_id = {r.id: r for r in [_probe(i) for i in ids]}
        res = D._judge_axes(
            base, brch, probe_by_id, caller=object(), samples=1,
            concurrency=2, null_band=0.01,
        )
        assert "error" not in res
        for _ax, label in D._JUDGE_AXES:
            v = res["axes"][label]
            assert v["delta"] == pytest.approx(-1.0)
            assert v["baseline"] == pytest.approx(1.0)
            assert v["branch"] == pytest.approx(0.0)
            assert v["verdict"] == "LOSS"
            assert v["n_pairs"] == len(ids)

    def test_branch_better_reads_as_win(self, monkeypatch):
        def _fake(r, caller, k):  # noqa: ARG001
            return _verdict_row(
                r["id"],
                "pass" if str(r["answer"] or "").startswith("b") else "fail",
            )

        _patch_judge_row(monkeypatch, _fake)
        ids = ["1", "2", "3", "4"]
        base = [_rec(i, f"a{i}") for i in ids]
        brch = [_rec(i, f"b{i}") for i in ids]
        probe_by_id = {r.id: r for r in [_probe(i) for i in ids]}
        res = D._judge_axes(
            base, brch, probe_by_id, caller=object(), samples=1,
            concurrency=2, null_band=0.01,
        )
        assert res["axes"]["ans_corr"]["delta"] == pytest.approx(1.0)
        assert res["axes"]["ans_corr"]["verdict"] == "WIN"

    def test_two_pairs_cannot_resolve(self, monkeypatch):
        """R350 — a unanimous 2-pair result is UNDERPOWERED, not a WIN.

        The judge axes score only rows that reach Stage-2 and judge cleanly in
        BOTH arms, so they routinely land on a handful of pairs while the run
        header advertises the much larger deterministic n. A bootstrap over 1-2
        observations has (near) zero width, which used to read as the MOST
        resolved state when it is the least. Same fixture as
        ``test_branch_better_reads_as_win``, two rows short.
        """
        def _fake(r, caller, k):  # noqa: ARG001
            return _verdict_row(
                r["id"],
                "pass" if str(r["answer"] or "").startswith("b") else "fail",
            )

        _patch_judge_row(monkeypatch, _fake)
        base = [_rec("1", "a1"), _rec("2", "a2")]
        brch = [_rec("1", "b1"), _rec("2", "b2")]
        probe_by_id = {r.id: r for r in [_probe("1"), _probe("2")]}
        res = D._judge_axes(
            base, brch, probe_by_id, caller=object(), samples=1,
            concurrency=2, null_band=0.01,
        )
        v = res["axes"]["ans_corr"]
        assert v["delta"] == pytest.approx(1.0)   # direction is still reported
        assert v["n_pairs"] == 2
        assert v["verdict"] == "UNDERPOWERED"     # but it is NOT resolved

    def test_transport_error_verdict_is_not_a_real_fail(self, monkeypatch):
        """R350 — `legal_v2` returns a genuine ``{"verdict": "fail",
        "evaluation_error": "empty_answer"}`` when the answer came back empty,
        which is what a branch-arm HTTP timeout looks like from here. Scoring
        that as a real fail turned one network blip into the branch losing an
        entire answer-quality axis. The shape production actually emits — a
        `fail` verdict carrying an error marker — must be unscorable.
        """
        def _fake(r, caller, k):  # noqa: ARG001
            if r["answer"] == "b2":
                return {
                    "id": r["id"], "category": "c",
                    "verdicts": {
                        ax: {"verdict": "fail",
                             "evaluation_error": "empty_answer",
                             "_samples_n": 0}
                        for ax, _label in D._JUDGE_AXES
                    },
                }
            return _verdict_row(r["id"], "pass")

        _patch_judge_row(monkeypatch, _fake)
        ids = ["1", "2", "3", "4"]
        base = [_rec(i, f"a{i}") for i in ids]
        brch = [_rec(i, f"b{i}") for i in ids]
        probe_by_id = {r.id: r for r in [_probe(i) for i in ids]}
        res = D._judge_axes(
            base, brch, probe_by_id, caller=object(), samples=1,
            concurrency=2, null_band=0.01,
        )
        v = res["axes"]["ans_corr"]
        assert v["n_pairs"] == 3      # row "2" dropped, not scored 0.0
        assert v["n_skipped"] == 1
        assert v["delta"] == pytest.approx(0.0)   # NOT -0.25

    def test_error_on_one_arm_skips_the_pair(self, monkeypatch):
        """An errored arm must not read as a pass or a fail — only the clean
        pair survives, and the skip is counted."""
        def _fake(r, caller, k):  # noqa: ARG001
            if r["id"] == "1" and r["answer"] == "b1":
                return {
                    "id": "1", "category": "c",
                    "verdicts": {
                        ax: {"judge_error": "transport", "_samples_n": 0}
                        for ax, _label in D._JUDGE_AXES
                    },
                }
            return _verdict_row(r["id"], "pass")

        _patch_judge_row(monkeypatch, _fake)
        base = [_rec("1", "a1"), _rec("2", "a2")]
        brch = [_rec("1", "b1"), _rec("2", "b2")]
        probe_by_id = {r.id: r for r in [_probe("1"), _probe("2")]}
        res = D._judge_axes(
            base, brch, probe_by_id, caller=object(), samples=1,
            concurrency=2, null_band=0.01,
        )
        v = res["axes"]["ans_corr"]
        assert v["n_pairs"] == 1
        assert v["n_skipped"] == 1
        assert v["delta"] == pytest.approx(0.0)  # the clean pair is a no-op

    def test_caller_boom_fails_soft(self, monkeypatch):
        def _boom(r, caller, k):  # pragma: no cover
            raise RuntimeError("judge transport down")

        _patch_judge_row(monkeypatch, _boom)
        base = [_rec("1", "a1")]
        brch = [_rec("1", "b1")]
        probe_by_id = {r.id: r for r in [_probe("1")]}
        res = D._judge_axes(
            base, brch, probe_by_id, caller=object(), samples=1,
            concurrency=1, null_band=0.01,
        )
        assert "error" in res  # never raises into the A/B


class TestRunWiring:
    def test_run_merges_judge_axes(self, monkeypatch):
        """run() with a judge model → res carries the judge axes + provenance."""
        import evals.judge.legal_v2 as L

        probe_rows = [_probe("1"), _probe("2")]

        def _fake_load():
            return probe_rows

        def _fake_run_rows(rows, env, **kw):  # noqa: ARG001
            ans = "b" if env else "a"
            return [_rec(r.id, f"{ans}{r.id}") for r in rows]

        def _fake_judge_row(r, caller, k):  # noqa: ARG001
            return _verdict_row(r["id"], "pass")

        monkeypatch.setattr(D, "load_probe_set", _fake_load)
        monkeypatch.setattr(D, "_run_rows", _fake_run_rows)
        monkeypatch.setattr(D, "_write_sidecar", lambda *a, **k: None)
        monkeypatch.setattr(D, "_judge_caller", lambda *a, **k: object())
        monkeypatch.setattr(L, "_judge_row", _fake_judge_row)

        res = D.run(
            branch_env={"REGENOLD_FAKE": "1"}, label="r349-test",
            max_rows=2, batch=2, local=True, endpoint=None, api_key=None,
            timeout=30.0, null_band=0.01, seed=1,
            judge_model="claude-sonnet-4-6", judge_provider="bedrock",
            judge_concurrency=2, judge_timeout=30.0, judge_samples=1,
            emit=lambda *a, **k: None,
        )
        assert res["fire"]["fired"] is True
        for _ax, label in D._JUDGE_AXES:
            assert label in res["axes"], label
            assert res["axes"][label]["delta"] == pytest.approx(0.0)
        assert res["judge"]["model"] == "claude-sonnet-4-6"
        assert res["judge"]["provider"] == "bedrock"

    def test_run_without_judge_skips(self, monkeypatch):
        """judge_model=None (--no-judge) leaves the judge axes absent."""
        def _fake_load():
            return [_probe("1")]

        monkeypatch.setattr(D, "load_probe_set", _fake_load)
        monkeypatch.setattr(
            D, "_run_rows",
            lambda rows, env, **kw: [_rec(r.id, f"{'b' if env else 'a'}{r.id}")
                                     for r in rows],
        )
        monkeypatch.setattr(D, "_write_sidecar", lambda *a, **k: None)

        res = D.run(
            branch_env={"REGENOLD_FAKE": "1"}, label="r349-nojudge",
            max_rows=1, batch=1, local=True, endpoint=None, api_key=None,
            timeout=30.0, null_band=0.01, seed=1,
            judge_model=None, emit=lambda *a, **k: None,
        )
        assert "judge" not in res
        assert not any(label in res["axes"] for _ax, label in D._JUDGE_AXES)
