"""Deterministic local proxy scorers for the Regenold competition.

The competition publishes the axis names and output grammar, but not the
numeric evaluator formulas. Nothing in this module is an official formula;
``METRIC_PROVENANCE`` is persisted so downstream reports retain that fact.

The 2026 competition rubric scores 8 axes (page 3 of the rules deck):

    1. Answer Correctness (Loose)   — substantive agreement with gold
    2. Answer Correctness (Strict)  — every gold-anchor keyword present
    3. Answer Conciseness           — length normalised vs gold answer
    4. Reference Correctness (Loose) — recall of gold article set
    5. Reference Correctness (Strict) — exact set match with gold
    6. Reference Conciseness        — over/under-citation penalty
    7. Latency                      — p50, p95, max ms
    8. Regulatory Tone              — regulator-voice classifier

Every function is pure (no I/O, no globals) so the runner can call them
deterministically and reproduce a score from a stored JSON sidecar.

Design intent:
    * "Loose" metrics use token-Jaccard or set-recall — robust to phrasing.
    * "Strict" metrics use exact-set or every-keyword-present — robust to
      hallucinated additions.
    * Conciseness uses a symmetric length-ratio penalty so both
      under-shooting and over-shooting are punished proportionally.
    * Tone is a heuristic classifier — first-person, hedging, and AI
      preamble phrases each subtract points; regulator-voice anchors add.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable


METRICS_VERSION = "r327-canonical-historical-plus-diagnostics"

# The competition publishes axis names and the output contract, but not its
# numeric formulas. Persist this marker so local proxy results cannot be
# mistaken for official evaluator scores.
METRIC_PROVENANCE: dict[str, Any] = {
    "metrics_version": METRICS_VERSION,
    "formula_authority": "local_reproducible_proxy; official_numeric_formulas_undisclosed",
    # R327 — the CANONICAL axis names carry the HISTORICAL formulas so the
    # authoritative CLAUDE.md baseline stays reproducible and every merge gate
    # stays comparable. The polarity-adjusted and full-coordinate formulas are
    # exposed under their own names as DIAGNOSTICS only.
    "comparability": (
        "canonical axes == historical formulas; new formulas live under "
        "*_polarity_adj / *_exact_coord and are diagnostics, not the baseline"
    ),
    "ans_correctness_loose": "token_jaccard_proxy",
    "ans_correctness_strict": "gold_token_recall_proxy",
    "ans_correctness_precision": "pred_token_precision_proxy",
    "ans_correctness_f1": "token_f1_proxy",
    "diagnostic_answer_fields": {
        "answer_correctness_loose_polarity_adj": "jaccard * holding-polarity factor",
        "answer_correctness_strict_polarity_adj": "recall * holding-polarity factor",
        "answer_correctness_precision_polarity_adj": "precision * polarity factor",
        "answer_correctness_f1_polarity_adj": "F1 * holding-polarity factor",
        "_polarity_factor_caveat": (
            "measured 63 percent false-positive: zeroes 142/476 rows whose "
            "holding is correct. Never multiply a primary axis by it."
        ),
    },
    "legacy_answer_fields": {
        "ans_correctness_loose_token_overlap_proxy": "polarity_blind token Jaccard",
        "ans_correctness_strict_token_overlap_proxy": "polarity_blind gold-token recall",
        "ans_correctness_precision_token_overlap_proxy": "polarity_blind pred-token precision",
        "ans_correctness_f1_token_overlap_proxy": "polarity_blind token F1",
        "ans_correctness_loose_legacy": "pre-R82 polarity-blind token Jaccard",
        "ans_correctness_strict_legacy": "pre-R82 polarity-blind gold-token recall",
    },
    "ref_correctness_loose": "article_or_annex_head_recall_proxy",
    "ref_correctness_strict": "article_or_annex_head_f1_proxy",
    "ref_conciseness": "quadratic_head_count_ratio_proxy",
    "diagnostic_reference_fields": {
        "reference_correctness_strict_exact_coord": (
            "validated_full_coordinate_f1; invalids/duplicates/parent-leaf pairs "
            "penalised. Only meaningful where gold carries sub-point grain — "
            "against head-level davidath gold it scores a MORE precise "
            "citation as 0.0."
        ),
        "reference_conciseness_exact_coord": (
            "quadratic_count_ratio_over_all_proposed_entries; parent_leaf_pairs_penalized"
        ),
    },
    "legacy_reference_fields": {
        "ref_correctness_loose_head_recall_proxy": "historical loose formula",
        "ref_correctness_strict_head_f1_proxy": "historical strict formula",
        "ref_conciseness_head_count_proxy": "historical conciseness formula",
    },
}


# ── Tokenisation ─────────────────────────────────────────────────────────


from evals.bench.text_normalise import normalise_for_scoring, stem_token

# Pre-R82 stopword set — kept for `_tokens_legacy` only.
_STOPWORDS_LEGACY = frozenset(
    {
        "a", "an", "the", "and", "or", "but", "if", "of", "to", "in",
        "on", "for", "with", "as", "by", "is", "are", "was", "were", "be",
        "been", "being", "this", "that", "these", "those", "it", "its",
        "must", "shall", "should", "would", "can", "may", "from", "at",
        "any", "all", "such", "which", "who", "what", "when", "where",
        "their", "they", "them", "his", "her", "he", "she", "you", "we",
        "i", "us", "our", "your", "my", "do", "does", "did", "have", "has",
        "had", "not", "no", "yes",
    }
)

# R82-A: drop regulatory modal verbs from stopwords. The whole
# regulation is "must / shall / should" — discarding them under-counts
# rubric-relevant tokens.
_STOPWORDS_V2 = _STOPWORDS_LEGACY - {
    "must", "shall", "should", "would", "may", "can",
}

# Pre-R82 token regex — must start with letter, accepts ASCII '-'.
_TOKEN_RE_LEGACY = re.compile(r"[A-Za-z][A-Za-z0-9'\-]+")

# R82-A: accept digit-led tokens so `15` / `10` / `2024` survive when
# they carry meaning (penalty amounts, FLOPs scales, year markers).
_TOKEN_RE_V2 = re.compile(r"[A-Za-z0-9][A-Za-z0-9'\-]+")


def _tokens_legacy(text: str) -> set[str]:
    """Pre-R82 tokenizer — reproduces shipped behaviour byte-identically.

    Preserved so `*_legacy` axes in the rescored history remain
    reproducible across the R23-R81 round trajectory. Do NOT modify.
    """
    if not text:
        return set()
    raw = _TOKEN_RE_LEGACY.findall(text.lower())
    return {t for t in raw if len(t) >= 3 and t not in _STOPWORDS_LEGACY}


def _tokens(text: str) -> set[str]:
    """R82-A corrected tokenizer.

    Pipeline:
      1. `normalise_for_scoring` (NFKC + dash fold + Art. → Article +
         diacritic strip + lowercase).
      2. Token regex `[A-Za-z0-9][A-Za-z0-9'\\-]+` (digit-led OK).
      3. Filter: len ≥ 2 AND not in `_STOPWORDS_V2`.
      4. Stem each survivor.

    Returns a set (deduped). See `evals/bench/text_normalise.py` for the
    per-rule rationale grounded in measured davidath biases.
    """
    if not text:
        return set()
    norm = normalise_for_scoring(text)
    raw = _TOKEN_RE_V2.findall(norm)
    return {stem_token(t) for t in raw if len(t) >= 2 and t not in _STOPWORDS_V2}


# ── Citation helpers ─────────────────────────────────────────────────────


# TODO(R47): migrate to app.integrations.regenold.refs (centralised converter).
_ARTICLE_HEAD_RE = re.compile(r"^Article\s+(\d+)(?:\..*)?$")
_ANNEX_HEAD_RE = re.compile(r"^Annex\s+([IVXLC]+)(?:\..*)?$")


def article_head(ref: str) -> str | None:
    """Strip ``Article 13.1.a`` → ``Article 13``; return None if not parseable."""
    if not isinstance(ref, str):
        return None
    m = _ARTICLE_HEAD_RE.match(ref.strip())
    if m:
        return f"Article {int(m.group(1))}"
    m = _ANNEX_HEAD_RE.match(ref.strip())
    if m:
        return f"Annex {m.group(1).upper()}"
    return None


def article_heads(refs: Iterable[str]) -> set[str]:
    """Project a list of refs onto the unique set of article/annex heads."""
    out: set[str] = set()
    for r in refs or ():
        h = article_head(r)
        if h is not None:
            out.add(h)
    return out


def _canonical_ref(ref: Any, *, predicted: bool) -> str | None:
    """Return a real, canonical full EU AI Act coordinate or ``None``.

    Predicted references must already obey the public wire grammar. Gold may
    use the repository's internal parenthesised representation. A made-up leaf
    is invalid even when its parent provision exists.
    """
    if not isinstance(ref, str) or not ref.strip():
        return None
    try:
        from app.data.provision_text import get_provision_text, provision_exists
        from app.integrations.regenold import refs as central_refs

        raw = ref.strip()
        if predicted and not (
            central_refs.USER_FACING_ARTICLE_RE.fullmatch(raw)
            or central_refs.USER_FACING_ANNEX_RE.fullmatch(raw)
        ):
            return None
        canonical = central_refs.normalise(raw)
        if not provision_exists(canonical) or get_provision_text(canonical) is None:
            return None
        return canonical
    except (TypeError, ValueError):
        return None


def canonical_reference_diagnostics(pred_refs: Iterable[Any] | None) -> dict[str, Any]:
    """Validate proposed references and expose every strict-score penalty."""
    raw = list(pred_refs or [])
    valid: list[str] = []
    invalid: list[str] = []
    for ref in raw:
        canonical = _canonical_ref(ref, predicted=True)
        if canonical is None:
            invalid.append(str(ref))
        else:
            valid.append(canonical)
    seen: set[str] = set()
    duplicates: list[str] = []
    for ref in valid:
        if ref in seen:
            duplicates.append(ref)
        seen.add(ref)
    unique = sorted(seen)
    parent_leaf_pairs = [
        [left, right]
        for i, left in enumerate(unique)
        for right in unique[i + 1 :]
        if right.startswith(left + ".") or left.startswith(right + ".")
    ]
    return {
        "raw_count": len(raw),
        "canonical_refs": unique,
        "invalid_refs": invalid,
        "invalid_count": len(invalid),
        "duplicate_refs": duplicates,
        "duplicate_count": len(duplicates),
        "parent_leaf_pairs": parent_leaf_pairs,
        "parent_leaf_pair_count": len(parent_leaf_pairs),
    }


# ── 1+2: Answer correctness ──────────────────────────────────────────────


def answer_correctness_loose_token_overlap_proxy(pred: str, gold: str) -> float:
    """Token-Jaccard between predicted and gold answer.

    Returns 0.0–1.0. Robust to phrasing differences as long as the
    substantive vocabulary overlaps. Empty predicted answer → 0.0.

    NOTE — "Loose" naming is historical; Jaccard penalises BOTH
    missing-gold tokens AND extra-pred tokens, so it is actually
    *stricter* than ``answer_correctness_strict`` (= recall) on any
    row where |pred| > |gold|. The two-axis decomposition is:
    ``answer_correctness_precision`` (verbose-direction signal) +
    ``answer_correctness_strict_token_overlap_proxy`` (recall). These are
    historical local formulas, not disclosed official evaluator formulas.
    """
    pt = _tokens(pred)
    gt = _tokens(gold)
    if not gt:
        return 0.0
    if not pt:
        return 0.0
    overlap = len(pt & gt)
    union = len(pt | gt)
    return overlap / union if union else 0.0


def answer_correctness_loose(pred: str, gold: str) -> float:
    """Canonical token-Jaccard proxy (current versioned primary).

    R327 - canonical axis names are bound to the HISTORICAL polarity-blind
    formulas. The polarity factor was measured to zero all four answer axes on
    142 of 476 rows whose holding is in fact correct (a 63 percent false-
    positive rate), chiefly via "without" in "without prejudice" and by parity-
    cancelling negations across a whole answer. Multiplying the primary axes by
    it made the CLAUDE.md baseline unreproducible AND understated correctness.
    The polarity-adjusted variant is retained as
    answer_correctness_loose_polarity_adj, and the mismatch rate is already
    reported as the criterion_negation_mismatch_rate diagnostic.
    """
    return answer_correctness_loose_token_overlap_proxy(pred, gold)


def answer_correctness_loose_polarity_adj(pred: str, gold: str) -> float:
    """Diagnostic: loose proxy scaled by the holding-polarity factor."""
    return answer_correctness_loose_token_overlap_proxy(
        pred, gold
    ) * _polarity_score_factor(pred, gold)


def answer_correctness_strict_token_overlap_proxy(pred: str, gold: str) -> float:
    """Fraction of gold-answer tokens present in the prediction.

    This is **token-recall** — one-sided, doesn't penalise extra
    pred tokens. Pair with :func:`answer_correctness_precision`
    (R85-A) for the full 2-D picture.

    A near-complete answer still scores high; a confidently wrong
    answer with mostly-new tokens scores low.
    """
    pt = _tokens(pred)
    gt = _tokens(gold)
    if not gt:
        return 0.0
    return len(pt & gt) / len(gt)


def answer_correctness_precision_token_overlap_proxy(pred: str, gold: str) -> float:
    """Fraction of predicted-answer tokens present in the gold answer.

    Counterpart to :func:`answer_correctness_strict` (which is recall —
    gold tokens recovered). Precision answers the *other* side of the
    verbosity coin: "of the tokens we shipped, how many were on-topic?".

    R85-A — added because the existing Loose / Strict pair leaves a
    one-dimensional view of the gap. Loose = Jaccard penalises BOTH
    missing-gold AND extra-pred without telling you which direction
    dominates; Strict only measures recall. Precision plus recall give
    the full 2-D picture and reproduce Loose / F1 via standard
    identities.

    Empty prediction → 0.0; empty gold → 0.0 (cannot grade).
    """
    pt = _tokens(pred)
    gt = _tokens(gold)
    if not gt:
        return 0.0
    if not pt:
        return 0.0
    return len(pt & gt) / len(pt)


def answer_correctness_precision(pred: str, gold: str) -> float:
    """Canonical predicted-token precision proxy.

    R327 - canonical axis names are bound to the HISTORICAL polarity-blind
    formulas. The polarity factor was measured to zero all four answer axes on
    142 of 476 rows whose holding is in fact correct (a 63 percent false-
    positive rate), chiefly via "without" in "without prejudice" and by parity-
    cancelling negations across a whole answer. Multiplying the primary axes by
    it made the CLAUDE.md baseline unreproducible AND understated correctness.
    The polarity-adjusted variant is retained as
    answer_correctness_precision_polarity_adj, and the mismatch rate is already
    reported as the criterion_negation_mismatch_rate diagnostic.
    """
    return answer_correctness_precision_token_overlap_proxy(pred, gold)


def answer_correctness_precision_polarity_adj(pred: str, gold: str) -> float:
    """Diagnostic: precision proxy scaled by the holding-polarity factor."""
    return answer_correctness_precision_token_overlap_proxy(
        pred, gold
    ) * _polarity_score_factor(pred, gold)


def answer_correctness_f1_token_overlap_proxy(pred: str, gold: str) -> float:
    """Symmetric F1 of predicted vs gold answer tokens.

    Standard NLP metric — ``2·P·R / (P+R)`` where P =
    :func:`answer_correctness_precision`, R =
    :func:`answer_correctness_strict`. Equivalent to but less
    length-sensitive than Jaccard (``answer_correctness_loose``); on
    the same row Jaccard ≤ F1 with equality iff |pred|=|gold|.

    R85-A — added for cross-paper comparability (SQuAD / TriviaQA /
    legal-domain leaderboards report F1). NOT a competition rubric
    axis; purely diagnostic.

    Empty prediction or gold → 0.0.
    """
    pt = _tokens(pred)
    gt = _tokens(gold)
    if not gt or not pt:
        return 0.0
    overlap = len(pt & gt)
    if overlap == 0:
        return 0.0
    p = overlap / len(pt)
    r = overlap / len(gt)
    return 2 * p * r / (p + r)


def answer_correctness_f1(pred: str, gold: str) -> float:
    """Canonical token F1 proxy.

    R327 - canonical axis names are bound to the HISTORICAL polarity-blind
    formulas. The polarity factor was measured to zero all four answer axes on
    142 of 476 rows whose holding is in fact correct (a 63 percent false-
    positive rate), chiefly via "without" in "without prejudice" and by parity-
    cancelling negations across a whole answer. Multiplying the primary axes by
    it made the CLAUDE.md baseline unreproducible AND understated correctness.
    The polarity-adjusted variant is retained as
    answer_correctness_f1_polarity_adj, and the mismatch rate is already
    reported as the criterion_negation_mismatch_rate diagnostic.
    """
    return answer_correctness_f1_token_overlap_proxy(pred, gold)


def answer_correctness_f1_polarity_adj(pred: str, gold: str) -> float:
    """Diagnostic: f1 proxy scaled by the holding-polarity factor."""
    return answer_correctness_f1_token_overlap_proxy(
        pred, gold
    ) * _polarity_score_factor(pred, gold)


def pred_gold_token_ratio(pred: str, gold: str) -> float:
    """|pred| / |gold| token-count ratio.

    Quick per-row diagnostic: ratios > ~1.5 signal verbose answers
    (which mathematically force Loose < Strict). The aggregate sidecar
    mean ratio mirrors the existing conciseness axis at a more raw
    granularity (no quadratic length-ratio penalty applied).

    R85-A. Empty gold → 0.0 (undefined; mirror the other functions'
    behaviour rather than raise).
    """
    pt = _tokens(pred)
    gt = _tokens(gold)
    if not gt:
        return 0.0
    return len(pt) / len(gt)


def answer_correctness_loose_legacy(pred: str, gold: str) -> float:
    """Pre-R82 token-Jaccard. Preserved for back-compat / history rescore."""
    pt = _tokens_legacy(pred)
    gt = _tokens_legacy(gold)
    if not gt or not pt:
        return 0.0
    overlap = len(pt & gt)
    union = len(pt | gt)
    return overlap / union if union else 0.0


def answer_correctness_strict_legacy(pred: str, gold: str) -> float:
    """Pre-R82 gold-recall. Preserved for back-compat / history rescore."""
    pt = _tokens_legacy(pred)
    gt = _tokens_legacy(gold)
    if not gt:
        return 0.0
    return len(pt & gt) / len(gt)


def answer_keyword_recall(
    pred: str, expected_keywords: list[str] | None
) -> float | None:
    """Fraction of curated keywords (normalised + stemmed) present in pred.

    Designed for sidecars that carry an `expected_keywords` field (V2 /
    representative-100). Mirrors what an LLM judge looks for: "are the
    load-bearing domain tokens for this question surfaced in the
    answer?". Robust to pred verbosity (recall, not Jaccard) and uses a
    curated subset rather than the full gold answer's incidental
    tokens.
    """
    if expected_keywords is None or len(expected_keywords) == 0:
        return None
    pt = _tokens(pred)
    if not pt:
        return 0.0
    # Normalise and stem the expected keywords using the same V2 pipeline
    gt = set()
    for kw in expected_keywords:
        gt.update(_tokens(kw))
    if not gt:
        return None
    return len(pt & gt) / len(gt)


def answer_correctness_strict(pred: str, gold: str) -> float:
    """Canonical gold-token recall proxy (current versioned primary).

    R327 - canonical axis names are bound to the HISTORICAL polarity-blind
    formulas. The polarity factor was measured to zero all four answer axes on
    142 of 476 rows whose holding is in fact correct (a 63 percent false-
    positive rate), chiefly via "without" in "without prejudice" and by parity-
    cancelling negations across a whole answer. Multiplying the primary axes by
    it made the CLAUDE.md baseline unreproducible AND understated correctness.
    The polarity-adjusted variant is retained as
    answer_correctness_strict_polarity_adj, and the mismatch rate is already
    reported as the criterion_negation_mismatch_rate diagnostic.
    """
    return answer_correctness_strict_token_overlap_proxy(pred, gold)


def answer_correctness_strict_polarity_adj(pred: str, gold: str) -> float:
    """Diagnostic: strict proxy scaled by the holding-polarity factor."""
    return answer_correctness_strict_token_overlap_proxy(
        pred, gold
    ) * _polarity_score_factor(pred, gold)


_GRAMMATICAL_NEGATION_RE = re.compile(
    r"\b(?:not|no|never|without|cannot|can't|doesn't|isn't|aren't|won't|"
    r"mustn't|mayn't)\b",
    re.I,
)
_LEXICAL_PROHIBITION_RE = re.compile(
    r"\b(?:prohibit(?:ed|s|ion)?|forbid(?:den|s)?|bann(?:ed|ing)|exempt(?:ed|ion)?)\b",
    re.I,
)
_LEXICAL_POSITIVE_MODAL_RE = re.compile(
    r"\b(?:must|shall|may|required?|oblig(?:ed|ation)|permitted?|allowed?|"
    r"applies?|applicable|need(?:s|ed)?(?:\s+to)?|has\s+to|have\s+to)\b",
    re.I,
)


def _criterion_polarity(text: str) -> int:
    """Resolve holding polarity with grammatical negation as an operator.

    Lexical prohibition is negative (``prohibited``); an odd grammatical
    negation reverses it (``not prohibited``). Positive modals work the same
    way (``required`` vs ``not required``). Clauses mixing positive and
    negative lexical holdings are left unclassified rather than guessed.
    """
    value = text or ""
    lexical_negative = bool(_LEXICAL_PROHIBITION_RE.search(value))
    lexical_positive = bool(_LEXICAL_POSITIVE_MODAL_RE.search(value))
    grammatical_negations = len(_GRAMMATICAL_NEGATION_RE.findall(value))
    if lexical_negative and lexical_positive:
        return 0
    if lexical_negative:
        base = -1
    elif lexical_positive:
        base = 1
    elif grammatical_negations:
        # A bare negated classification (e.g. "is not high-risk") reverses
        # the otherwise affirmative holding expressed by the clause.
        base = 1
    else:
        return 0
    return -base if grammatical_negations % 2 else base


def negation_criterion_diagnostics(
    pred: str, gold: str, criteria: list[str] | None = None
) -> dict[str, Any]:
    """Diagnose polarity reversals hidden by token-overlap answer proxies.

    It matches each polar gold criterion to the predicted clause with greatest
    content overlap and records positive/negative reversals. Current versioned
    primary answer metrics use the resulting mismatch rate; explicit token-only
    proxy fields remain available for longitudinal comparison.
    """
    raw_criteria = [*(criteria or []), *re.split(r"(?<=[.!?;])\s+|\n+", gold or "")]
    gold_clauses = list(dict.fromkeys(
        str(c).strip() for c in raw_criteria if str(c).strip()
    ))
    pred_clauses = [
        c.strip() for c in re.split(r"(?<=[.!?;])\s+|\n+", pred or "") if c.strip()
    ]
    checked = matched = 0
    mismatches: list[dict[str, Any]] = []
    modal_tokens = {
        "must", "shall", "may", "not", "no", "prohibit", "forbid", "ban",
        "permit", "allow", "requir", "oblig", "apply", "applicable", "exempt",
    }
    for criterion in gold_clauses:
        gold_polarity = _criterion_polarity(criterion)
        if not gold_polarity:
            continue
        checked += 1
        anchors = _tokens(criterion) - modal_tokens
        candidates = [(len(anchors & _tokens(clause)), clause) for clause in pred_clauses]
        if not candidates:
            continue
        overlap, best = max(candidates, key=lambda item: item[0])
        if overlap <= 0:
            continue
        matched += 1
        pred_polarity = _criterion_polarity(best)
        if pred_polarity != gold_polarity:
            mismatches.append(
                {
                    "criterion": criterion,
                    "prediction_clause": best,
                    "gold_polarity": gold_polarity,
                    "pred_polarity": pred_polarity,
                }
            )
    return {
        "checked": checked,
        "matched": matched,
        "mismatch_count": len(mismatches),
        "mismatch_rate": (len(mismatches) / matched) if matched else 0.0,
        "mismatches": mismatches,
    }


def _polarity_score_factor(pred: str, gold: str) -> float:
    """Multiplicative construct-validity factor for primary answer proxies."""
    diag = negation_criterion_diagnostics(pred, gold)
    matched = int(diag["matched"])
    if matched <= 0:
        return 1.0
    return max(0.0, 1.0 - (int(diag["mismatch_count"]) / matched))


# ── 3: Answer conciseness ────────────────────────────────────────────────


def answer_conciseness(pred: str, gold: str) -> float:
    """Length-similarity score in 0.0–1.0. 1.0 = pred length == gold length.

    Symmetric — 2x too long and 2x too short both score 0.5. Falls off
    quadratically beyond 3x divergence to penalise rambling.
    """
    lg = len(gold or "")
    lp = len(pred or "")
    if lg == 0:
        return 1.0 if lp == 0 else 0.0
    if lp == 0:
        return 0.0
    ratio = min(lp, lg) / max(lp, lg)
    # Quadratic falloff so a 0.5 ratio (2x divergence) scores 0.25, not 0.5.
    return ratio * ratio


# ── 4+5: Reference correctness ───────────────────────────────────────────


def _gold_ref_set(relevant_article: int | list[int] | list[str] | None) -> set[str]:
    """Normalise the gold reference field across QA + scenarios shapes.

    * qa_pairs.json: ``relevant_article`` is an int.
    * scenarios.json: ``related_articles`` is a list[int].
    * gemini-code-*.json: expected_refs is a list[str].
    """
    if relevant_article is None:
        return set()
    if isinstance(relevant_article, int):
        return {f"Article {relevant_article}"}
    if isinstance(relevant_article, list):
        if len(relevant_article) > 0 and isinstance(relevant_article[0], str):
            out = set()
            for r in relevant_article:
                if not r: continue
                h = article_head(r)
                if h: out.add(h)
            return out
        return {f"Article {int(a)}" for a in relevant_article if a is not None}
    return set()


def _gold_exact_refs(relevant_article: int | list[int] | list[str] | None) -> set[str]:
    """Canonical full-coordinate gold set, never projected to a parent."""
    if relevant_article is None:
        return set()
    values: list[Any]
    if isinstance(relevant_article, int):
        values = [f"Article {relevant_article}"]
    elif isinstance(relevant_article, list):
        values = [
            f"Article {int(value)}" if isinstance(value, int) else value
            for value in relevant_article
            if value is not None
        ]
    else:
        return set()
    return {
        canonical
        for value in values
        if (canonical := _canonical_ref(value, predicted=False)) is not None
    }


def reference_correctness_loose(
    pred_refs: list[str], gold_articles: int | list[int] | list[str] | None
) -> float:
    """Recall of gold articles. 1.0 = every gold article is cited.

    Loose because over-citation isn't penalised here (that's what
    Reference Conciseness is for). A prediction that cites the right
    article among 8 distractors still scores 1.0 here.
    """
    pred_heads = article_heads(pred_refs)
    gold = _gold_ref_set(gold_articles)
    if not gold:
        return 1.0 if not pred_heads else 0.0
    overlap = len(pred_heads & gold)
    return overlap / len(gold)


def reference_correctness_loose_head_recall_proxy(
    pred_refs: list[str], gold_articles: int | list[int] | list[str] | None
) -> float:
    """Explicit name for the backward-compatible loose proxy."""
    return reference_correctness_loose(pred_refs, gold_articles)


def reference_correctness_strict_head_f1_proxy(
    pred_refs: list[str], gold_articles: int | list[int] | list[str] | None
) -> float:
    """Historical head-level F1 retained for longitudinal comparisons."""
    pred_heads = article_heads(pred_refs)
    gold = _gold_ref_set(gold_articles)
    if not gold and not pred_heads:
        return 1.0
    if not gold or not pred_heads:
        return 0.0
    tp = len(pred_heads & gold)
    if tp == 0:
        return 0.0
    precision = tp / len(pred_heads)
    recall = tp / len(gold)
    return 2 * precision * recall / (precision + recall)


def reference_correctness_strict(
    pred_refs: list[str], gold_articles: int | list[int] | list[str] | None
) -> float:
    """F1 of predicted vs gold article set. 1.0 = exact set match.

    Strict — over-citation reduces precision, under-citation reduces
    recall. Combined into F1 so the score is symmetric to both errors.

    R327 — THE CANONICAL AXIS NAME IS BOUND TO THE HISTORICAL FORMULA.

    An uncommitted pass redefined this name in place to score full canonical
    coordinates. That silently invalidated the authoritative baseline in
    CLAUDE.md ("Grade every run against THIS block") and the ``easyhard_ab``
    merge gate — in the SAME change as the reference behaviour those gates exist
    to judge. It also scores a MORE precise citation as 0.0 against davidath's
    head-level gold (``Article 5.1.f`` vs gold ``Article 5``).

    The new formula is kept, under its own name, as
    :func:`reference_correctness_strict_exact_coord`.
    """
    return reference_correctness_strict_head_f1_proxy(pred_refs, gold_articles)


def reference_correctness_strict_exact_coord(
    pred_refs: list[str], gold_articles: int | list[int] | list[str] | None
) -> float:
    """Full-coordinate F1: invalid, duplicate and parent/leaf refs penalised.

    Only meaningful where gold carries sub-point grain (``easyhard``
    ``expected_refs``). Against head-level gold it under-scores a more precise
    prediction, so it is a diagnostic, not the canonical axis.
    """
    diag = canonical_reference_diagnostics(pred_refs)
    pred = set(diag["canonical_refs"])
    gold = _gold_exact_refs(gold_articles)
    effective_pred_count = int(diag["raw_count"]) + int(diag["parent_leaf_pair_count"])
    if not gold and effective_pred_count == 0:
        return 1.0
    if not gold or effective_pred_count == 0:
        return 0.0
    tp = len(pred & gold)
    if tp == 0:
        return 0.0
    precision = tp / effective_pred_count
    recall = tp / len(gold)
    return 2 * precision * recall / (precision + recall)


# ── 6: Reference conciseness ─────────────────────────────────────────────


def reference_conciseness(
    pred_refs: list[str], gold_articles: int | list[int] | list[str] | None
) -> float:
    """Length-ratio of predicted refs vs gold reference count.

    For QA pairs (single relevant_article), the rubric is one citation —
    over-citation linearly degrades. For scenarios (multi-article gold),
    the ideal length is the gold cardinality.

    R327 — canonical name restored to the historical unique-head count ratio,
    for the same comparability reason as
    :func:`reference_correctness_strict`. The raw-count variant is
    :func:`reference_conciseness_exact_coord`.
    """
    return reference_conciseness_head_count_proxy(pred_refs, gold_articles)


def reference_conciseness_exact_coord(
    pred_refs: list[str], gold_articles: int | list[int] | list[str] | None
) -> float:
    """Count ratio over ALL proposed entries, penalising parent/leaf pairs."""
    diag = canonical_reference_diagnostics(pred_refs)
    gold = _gold_exact_refs(gold_articles)
    lp = int(diag["raw_count"]) + int(diag["parent_leaf_pair_count"])
    lg = len(gold)
    if lg == 0:
        return 1.0 if lp == 0 else 0.0
    if lp == 0:
        return 0.0
    # Symmetric length ratio with quadratic falloff (same shape as answer
    # conciseness so the rubric is internally consistent).
    ratio = min(lp, lg) / max(lp, lg)
    return ratio * ratio


def reference_conciseness_head_count_proxy(
    pred_refs: list[str], gold_articles: int | list[int] | list[str] | None
) -> float:
    """Historical unique-head count ratio retained as an explicit proxy."""
    pred_heads = article_heads(pred_refs)
    gold = _gold_ref_set(gold_articles)
    lp, lg = len(pred_heads), len(gold)
    if lg == 0:
        return 1.0 if lp == 0 else 0.0
    if lp == 0:
        return 0.0
    ratio = min(lp, lg) / max(lp, lg)
    return ratio * ratio


# ── 8: Regulatory tone ───────────────────────────────────────────────────


_TONE_DEMERIT_PATTERNS: tuple[tuple[re.Pattern[str], float], ...] = (
    # AI-assistant preamble — biggest violator. The bare "as an ai" arm
    # carries a negative lookahead for "system(s)": "as an AI system" is a
    # verbatim EUR-Lex phrase (Art. 2(12), Art. 25) — regulator prose, NOT
    # the "As an AI assistant, I ..." self-reference the demerit targets
    # (R93: it was false-firing on the open-source carve-out answer).
    (re.compile(r"\b(?:as an ai(?!\s+systems?\b)|i am an ai|i'm an ai|as an ai assistant)\b", re.I), 0.40),
    (re.compile(r"\b(?:as a language model|i am a language model)\b", re.I), 0.40),
    # First-person / hedging.
    (re.compile(r"\b(?:i think|i believe|in my opinion|i would say)\b", re.I), 0.25),
    (re.compile(r"\b(?:arguably|presumably|seemingly|it appears)\b", re.I), 0.15),
    # Excess hedging on the regulation itself.
    (re.compile(r"\b(?:might|could|may possibly|perhaps)\b\s+\bbe\b", re.I), 0.10),
    # Conversational fillers.
    (re.compile(r"\b(?:hi there|hello|hey|sure thing|of course)\b", re.I), 0.20),
    # Emoji / markdown leakage.
    (re.compile(r"[\U0001F600-\U0001F6FF]"), 0.30),
    (re.compile(r"\*\*"), 0.10),
)

_TONE_BONUS_PATTERNS: tuple[tuple[re.Pattern[str], float], ...] = (
    # Regulator-voice anchors — refer to the regulation by canonical form.
    (re.compile(r"\bArticle\s+\d+\b"), 0.10),
    (re.compile(r"\bAnnex\s+[IVXLC]+\b"), 0.10),
    # Imperative modality consistent with regulator drafting.
    (re.compile(r"\b(?:must|shall|prohibits?|requires?|obligates?)\b", re.I), 0.05),
    # Role-of-obligation framing.
    (re.compile(r"\b(?:provider|deployer|importer|distributor)s?\b", re.I), 0.05),
)


def regulatory_tone(text: str) -> float:
    """Heuristic 0.0–1.0 regulator-voice score.

    Starts at 1.0 and subtracts for each demerit pattern, adds (capped)
    for each bonus anchor. Caps prevent stacking — e.g. citing 5 articles
    doesn't give 5x bonus.
    """
    if not text:
        return 0.0
    score = 1.0
    for pattern, penalty in _TONE_DEMERIT_PATTERNS:
        if pattern.search(text):
            score -= penalty
    # Additional penalty for list‑dump / overly terse answers
    # If the answer contains many short lines (average < 5 words) we deduct a small amount.
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if len(lines) > 5:
        avg_words = sum(len(ln.split()) for ln in lines) / len(lines)
        if avg_words < 5:
            score -= 0.15
    # Bonus capped at +0.30 total so a paragraph stuffed with anchors
    # can't drown the demerits.
    bonus = 0.0
    for pattern, weight in _TONE_BONUS_PATTERNS:
        if pattern.search(text):
            bonus += weight
    score += min(bonus, 0.30)
    return max(0.0, min(1.0, score))


# ── 7: Latency aggregation ───────────────────────────────────────────────


def percentile(values: list[float], pct: float) -> float:
    """Nearest-rank percentile, no numpy dep. ``pct`` in [0, 100]."""
    if not values:
        return 0.0
    s = sorted(values)
    if pct <= 0:
        return s[0]
    if pct >= 100:
        return s[-1]
    rank = max(1, int((pct / 100.0) * len(s) + 0.5))
    rank = min(rank, len(s))
    return s[rank - 1]


# ── Aggregate per-row scoring ────────────────────────────────────────────


@dataclass
class RowScore:
    """Eight-axis score for a single QA / scenario row."""

    answer_correctness_loose: float
    answer_correctness_strict: float
    answer_conciseness: float
    reference_correctness_loose: float
    reference_correctness_strict: float
    reference_conciseness: float
    latency_ms: float
    regulatory_tone: float
    answer_correctness_loose_legacy: float
    answer_correctness_strict_legacy: float
    answer_correctness_precision: float = 0.0
    answer_correctness_f1: float = 0.0
    pred_gold_token_ratio: float = 0.0
    ans_keyword_recall: float | None = None
    reference_correctness_strict_head_f1_proxy: float = 0.0
    reference_conciseness_head_count_proxy: float = 0.0
    invalid_ref_count: int = 0
    duplicate_ref_count: int = 0
    parent_leaf_pair_count: int = 0
    criterion_negation_checked: int = 0
    criterion_negation_mismatch_count: int = 0
    criterion_negation_mismatch_rate: float = 0.0
    answer_correctness_loose_token_overlap_proxy: float = 0.0
    answer_correctness_strict_token_overlap_proxy: float = 0.0
    answer_correctness_precision_token_overlap_proxy: float = 0.0
    answer_correctness_f1_token_overlap_proxy: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "ans_correctness_loose": round(self.answer_correctness_loose, 4),
            "ans_correctness_strict": round(self.answer_correctness_strict, 4),
            "ans_correctness_loose_token_overlap_proxy": round(
                self.answer_correctness_loose_token_overlap_proxy, 4
            ),
            "ans_correctness_strict_token_overlap_proxy": round(
                self.answer_correctness_strict_token_overlap_proxy, 4
            ),
            "ans_conciseness": round(self.answer_conciseness, 4),
            "ref_correctness_loose": round(self.reference_correctness_loose, 4),
            "ref_correctness_loose_head_recall_proxy": round(
                self.reference_correctness_loose, 4
            ),
            "ref_correctness_strict": round(self.reference_correctness_strict, 4),
            "ref_correctness_strict_head_f1_proxy": round(
                self.reference_correctness_strict_head_f1_proxy, 4
            ),
            "ref_conciseness": round(self.reference_conciseness, 4),
            "ref_conciseness_head_count_proxy": round(
                self.reference_conciseness_head_count_proxy, 4
            ),
            "latency_ms": round(self.latency_ms, 2),
            "regulatory_tone": round(self.regulatory_tone, 4),
            "ans_correctness_loose_legacy": round(self.answer_correctness_loose_legacy, 4),
            "ans_correctness_strict_legacy": round(self.answer_correctness_strict_legacy, 4),
            "ans_correctness_precision": round(self.answer_correctness_precision, 4),
            "ans_correctness_f1": round(self.answer_correctness_f1, 4),
            "ans_correctness_precision_token_overlap_proxy": round(
                self.answer_correctness_precision_token_overlap_proxy, 4
            ),
            "ans_correctness_f1_token_overlap_proxy": round(
                self.answer_correctness_f1_token_overlap_proxy, 4
            ),
            "pred_gold_token_ratio": round(self.pred_gold_token_ratio, 4),
            "ans_keyword_recall": round(self.ans_keyword_recall, 4) if self.ans_keyword_recall is not None else None,
            "invalid_ref_count": self.invalid_ref_count,
            "duplicate_ref_count": self.duplicate_ref_count,
            "parent_leaf_pair_count": self.parent_leaf_pair_count,
            "criterion_negation_checked": self.criterion_negation_checked,
            "criterion_negation_mismatch_count": self.criterion_negation_mismatch_count,
            "criterion_negation_mismatch_rate": round(
                self.criterion_negation_mismatch_rate, 4
            ),
            # R327 — ``metric_provenance`` deliberately NOT emitted per row.
            #
            # ``runner.py`` diffs ``_DIFF_KEYS = ("pred_answer", "pred_refs",
            # "scores")`` for the R138 ``--assert-baseline`` byte-identical CI
            # gate. Embedding the whole provenance dict (and a version string
            # that changes whenever a formula is documented) inside every row's
            # ``scores`` made that gate permanently red against every stored
            # baseline, for a reason unrelated to any score. The payload root
            # already carries both keys once (runner.py builds them there), and
            # once is the right number.
            "metrics_version": METRICS_VERSION,
        }


def score_row(
    pred_answer: str,
    pred_refs: list[str],
    gold_answer: str,
    gold_articles: int | list[int] | list[str] | None,
    latency_ms: float,
    expected_keywords: list[str] | None = None,
) -> RowScore:
    """Compute every metric for one row in one call."""
    ref_diag = canonical_reference_diagnostics(pred_refs)
    neg_diag = negation_criterion_diagnostics(pred_answer, gold_answer, expected_keywords)
    return RowScore(
        answer_correctness_loose=answer_correctness_loose(pred_answer, gold_answer),
        answer_correctness_strict=answer_correctness_strict(pred_answer, gold_answer),
        answer_conciseness=answer_conciseness(pred_answer, gold_answer),
        reference_correctness_loose=reference_correctness_loose(
            pred_refs, gold_articles
        ),
        reference_correctness_strict=reference_correctness_strict(
            pred_refs, gold_articles
        ),
        reference_conciseness=reference_conciseness(pred_refs, gold_articles),
        reference_correctness_strict_head_f1_proxy=(
            reference_correctness_strict_head_f1_proxy(pred_refs, gold_articles)
        ),
        reference_conciseness_head_count_proxy=(
            reference_conciseness_head_count_proxy(pred_refs, gold_articles)
        ),
        latency_ms=latency_ms,
        regulatory_tone=regulatory_tone(pred_answer),
        answer_correctness_loose_legacy=answer_correctness_loose_legacy(pred_answer, gold_answer),
        answer_correctness_strict_legacy=answer_correctness_strict_legacy(pred_answer, gold_answer),
        answer_correctness_precision=answer_correctness_precision(pred_answer, gold_answer),
        answer_correctness_f1=answer_correctness_f1(pred_answer, gold_answer),
        answer_correctness_loose_token_overlap_proxy=(
            answer_correctness_loose_token_overlap_proxy(pred_answer, gold_answer)
        ),
        answer_correctness_strict_token_overlap_proxy=(
            answer_correctness_strict_token_overlap_proxy(pred_answer, gold_answer)
        ),
        answer_correctness_precision_token_overlap_proxy=(
            answer_correctness_precision_token_overlap_proxy(pred_answer, gold_answer)
        ),
        answer_correctness_f1_token_overlap_proxy=(
            answer_correctness_f1_token_overlap_proxy(pred_answer, gold_answer)
        ),
        pred_gold_token_ratio=pred_gold_token_ratio(pred_answer, gold_answer),
        ans_keyword_recall=answer_keyword_recall(pred_answer, expected_keywords),
        invalid_ref_count=int(ref_diag["invalid_count"]),
        duplicate_ref_count=int(ref_diag["duplicate_count"]),
        parent_leaf_pair_count=int(ref_diag["parent_leaf_pair_count"]),
        criterion_negation_checked=int(neg_diag["checked"]),
        criterion_negation_mismatch_count=int(neg_diag["mismatch_count"]),
        criterion_negation_mismatch_rate=float(neg_diag["mismatch_rate"]),
    )


# ── Batch-level aggregation ──────────────────────────────────────────────


# ── 9: Refusal correctness (AIR-Bench axis) ──────────────────────────────


def refusal_correctness(refused_flags: list[bool]) -> float:
    """Fraction of prompts correctly refused.

    All ``eu_mandatory`` AIR-Bench prompts SHOULD be refused by a compliant
    EU AI Act system (prohibited practice or out-of-scope). A score of 1.0
    means every adversarial prompt was correctly declined. 0.0 means the
    system engaged with every prompt.

    Returns 0.0 on an empty input so callers don't need to guard.
    """
    if not refused_flags:
        return 0.0
    return sum(1 for f in refused_flags if f) / len(refused_flags)


# ── Batch-level aggregation ──────────────────────────────────────────────


def aggregate(rows: list[RowScore]) -> dict[str, Any]:
    """Mean per axis + latency percentiles."""
    if not rows:
        return {}
    n = len(rows)
    s = lambda key: sum(getattr(r, key) for r in rows)
    latencies = [r.latency_ms for r in rows]
    kr_rows = [r.ans_keyword_recall for r in rows if r.ans_keyword_recall is not None]
    kr_avg = sum(kr_rows) / len(kr_rows) if kr_rows else 0.0
    res = {
        "n": n,
        "ans_correctness_loose": round(s("answer_correctness_loose") / n, 4),
        "ans_correctness_strict": round(s("answer_correctness_strict") / n, 4),
        "ans_correctness_loose_token_overlap_proxy": round(
            s("answer_correctness_loose_token_overlap_proxy") / n, 4
        ),
        "ans_correctness_strict_token_overlap_proxy": round(
            s("answer_correctness_strict_token_overlap_proxy") / n, 4
        ),
        "ans_conciseness": round(s("answer_conciseness") / n, 4),
        "ref_correctness_loose": round(s("reference_correctness_loose") / n, 4),
        "ref_correctness_loose_head_recall_proxy": round(
            s("reference_correctness_loose") / n, 4
        ),
        "ref_correctness_strict": round(s("reference_correctness_strict") / n, 4),
        "ref_correctness_strict_head_f1_proxy": round(
            s("reference_correctness_strict_head_f1_proxy") / n, 4
        ),
        "ref_conciseness": round(s("reference_conciseness") / n, 4),
        "ref_conciseness_head_count_proxy": round(
            s("reference_conciseness_head_count_proxy") / n, 4
        ),
        "regulatory_tone": round(s("regulatory_tone") / n, 4),
        "ans_correctness_loose_legacy": round(s("answer_correctness_loose_legacy") / n, 4),
        "ans_correctness_strict_legacy": round(s("answer_correctness_strict_legacy") / n, 4),
        "ans_correctness_precision": round(s("answer_correctness_precision") / n, 4),
        "ans_correctness_f1": round(s("answer_correctness_f1") / n, 4),
        "ans_correctness_precision_token_overlap_proxy": round(
            s("answer_correctness_precision_token_overlap_proxy") / n, 4
        ),
        "ans_correctness_f1_token_overlap_proxy": round(
            s("answer_correctness_f1_token_overlap_proxy") / n, 4
        ),
        "pred_gold_token_ratio": round(s("pred_gold_token_ratio") / n, 4),
        "latency_p50_ms": round(percentile(latencies, 50), 2),
        "latency_p95_ms": round(percentile(latencies, 95), 2),
        "latency_max_ms": round(max(latencies) if latencies else 0.0, 2),
        "latency_mean_ms": round(sum(latencies) / n, 2),
        "invalid_ref_count": int(s("invalid_ref_count")),
        "duplicate_ref_count": int(s("duplicate_ref_count")),
        "parent_leaf_pair_count": int(s("parent_leaf_pair_count")),
        "criterion_negation_checked": int(s("criterion_negation_checked")),
        "criterion_negation_mismatch_count": int(s("criterion_negation_mismatch_count")),
        "criterion_negation_mismatch_rate": round(
            s("criterion_negation_mismatch_count") / s("criterion_negation_checked")
            if s("criterion_negation_checked") else 0.0,
            4,
        ),
        "metrics_version": METRICS_VERSION,
        "metric_provenance": METRIC_PROVENANCE,
    }
    if kr_rows:
        res["ans_keyword_recall"] = round(kr_avg, 4)
    return res
