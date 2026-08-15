"""R338 — the Cappelli (2026) gold dataset must resolve against the PINNED statute.

Six commits landed on ``main`` unreviewed on 2026-08-15 carrying
``evals/bench/data/cappelli_compliance_2026.json``. A 10-lens review found four
legal defects in its ``gold_answer`` prose and one **fabricated coordinate** in
its ``expected_refs`` (``Annex III.2.a`` — Annex III point 2 is a single
unlettered paragraph, so the sub-point does not exist).

The fabricated coordinate is the reason this file exists. It shipped because the
only validator anyone reaches for, ``provision_exists``, is **head-level LAX**
(CLAUDE.md hard rule #5): it answers "does the HEAD exist?", so it returns True
for ``Article 3.999`` and for ``Annex III.2.a`` alike. The only instrument that
can falsify a leaf coordinate is ``get_provision_text(ref) is not None`` — it
returns the verbatim pinned prose or ``None``, with no head-level fallback for a
coordinate that was never in the corpus.

Scope of the pin: Regulation (EU) 2024/1689 **as adopted**, CELEX ``32024R1689``,
PRE-Omnibus (``app/data/official_eu_ai_act.py``). Every assertion below is
anchored on that corpus rather than on a hard-coded sentence, so the tests state
what the law says, not what one round happened to believe.
"""
from __future__ import annotations

import re

from app.data.provision_text import get_provision_text, provision_exists

# ONE CONCEPT, ONE DEFINITION — do NOT re-open the JSON here. ``load_dataset``
# in the runner is the REAL caller; a fixture that re-reads the file with its own
# json.load would keep passing if the runner's loader ever diverged (different
# path, a filter, a schema migration). Assert against the shape the production
# caller actually emits.
from evals.bench.run_cappelli_bench import load_dataset


DATASET = load_dataset()

# ``Article 5.1.h`` / ``Annex III.4.a`` / ``Annex IV`` — the wire-format coordinate
# grammar of hard rule #1, as it appears inside the dataset's structured fields.
_COORDINATE_RE = re.compile(r"\b(?:Article|Annex)\s+[IVXLC0-9]+(?:\.[A-Za-z0-9]+)*")


def _rows_by_dimension(dimension: str) -> list[dict]:
    return [row for row in DATASET if row.get("dimension") == dimension]


def test_dataset_loads_and_is_the_20_scenario_benchmark():
    """Guard the fixture itself: a silently empty dataset makes every test below vacuous."""
    assert len(DATASET) == 20, f"expected the 20-scenario Cappelli benchmark, got {len(DATASET)}"
    for row in DATASET:
        assert row.get("expected_refs"), f"{row.get('id')} carries no expected_refs"


# ─────────────────────────────────────────────────────────────────────────────
# The required guard: no fabricated coordinate may ship in gold again.
# ─────────────────────────────────────────────────────────────────────────────


def test_every_expected_ref_resolves_to_verbatim_pinned_text():
    """EVERY ``expected_refs`` entry must resolve to real text in the pinned Act.

    Measured 2026-08-15 on the pre-fix dataset: ``Annex III.2.a``
    (``cappelli_cs3_q1_risk_level``) returned ``None`` here while
    ``provision_exists('Annex III.2.a')`` returned ``True`` — i.e. this
    assertion is the ONLY one of the two that could have stopped it.

    Scoring-inert today (``evals.bench.metrics.article_heads`` collapses
    ``Annex III.2.a`` to the head ``Annex III``), but it becomes a silent
    gold-SHRINK the moment this bench moves to the ``*_exact_coord`` reference
    formulas that its sub-point-grain gold would justify — the fabricated
    coordinate would simply never be matched by any prediction.
    """
    unresolvable: list[str] = []
    for row in DATASET:
        for ref in row["expected_refs"]:
            if get_provision_text(ref) is None:
                unresolvable.append(f"{row['id']}: {ref!r}")
    assert not unresolvable, (
        "expected_refs that do not resolve to verbatim text in the pinned "
        f"Regulation (EU) 2024/1689: {unresolvable}"
    )


