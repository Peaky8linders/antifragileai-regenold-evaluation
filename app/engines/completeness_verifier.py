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


def _extract_subpoint_label(sub_text: str) -> str:
    """Extract a concise substantive noun phrase label for a missing subpoint."""
    kws = _get_subpoint_keywords(sub_text)
    if kws:
        return " ".join(kws[:3])
    # Fallback to first few cleaned words
    clean = " ".join((sub_text or "").split()[:4]).rstrip(";,.")
    return clean or "requirement"


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
                # Only supplement if PARTIAL omission (some points present, some missing)
                labels = ", ".join(f"({let}) {txt}" for let, txt in missing_letters)
                missing_supplements.append(f"including points {labels}")

    if missing_supplements:
        supp = " [" + "; ".join(missing_supplements) + "]"
        if answer_clean.endswith("."):
            return answer_clean[:-1] + supp + "."
        return answer_clean + supp

    return answer
