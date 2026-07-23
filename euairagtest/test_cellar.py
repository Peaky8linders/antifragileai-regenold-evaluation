"""Offline tests for euaiact.ingest.cellar.

Network is NOT used here.  We supply a minimal inline Formex 4 XML fixture
that mirrors the real structure (ARTICLE + CONSID/NO.P elements) so the
parse functions can be exercised deterministically.
"""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import pytest

from euaiact.ingest.cellar import (
    _annex_entry_names,
    _parse_annexes,
    _parse_articles,
    _parse_recitals,
    _parse_zip,
    load_registry,
)
import xml.etree.ElementTree as ET

# ---------------------------------------------------------------------------
# Inline Formex 4 XML fixture (trimmed — only the elements we parse)
# ---------------------------------------------------------------------------
# Mimics the real .000101.fmx.xml structure:
#   ARTICLE IDENTIFIER="001" ... ARTICLE IDENTIFIER="113"
#   CONSID with NO.P "(1)" ... NO.P "(180)"
# We use a tiny subset (3 articles, 4 recitals) to keep the fixture small.

_FIXTURE_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<ACT>
  <PREAMBLE>
    <CONSID>
      <NO.P>(1)</NO.P>
      <TXT>First recital text.</TXT>
    </CONSID>
    <CONSID>
      <NO.P>(2)</NO.P>
      <TXT>Second recital text.</TXT>
    </CONSID>
    <CONSID>
      <NO.P>(3)</NO.P>
      <TXT>Third recital text.</TXT>
    </CONSID>
    <CONSID>
      <NO.P>(7)</NO.P>
      <TXT>Seventh recital (gap in numbering).</TXT>
    </CONSID>
  </PREAMBLE>
  <ENACTING.TERMS>
    <ARTICLE IDENTIFIER="001">
      <TI.ART>Article 1</TI.ART>
    </ARTICLE>
    <ARTICLE IDENTIFIER="005">
      <TI.ART>Article 5</TI.ART>
    </ARTICLE>
    <ARTICLE IDENTIFIER="113">
      <TI.ART>Article 113</TI.ART>
    </ARTICLE>
  </ENACTING.TERMS>
</ACT>
"""


def _make_zip(xml_content: str, entry_name: str = "body.000101.fmx.xml") -> bytes:
    """Build an in-memory ZIP with a single XML entry."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(entry_name, xml_content.encode())
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Tests for _parse_articles
# ---------------------------------------------------------------------------

def test_parse_articles_extracts_correct_numbers() -> None:
    root = ET.fromstring(_FIXTURE_XML)
    articles = _parse_articles(root)
    assert articles == [1, 5, 113]


def test_parse_articles_deduplicates() -> None:
    xml = """\
    <ACT>
      <ARTICLE IDENTIFIER="006"/>
      <ARTICLE IDENTIFIER="006"/>
      <ARTICLE IDENTIFIER="007"/>
    </ACT>"""
    root = ET.fromstring(xml)
    articles = _parse_articles(root)
    assert articles == [6, 7]


def test_parse_articles_ignores_non_numeric_identifiers() -> None:
    xml = """\
    <ACT>
      <ARTICLE IDENTIFIER="001"/>
      <ARTICLE IDENTIFIER="annex"/>
      <ARTICLE IDENTIFIER="003"/>
    </ACT>"""
    root = ET.fromstring(xml)
    articles = _parse_articles(root)
    assert articles == [1, 3]


# ---------------------------------------------------------------------------
# Tests for _parse_recitals
# ---------------------------------------------------------------------------

def test_parse_recitals_extracts_correct_numbers() -> None:
    root = ET.fromstring(_FIXTURE_XML)
    recitals = _parse_recitals(root)
    assert recitals == [1, 2, 3, 7]


def test_parse_recitals_handles_gap_in_numbering() -> None:
    root = ET.fromstring(_FIXTURE_XML)
    recitals = _parse_recitals(root)
    assert 7 in recitals
    # 4, 5, 6 are NOT in fixture — should not appear
    assert 4 not in recitals
    assert 5 not in recitals


# ---------------------------------------------------------------------------
# Tests for _parse_zip
# ---------------------------------------------------------------------------

def test_parse_zip_roundtrip() -> None:
    """_parse_zip on our fixture returns the expected article and recital lists."""
    zip_bytes = _make_zip(_FIXTURE_XML)
    result = _parse_zip(zip_bytes)
    assert result["articles"] == [1, 5, 113]
    assert result["recitals"] == [1, 2, 3, 7]
    assert result["main_entry"] == "body.000101.fmx.xml"


