"""Fetch the OFFICIAL Formex 4 XML for CELEX 32024R1689 from the EU Publications
Office (Cellar) and parse an authoritative provision registry.

Lazy/optional-network discipline mirrors the HF loader: the deterministic graph
build does NOT call this module.  Only the ``euaiact-cellar`` CLI (or an explicit
``fetch_registry()`` call) touches the network.  The result is persisted to
``data/authoritative_registry.json`` and loaded offline by the graph builder.

Usage::

    euaiact-cellar                            # writes data/authoritative_registry.json
    euaiact-cellar --out path/to/file.json

Pure standard library (urllib, zipfile, xml.etree.ElementTree, json).
No extra dependencies required.
"""

from __future__ import annotations

import json
import re
import sys
import urllib.parse
import urllib.request
import zipfile
import xml.etree.ElementTree as ET
from io import BytesIO
from pathlib import Path
from typing import Any

__all__ = ["fetch_registry", "load_registry", "main"]

CELEX = "32024R1689"

# Fallback if SPARQL returns nothing (verified 2026-07-22 against Cellar).
_FALLBACK_MANIFESTATION_URI = (
    "http://publications.europa.eu/resource/cellar/"
    "dc8116a1-3fe6-11ef-865a-01aa75ed71a1.0006.02"
)

_SPARQL_ENDPOINT = "http://publications.europa.eu/webapi/rdf/sparql"
_SPARQL_QUERY = """\
PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
SELECT ?manif WHERE {
  ?work cdm:resource_legal_id_celex "32024R1689"^^<http://www.w3.org/2001/XMLSchema#string> .
  ?expr cdm:expression_belongs_to_work ?work ;
        cdm:expression_uses_language <http://publications.europa.eu/resource/authority/language/ENG> .
  ?manif cdm:manifestation_manifests_expression ?expr ;
         cdm:manifestation_type "fmx4"^^<http://www.w3.org/2001/XMLSchema#string> .
}
"""

# Valid annex romans for the EU AI Act (I–XIII); hardcoded because annex bodies
# may span multiple ZIP entries and cross-referencing is unreliable.
_VALID_ANNEXES = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII", "XIII"]


# ---------------------------------------------------------------------------
# SPARQL discovery
# ---------------------------------------------------------------------------

