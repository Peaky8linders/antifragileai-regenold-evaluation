"""R350 — the graphrag / medtech / expert-review probe sources.

The live A/Bs run over a significant sample (>50) drawn from the GraphRAG
paper benchmark (40), the fresh medical/healthcare/life-sciences benchmark
(24, each with a regulator-voice gold_answer) and the 20-question expert
review set (gold derived from the EU AI Act expert's critique) — 84 rows
total. These tests pin that the sources load, that the expert-review gold
is grounded (every row carries a gold_answer and its article-less rows are
exactly the two the review flags as recital/residual-only), and that the
harness ``run()`` threads a ``--probe-sources`` filter through to the
loader.
"""

from __future__ import annotations

from evals.harness import dynamic_ab as D
from evals.harness.probe_set import load_probe_set

_THREE = ("graphrag", "medtech", "expert_review")


def test_three_source_pool_is_84_rows():
    rows = load_probe_set(sources=_THREE)
    assert len(rows) == 84  # 40 graphrag + 24 medtech + 20 expert_review


def test_live_answers_pool_is_81_rows():
    """R350.2 — the attached questions file loads: 81 rows, gold grounded,
    every expected ref resolves in the provision text, and the two OOS rows
    carry refusal gold with empty refs."""
    rows = load_probe_set(sources=("live_answers",))
    assert len(rows) == 81
    ids = [r.id for r in rows]
    assert len(ids) == len(set(ids))
    assert all(r.gold_answer for r in rows)
    from app.data.provision_text import provision_exists

    unresolved = [
        (r.id, ref) for r in rows for ref in r.expected_refs
        if not provision_exists(ref)
    ]
    assert unresolved == []
    # The two out-of-scope rows (greeting / restaurant) carry refusal gold
    # and NO expected refs — they measure the OOS guard, not retrieval.
    oos = [r for r in rows if not r.expected_refs]
    assert {r.id for r in oos} == {"live_answers:la_q55", "live_answers:la_q56"}
    assert all("EU AI Act questions only" in r.gold_answer for r in oos)


def test_pool_has_no_duplicate_ids():
    rows = load_probe_set(sources=_THREE)
    ids = [r.id for r in rows]
    assert len(ids) == len(set(ids))


def test_expert_review_gold_is_grounded():
    xr = [r for r in load_probe_set(sources=("expert_review",))]
    assert len(xr) == 20
    # Every row carries a gold answer; the only article-less rows are the two
    # the review itself flags (residual category + recital-only principles).
    assert all(r.gold_answer for r in xr)
    # Only Q7 is article-less: guiding principles live in Recital 27 (the wire
    # never cites recitals). Q6 carries the boundary refs (Art. 5 / 6 / 50)
    # because the residual category is defined BY exclusion.
    article_less = [r for r in xr if not r.expected_refs]
    assert len(article_less) == 1
    assert article_less[0].id.endswith("xr_07")


def test_medtech_rows_carry_gold_answer():
    mt = [r for r in load_probe_set(sources=("medtech",))]
    assert len(mt) == 24
    assert all(r.gold_answer for r in mt)


def test_harness_threads_probe_sources(monkeypatch):
    captured: dict = {}

    def _fake_load(**kw):
        captured.update(kw)
        return load_probe_set(sources=_THREE)

    monkeypatch.setattr(D, "load_probe_set", _fake_load)
    monkeypatch.setattr(D, "_run_rows",
                        lambda rows, env, **kw: [{
                            "id": r.id, "source": r.source, "pred_answer": "x",
                            "pred_refs": list(r.expected_refs),
                            "gold_refs": list(r.expected_refs), "error": None,
                            "latency_ms": 1.0, "http_status": 200,
                            "scores": {"ref_loose": 1.0, "ref_strict": 1.0,
                                       "ref_conc": 1.0, "kw_recall": 1.0,
                                       "gold_dropped_head": 0.0,
                                       "gold_dropped_exact": 0.0,
                                       "answer_chars": 1.0, "n_refs": 1.0},
                        } for r in rows])
    monkeypatch.setattr(D, "_write_sidecar", lambda *a, **k: None)
    res = D.run(
        branch_env={"REGENOLD_FAKE": "1"}, label="r350-probe",
        max_rows=4, batch=4, local=True, endpoint=None, api_key=None,
        timeout=30.0, null_band=0.01, seed=1,
        judge_model=None, probe_sources=_THREE,
        emit=lambda *a, **k: None,
    )
    assert captured.get("sources") == _THREE
    assert res["n"] == 4
