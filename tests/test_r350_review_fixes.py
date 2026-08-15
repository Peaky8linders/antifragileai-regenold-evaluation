"""R350 — regression pins for the multi-agent code review of R341-R349.

Each class pins ONE defect the review found, and each test states the failure it
prevents rather than merely exercising the happy path. Where the original defect
survived because no test asserted the invariant at all, that is called out — an
untested invariant is how every one of these shipped.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.engines import cohere_rerank as cr
from evals.harness import dynamic_ab as D
from evals.judge import legal_v2 as L


class TestKGPoolOrdersButNeverAdmits:
    """Hard rule #10 — the graph is additive CONTEXT, never a wire citation.

    R347 built the KG candidate pool as a SUPERSET of the keyword entities and
    then did ``entities = reranked``, adopting every CROSS_REFERENCES neighbour
    into the entity set. ``entities`` become obligations, obligations become
    ``CitationNode``s, and those become the wire ``references`` — so graph
    adjacency was emitting citations. Measured with an identity rerank (the
    cross-encoder expressing no preference, which still returns ok=True):
    a chatbot-transparency question gained ``Art. 98`` (Committee procedure —
    comitology), and a FRIA question went 3 refs -> 11.

    No test asserted the membership invariant, which is why it shipped.
    """

    def test_pool_is_a_superset_of_the_entities(self):
        pool = cr.build_kg_candidate_pool_with_reasons(["Art. 50"], per_ref=3)
        assert pool, "no KG edges for Art. 50 — fixture assumption broken"
        assert all(ref not in ("Art. 50",) for ref, _ in pool)

    def test_projection_preserves_membership_under_worst_case_rerank(self):
        """The cross-encoder ranking every KG neighbour ABOVE the keyword hit
        must still not change which provisions are cited."""
        original = ["Art. 50"]
        pairs = cr.build_kg_candidate_pool_with_reasons(original, per_ref=3)
        pool = list(original) + [e for e, _ in pairs]
        # Worst case: the rerank inverts, putting KG neighbours first.
        reranked = list(reversed(pool))
        projected = [r for r in reranked if r in set(original)]
        assert projected == original
        assert not (set(projected) - set(original)), (
            "a KG-sourced provision reached the entity set — hard rule #10"
        )

    def test_ok_is_true_even_for_a_noop_rerank(self):
        """The ok-bit means "the API answered", NOT "the ranking changed".

        The adoption bug was amplified by this: a successful NOOP also returns
        ok=True, so the pool expansion landed even when the cross-encoder had
        expressed no preference at all. Pinned so nobody re-reads ok as a
        "the ranking is meaningful" signal.
        """
        assert "successful noop" in (cr.rerank_pool.__doc__ or "")


class TestRerankKGHopsIsLive:
    """R348 shipped ``REGENOLD_RERANK_KG_HOPS`` wired to the WRONG builder.

    ``rerank_kg_hops()`` reached only ``build_kg_candidate_pool``, which the
    caller uses solely in the ``else`` of ``if pairs:``. But
    ``cross_refs_with_reason`` resolves a pair for essentially every entity, so
    that branch almost never ran: 5/5 representative questions produced
    byte-identical pools at hops=1 and hops=2.

    The flag WAS registered in ``_engine_cache_key``, so both arms were
    cache-distinct and genuinely re-ran — the fire check passed on Stage-2
    noise and the harness would have reported an axis table for a depth change
    that never happened. The inert-feature trap arriving through the guard
    built to catch it.
    """

    def test_hops_2_expands_the_with_reasons_pool(self):
        one = cr.build_kg_candidate_pool_with_reasons(["Art. 6"], hops=1)
        two = cr.build_kg_candidate_pool_with_reasons(["Art. 6"], hops=2)
        assert len(two) > len(one), (
            "hops=2 did not expand the reasons pool — the depth knob is inert"
        )
        assert {r for r, _ in one} <= {r for r, _ in two}

    def test_hop2_reasons_are_labelled_as_transitive(self):
        two = cr.build_kg_candidate_pool_with_reasons(["Art. 6"], hops=2)
        one_refs = {r for r, _ in cr.build_kg_candidate_pool_with_reasons(
            ["Art. 6"], hops=1)}
        hop2 = [(r, reason) for r, reason in two if r not in one_refs]
        assert hop2, "no hop-2 neighbours to check"
        assert all(reason.startswith("via ") for _r, reason in hop2), (
            "a transitive edge must be distinguishable from a direct one"
        )

    def test_hops_1_budget_is_not_reduced_by_the_split(self):
        """A depth knob must not change the depth-1 result.

        The 2:1 split was computed unconditionally, so hops=1 silently capped
        the pool at 2/3 of ``max_extra`` — meaning "hops=1 is the existing
        behaviour" was false and an A/B would have measured two changes.
        """
        assert cr._hop_budgets(8, 1) == (8, 0)
        assert cr._hop_budgets(8, 2) == (5, 3)

    def test_pool_has_no_duplicates_at_either_depth(self):
        for hops in (1, 2):
            pool = cr.build_kg_candidate_pool(["Art. 6", "Art. 9"], hops=hops)
            assert len(pool) == len(set(pool))


class TestFireCheckIgnoresTransportErrors:
    """An ERROR is not a divergence.

    ``fire_check`` compared ``pred_refs``/``pred_answer`` with no error filter
    while ``_analyse`` drops any row that errored in either arm. An errored row
    carries ``pred_answer == ""`` and ``pred_refs == []``, which always differs
    from a healthy baseline — so a branch-arm timeout counted as the lever
    firing, the INERT gate passed, and the very rows that "proved" it fired
    were then excluded from every axis. The harness's defining property
    inverted: the instrument breaking made a dead lever look alive.
    """

    @staticmethod
    def _rows(branch_error: bool):
        base = [{"id": "1", "pred_refs": ["A"], "pred_answer": "x"},
                {"id": "2", "pred_refs": ["B"], "pred_answer": "y"}]
        brch = [{"id": "1", "pred_refs": ["A"], "pred_answer": "x"},
                {"id": "2", "pred_refs": ([] if branch_error else ["B"]),
                 "pred_answer": ("" if branch_error else "y")}]
        if branch_error:
            brch[1]["error"] = "timeout: read timed out"
        return base, brch

    def test_an_inert_lever_with_a_timeout_does_not_read_as_fired(self):
        f = D.fire_check(*self._rows(branch_error=True))
        assert f["fired"] is False, "a transport error was counted as a change"
        assert f["errored"] == 1
        assert f["common"] == 1

    def test_a_genuinely_inert_lever_still_reads_inert(self):
        f = D.fire_check(*self._rows(branch_error=False))
        assert f["fired"] is False
        assert f["errored"] == 0


class TestJudgeVerdictScorability:
    """``legal_v2`` returns a REAL ``verdict: "fail"`` carrying
    ``evaluation_error: "empty_answer"`` when the answer came back empty —
    which is exactly what a branch-arm HTTP timeout produces.

    The pair filter tested only the verdict STRING, so that scored as a genuine
    0.0 and one network blip read as the branch losing an entire answer-quality
    axis. ``_scorable`` is now the single definition, shared with
    ``_pair_scored``.
    """

    @pytest.mark.parametrize("verdict,expected", [
        ({"verdict": "pass"}, True),
        ({"verdict": "fail"}, True),
        ({"verdict": "FAIL"}, True),
        ({"verdict": "fail", "evaluation_error": "empty_answer"}, False),
        ({"verdict": "pass", "judge_error": "no_json"}, False),
        ({"judge_error": "unbalanced_json"}, False),
        ({"verdict": None}, False),
        ({}, False),
    ])
    def test_scorable(self, verdict, expected):
        assert D._scorable(verdict) is expected

    def test_absent_is_not_zero(self):
        """A missing verdict must be UNSCORABLE, never a 0.0 reading."""
        assert D._scorable({}) is False
        assert D._scorable({"verdict": ""}) is False


class TestUnderpoweredBelowMinimumPairs:
    """A bootstrap over one observation has zero width, which read as the MOST
    resolved state when it is the least. The judge axes score only rows that
    reach Stage-2 and judge cleanly in both arms, so they routinely land on a
    couple of pairs while the header advertises the deterministic n.
    """

    def test_single_pair_ci_is_unbounded(self):
        assert D._bootstrap_ci([1.0]) == (float("-inf"), float("inf"))

    @pytest.mark.parametrize("n", [1, 2])
    def test_below_the_floor_never_resolves(self, n):
        lo, hi = D._bootstrap_ci([1.0] * n)
        assert D._verdict(1.0, lo, hi, null_band=0.01, n_pairs=n) == "UNDERPOWERED"

    def test_at_the_floor_a_unanimous_result_resolves(self):
        deltas = [1.0] * D._MIN_PAIRS_FOR_VERDICT
        lo, hi = D._bootstrap_ci(deltas)
        assert D._verdict(1.0, lo, hi, null_band=0.01,
                          n_pairs=len(deltas)) == "WIN"


class TestControlLayerInference:
    """R345 fixed ``REGENOLD_PROMPT_V2`` being probed at the retrieval layer.
    The flags added immediately AFTER that fix reintroduced the same bug:
    ``REGENOLD_RERANK_KG_CANDIDATES`` / ``_HOPS`` contain ``KG_``, so they
    inferred layer=graph and probed with ``REGENOLD_KG_CONTEXT=0`` — a Stage-2
    context switch that cannot exercise the rerank pool at all.

    Getting this wrong flips the diagnosis between "fix the feature" (exit 2)
    and "fix the rows" (exit 3): opposite actions.
    """

    @pytest.mark.parametrize("flag,layer", [
        ("REGENOLD_RERANK_KG_CANDIDATES", "retrieval"),
        ("REGENOLD_RERANK_KG_HOPS", "retrieval"),
        ("REGENOLD_COHERE_RERANK", "retrieval"),
        ("REGENOLD_QUERY_EXPANSION", "retrieval"),
        ("REGENOLD_PROMPT_V2", "stage2"),
        ("REGENOLD_KG_CONTEXT", "graph"),
        ("REGENOLD_GRAPH_SEMANTIC_LAYERS", "graph"),
    ])
    def test_layer(self, flag, layer):
        assert D._infer_control_layer({flag: "1"}, emit=lambda _s: None) == layer

    def test_an_unmatched_flag_says_so_out_loud(self):
        """A silent default is how PROMPT_V2 was probed at the wrong layer for
        a whole round: the inference looked authoritative and was guessing."""
        said: list[str] = []
        assert D._infer_control_layer(
            {"REGENOLD_TOTALLY_MADE_UP": "1"}, emit=said.append) == "retrieval"
        assert said and "INFERRED" in said[0]


class TestSidecarWriteIsAtomic:
    """The checkpoint was a bare ``write_text``, which truncates before writing.
    An interrupt destroyed the PREVIOUS good checkpoint too — and it is called
    after every batch precisely so a killed multi-hour run keeps its rows.
    """

    def test_replace_leaves_no_partial_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(D, "_RESULTS", tmp_path)
        res = {"label": "x", "n_scored": 1, "baseline_rows": [{"id": "1"}],
               "branch_rows": [{"id": "1"}]}
        D._write_sidecar(res, "atomic-test")
        out = tmp_path / "dynamic-ab-atomic-test.json"
        assert json.loads(out.read_text(encoding="utf-8"))["label"] == "x"
        # a second write must not leave the temp file behind
        D._write_sidecar(res, "atomic-test")
        assert not list(tmp_path.glob("*.tmp"))

    def test_sidecar_is_strict_valid_json(self, tmp_path, monkeypatch):
        """R350 — non-finite floats must never reach the durable artefact.

        ``json.dumps`` emits bare ``Infinity``/``NaN``, which Python round-trips
        happily but which RFC 8259 does not define — ``jq``, browsers and every
        strict parser reject the whole file. This became reachable in the same
        round: ``_bootstrap_ci`` returns ``(-inf, +inf)`` for a single
        observation. A run whose evidence cannot be re-read by standard tooling
        has lost its evidence, so this test parses with ``parse_constant``
        raising — the only way to actually catch it from Python.
        """
        monkeypatch.setattr(D, "_RESULTS", tmp_path)
        res = {
            "label": "inf", "n_scored": 1,
            "axes": {"ans_corr": {"ci_lo": float("-inf"),
                                  "ci_hi": float("inf"), "delta": 1.0}},
            "baseline_rows": [], "branch_rows": [],
        }
        D._write_sidecar(res, "inf-test")
        raw = (tmp_path / "dynamic-ab-inf-test.json").read_text(encoding="utf-8")
        assert "Infinity" not in raw and "NaN" not in raw

        def _reject(const):
            raise ValueError(f"non-JSON constant {const!r} in sidecar")

        parsed = json.loads(raw, parse_constant=_reject)
        assert parsed["axes"]["ans_corr"]["ci_lo"] is None

    def test_json_safe_leaves_finite_values_alone(self):
        assert D._json_safe({"a": 1.5, "b": [0.0, -2.5], "c": "x", "d": None}) == {
            "a": 1.5, "b": [0.0, -2.5], "c": "x", "d": None,
        }


class TestJudgeAxisAnsweredGuard:
    """`legal_v2` recomputed each axis's verdict from `raw.get(key) or []` with
    no check that the model had answered that axis at all. A reply carrying
    `{"verdict": "fail", "failure_mode": "…"}` and none of the axis's arrays
    parsed cleanly and postprocessed to **pass** — the unsafe direction, on the
    shipped grading path with no flag.

    ⚠ The FIRST fix for this gated on ONE array per axis and was too narrow in
    the direction that loses data: `reference_correctness` also answers through
    `missing_governing`, `answer_conciseness` through `unrequested_topics`, and
    the array a model is most likely to omit is the EMPTY one — which is the
    pass case. Both directions are pinned here.
    """

    _NO_AXIS_KEYS = {"verdict": "fail", "failure_mode": "Article 6 mismatched"}

    def test_reply_with_no_axis_keys_is_unscorable(self):
        for axis, call in [
            ("citation_faithfulness",
             lambda r: L._postprocess_citation_faithfulness(
                 r, {"Article 6": "t"}, ["Article 6"])),
            ("reference_correctness",
             lambda r: L._postprocess_reference_correctness(
                 r, {"Article 6": "t"}, {}, ["Article 6"])),
            ("answer_correctness",
             lambda r: L._postprocess_answer_correctness(r, {"Article 6": "t"})),
        ]:
            out = call(dict(self._NO_AXIS_KEYS))
            assert out.get("verdict") is None, f"{axis} still produced a verdict"
            assert out["judge_error"] == f"axis_unanswered_{axis}"

    def test_empty_arrays_still_score_because_empty_is_the_pass(self):
        out = L._postprocess_citation_faithfulness(
            {"citations": []}, {"Article 6": "t"}, ["Article 6"])
        assert out.get("judge_error") is None
        assert out["verdict"] == "pass"

    def test_axis_answered_through_its_OTHER_key_still_scores(self):
        """The narrow first fix discarded these. Both are real findings."""
        conc = L._postprocess_answer_conciseness(
            {"sentence_count": 5, "unrequested_topics": ["Detailed GDPR mechanics."]},
            "a. b. c. d. e.")
        assert conc.get("judge_error") is None

        ref = L._postprocess_reference_correctness(
            {"missing_governing": [{"ref": "Article 6", "quote": "x"}]},
            {}, {"Article 6": "t"}, [])
        assert ref.get("judge_error") is None

    def test_every_axis_has_a_key_set(self):
        """A new axis without an entry would silently never be guarded."""
        assert set(L._AXIS_KEYS) == {
            "answer_correctness", "reference_correctness",
            "citation_faithfulness", "answer_conciseness",
        }


class TestTransportOutageIsNotALeverResult:
    """R350.1 — excluding errored rows from the fire check (correct) created a
    new way to be wrong: if most rows error, `common` collapses, `fired` goes
    False, and the run reported INERT ("fix the feature") or BLIND_PROBE ("fix
    the rows"). Both remedies are wrong for a dead endpoint or an expired key —
    and `_report` returns early on exactly those verdicts, so the `errored`
    count that would explain it never printed.
    """

    def test_all_rows_errored_is_a_transport_verdict_not_inert(self):
        base = [{"id": str(i), "pred_refs": ["A"], "pred_answer": "x"}
                for i in range(4)]
        brch = [{"id": str(i), "pred_refs": [], "pred_answer": "",
                 "error": "timeout"} for i in range(4)]
        f = D.fire_check(base, brch)
        assert f["fired"] is False and f["common"] == 0 and f["errored"] == 4
        ratio = f["errored"] / (f["errored"] + f["common"])
        assert ratio >= D._TRANSPORT_FAILURE_RATIO

    def test_a_few_errors_do_not_trip_the_transport_verdict(self):
        base = [{"id": str(i), "pred_refs": ["A"], "pred_answer": "x"}
                for i in range(10)]
        brch = [{"id": str(i), "pred_refs": ["A"], "pred_answer": "x"}
                for i in range(10)]
        brch[0] = {"id": "0", "pred_refs": [], "pred_answer": "", "error": "t"}
        f = D.fire_check(base, brch)
        assert f["errored"] == 1
        assert f["errored"] / (f["errored"] + f["common"]) < D._TRANSPORT_FAILURE_RATIO

    def test_report_prints_the_error_count_on_early_return_verdicts(self):
        """The one line that separates "the lever is dead" from "the endpoint
        is dead" must survive the verdicts a dead endpoint actually produces."""
        for verdict in ("INERT", "BLIND_PROBE", "TRANSPORT"):
            lines: list[str] = []
            D._report({"verdict": verdict, "fire": {"errored": 7, "common": 1}},
                      emit=lines.append)
            assert any("errored" in ln for ln in lines), verdict


class TestReportSurvivesOnACp1252Console:
    """R349's judge-provenance line used U+2500 (a box-drawing character).

    Windows with a cp1252 console is the documented platform and
    ``sys.stdout.encoding`` is cp1252 here. That line sat BETWEEN the axis
    table and the gold_dropped veto block, so ``_report`` raised
    UnicodeEncodeError and the HARD RULE #8 VETO never printed — and because
    ``_write_sidecar`` ran after ``_report``, the whole run's data was lost too.
    A multi-hour live A/B losing its verdict AND its rows to a box character.
    """

    def test_every_report_line_encodes_on_cp1252(self):
        src = Path(D.__file__).read_text(encoding="utf-8")
        offenders = []
        for i, line in enumerate(src.splitlines(), 1):
            if "emit(" not in line and "print(" not in line:
                continue
            try:
                line.encode("cp1252")
            except UnicodeEncodeError as exc:
                offenders.append((i, hex(ord(line[exc.start]))))
        assert not offenders, (
            f"cp1252-unencodable characters on output lines: {offenders}"
        )
