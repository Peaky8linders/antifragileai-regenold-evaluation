"""Live Deep Evaluation Runner across Hard Statutory Scenarios & Expert Benchmarks.

Runs:
1. The 20 Antifragile Human Expert Review Questions (with mistake resolution & reviewer critique tracking).
2. The Top-10 Hardest Content Scenarios from July-7 (Complex Decision Boundary, GPAI Systemic Risk, MedTech MDR, Two-Article Conflict).
3. Full multi-level metric calculation (Jaccard Loose, Keyword Recall Strict, ROUGE-L LCS F1, Semantic Similarity Proxy, Ref Loose/Strict, Ref Conciseness, CRAG Fine, Regulatory Tone, Latency).
4. Grounded proposition verification & judge remarks analysis.

CLI:
    # honours an exported P2P_GRAPH_RAG_PROVIDER; resolves an unset one to
    # openai_wrapper (the LIVE path this module is named after)
    py -3.12 -m evals.bench.run_live_deep_eval

    # explicit override, e.g. the deterministic no-Stage-2 path for a smoke test
    py -3.12 -m evals.bench.run_live_deep_eval --provider cli

⚠ This runner is NOT a merge gate. `evals.harness.dynamic_ab` is (CLAUDE.md,
Validation policy). Read `run_config.stage2_landed_rate` in the output before
quoting any number from here: at 0.0 the run took the deterministic path and
every prompt / judge / reranker / KG-context change was invisible to it.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from app.main import app
from app.llm import resolve_provider
from app.rate_limit import limiter

from evals.bench.metrics import (
    answer_correctness_loose,
    answer_correctness_strict,
    answer_keyword_recall,
    answer_rouge_l,
    answer_semantic_similarity_proxy,
    reference_correctness_loose,
    reference_correctness_strict,
    reference_conciseness,
    regulatory_tone,
    threshold_precision_recall_curve,
)
from evals.regenold.antifragile_groundtruth import ANTIFRAGILE_GT
from evals.regenold.antifragile_reviewer_remarks import ANTIFRAGILE_REVIEWER_REMARKS

# R338/[C3] — ONE CONCEPT, ONE DEFINITION. `_mistake_resolved` is the canonical
# per-mistake resolver (R333 gave it head-normalised reference matching); `_norm`
# is the exact answer normalisation it expects its first argument to already have
# been through; `_parse_reasoning` is the canonical scraper for the reasoning
# trace. All three are imported rather than re-implemented — the from-scratch copy
# this module used to carry is precisely the divergence this repo keeps paying for.
from evals.regenold.antifragile_live import (
    _mistake_resolved as canonical_mistake_resolved,
)
from evals.regenold.antifragile_live import _norm as canonical_norm
from evals.regenold.antifragile_live import (
    _parse_reasoning as canonical_parse_reasoning,
)
from app.data.provision_text import get_provision_text


# 10 Hard Content Scenarios from July-7 & SOTA
HARD_JULY7_SCENARIOS = [
    {
        "id": "hard_july7_01_emotion_workplace",
        "category": "Borderline Prohibition & Exception",
        "question": "Is an AI system that detects worker fatigue and emotional stress in a manufacturing plant prohibited under the EU AI Act?",
        "gold_answer": "Emotion-recognition AI systems in the workplace are prohibited under Article 5(1)(f), except where placed on the market or put into service strictly for medical or safety reasons.",
        "expected_refs": ["Article 5.1.f", "Article 5"],
        "expected_keywords": ["prohibited", "emotion", "workplace", "safety", "medical", "Article 5"],
    },
    {
        "id": "hard_july7_02_gpai_systemic",
        "category": "GPAI & Systemic Risk Boundary",
        "question": "What criteria trigger the systemic risk classification for a general-purpose AI model, and what additional obligations apply to its provider?",
        "gold_answer": "Under Article 51, a general-purpose AI model is presumed to have systemic risk if its cumulative compute during training exceeds 10^25 FLOPs. Providers of systemic GPAI models must perform model evaluation (Article 55(1)(a)), assess and mitigate systemic risks (Article 55(1)(b)), report serious incidents (Article 55(1)(c)), and ensure adequate cybersecurity protection (Article 55(1)(d)).",
        "expected_refs": ["Article 51", "Article 55"],
        "expected_keywords": ["systemic risk", "10^25", "FLOPs", "Article 51", "Article 55", "model evaluation", "mitigation", "cybersecurity"],
    },
    {
        "id": "hard_july7_03_article_6_3_derogation",
        "category": "Complex Decision Boundary",
        "question": "When is an AI system listed in Annex III exempt from being classified as high-risk under Article 6(3)?",
        "gold_answer": "An Annex III AI system is not high-risk if it does not pose a significant risk of harm to health, safety, or fundamental rights and fulfills at least one of four conditions under Article 6(3): (a) performs a narrow procedural task, (b) improves the result of a previous human activity, (c) detects decision patterns without replacing human assessment, or (d) performs a preparatory task. Profiling natural persons always prevents this exemption.",
        "expected_refs": ["Article 6.3", "Article 6", "Annex III"],
        "expected_keywords": ["derogation", "significant risk", "procedural task", "profiling", "Article 6", "Annex III"],
    },
    {
        "id": "hard_july7_04_medtech_notified_body",
        "category": "Cross-Framework & Sectoral MedTech Integration",
        "question": "What conformity assessment procedure applies to an AI software classified as a high-risk medical device under MDR and the EU AI Act?",
        "gold_answer": "Under Article 43(3), high-risk AI systems that are safety components of medical devices undergo a single, integrated conformity assessment procedure under Regulation (EU) 2017/745 (MDR) involving a notified body competent for both medical devices and AI requirements.",
        "expected_refs": ["Article 43.3", "Article 43", "Annex I", "Article 6.1"],
        "expected_keywords": ["conformity assessment", "medical device", "MDR", "notified body", "Article 43", "Article 6"],
    },
    {
        "id": "hard_july7_05_article_10_special_data",
        "category": "Two-Article Conflict & Reconciliation",
        "question": "Does the EU AI Act allow the processing of special categories of personal data to identify and correct bias in high-risk AI models?",
        "gold_answer": "Yes, Article 10(5) provides a specific derogation permitting providers of high-risk AI systems to process special categories of personal data strictly to the extent necessary for bias detection and correction, subject to appropriate safeguards including pseudonymization, encryption, and strict access controls, without prejudice to GDPR.",
        "expected_refs": ["Article 10.5", "Article 10"],
        "expected_keywords": ["special categories", "bias correction", "derogation", "Article 10", "pseudonymization", "safeguards"],
    },
    {
        "id": "hard_july7_06_value_chain_transition",
        "category": "Complex Decision Boundary",
        "question": "Under what circumstances does a downstream deployer or distributor become legally classified as a provider under Article 25?",
        "gold_answer": "Under Article 25(1), any distributor, importer, deployer, or third party is considered a provider and assumes all provider obligations if they: (a) put their name or trademark on a high-risk AI system, (b) make a substantial modification to a high-risk AI system, or (c) modify the intended purpose of an AI system such that it becomes high-risk.",
        "expected_refs": ["Article 25.1", "Article 25"],
        "expected_keywords": ["provider", "deployer", "trademark", "substantial modification", "intended purpose", "Article 25"],
    },
    {
        "id": "hard_july7_07_fria_article_27",
        "category": "Complex Decision Boundary",
        "question": "Who is obligated to perform a Fundamental Rights Impact Assessment under Article 27, and what must it include?",
        "gold_answer": "Under Article 27, deployers that are bodies governed by public law or private entities providing public services, as well as deployers of high-risk AI in credit scoring and life/health insurance, must perform a FRIA prior to putting the system into service. The assessment must detail intended processes, timeframe, affected natural persons, specific fundamental rights risks, human oversight measures, and mitigation plans.",
        "expected_refs": ["Article 27", "Article 26"],
        "expected_keywords": ["fundamental rights impact assessment", "FRIA", "deployers", "public law", "insurance", "credit scoring", "Article 27"],
    },
    {
        "id": "hard_july7_08_serious_incident_clocks",
        "category": "Cross-Framework & Sectoral MedTech Integration",
        "question": "What are the mandatory reporting deadlines for serious incidents under Article 73 of the EU AI Act?",
        # R338 gold correction. The previous wording attached the 10-day clock to
        # "death of a person OR serious harm to a person's health". Resolved against
        # the pin (CELEX 32024R1689, pre-Omnibus) via get_provision_text:
        #   Article 73(4): "Notwithstanding paragraph 2, in the event of the DEATH OF
        #   A PERSON, the report shall be provided ... not later than 10 days ..."
        # Death only. "Serious harm to a person's health" is the OTHER limb of the
        # Article 3(49)(a) serious-incident definition and carries NO special clock,
        # so it falls back to Article 73(2)'s general 15 days. Grading an answer that
        # correctly said "15 days for serious harm to health" against the old gold
        # would have penalised the right law.
        "gold_answer": "Under Article 73, providers must report serious incidents immediately and no later than: (a) 15 days generally after becoming aware (Article 73(2)), including where the incident is serious harm to a person's health, (b) 2 days in the event of a widespread infringement or a serious and irreversible disruption of critical infrastructure (Article 73(3)), or (c) 10 days in the event of the death of a person (Article 73(4)).",
        "expected_refs": ["Article 73"],
        "expected_keywords": ["serious incident", "15 days", "2 days", "10 days", "critical infrastructure", "death", "Article 73"],
    },
    {
        "id": "hard_july7_09_annex_iv_technical_file",
        "category": "Complex Decision Boundary",
        "question": "What specific elements must be documented in the technical documentation of a high-risk AI system under Annex IV?",
        "gold_answer": "Annex IV requires: general description of the AI system, design specifications and algorithms, computational resources and training methods (Annex IV(2)(c)), risk management system file (Article 9), data governance and validation records (Article 10), human oversight measures (Article 14), cybersecurity safeguards (Article 15), logging mechanism documentation (Article 12), and post-market monitoring plan (Article 72).",
        "expected_refs": ["Article 11", "Annex IV"],
        "expected_keywords": ["technical documentation", "system architecture", "computational resources", "risk management", "Annex IV", "Article 11"],
    },
    {
        "id": "hard_july7_10_penalties_tier_ceiling",
        "category": "Borderline Prohibition & Exception",
        "question": "What are the maximum administrative fine thresholds under Article 99 for non-compliance with the EU AI Act?",
        # R338 gold correction: the third tier is 1 %, not 1.5 %. Resolved against the
        # pin via get_provision_text("Article 99.5"): "...administrative fines of up to
        # EUR 7 500 000 or, if the offender is an undertaking, up to 1 % of its total
        # worldwide annual turnover ...". 1.5 % is not a figure that appears anywhere
        # in Article 99. This string is persisted verbatim as `gold_answer` into the
        # results sidecar, so the wrong number propagated into every artefact.
        "gold_answer": "Article 99 establishes three fine tiers: (1) up to EUR 35 000 000 or 7% of total worldwide annual turnover for violations of Article 5 prohibited practices; (2) up to EUR 15 000 000 or 3% for non-compliance with provider or deployer high-risk obligations; (3) up to EUR 7 500 000 or 1% for supplying incorrect, incomplete or misleading information to notified bodies or national competent authorities.",
        "expected_refs": ["Article 99.3", "Article 99.4", "Article 99.5", "Article 99"],
        # ⚠ The percentage entries here are INERT under the scorer: metrics._tokens
        # strips them to the empty set ("1.5%", "1%", "7%", "3%" all tokenise to []),
        # so they contribute nothing to `answer_keyword_recall`'s denominator. They are
        # corrected anyway because the list is read by humans, but do NOT read a
        # keyword-recall movement here as evidence the percentage changed.
        "expected_keywords": ["35 000 000", "7%", "15 000 000", "3%", "7 500 000", "1%", "prohibited", "penalties", "Article 99"],
    },
]


_CONSTRAINT_KINDS_IN_VERIFY = ("present", "present_any", "absent")


def _mistake_constraint_count(mistake: dict[str, Any]) -> int:
    """How many evaluable constraints a GT mistake record actually carries.

    Counts all FIVE kinds the canonical resolver honours. A record scoring 0 here
    is unfalsifiable — it would resolve for every possible answer — so the runner
    refuses to count it (see :func:`evaluate_mistake_resolution`). Measured
    2026-08-15 on ``ANTIFRAGILE_GT``: 0 of 38 mistakes score 0, so this guard is
    a standing tripwire for a future GT edit, not a live filter.
    """
    verify = mistake.get("verify", {}) or {}
    n = sum(len(verify.get(k) or []) for k in _CONSTRAINT_KINDS_IN_VERIFY)
    return n + len(mistake.get("ref_present") or []) + len(mistake.get("ref_absent") or [])


def evaluate_mistake_resolution(
    pred_ans: str,
    pred_refs: list[str],
    mistakes: list[dict[str, Any]],
) -> dict[str, Any]:
    """Aggregate the CANONICAL per-mistake resolver over one row's mistakes.

    R338/[C3]. This function used to be a from-scratch reimplementation that read
    only ``verify.present`` and ``verify.absent``, and did not accept ``pred_refs``
    at all. ``ANTIFRAGILE_GT`` carries three more constraint kinds that
    ``evals/regenold/antifragile_live._mistake_resolved`` has always honoured:
    ``verify.present_any``, ``mistake['ref_present']`` and
    ``mistake['ref_absent']`` — the last two being *reference* constraints, which
    were structurally unevaluable here because the predicted references were never
    passed in even though they were in scope at the call site.

    The consequence was not a small drift. Measured over all 20 GT rows with the
    EMPTY STRING as the predicted answer, the old code resolved 14 of 38 mistakes,
    and **11 of 38 were resolved for every possible answer** (``q02_m3``,
    ``q03_m3``, ``q04_m2``, ``q06_m1``, ``q07_m2``, ``q10_m1``, ``q10_m2``,
    ``q13_m1``, ``q14_m2``, ``q15_m1``, ``q18_m3`` — each has empty ``present``
    AND empty ``absent``, so both ``... if X else True`` guards returned True).
    Handed the string "This system is governed by Annex II and Article 27, and
    also Article 5 and Annex III apply.", ``q02_m3`` (``ref_absent=['Annex II',
    'Article 27']``) and ``q14_m2`` (``ref_absent=['Article 5', 'Annex III']``)
    both scored FIXED — the metric certifying a mistake as resolved inside the
    very text that makes it.

    So: no second copy. Delegate to the canonical resolver, thread the wire
    ``references`` through, and normalise the answer with the same ``_norm`` the
    resolver's contract assumes its first argument has already been through
    (lowercase + unicode hyphen/superscript folding).
    """
    answer_low = canonical_norm(pred_ans or "")
    refs = list(pred_refs or [])

    resolved = 0
    evaluable = 0
    details: list[dict[str, Any]] = []
    for m in mistakes:
        n_constraints = _mistake_constraint_count(m)
        if n_constraints == 0:
            # FAIL CLOSED. A mistake nothing can falsify is not evidence that the
            # mistake was fixed; it is evidence the GT record is incomplete.
            is_fixed = False
        else:
            evaluable += 1
            is_fixed = canonical_mistake_resolved(answer_low, refs, m)
        if is_fixed:
            resolved += 1
        details.append({
            "mistake_id": m.get("id"),
            "desc": m.get("desc"),
            "fixed": is_fixed,
            "constraints": n_constraints,
        })
    return {
        "total_mistakes": len(mistakes),
        "evaluable_mistakes": evaluable,
        "unfalsifiable_mistakes": len(mistakes) - evaluable,
        "resolved_mistakes": resolved,
        # ``None`` for a row with no expert-flagged mistakes (q19). A rate over an
        # empty set is not 1.0; reporting it as 1.0 puts a perfect score on a row
        # that was never asked a question.
        "resolution_rate": round(resolved / len(mistakes), 4) if mistakes else None,
        "details": details,
    }


# ``?include_reasoning=true`` is what makes ``stage2_landed`` observable at all.
# Without it the route returns no trace and this runner cannot tell a Stage-2
# answer from a deterministic one — which is the whole of [I7]. Measured
# 2026-08-15 on the plain path: ``reasoning`` comes back as the EMPTY STRING, so
# ``_parse_reasoning`` returns all-``None`` and ``stage2_landed`` would be a
# constant ``False`` for every row on every provider — the dead-feature shape.
#
# ⚠ BUT THE PROBE IS NOT FREE, AND THAT IS NOT OBVIOUS. Activating the trace is
# an OBSERVER EFFECT on the system being measured: `_graph_rag_impl.py:8160-8166`
# sets ``force_stage2 = True`` whenever ``reasoning_trace.current()`` is not
# ``None``, so this runner asks a slightly different question than a plain
# caller does. Measured 2026-08-15, ``force_stage2`` has exactly TWO consumers
# and BOTH are default-OFF gates, so under the shipped defaults the coupling is
# inert — verified end-to-end on ``provider=cli``: plain vs ``?include_reasoning``
# returned byte-identical answers AND byte-identical reference lists.
#
#   * `_graph_rag_impl.py:8195` — the ``REGENOLD_STAGE2_SIMPLE_SKIP`` skip is
#     suppressed by ``force_stage2``. Flip that flag ON and this runner keeps
#     Stage-2 on rows where production would ship the deterministic answer.
#   * `_graph_rag_impl.py:8277-8289` — at ``_compute_confidence(context) < 0.5``
#     it fires a supplemental DuckDuckGo search into the Stage-2 context. Gated
#     behind ``REGENOLD_STAGE2_WEB_SEARCH`` (default OFF); flip it ON and this
#     runner grounds some rows on web snippets production never sees.
#
# So: with either flag ON, `stage2_landed_rate` measures a property the
# observation itself partly creates, and the numbers are no longer a measurement
# of the deployed configuration. `regenold.py:1963-1972` (R104) also folds
# ``reasoning:{0|1}`` into ``_engine_cache_key``, so the two paths never share a
# cache entry — correct, and it means a run here cannot be compared row-for-row
# against a plain-path run either. Re-check both gates before quoting a number.
_ASK_PATH = "/api/v1/regenold/eu-ai-act/ask?include_reasoning=true"


def _ask(client: TestClient, question: str) -> tuple[dict[str, Any], float, int]:
    """One request. Returns ``(body, latency_ms, http_status)``.

    R338 — two hardening fixes over the inline call this replaces:

    * ``limiter.reset()`` is called PER REQUEST, matching every other runner in
      the repo (``evals/bench/runner.py:_ask``). It used to be called once before
      the loop, which is not a reset policy at all: this runner issues 30 requests
      against a 30/min bucket, so the 31st of any longer run — or any run sharing
      the process with another suite — starts getting 429s that the old code then
      scored as an empty answer.
    * ``resp.status_code`` is RETURNED. It was never inspected, so a 429/500/503
      fell into the bare ``except`` below, became ``answer="" / references=[]``,
      and was scored 0.0 on eight axes. A transport failure that looks like a
      quality failure is the instrument trap in miniature.
    """
    try:
        limiter.reset()
    except Exception:  # noqa: BLE001
        pass
    start = time.perf_counter()
    resp = client.post(_ASK_PATH, json=[{"role": "user", "content": question}])
    elapsed = (time.perf_counter() - start) * 1000.0
    try:
        body = resp.json()
    except Exception:  # noqa: BLE001
        body = {"answer": "", "references": [], "reasoning": None}
    if not isinstance(body, dict):
        body = {"answer": "", "references": [], "reasoning": None}
    return body, elapsed, resp.status_code


def _mean(rows: list[dict[str, Any]], key: str) -> float | None:
    """Mean over SCORED rows only — ``None`` entries (error rows) are excluded.

    An HTTP error row carries ``None`` on every axis rather than 0.0, so it can
    never silently drag an average down as if the system had answered badly.
    """
    vals = [r[key] for r in rows if r.get(key) is not None]
    return round(sum(vals) / len(vals), 4) if vals else None


def _resolve_run_provider(provider: str | None) -> str:
    """[I7] — READ WITH A DEFAULT, DO NOT ASSIGN. Returns the resolved provider.

    The old code did an unconditional ``os.environ["P2P_GRAPH_RAG_PROVIDER"] =
    provider`` with ``provider`` defaulted to ``"cli"`` at the CLI. So a module
    calling itself a *Live* Deep Evaluation silently OVERWROTE an operator's
    exported provider and ran the deterministic, no-Stage-2 path — the instrument
    trap, in the runner whose entire purpose is to measure the live path.

    New contract, in precedence order:

    1. an explicit ``--provider`` is an operator instruction and is honoured
       (it is the only case that writes to the environment);
    2. otherwise an exported ``P2P_GRAPH_RAG_PROVIDER`` stands, untouched;
    3. otherwise unset/``auto`` resolves the way the engine itself resolves it,
       via the canonical :func:`app.llm.resolve_provider` — to ``openai_wrapper``.

    Note that in case 3 nothing is written either: the engine performs the same
    resolution internally, so the returned value is a REPORT of what will run,
    not a mutation that makes it run.
    """
    if provider:
        os.environ["P2P_GRAPH_RAG_PROVIDER"] = provider
    return resolve_provider(
        os.environ.get("P2P_GRAPH_RAG_PROVIDER"),
        default_when_auto="openrouter",
    )


def run_live_eval(provider: str | None = None, output_path: str | None = None) -> dict[str, Any]:
    resolved_provider = _resolve_run_provider(provider)
    print(f"[Live Deep Eval] resolved provider: {resolved_provider}")
    if resolved_provider == "cli":
        print(
            "[Live Deep Eval] WARNING: provider=cli — this is the DETERMINISTIC path with NO "
            "Stage-2. Prompt, judge, reranker and KG-context changes are invisible to "
            "this run. Do not report these numbers as a live measurement."
        )

    client = TestClient(app)

    # ── Section 1: Antifragile Expert Questions (20 rows) ───────────
    print("\n" + "=" * 90)
    print("RUNNING LIVE EVALUATION: 20 ANTIFRAGILE HUMAN EXPERT REVIEW QUESTIONS")
    print("=" * 90)

    af_results = []
    total_mistakes_count = 0
    total_mistakes_resolved = 0
    total_mistakes_unfalsifiable = 0
    stage2_models: set[str] = set()

    for qid, data in ANTIFRAGILE_GT.items():
        q_text = data["question"]
        gold_ans = data["gold_answer"]
        gold_refs = data["gold_refs"]
        kws = data.get("expected_keywords", [])
        mistakes = data.get("mistakes", [])
        reviewer_remark = ANTIFRAGILE_REVIEWER_REMARKS.get(qid, {}).get("review", "")

        body, latency_ms, status = _ask(client, q_text)

        if status != 200:
            # An HTTP failure is an ERROR, not a zero. Recording it as 0.0 on eight
            # axes would report a transport problem as a quality regression, and
            # would then be silently averaged into the headline number.
            af_results.append({
                "qid": qid,
                "question": q_text,
                "gold_answer": gold_ans,
                "gold_refs": gold_refs,
                "http_status": status,
                "error": f"http_{status}",
                "predicted_answer": None,
                "predicted_refs": None,
                "reviewer_remark": reviewer_remark,
                "jaccard": None, "rouge_l": None, "semantic_similarity": None,
                "keyword_recall": None, "ref_loose": None, "ref_strict": None,
                "ref_conciseness": None, "regulatory_tone": None,
                "stage2_landed": None,
                "latency_ms": round(latency_ms, 2),
                "mistake_resolution": None,
            })
            print(f"[{qid}] ERROR http_{status} — row excluded from every axis (not scored 0.0)")
            continue

        pred_ans = body.get("answer", "")
        pred_refs = body.get("references", []) or []
        trace = canonical_parse_reasoning(body.get("reasoning"))
        stage2_landed = bool(trace.get("stage2_polish"))
        if trace.get("stage2_model"):
            stage2_models.add(trace["stage2_model"])

        # Metrics
        jaccard = answer_correctness_loose(pred_ans, gold_ans)
        rouge_l = answer_rouge_l(pred_ans, gold_ans)
        sem_sim = answer_semantic_similarity_proxy(pred_ans, gold_ans)
        kw_rec = answer_keyword_recall(pred_ans, kws)
        ref_l = reference_correctness_loose(pred_refs, gold_refs)
        ref_s = reference_correctness_strict(pred_refs, gold_refs)
        ref_c = reference_conciseness(pred_refs, gold_refs)
        tone = regulatory_tone(pred_ans)

        # Mistake verification — canonical resolver, WITH the wire references.
        m_eval = evaluate_mistake_resolution(pred_ans, pred_refs, mistakes)
        total_mistakes_count += m_eval["total_mistakes"]
        total_mistakes_resolved += m_eval["resolved_mistakes"]
        total_mistakes_unfalsifiable += m_eval["unfalsifiable_mistakes"]

        af_results.append({
            "qid": qid,
            "question": q_text,
            "gold_answer": gold_ans,
            "gold_refs": gold_refs,
            "http_status": status,
            "error": None,
            "predicted_answer": pred_ans,
            "predicted_refs": pred_refs,
            "reviewer_remark": reviewer_remark,
            "jaccard": round(jaccard, 4),
            "rouge_l": round(rouge_l, 4),
            "semantic_similarity": round(sem_sim, 4),
            "keyword_recall": round(kw_rec, 4) if kw_rec is not None else 0.0,
            "ref_loose": round(ref_l, 4),
            "ref_strict": round(ref_s, 4),
            "ref_conciseness": round(ref_c, 4),
            "regulatory_tone": round(tone, 4),
            "stage2_landed": stage2_landed,
            "stage2_model": trace.get("stage2_model"),
            "latency_ms": round(latency_ms, 2),
            "mistake_resolution": m_eval,
        })
        print(f"[{qid}] Jaccard: {jaccard:.3f} | ROUGE-L: {rouge_l:.3f} | SBERT: {sem_sim:.3f} | RefL: {ref_l:.3f} | RefS: {ref_s:.3f} | S2: {int(stage2_landed)} | Fixed: {m_eval['resolved_mistakes']}/{m_eval['total_mistakes']}")

    # ── Section 2: Hard July-7 SOTA Scenarios (10 rows) ─────────────
    print("\n" + "=" * 90)
    print("RUNNING LIVE EVALUATION: 10 HARDEST JULY-7 CONTENT SCENARIOS")
    print("=" * 90)

    hard_results = []
    for scn in HARD_JULY7_SCENARIOS:
        q_id = scn["id"]
        q_text = scn["question"]
        gold_ans = scn["gold_answer"]
        gold_refs = scn["expected_refs"]
        kws = scn["expected_keywords"]

        body, latency_ms, status = _ask(client, q_text)

        if status != 200:
            hard_results.append({
                "id": q_id,
                "category": scn["category"],
                "question": q_text,
                "gold_answer": gold_ans,
                "gold_refs": gold_refs,
                "http_status": status,
                "error": f"http_{status}",
                "predicted_answer": None,
                "predicted_refs": None,
                "jaccard": None, "rouge_l": None, "semantic_similarity": None,
                "keyword_recall": None, "ref_loose": None, "ref_strict": None,
                "ref_conciseness": None, "regulatory_tone": None,
                "stage2_landed": None,
                "latency_ms": round(latency_ms, 2),
            })
            print(f"[{q_id:<32}] ERROR http_{status} — row excluded from every axis (not scored 0.0)")
            continue

        pred_ans = body.get("answer", "")
        pred_refs = body.get("references", []) or []
        trace = canonical_parse_reasoning(body.get("reasoning"))
        stage2_landed = bool(trace.get("stage2_polish"))
        if trace.get("stage2_model"):
            stage2_models.add(trace["stage2_model"])

        # Metrics
        jaccard = answer_correctness_loose(pred_ans, gold_ans)
        rouge_l = answer_rouge_l(pred_ans, gold_ans)
        sem_sim = answer_semantic_similarity_proxy(pred_ans, gold_ans)
        kw_rec = answer_keyword_recall(pred_ans, kws)
        ref_l = reference_correctness_loose(pred_refs, gold_refs)
        ref_s = reference_correctness_strict(pred_refs, gold_refs)
        ref_c = reference_conciseness(pred_refs, gold_refs)
        tone = regulatory_tone(pred_ans)

        hard_results.append({
            "id": q_id,
            "category": scn["category"],
            "question": q_text,
            "gold_answer": gold_ans,
            "gold_refs": gold_refs,
            "http_status": status,
            "error": None,
            "predicted_answer": pred_ans,
            "predicted_refs": pred_refs,
            "jaccard": round(jaccard, 4),
            "rouge_l": round(rouge_l, 4),
            "semantic_similarity": round(sem_sim, 4),
            "keyword_recall": round(kw_rec, 4) if kw_rec is not None else 0.0,
            "ref_loose": round(ref_l, 4),
            "ref_strict": round(ref_s, 4),
            "ref_conciseness": round(ref_c, 4),
            "regulatory_tone": round(tone, 4),
            "stage2_landed": stage2_landed,
            "stage2_model": trace.get("stage2_model"),
            "latency_ms": round(latency_ms, 2),
        })
        print(f"[{q_id:<32}] Jaccard: {jaccard:.3f} | ROUGE-L: {rouge_l:.3f} | SBERT: {sem_sim:.3f} | RefL: {ref_l:.3f} | RefS: {ref_s:.3f} | S2: {int(stage2_landed)}")

    # ── Summary ────────────────────────────────────────────────────
    # Every mean goes through _mean(), which skips None — so an HTTP error row
    # never enters an average. `scored_rows` / `error_rows` make the denominator
    # explicit rather than assumed to be 20 / 10.
    all_rows = af_results + hard_results
    scored_all = [r for r in all_rows if r.get("error") is None]
    stage2_landed_rows = [r for r in scored_all if r.get("stage2_landed")]

    af_summary = {
        "rows": len(af_results),
        "scored_rows": sum(1 for r in af_results if r.get("error") is None),
        "error_rows": sum(1 for r in af_results if r.get("error") is not None),
        "jaccard_loose": _mean(af_results, "jaccard"),
        "rouge_l": _mean(af_results, "rouge_l"),
        "semantic_similarity": _mean(af_results, "semantic_similarity"),
        "keyword_recall": _mean(af_results, "keyword_recall"),
        "ref_loose": _mean(af_results, "ref_loose"),
        "ref_strict": _mean(af_results, "ref_strict"),
        "ref_conciseness": _mean(af_results, "ref_conciseness"),
        "regulatory_tone": _mean(af_results, "regulatory_tone"),
        "total_historical_mistakes": total_mistakes_count,
        "resolved_historical_mistakes": total_mistakes_resolved,
        # ⚠ R338/[C3]: this rate is NOT comparable to any figure recorded before
        # 2026-08-15. The pre-fix runner honoured 2 of the 5 constraint kinds and
        # never saw the predicted references, so 11 of 38 mistakes were resolved
        # unconditionally. The name is kept because the CONCEPT is unchanged (the
        # canonical resolver's definition, which the rest of the repo already
        # used); what changed is that this module stopped using a broken copy of it.
        # ``None``, not 1.0, when nothing was measured. The old `else 1.0` reported
        # a PERFECT resolution rate for a run in which every row errored out — the
        # same fail-open shape as the [C3] defect one level up.
        "mistake_resolution_rate": round(total_mistakes_resolved / total_mistakes_count, 4) if total_mistakes_count else None,
        "unfalsifiable_mistakes": total_mistakes_unfalsifiable,
    }

    hard_summary = {
        "rows": len(hard_results),
        "scored_rows": sum(1 for r in hard_results if r.get("error") is None),
        "error_rows": sum(1 for r in hard_results if r.get("error") is not None),
        "jaccard_loose": _mean(hard_results, "jaccard"),
        "rouge_l": _mean(hard_results, "rouge_l"),
        "semantic_similarity": _mean(hard_results, "semantic_similarity"),
        "keyword_recall": _mean(hard_results, "keyword_recall"),
        "ref_loose": _mean(hard_results, "ref_loose"),
        "ref_strict": _mean(hard_results, "ref_strict"),
        "ref_conciseness": _mean(hard_results, "ref_conciseness"),
        "regulatory_tone": _mean(hard_results, "regulatory_tone"),
    }

    # [I7] provenance. A run that silently took the deterministic path is the
    # instrument trap, so the artefact records what actually executed — not what
    # the module's docstring calls itself. `stage2_landed_rate == 0.0` means every
    # number above was produced WITHOUT Stage-2.
    run_config = {
        "provider_resolved": resolved_provider,
        "provider_env_raw": os.environ.get("P2P_GRAPH_RAG_PROVIDER"),
        "provider_arg": provider,
        "stage2_models": sorted(stage2_models),
        "stage2_model_resolved": (
            sorted(stage2_models)[0] if len(stage2_models) == 1 else None
        ),
        "stage2_landed_rows": len(stage2_landed_rows),
        "stage2_landed_rate": (
            round(len(stage2_landed_rows) / len(scored_all), 4) if scored_all else None
        ),
        "http_error_rows": sum(1 for r in all_rows if r.get("error") is not None),
    }

    grand_summary = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "run_config": run_config,
        "antifragile_expert_questions_summary": af_summary,
        "hard_july7_scenarios_summary": hard_summary,
        "overall_30_hard_rows": {
            "scored_rows": len(scored_all),
            "jaccard_loose": _mean(all_rows, "jaccard"),
            "rouge_l": _mean(all_rows, "rouge_l"),
            "semantic_similarity": _mean(all_rows, "semantic_similarity"),
            "keyword_recall": _mean(all_rows, "keyword_recall"),
            "ref_loose": _mean(all_rows, "ref_loose"),
            "ref_strict": _mean(all_rows, "ref_strict"),
            "regulatory_tone": _mean(all_rows, "regulatory_tone"),
        },
        "antifragile_details": af_results,
        "hard_july7_details": hard_results,
    }

    print(
        f"\n[Live Deep Eval] provider={run_config['provider_resolved']} "
        f"stage2_landed={run_config['stage2_landed_rows']}/{len(scored_all)} "
        f"stage2_models={run_config['stage2_models'] or '-'} "
        f"http_errors={run_config['http_error_rows']}"
    )
    if run_config["stage2_landed_rows"] == 0:
        print(
            "[Live Deep Eval] WARNING: Stage-2 landed on ZERO rows — this is a DETERMINISTIC "
            "measurement. Any prompt / judge / reranker / KG-context change is invisible here."
        )

    if output_path:
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        with open(out_p, "w", encoding="utf-8") as f:
            json.dump(grand_summary, f, indent=2)
        print(f"\n[Live Deep Eval] Saved results to {output_path}")

    return grand_summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Live Deep Evaluation on Hard Sets")
    # [I7] default is None, NOT "cli". Omitting the flag leaves an exported
    # P2P_GRAPH_RAG_PROVIDER untouched and resolves an unset one to
    # `openai_wrapper` — the live path this module claims to measure.
    parser.add_argument(
        "--provider",
        default=None,
        help=(
            "Override the provider (cli, openai_wrapper, anthropic, bedrock). "
            "Omit to honour an exported P2P_GRAPH_RAG_PROVIDER, or openai_wrapper "
            "if none is exported."
        ),
    )
    parser.add_argument("--out", default="evals/bench/results/live_deep_eval_results.json", help="Output JSON path")
    args = parser.parse_args()

    summary = run_live_eval(provider=args.provider, output_path=args.out)
