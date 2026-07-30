"""R299 — Move 2: Deterministic enumerated-element completeness verifier.

Every remaining answer failure on the grounded judge is an omission of an
enumerated sub-element of a cited provision when the question asks for a set.
This module deterministically checks whether all subpoints ((a)/(b)/(c)/(d),
(i)/(ii)/(iii), numbered paragraphs) of a cited provision are represented in
the generated answer, and appends compact missing element labels when omitted.

Pure stdlib. Zero LLM calls. Millisecond latency.
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.engines._graph_rag_impl import GraphContext

__all__ = [
    "is_enumerated_set_question",
    "verify_and_enrich_enumerated_completeness",
]

# Rule 12b and set-question indicator shapes ("what are the", "which", "list", etc.)
_SET_QUESTION_RE = re.compile(
    r"\b(?:what (?:are|is) the|which|list|name|on what grounds|what obligations|"
    r"what requirements|what conditions|what information|what details|what steps|"
    r"what criteria|what exceptions|what elements|what duties|what practices|"
    r"what obligations must|what tasks)\b",
    re.IGNORECASE,
)

# Extract Article numbers cited in answer prose ("Article 23", "Articles 10 and 14", etc.)
_CITED_ART_LIST_RE = re.compile(
    r"\b(?:Articles?|Art\.?s?)\s+(\d{1,3}(?:\s*(?:,|and|or|&)\s*\d{1,3})*)",
    re.IGNORECASE,
)
_NUM_RE = re.compile(r"\b\d{1,3}\b")

# Generic legal/statutory stopwords to exclude from subpoint keyword matching
_SUBPOINT_STOPWORDS = frozenset(
    "the a an of to in on for and or as is are be by with that this which "
    "what when who how do does shall must may any all its their our we us "
    "eu ai act article articles annex regulation system systems provider "
    "deployer operator placing market market-surveillance requirement "
    "requirements obligation obligations provided drawn bears carry "
    "compliance ensure perform performed applicable specific general".split()
)


def is_enumerated_set_question(question: str) -> bool:
    """Return True if the question asks for a set/list of enumerated items."""
    if not question or not isinstance(question, str):
        return False
    return bool(_SET_QUESTION_RE.search(question))


def _extract_cited_article_numbers(text: str) -> list[int]:
    """Extract distinct article numbers cited in text in order of appearance."""
    seen: set[int] = set()
    nums: list[int] = []
    if not text or not isinstance(text, str):
        return nums
    for m in _CITED_ART_LIST_RE.finditer(text):
        for num_str in _NUM_RE.findall(m.group(1)):
            n = int(num_str)
            if n not in seen:
                seen.add(n)
                nums.append(n)
    return nums


def _get_subpoint_keywords(sub_text: str) -> list[str]:
    """Extract significant keywords (>3 chars, non-stopword) from subpoint text."""
    words = re.findall(r"\b[a-z]{4,}\b", (sub_text or "").lower())
    seen: set[str] = set()
    out: list[str] = []
    for w in words:
        if w not in _SUBPOINT_STOPWORDS and w not in seen:
            seen.add(w)
            out.append(w)
    return out


_MAX_LABEL_CHARS = 70
_MIN_LABEL_CHARS = 25

# Function words that must not END a label — cutting on them leaves a dangling
# fragment ("provide information as", "the responsibilities of the").
_LABEL_DANGLERS = frozenset(
    "a an the and or of to in on at by for with from as into under over "
    "that which who whose is are be been being shall must may including "
    "such referred set out pursuant accordance".split()
)


def _trim_dangling(label: str) -> str:
    """Drop trailing function words so the label ends on a content word."""
    words = label.split()
    while len(words) > 2 and words[-1].lower().strip(".,;:") in _LABEL_DANGLERS:
        words.pop()
    return " ".join(words)


def _extract_subpoint_label(sub_text: str) -> str:
    """Extract a concise, GRAMMATICAL label for a missing subpoint.

    R300 — was ``" ".join(kws[:3])``, i.e. the first three non-stopword
    tokens, which produced keyword salad that reads as broken English and
    misstates the provision: Article 16(g) "draw up the EU declaration of
    conformity" became "draw declaration conformity"; 16(d) "keep the
    documentation referred to in Article 18" became "keep documentation
    referred". A supplement is appended verbatim to a shipped legal answer,
    so it must read as regulatory prose, not as a bag of words.

    Now: take the VERBATIM opening clause of the sub-point, cut on a clause
    boundary (``;`` / ``,``) or a word boundary within ``_MAX_LABEL_CHARS``.
    Falls back to the keyword join only if no usable prose is present.
    """
    text = " ".join((sub_text or "").split()).strip()
    if not text:
        kws = _get_subpoint_keywords(sub_text)
        return " ".join(kws[:3]) if kws else "requirement"

    if len(text) <= _MAX_LABEL_CHARS:
        return _trim_dangling(text.rstrip(" .;,"))

    # Prefer a natural clause boundary inside the budget, but only when it
    # yields a substantive label — Article 17(h) opens "the setting-up, ..."
    # so an unguarded first-comma cut would emit the useless "the setting-up".
    for sep in (";", ","):
        idx = text.find(sep)
        if _MIN_LABEL_CHARS <= idx <= _MAX_LABEL_CHARS:
            return _trim_dangling(text[:idx].rstrip(" .;,"))

    cut = text.rfind(" ", 0, _MAX_LABEL_CHARS)
    if cut <= 0:
        cut = _MAX_LABEL_CHARS
    return _trim_dangling(text[:cut].rstrip(" .;,"))


def verify_and_enrich_enumerated_completeness(
    question: str,
    answer: str,
    context: Any = None,
) -> str:
    """Check answer completeness against verbatim enumerated subpoints of cited articles.

    If the question asks for a set/list and the answer omits sub-elements of a cited
    provision (e.g. points (c) and (d) of Article 23(1)), append a compact
    label supplement without inflating paragraph length or violating conciseness.
    """
    from app.data.graph_rag_prompts import completeness_verifier_enabled

    if not completeness_verifier_enabled() or not answer or not is_enumerated_set_question(question):
        return answer

    try:
        from app.data.provision_text import _paragraphs, _subpoints, article_body
    except Exception:  # noqa: BLE001
        return answer

    cited_arts = _extract_cited_article_numbers(answer)
    if not cited_arts:
        return answer

    answer_clean = answer.rstrip()
    answer_lower = answer_clean.lower()
    answer_words = set(re.findall(r"\b[a-z]{3,}\b", answer_lower))
    missing_supplements: list[str] = []

    for art_num in cited_arts[:2]:  # Check top 2 cited articles max to control budget
        long_key = f"Article {art_num}"
        body = article_body(long_key)
        if not body:
            continue

        paras = _paragraphs(body)
        target_paras = list(paras.values()) if paras else [body]

        for p_text in target_paras:
            subs = _subpoints(p_text)
            if len(subs) < 2:
                continue

            missing_letters: list[tuple[str, str]] = []
            for letter, sub_content in sorted(subs.items()):
                # Check explicit point mention like "(a)" or "point (a)"
                explicit_ref = f"({letter})" in answer_lower or f"point ({letter})" in answer_lower
                if explicit_ref:
                    continue

                # Check exact keyword overlap (word boundary match)
                kws = _get_subpoint_keywords(sub_content)
                if kws:
                    overlap = sum(1 for kw in kws if kw in answer_words)
                    if overlap >= max(1, min(2, len(kws))):
                        continue

                label = _extract_subpoint_label(sub_content)
                missing_letters.append((letter, label))

            if missing_letters and len(missing_letters) < len(subs):
                # Only supplement if PARTIAL omission (some points present, some
                # missing). NOTE (R300): the complete-omission case — where the
                # answer names NONE of the sub-points — is deliberately NOT
                # supplemented here. That is the inverse of the intent and is a
                # genuine defect, but widening the firing condition is an
                # answer-affecting change that needs the hard-rule-#6 live
                # ab_judge gate; deferred rather than shipped blind.
                labels = ", ".join(f"({let}) {txt}" for let, txt in missing_letters)
                # R300 — ATTRIBUTE the points to their own Article.
                #
                # Was: a single flat blob joined across BOTH cited articles,
                # e.g. "[including points (d) ..., (g) ...; including points
                # (h) ..., (m) ...]" for an answer citing Article 16 AND
                # Article 17. That reads as ONE list, repeats letters (i)/(j)
                # meaning different provisions, and — worst — presents Article
                # 17's points (a)-(m) as if they continued Article 16's list,
                # which stops at (l). Article 16 HAS no point (m). Asserting it
                # does is a confidently-wrong legal claim (hard rule #4), the
                # single worst defect class in this codebase.
                missing_supplements.append(
                    f"Article {art_num} also requires {labels}"
                )

    if missing_supplements:
        supp = " " + ". ".join(missing_supplements) + "."
        if answer_clean.endswith("."):
            return answer_clean + supp
        return answer_clean + "." + supp

    return answer