def _sparql_discover(timeout: int = 20) -> str | None:
    """Query Cellar SPARQL for the English fmx4 manifestation URI.

    Returns the URI string or None on any failure (network, parse, empty result).
    """
    params = urllib.parse.urlencode({
        "query": _SPARQL_QUERY,
        "format": "application/sparql-results+json",
    })
    url = f"{_SPARQL_ENDPOINT}?{params}"
    req = urllib.request.Request(url, headers={"Accept": "application/sparql-results+json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
        bindings = data.get("results", {}).get("bindings", [])
        if not bindings:
            return None
        return bindings[0]["manif"]["value"]
    except Exception:
        return None


# ---------------------------------------------------------------------------
# ZIP + Formex parse
# ---------------------------------------------------------------------------

def _fetch_zip(manif_uri: str, timeout: int = 60) -> bytes:
    """GET the manifestation URI with Accept: application/zip; follow redirects."""
    req = urllib.request.Request(manif_uri, headers={"Accept": "application/zip"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _main_fmx_entry(zf: zipfile.ZipFile) -> str | None:
    """Return the ZIP entry name for the enacting-terms body (*.000101.fmx.xml)."""
    for name in zf.namelist():
        if name.endswith(".000101.fmx.xml"):
            return name
    # Fallback: largest .fmx.xml file (body is usually the biggest).
    fmx = [n for n in zf.namelist() if n.endswith(".fmx.xml")]
    if not fmx:
        return None
    return max(fmx, key=lambda n: zf.getinfo(n).file_size)


def _parse_articles(root: ET.Element) -> list[int]:
    """Extract article numbers from ARTICLE elements with an IDENTIFIER attribute."""
    articles: list[int] = []
    # Formex 4 uses namespace-less elements in older schema versions.
    # Strip any namespace prefix for robustness.
    for elem in root.iter():
        tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        if tag == "ARTICLE":
            ident = elem.get("IDENTIFIER") or elem.get("identifier")
            if ident and re.match(r"^\d+$", ident.strip()):
                articles.append(int(ident.strip()))
    return sorted(set(articles))


def _parse_recitals(root: ET.Element) -> list[int]:
    """Extract recital numbers from CONSID/NO.P elements like '(1)'."""
    recitals: list[int] = []
    for elem in root.iter():
        tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        if tag == "CONSID":
            # Look for a child NO.P containing "(N)".
            for child in elem.iter():
                ctag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                if ctag == "NO.P" and child.text:
                    m = re.search(r"\(?(\d+)\)?", child.text.strip())
                    if m:
                        recitals.append(int(m.group(1)))
                        break
    return sorted(set(recitals))


def _parse_zip(zip_bytes: bytes) -> dict[str, Any]:
    """Parse the Formex ZIP and return raw counts dict."""
    zf = zipfile.ZipFile(BytesIO(zip_bytes))
    entry = _main_fmx_entry(zf)
    if entry is None:
        raise RuntimeError("No .fmx.xml file found in ZIP")

    xml_bytes = zf.read(entry)
    root = ET.fromstring(xml_bytes)

    articles = _parse_articles(root)
    recitals = _parse_recitals(root)

    return {
        "articles": articles,
        "recitals": recitals,
        "zip_entries": zf.namelist(),
        "main_entry": entry,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_registry(out_path: Path | None = None, *, verbose: bool = True) -> dict[str, Any]:
    """Fetch the Cellar ZIP, parse it, persist ``authoritative_registry.json``.

    Returns the registry dict.  If network is unavailable, raises an exception
    rather than returning fabricated data — callers must handle the error.
    """
    if out_path is None:
        # Default: data/ relative to the package root (two levels up from this file).
        out_path = Path(__file__).resolve().parents[3] / "data" / "authoritative_registry.json"

    if verbose:
        print(f"Querying Cellar SPARQL for CELEX {CELEX} …", flush=True)
    manif_uri = _sparql_discover()
    if manif_uri:
        if verbose:
            print(f"  Manifestation URI (SPARQL): {manif_uri}", flush=True)
    else:
        manif_uri = _FALLBACK_MANIFESTATION_URI
        if verbose:
            print(f"  SPARQL returned nothing; using fallback URI: {manif_uri}", flush=True)

    if verbose:
        print("Fetching ZIP …", flush=True)
    zip_bytes = _fetch_zip(manif_uri)
    if verbose:
        print(f"  ZIP size: {len(zip_bytes):,} bytes", flush=True)

    parsed = _parse_zip(zip_bytes)

    articles = parsed["articles"]
    recitals = parsed["recitals"]

    # Annexes: the AI Act defines Annexes I–XIII.  The Formex ZIP may contain
    # separate annex files (*.000102.fmx.xml etc.) but parsing them is fragile;
    # the hardcoded list is the authoritative ground truth from the Act itself.
    annexes = _VALID_ANNEXES[:]

    registry: dict[str, Any] = {
        "celex": CELEX,
        "source": manif_uri,
        "articles": articles,
        "recitals": recitals,
        "annexes": annexes,
        "counts": {
            "articles": len(articles),
            "recitals": len(recitals),
            "annexes": len(annexes),
        },
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(registry, ensure_ascii=False, indent=2))
    if verbose:
        print(
            f"Wrote {out_path}  "
            f"({len(articles)} articles, {len(recitals)} recitals, {len(annexes)} annexes)",
            flush=True,
        )

    return registry


def load_registry(path: Path | None = None) -> dict[str, Any] | None:
    """Load the persisted registry, or None if the file doesn't exist."""
    if path is None:
        path = Path(__file__).resolve().parents[3] / "data" / "authoritative_registry.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(
        description="Fetch EU AI Act authoritative provision registry from Cellar (Formex 4)."
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output path (default: data/authoritative_registry.json relative to repo root)",
    )
    ap.add_argument("--quiet", action="store_true", help="Suppress progress messages")
    args = ap.parse_args(argv)

    try:
        registry = fetch_registry(out_path=args.out, verbose=not args.quiet)
    except Exception as e:
        print(f"network fetch failed: {e}", file=sys.stderr)
        return 1

    counts = registry["counts"]
    print(
        f"Registry: {counts['articles']} articles, "
        f"{counts['recitals']} recitals, "
        f"{counts['annexes']} annexes"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