def test_every_annex_iii_category_coordinate_resolves():
    """The same guard on the second field that carried the fabricated coordinate.

    ``annex_iii_category`` is free text (``"Annex I / MDR / Annex III"``) read by
    no scoring code, but ``Annex III.2.a`` appeared in it on all five ``cs3``
    rows as well as in ``expected_refs``. A guard that covers only the scored
    field leaves the same false statement of law in the published artifact.
    """
    unresolvable: list[str] = []
    for row in DATASET:
        category = row.get("annex_iii_category") or ""
        for coordinate in _COORDINATE_RE.findall(category):
            if get_provision_text(coordinate) is None:
                unresolvable.append(f"{row['id']}: {coordinate!r}")
    assert not unresolvable, (
        f"annex_iii_category coordinates absent from the pinned Act: {unresolvable}"
    )


def test_provision_exists_is_head_lax_and_therefore_not_the_validator():
    """Executable proof of WHY the two tests above use ``get_provision_text``.

    CLAUDE.md hard rule #5's caveat, run rather than quoted. If this ever starts
    failing, ``provision_exists`` was tightened and the caveat is stale — that is
    a docs update, not a licence to swap the validator here without re-measuring.
    """
    assert provision_exists("Article 3.999") is True
    assert get_provision_text("Article 3.999") is None


# ─────────────────────────────────────────────────────────────────────────────
# Statute-anchored regression guards for the four gold defects R338 corrected.
# Each asserts the PIN first, then the dataset against it.
# ─────────────────────────────────────────────────────────────────────────────


def test_pinned_annex_iv_has_nine_points_and_contains_no_ce_marking_or_fria():
    """The ground truth the four ``technical_documentation`` rows must respect.

    Pre-fix, all four claimed an 8-item Annex IV and listed CE marking as a
    component; ``cappelli_cs4_q5`` also placed an Article 27 FRIA report inside
    it. Annex IV(8) asks only for *a copy of the EU declaration of conformity
    referred to in Article 47*; CE marking is Article 48, a separate obligation
    that is not part of the technical file.
    """
    for point in range(1, 10):
        assert get_provision_text(f"Annex IV.{point}") is not None, f"Annex IV.{point} missing"
    assert get_provision_text("Annex IV.10") is None, "Annex IV has nine points, not ten"

    annex_iv = get_provision_text("Annex IV")
    assert annex_iv is not None
    lowered = annex_iv.lower()
    assert "ce mark" not in lowered
    assert "fundamental rights impact" not in lowered
    assert "declaration of conformity" in lowered  # Annex IV(8), via Article 47


def test_no_gold_answer_miscounts_the_annex_iv_points():
    """Catches the literal defect: *"the 8 mandatory Annex IV files"*.

    Any gold that puts a cardinal immediately in front of ``Annex IV`` is making
    a count claim about the Annex, and the pinned Annex has exactly nine points.
    """
    _NOUNS = r"(?:files|points|items|elements|documents)"
    # Restricted to actual cardinals on purpose. A looser ``(\w+)`` capture reads
    # the corrected prose "three items commonly listed here are NOT Annex IV
    # elements" as a claim of "NOT" many elements — measured, it failed exactly
    # that way. A count guard must fire only on a count.
    _CARDINAL = r"(\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)"
    counters = (
        # "the 8 mandatory Annex IV files"  — the shipped defect
        re.compile(rf"\b{_CARDINAL}\s+(?:mandatory\s+)?Annex\s+IV\s+{_NOUNS}\b", re.IGNORECASE),
        # "the nine elements set out in Annex IV" — the corrected word order. Both
        # directions must be covered or the guard silently stops binding the gold
        # the moment someone rephrases it.
        re.compile(
            rf"\b{_CARDINAL}\s+(?:mandatory\s+)?{_NOUNS}\s+(?:set out\s+)?(?:of|in|under)\s+Annex\s+IV\b",
            re.IGNORECASE,
        ),
    )
    offenders: list[str] = []
    for row in DATASET:
        for counter in counters:
            for claimed in counter.findall(row["gold_answer"]):
                if claimed.lower() not in {"nine", "9"}:
                    offenders.append(f"{row['id']}: claims {claimed!r} Annex IV items")
    assert not offenders, f"Annex IV has NINE points in the pinned Act: {offenders}"


