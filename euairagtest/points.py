"""Deterministic point / sub-point splitter.

The Hugging Face corpus (``jeroenherczeg/eu-ai-act``) is only granular down to the
*paragraph*; its finest article chunk is e.g. ``art_5__para_1``. But the citation
target — and the project's gold eval set — needs *point* and *sub-point* grain
(``art_5__para_1__point_a``, ``art_5__para_1__point_h__sub_i``).

We recover that grain by parsing the enumerated markers out of the paragraph text:
lettered points ``(a) … (b) …`` and roman sub-points ``(i) … (ii) …``. This is
deterministic (no LLM, zero hallucination) and mints IDs that round-trip through
``ProvisionId``. It is a heuristic on prose, so the authoritative Formex/Cellar XML
remains the cross-check (plan §3) — see the documented limitations below.

Limitations (by design, for a first cut):
* Only two levels: lettered points and roman sub-points.
* A lone ``(i)`` is read as the roman sub-point start only when an ``(ii)`` follows;
  otherwise it is the 9th lettered point. Deeper/irregular nesting is left to Formex.
"""

from __future__ import annotations

import re

from ..models import Provision

__all__ = [
    "split_paragraph",
    "split_annex_item",
    "split_definitions",
    "extract_enumeration",
    "extract_definitions",
]

_MARKER_RE = re.compile(r"\(([a-z]{1,5})\)")
_LETTERS = "abcdefghijklmnopqrstuvwxyz"
# A definition starts with a numbered marker immediately followed by an opening
# quote — ``(1) "AI system" means …``. The look-ahead keeps the quote in the sliced
# text and excludes inline numeric cross-references like ``point (44)``.
_DEF_RE = re.compile(r"\((\d{1,3})\)\s+(?=[\"“”'‘’])")


def _next_letter(c: str) -> str:
    i = _LETTERS.index(c)
    return _LETTERS[i + 1] if i + 1 < len(_LETTERS) else ""