def test_parse_zip_selects_000101_entry_over_others() -> None:
    """When multiple fmx.xml entries exist, *.000101.fmx.xml is preferred."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        # A decoy non-body file (larger by byte count to foil the size fallback).
        decoy = "<ACT>" + "<ARTICLE IDENTIFIER='999'/>" * 10 + "</ACT>"
        zf.writestr("annex.000102.fmx.xml", decoy.encode())
        zf.writestr("body.000101.fmx.xml", _FIXTURE_XML.encode())
    result = _parse_zip(buf.getvalue())
    assert result["main_entry"] == "body.000101.fmx.xml"
    assert 999 not in result["articles"]


# ---------------------------------------------------------------------------
# Tests for annex parsing (_annex_entry_names / _parse_annexes)
# ---------------------------------------------------------------------------
# The real ZIP holds each annex as its own *.NNNN01.fmx.xml entry whose body
# opens with "ANNEX <roman>"; the enacting-terms body is *.000101.fmx.xml and
# the *.doc./*.toc. entries are metadata.  These fixtures mirror that layout.

def _annex_xml(roman: str) -> str:
    return f'<?xml version="1.0" encoding="UTF-8"?><ACT><TITLE><TI><P>ANNEX {roman}</P></TI></TITLE></ACT>'


def _make_multi_zip(entries: dict[str, str]) -> zipfile.ZipFile:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, content in entries.items():
            zf.writestr(name, content.encode())
    buf.seek(0)
    return zipfile.ZipFile(buf)


def test_annex_entry_names_excludes_body_doc_toc() -> None:
    zf = _make_multi_zip({
        "L.000101.fmx.xml": _FIXTURE_XML,          # enacting-terms body
        "L.doc.fmx.xml": "<X/>",                    # metadata
        "L.toc.fmx.xml": "<X/>",                    # metadata
        "L.012401.fmx.xml": _annex_xml("I"),        # annex
        "L.012601.fmx.xml": _annex_xml("II"),       # annex
    })
    names = _annex_entry_names(zf)
    assert names == ["L.012401.fmx.xml", "L.012601.fmx.xml"]


def test_parse_annexes_extracts_romans_in_order() -> None:
    zf = _make_multi_zip({
        "L.000101.fmx.xml": _FIXTURE_XML,
        "L.014401.fmx.xml": _annex_xml("XIII"),
        "L.012401.fmx.xml": _annex_xml("I"),
        "L.012601.fmx.xml": _annex_xml("II"),
    })
    # Entries are visited in ascending name order -> I, II, then XIII.
    assert _parse_annexes(zf) == ["I", "II", "XIII"]


def test_parse_annexes_takes_title_not_cross_reference() -> None:
    # An annex body that references another annex AFTER its own title must
    # still resolve to its own number (first match wins).
    body = ('<ACT><TITLE><TI><P>ANNEX V</P></TI></TITLE>'
            '<P>as set out in ANNEX I to this Regulation</P></ACT>')
    zf = _make_multi_zip({"L.000101.fmx.xml": _FIXTURE_XML, "L.013201.fmx.xml": body})
    assert _parse_annexes(zf) == ["V"]


def test_parse_annexes_dedups_repeated_roman() -> None:
    body = ('<ACT><TITLE><TI><P>ANNEX III</P></TI></TITLE>'
            '<P>see ANNEX III again</P></ACT>')
    zf = _make_multi_zip({"L.000101.fmx.xml": _FIXTURE_XML, "L.012701.fmx.xml": body})
    assert _parse_annexes(zf) == ["III"]


def test_parse_annexes_empty_when_no_annex_entries() -> None:
    zf = _make_multi_zip({"L.000101.fmx.xml": _FIXTURE_XML})
    assert _parse_annexes(zf) == []


def test_parse_zip_includes_parsed_annexes() -> None:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("L.000101.fmx.xml", _FIXTURE_XML.encode())
        zf.writestr("L.012401.fmx.xml", _annex_xml("I").encode())
        zf.writestr("L.012601.fmx.xml", _annex_xml("II").encode())
    result = _parse_zip(buf.getvalue())
    assert result["annexes"] == ["I", "II"]
    assert result["articles"] == [1, 5, 113]


# ---------------------------------------------------------------------------
# Test load_registry against the real persisted file (if present)
# ---------------------------------------------------------------------------

def test_load_registry_returns_none_when_absent(tmp_path: Path) -> None:
    result = load_registry(tmp_path / "nonexistent.json")
    assert result is None


def test_load_registry_returns_dict_when_present(tmp_path: Path) -> None:
    data = {"celex": "32024R1689", "articles": [1, 2, 3], "recitals": list(range(1, 5)),
            "annexes": ["I"], "counts": {"articles": 3, "recitals": 4, "annexes": 1}}
    p = tmp_path / "reg.json"
    p.write_text(json.dumps(data))
    result = load_registry(p)
    assert result is not None
    assert result["celex"] == "32024R1689"
    assert result["counts"]["articles"] == 3


@pytest.mark.skipif(
    not (Path(__file__).resolve().parents[1] / "data" / "authoritative_registry.json").exists(),
    reason="authoritative_registry.json not present (run euaiact-cellar first)",
)
def test_live_registry_has_expected_counts() -> None:
    """Smoke-test the real registry produced by the cellar fetch."""
    registry = load_registry()
    assert registry is not None
    assert registry["celex"] == "32024R1689"
    assert registry["counts"]["articles"] == 113
    assert registry["counts"]["recitals"] == 180
    assert registry["counts"]["annexes"] == 13
    assert max(registry["articles"]) == 113
    assert max(registry["recitals"]) == 180
    assert registry["annexes"] == [
        "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII", "XIII"
    ]