def test_six_month_log_retention_is_never_attributed_to_article_12():
    """Article 12 states a logging CAPABILITY; it states no retention period.

    Verified against the pin: the only provisions whose verbatim text contains
    "six months" in a logging context are **Article 19(1)** (provider) and
    **Article 26(6)** (deployer). Pre-fix, ``cappelli_cs3_q5`` and
    ``cappelli_cs4_q5`` both wrote "6-month ... (Article 12)" while the same file
    got it right at ``cappelli_cs4_q2`` with Article 26(6) — the dataset
    contradicted itself.
    """
    article_12 = get_provision_text("Article 12")
    assert article_12 is not None
    assert "six months" not in article_12.lower(), (
        "Article 12 acquired a retention period — the pin changed, re-derive this test"
    )
    for owner in ("Article 19.1", "Article 26.6"):
        text = get_provision_text(owner)
        assert text is not None and "six months" in text.lower(), owner

    # A clause that states a six-month log period must name a provision that
    # actually states it. Split on ';' / ',' so one bad clause cannot hide behind
    # a correct citation elsewhere in the same long sentence.
    # ``months?`` matters: the first draft of this guard used ``month\b`` and so
    # silently skipped "for at least 6 months" — it caught the two hyphenated
    # rows and missed a third (``cs3_q2``) that attributed the floor to
    # "Articles 12 and 26(6)" jointly. ``Articles?`` closes the plural form.
    period = re.compile(r"\b(?:6|six)[-\s]months?\b", re.IGNORECASE)
    offenders: list[str] = []
    for row in DATASET:
        for clause in re.split(r"[;,]", row["gold_answer"]):
            if not period.search(clause) or "log" not in clause.lower():
                continue
            if not re.search(r"Articles?\s+(?:19|26)\b", clause):
                offenders.append(f"{row['id']}: {clause.strip()!r}")
    assert not offenders, (
        "six-month log retention is Article 19(1) (provider) / Article 26(6) "
        f"(deployer), never Article 12: {offenders}"
    )


def test_retail_deployer_rows_do_not_demand_an_article_27_fria():
    """Article 27(1)'s scope test excludes the cs4 retail chain.

    Pinned Article 27(1) reaches only (i) deployers that are bodies governed by
    public law, (ii) private entities providing public services, and (iii)
    deployers of **Annex III point 5(b)/(c)** systems. ``cs4`` is a private
    in-store retail chain and the dataset's own ``annex_iii_category`` puts the
    system in **Annex III point 1** (biometrics), so it fails all three limbs.

    This mattered: in the archived ``cappelli_bench_results.json``, ``Article 27``
    was the ONLY predicted ref intersecting gold on both ``cs4_q2`` and
    ``cs4_q4`` — the ruler was laundering an over-citation into the score, on the
    exact axis CLAUDE.md names as the whole remaining competitive gap.
    """
    article_27_1 = get_provision_text("Article 27.1")
    assert article_27_1 is not None
    lowered = article_27_1.lower()
    assert "bodies governed by public law" in lowered
    assert "private entities providing public services" in lowered
    assert "points 5 (b) and (c) of annex iii" in lowered

    offenders = [
        row["id"]
        for row in DATASET
        if row.get("case_study") == "cs4_retail_facial_recognition"
        and any(ref.split(".")[0].strip() == "Article 27" for ref in row["expected_refs"])
    ]
    assert not offenders, (
        "cs4 is a private retail deployer of an Annex III point 1 system — "
        f"Article 27(1) does not reach it: {offenders}"
    )