def _int_to_roman(n: int) -> str:
    table = [(10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i")]
    out = []
    for val, sym in table:
        while n >= val:
            out.append(sym)
            n -= val
    return "".join(out)


def _marker_spans(text: str) -> list[tuple[int, int, str]]:
    return [(m.start(), m.end(), m.group(1)) for m in _MARKER_RE.finditer(text)]


def extract_enumeration(text: str) -> list[tuple[str, str, list[tuple[str, str]]]]:
    """Return ``[(letter, point_text, [(roman, subpoint_text), ...]), ...]``.

    Only markers that continue the expected sequence (a, b, c, …) are treated as
    real item boundaries, which filters out inline references like "point (a)".
    Item text runs to the next *kept* boundary, so spurious inline markers do not
    truncate it.
    """
    spans = _marker_spans(text)
    if not spans:
        return []

    # Classify each marker as a level-1 letter point or part of a roman sub-run.
    points: list[tuple[str, int]] = []  # (letter, span_index)
    subs: dict[int, list[tuple[str, int]]] = {}  # point_span_idx -> [(roman, span_idx)]
    expected_letter = "a"
    i = 0
    while i < len(spans):
        label = spans[i][2]
        # roman sub-run: current is "i" and the next marker is "ii"
        if label == "i" and i + 1 < len(spans) and spans[i + 1][2] == "ii" and points:
            parent_idx = points[-1][1]
            run: list[tuple[str, int]] = []
            expected_roman_n = 1
            j = i
            while j < len(spans) and spans[j][2] == _int_to_roman(expected_roman_n):
                run.append((spans[j][2], j))
                expected_roman_n += 1
                j += 1
            subs[parent_idx] = run
            i = j
            continue
        if label == expected_letter:
            points.append((label, i))
            expected_letter = _next_letter(expected_letter)
            i += 1
            continue
        i += 1  # spurious / inline marker — skip

    # Each kept item's text ends where the next kept item begins (ignore spurious).
    kept = sorted([idx for _, idx in points] + [s for run in subs.values() for _, s in run])
    end_at: dict[int, int] = {}
    for a, b in zip(kept, kept[1:]):
        end_at[a] = spans[b][0]
    if kept:
        end_at[kept[-1]] = len(text)

    def slice_item(idx: int) -> str:
        return text[spans[idx][1] : end_at[idx]].strip(" ;.\n\t")

    result: list[tuple[str, str, list[tuple[str, str]]]] = []
    for letter, span_idx in points:
        sub_list = [(roman, slice_item(sidx)) for roman, sidx in subs.get(span_idx, [])]
        result.append((letter, slice_item(span_idx), sub_list))
    return result


def split_paragraph(paragraph: Provision) -> list[Provision]:
    """Expand a paragraph Provision into its point / sub-point child Provisions.

    Returns only the newly-minted children (not the paragraph itself). Non-paragraph
    provisions, or paragraphs with no enumeration, yield an empty list.
    """
    if paragraph.article is None or paragraph.paragraph is None:
        return []
    enum = extract_enumeration(paragraph.text)
    if not enum:
        return []

    children: list[Provision] = []
    common = dict(
        chapter=paragraph.chapter,
        section=paragraph.section,
        celex=paragraph.celex,
        lang=paragraph.lang,
        effective_from=paragraph.effective_from,
        source_url=paragraph.source_url,
    )
    for letter, point_text, subs in enum:
        point_id = f"{paragraph.provision_id}__point_{letter}"
        children.append(
            Provision(
                provision_id=point_id,
                chunk_type="point",
                text=point_text,
                parent_text=paragraph.text,
                **common,
            )
        )
        for roman, sub_text in subs:
            children.append(
                Provision(
                    provision_id=f"{point_id}__sub_{roman}",
                    chunk_type="subpoint",
                    text=sub_text,
                    parent_text=point_text,
                    **common,
                )
            )
    return children


def extract_definitions(text: str) -> list[tuple[int, str]]:
    """Return ``[(number, definition_text), …]`` for a definitions article (Art. 3).

    Article 3 is one monolithic block — ``… the following definitions apply: (1) "AI
    system" means …; (2) "risk" means …`` — with no separate paragraph rows in the HF
    corpus, so the per-definition citation grain the gold set needs (``art_3__para_39``)
    has to be recovered from prose. Only the sequential run ``(1), (2), (3), …`` is kept,
    so numeric cross-references embedded in a definition body do not create false splits.
    """
    marks = [(m.start(), m.end(), int(m.group(1))) for m in _DEF_RE.finditer(text)]
    kept: list[tuple[int, int, int]] = []
    expected = 1
    for start, end, n in marks:
        if n == expected:
            kept.append((start, end, n))
            expected += 1
    if len(kept) < 2:  # a lone match is almost certainly not a definitions list
        return []
    out: list[tuple[int, str]] = []
    for i, (_start, end, n) in enumerate(kept):
        stop = kept[i + 1][0] if i + 1 < len(kept) else len(text)
        out.append((n, text[end:stop].strip(" ;.\n\t")))
    return out


def split_definitions(article: Provision) -> list[Provision]:
    """Expand a definitions article (Art. 3) into one paragraph child per definition.

    Mints ``art_3__para_{n}`` with ``chunk_type="paragraph"`` — matching the gold set's
    grain for definitions. Non-definition articles yield an empty list (the sequential
    ``(n) "…"`` pattern only occurs in Art. 3), so this is safe to call on any article.
    """
    if article.article is None or article.paragraph is not None:
        return []
    defs = extract_definitions(article.text)
    if not defs:
        return []
    common = dict(
        chapter=article.chapter,
        section=article.section,
        celex=article.celex,
        lang=article.lang,
        effective_from=article.effective_from,
        source_url=article.source_url,
    )
    return [
        Provision(
            provision_id=f"art_{article.article}__para_{n}",
            chunk_type="paragraph",
            text=def_text,
            parent_text=article.text,
            **common,
        )
        for n, def_text in defs
    ]


def split_annex_item(annex_item: Provision) -> list[Provision]:
    """Expand a numbered annex point into its lettered sub-points.

    e.g. ``annex_III__point_4`` -> ``annex_III__point_4__point_a`` / ``__point_b``.
    Same enumeration mechanics as articles; the id suffix is ``__point_{letter}``
    in both cases (an annex sub-point and an article point share the AKN ``point``
    level), so this reuses ``extract_enumeration``.
    """
    if annex_item.annex is None or annex_item.annex_point is None:
        return []
    enum = extract_enumeration(annex_item.text)
    if not enum:
        return []
    common = dict(
        chapter=annex_item.chapter,
        section=annex_item.section,
        celex=annex_item.celex,
        lang=annex_item.lang,
        effective_from=annex_item.effective_from,
        source_url=annex_item.source_url,
    )
    children: list[Provision] = []
    for letter, point_text, _subs in enum:
        children.append(
            Provision(
                provision_id=f"{annex_item.provision_id}__point_{letter}",
                chunk_type="annex_subpoint",
                text=point_text,
                parent_text=annex_item.text,
                **common,
            )
        )
    return children