def test_retail_rows_do_not_apply_law_enforcement_only_article_5_1_h_unhedged():
    """Article 5(1)(h) is confined to *"the purposes of law enforcement"*.

    Pre-fix, ``cappelli_cs4_q3`` asserted "prohibited mass surveillance (Article
    5(1)(h) and Article 5(1)(c))" for a shop. 5(1)(c) is **social scoring**;
    5(1)(h) is real-time remote biometric identification *for law enforcement*.
    ``cappelli_cs4_q1`` already carried the hedge, so the file contradicted
    itself. Any row that names 5(1)(h) must carry the law-enforcement qualifier.
    """
    article_5_1_h = get_provision_text("Article 5.1.h")
    assert article_5_1_h is not None
    assert "for the purposes of law enforcement" in article_5_1_h.lower()
    article_5_1_c = get_provision_text("Article 5.1.c")
    assert article_5_1_c is not None and "social behaviour" in article_5_1_c.lower()

    offenders: list[str] = []
    for row in DATASET:
        gold = row["gold_answer"]
        if "5(1)(h)" not in gold:
            continue
        if "law enforcement" not in gold.lower():
            offenders.append(row["id"])
    assert not offenders, (
        f"Article 5(1)(h) named without its law-enforcement limb: {offenders}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# ``expected_keywords`` is a SECOND ruler on the same row, and it moves the score
# independently of ``expected_refs``. Correcting a citation while leaving the
# keyword that rewards the old framing keeps the metric paying for the wrong law
# — which is precisely what the review found. These two guards are scoped to the
# claim class each defect belongs to, and both are anchored on the pin.
#
# "Every keyword must also appear in the row's own gold_answer" is the property
# that matters, and it cannot be asserted outright: it fails on four rows for
# reasons with no legal content (the stemmer does not relate "cyber-attacks" to
# "cyberattacks", "fines" to "penalties", "controls" to "control"), and forcing
# cosmetic rewrites of untouched gold prose would be noise. Narrowing it to the
# rows R338 happens to touch would be a test built to pass.
#
# So it is asserted as a FROZEN BASELINE instead — the standard shape for
# "known-broken, must not get worse". See
# ``test_no_gold_answer_is_unable_to_satisfy_its_own_keywords`` below.
# ─────────────────────────────────────────────────────────────────────────────


def test_no_retail_row_rewards_the_mass_surveillance_framing():
    """"Mass surveillance" is not the operative framing for a private shop.

    Article 5(1)(c) is social scoring and Article 5(1)(h) is law-enforcement
    real-time RBI; the untargeted-scraping prohibition that actually binds any
    operator is **Article 5(1)(e)**. Leaving ``"mass surveillance"`` in
    ``expected_keywords`` costs a legally correct answer 2 of 9 keyword tokens on
    ``cs4_q3`` — the metric paying an answer to adopt a framing the statute does
    not support.
    """
    article_5_1_e = get_provision_text("Article 5.1.e")
    assert article_5_1_e is not None
    assert "untargeted scraping" in article_5_1_e.lower()

    offenders = [
        row["id"]
        for row in DATASET
        if row.get("case_study") == "cs4_retail_facial_recognition"
        and any("mass surveillance" in kw.lower() for kw in row["expected_keywords"])
    ]
    assert not offenders, (
        "retail rows must not reward the mass-surveillance framing; the pinned "
        f"prohibition on point here is Article 5(1)(e): {offenders}"
    )


def test_technical_documentation_keywords_exclude_ce_marking_and_the_fria():
    """Neither is Annex IV content, so neither may be a technical-file keyword.

    ``technical_documentation`` rows ask what belongs IN the Annex IV file. CE
    marking is Article 48 and the FRIA is Article 27 — both real obligations,
    neither an Annex IV element (asserted against the pin above). Measured
    pre-fix: a correct answer enumerating all nine Annex IV points scored 0.75 on
    ``answer_keyword_recall`` because it declined to claim CE marking is part of
    the technical file, while the fabricated gold scored 1.00.

    Scoped to this dimension on purpose — ``cs1_q2`` (``regulatory_obligations``)
    keeps ``"CE marking"`` because Articles 43/48 genuinely ARE obligations there.
    """
    for row in _rows_by_dimension("technical_documentation"):
        lowered = [kw.lower() for kw in row["expected_keywords"]]
        assert not any("ce marking" in kw for kw in lowered), (
            f"{row['id']}: CE marking (Article 48) is not an Annex IV element"
        )
        assert not any(kw in {"fria", "fundamental rights impact assessment"} for kw in lowered), (
            f"{row['id']}: the FRIA (Article 27) is not an Annex IV element"
        )


# The four rows below are the pre-R338 baseline, measured 2026-08-15. Each miss
# is a tokeniser/vocabulary artefact in gold R338 did NOT touch, not a statement
# of law: cs1_q3 writes "non-discrimination"/"fines" against keywords
# "discrimination"/"penalties"; cs2_q4 writes "override control" (singular
# "controls" does not stem to "control") and "biased"; cs3_q2 writes "road
# traffic"/"duties" against "critical infrastructure"/"deployer obligations";
# cs3_q4 writes "cyber-attacks"/"fail-safe fallback" hyphenated differently.
# Shrinking this map is an improvement — update it in the same change. GROWING
# it is the defect this guard exists to stop.
_KNOWN_UNSATISFIABLE_KEYWORD_TOKENS: dict[str, set[str]] = {
    "cappelli_cs1_q3_legal_risks": {"discrimination", "penalti"},
    "cappelli_cs2_q4_compliance_gaps": {"bias", "control"},
    "cappelli_cs3_q2_obligations": {"critical", "infrastructur", "obligation"},
    "cappelli_cs3_q4_compliance_gaps": {"cyberattack", "fail-saf"},
}


def test_no_gold_answer_is_unable_to_satisfy_its_own_keywords():
    """A keyword no legally correct answer can produce is a broken ruler.

    ``answer_keyword_recall`` pools ``expected_keywords`` into one stemmed token
    set and measures the answer's recall of it. The row's own ``gold_answer`` is
    the best answer that row admits, so its self-recall is that row's CEILING —
    a token the gold itself cannot hit is unreachable for every prediction, and
    the axis silently loses that fraction of its range.

    This is the failure mode [I14] named ("leaving ``mass surveillance`` while
    fixing the citation keeps the metric rewarding the wrong framing"), and the
    first R338 pass reproduced it while fixing it: correcting
    ``cappelli_cs4_q2_obligations`` to say "a valid lawful basis" left the
    keyword ``consent`` behind, and the new keyword ``deployer obligations`` was
    added against gold prose that said "deployer duties". Measured on that pass,
    that row's own gold scored **0.3750** — a legally perfect answer forfeiting
    5 of 8 keyword tokens, DOWN from 0.7000 before the fix. Repaired in the gold
    prose (obligations / explicit consent / six-month log retention floor), so
    every row R338 touches is back at self-recall 1.0.
    """
    from evals.bench.metrics import _tokens

    regressions: list[str] = []
    stale: list[str] = []
    for row in DATASET:
        expected_tokens: set[str] = set()
        for keyword in row["expected_keywords"]:
            expected_tokens |= _tokens(keyword)
        missing = expected_tokens - _tokens(row["gold_answer"])
        allowed = _KNOWN_UNSATISFIABLE_KEYWORD_TOKENS.get(row["id"], set())
        new_misses = missing - allowed
        if new_misses:
            regressions.append(
                f"{row['id']}: keyword token(s) {sorted(new_misses)} appear in "
                f"expected_keywords but NOT in that row's own gold_answer"
            )
        if allowed - missing:
            stale.append(f"{row['id']}: {sorted(allowed - missing)} now satisfied")

    assert not regressions, (
        "expected_keywords must be satisfiable by the row's own gold_answer — a "
        "token the gold cannot hit caps that row's answer_keyword_recall below "
        f"1.0 for every possible prediction: {regressions}"
    )
    assert not stale, (
        "the known-unsatisfiable baseline is now too permissive; shrink "
        f"_KNOWN_UNSATISFIABLE_KEYWORD_TOKENS in this change: {stale}"
    )
