#!/usr/bin/env python3
"""R318 — offline tripwire for EU AI Act corpus-version drift.

WHY THIS EXISTS, AND WHY IT IS THE *ONLY* SPARQL CODE IN THIS REPO
==================================================================

R318 probed whether a SPARQL / RDF layer over EU legal data is a moat for
answer- and reference-correctness. It is NOT, and the reason is a data fact
rather than an engineering one: the EU Publications Office **Cellar** RDF for
CELEX 32024R1689 is **document-level only**. Enumerating the complete predicate
set on the AI Act work returns 55 predicates / ~150 triples, every one
bibliographic — CELEX id, ELI string, OJ section/number/year, dates, in-force
flag, 7 EuroVoc subject tags, 64 document-to-document citations, 9
document-to-document amendments. There is no ``has_part``, no article resource,
no provision, no text.

Four independent falsification probes, each of which *could* have overturned
that and did not:

1. A ``VALUES``-based indexed lookup of five candidate ELI URIs — ``/oj``,
   ``/art_26``, ``/oj/art_26``, ``/article/26``, ``/1689`` — returned an EMPTY
   result set. Zero triples for ANY of them, the document-level ``/oj``
   included.
2. ``cdm:resource_legal_eli`` is an ``xsd:anyURI`` **literal**, not a node — the
   ELI is a string printed into the graph, not a thing in it.
3. The manifestation types served for the ENG expression are ``pdfa2a``,
   ``fmx4``, ``xhtml``. There is **no** ``akn`` — so Akoma Ntoso eIds, the only
   standard giving composable sub-point identifiers, are not published for this
   act.
4. ``work_cites_work`` targets are all ``cellar/<uuid>`` document URIs, and the
   deadline / entry-into-force values are bare date literals with no article
   attribution.

So SPARQL cannot answer "what does Article 26 require" — not slowly, not
partially, not at all; it has no representation in which the question can be
posed. Everything Cellar *does* know, this repo already holds offline and at
finer grain (``official_eu_ai_act`` 126 verbatim articles/annexes + 180
recitals, ``provision_text`` sub-point resolution, ``eu_ai_act_tree`` 1,412
structural nodes, ``kb_xrefs`` article-to-article edges). The repo's own
side project already ran this experiment: ``euairagtest/cellar.py`` uses SPARQL
for exactly one thing — resolving CELEX to a manifestation URI so it knows which
Formex ZIP to download — and hardcodes that URI as a verified fallback constant.

EXACTLY ONE QUESTION SURVIVED
-----------------------------

There is one thing Cellar knows that this repo cannot derive offline, precisely
because it is *about* the corpus rather than *in* it: **has the legal instrument
we pinned been amended or re-manifested since we pinned it?**

That question is authoritative, genuinely dynamic, and cheap. This script asks
it, and nothing else.

WHY IT IS WORTH ~200 LINES
--------------------------

This repository has already shipped corpus-version drift twice, both at
hard-rule-#4 severity:

* **R316** stamped the POST-Digital-Omnibus CELEX ``02024R1689-20260727`` onto
  every Stage-2 prompt, the ontology defaults, and all 126 Article/Annex nodes
  in the LIVE production graph — over a corpus that is the PRE-Omnibus original.
  The two differ by 69 EUR-Lex amendment markers and by the Article 113
  applicability dates.
* **R70**'s fetcher went silently dead behind the EUR-Lex anti-bot WAF and
  "treated the empty body as success and pinned nothing".

Both were caught late, by hand. This is the automated tripwire for that class.
Note it also sees drift the WAF-blocked HTML/PDF path structurally cannot:
Cellar is not behind the WAF (R70's own finding).

CONTRACT
--------

* **Never on the request path.** This is a script with zero importers under
  ``app/``. It cannot execute during a request, so it cannot move any rubric
  axis. Per hard rule #6 it needs no A/B — claiming one would be measuring a
  thing against itself.
* **Hard rule #1 is untouched.** No CELEX, ELI or Cellar URI ever reaches the
  wire. This writes to a developer's terminal.
* **Fail LOUD, inverting the R70 bug.** Any HTTP error, timeout, or EMPTY body
  is an explicit ``COULD NOT VERIFY`` failure, never a silent pass. The probes
  behind this script hit one 120 s timeout and one curl exit-28, so this path
  *will* fail intermittently and must say so.

USAGE
-----

    py -3.12 scripts/check_legal_version_drift.py            # human output
    py -3.12 scripts/check_legal_version_drift.py --json     # machine output

Exit codes:
    0  every pinned value still agrees with Cellar
    1  DRIFT — a pinned value no longer matches (act your way through the diff)
    2  COULD NOT VERIFY — network/endpoint failure; the pins are NOT confirmed
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from app.data.lawstronaut_provenance import (  # noqa: E402
    OFFICIAL_CELEX,
    OMNIBUS_AMENDING_ACT,
)

#: The EU Publications Office Cellar SPARQL endpoint. Verified live: HTTP 200,
#: median ~0.30 s over 5 consecutive runs. ``op.europa.eu/webapi/rdf/sparql`` is
#: NOT a second endpoint — it 302-redirects here.
CELLAR_SPARQL = "https://publications.europa.eu/webapi/rdf/sparql"

#: Cellar is a shared public service. Be a polite client and bound the wait —
#: an unbounded query against this endpoint timed out at 120 s during R318.
TIMEOUT_S = 45

_UA = "regenold-eu-ai-act-rag legal-version-drift-check (build-time, read-only)"

# ── Queries ──────────────────────────────────────────────────────────────────
#
# Both are INDEXED lookups keyed on the CELEX id, not scans. An unbounded
# FILTER/STRSTARTS scan over this store times out and proves nothing.

Q_AMENDERS = """
PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
SELECT DISTINCT ?amCelex WHERE {
  ?am cdm:resource_legal_amends_resource_legal ?base .
  ?base cdm:resource_legal_id_celex "%s"^^<http://www.w3.org/2001/XMLSchema#string> .
  ?am cdm:resource_legal_id_celex ?amCelex .
}
"""

Q_ELI = """
PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
SELECT DISTINCT ?eli WHERE {
  ?work cdm:resource_legal_id_celex "%s"^^<http://www.w3.org/2001/XMLSchema#string> ;
        cdm:resource_legal_eli ?eli .
}
"""

# NOTE THE EDGE DIRECTION. This is an INCOMING edge (?cons -> ?base), and it is
# the single most useful query in this file. An adversarial re-check of the R318
# SPARQL analysis found that the original probe enumerated only OUTGOING
# predicates (?work ?p ?o) and therefore MISSED consolidation entirely — an
# incoming-edge probe returns 363 triples across 19 predicates. Following this
# one surfaces a document the repo does not hold: the POST-Digital-Omnibus
# consolidated act. Verified independently: 10 consolidations, including
# ``02024R1689-20240712`` and ``02024R1689-20260727``.
#
# That is the honest correction to "SPARQL gives us nothing": it gives no
# ARTICLE TEXT (that finding stands — the RDF is document-level), but it IS a
# genuine DISCOVERY layer for consolidated versions of the pinned act.
Q_CONSOLIDATIONS = """
PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
SELECT DISTINCT ?consCelex WHERE {
  ?cons cdm:act_consolidated_consolidates_resource_legal ?base .
  ?base cdm:resource_legal_id_celex "%s"^^<http://www.w3.org/2001/XMLSchema#string> .
  ?cons cdm:resource_legal_id_celex ?consCelex .
}
"""

#: Consolidations of CELEX 32024R1689 known and deliberately accounted for as of
#: R318. Both are KNOWN-AND-NOT-INCORPORATED by design: R316 pinned the corpus to
#: the PRE-Omnibus original on purpose, and ``OMNIBUS_AMENDING_ACT`` records that
#: with ``incorporated_in_corpus=False``. So their presence is NOT drift — a
#: canary that screams about a deliberate decision gets muted and stops working.
#: A consolidation NOT in this set is the thing worth waking someone for.
KNOWN_CONSOLIDATIONS: frozenset[str] = frozenset(
    {
        "02024R1689-20240712",  # original OJ consolidation
        "02024R1689-20260727",  # post-Digital-Omnibus (CELEX 32026R1744)
    }
)


class VerificationError(RuntimeError):
    """The endpoint could not be consulted. NOT the same as 'no drift'."""


def _sparql(query: str) -> list[dict]:
    """Run one SPARQL SELECT. Raises :class:`VerificationError` on ANY doubt.

    An empty body, a non-200, a transport error and a malformed payload are all
    failures — never a silent pass. That inversion is the entire point: R70
    treated an empty body as success and pinned nothing.
    """
    url = CELLAR_SPARQL + "?" + urllib.parse.urlencode(
        {"query": query, "format": "application/sparql-results+json"}
    )
    req = urllib.request.Request(
        url,
        headers={"Accept": "application/sparql-results+json", "User-Agent": _UA},
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:  # noqa: S310
            if resp.status != 200:
                raise VerificationError(f"HTTP {resp.status} from Cellar")
            raw = resp.read()
    except VerificationError:
        raise
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        raise VerificationError(f"transport failure talking to Cellar: {exc}") from exc

    if not raw or not raw.strip():
        raise VerificationError(
            "EMPTY body from Cellar — treated as FAILURE, not as 'no results' "
            "(this is the exact R70 bug, inverted)"
        )
    try:
        payload = json.loads(raw.decode("utf-8"))
        return list(payload["results"]["bindings"])
    except (ValueError, KeyError, UnicodeDecodeError) as exc:
        raise VerificationError(f"malformed SPARQL JSON from Cellar: {exc}") from exc


def _values(rows: list[dict], var: str) -> set[str]:
    return {r[var]["value"] for r in rows if var in r}


def run_checks() -> tuple[list[dict], list[str]]:
    """Return ``(checks, hard_errors)``.

    ``checks`` entries carry ``name`` / ``status`` (``ok`` | ``DRIFT``) /
    ``pinned`` / ``live`` / ``detail``. ``hard_errors`` is non-empty only when
    the endpoint could not be consulted at all.
    """
    checks: list[dict] = []
    errors: list[str] = []

    # 1. AMENDERS — the canary that can actually change. A NEW amending act
    #    appearing here means the pinned corpus may no longer be the operative
    #    law, which is precisely the R316 failure.
    pinned_amenders = {str(OMNIBUS_AMENDING_ACT["celex"])}
    try:
        live_amenders = _values(_sparql(Q_AMENDERS % OFFICIAL_CELEX), "amCelex")
        if not live_amenders:
            errors.append(
                "amenders query returned ZERO rows — Cellar previously returned "
                "exactly one. Treated as COULD-NOT-VERIFY rather than 'the "
                "Omnibus was withdrawn'."
            )
        else:
            drifted = live_amenders != pinned_amenders
            checks.append(
                {
                    "name": "amending_acts",
                    "status": "DRIFT" if drifted else "ok",
                    "pinned": sorted(pinned_amenders),
                    "live": sorted(live_amenders),
                    "detail": (
                        "NEW amending act(s) not in OMNIBUS_AMENDING_ACT: "
                        f"{sorted(live_amenders - pinned_amenders)}. The pinned "
                        "corpus may no longer be the operative law — re-run "
                        "scripts/fetch_lawstronaut_provenance.py and re-read "
                        "Article 113 before asserting any applicability date."
                        if drifted
                        else "the only amender is the pinned Digital Omnibus"
                    ),
                }
            )
    except VerificationError as exc:
        errors.append(f"amenders check: {exc}")

    # 2. ELI — cheap identity confirmation that we are still asking about the
    #    same instrument. (It is a LITERAL in this store, not a node — which is
    #    itself part of why SPARQL is not a retrieval source here.)
    try:
        live_eli = _values(_sparql(Q_ELI % OFFICIAL_CELEX), "eli")
        if not live_eli:
            errors.append("ELI query returned ZERO rows — could not verify identity")
        else:
            # Cellar publishes several ELI spellings; agreement on the /oj form
            # is what matters.
            expect = f"/eli/reg/2024/1689"
            ok = any(expect in v for v in live_eli)
            checks.append(
                {
                    "name": "eli_identity",
                    "status": "ok" if ok else "DRIFT",
                    "pinned": [expect],
                    "live": sorted(live_eli),
                    "detail": (
                        "live ELI does not contain the pinned path — the CELEX "
                        "may now resolve to a different instrument"
                        if not ok
                        else "instrument identity confirmed"
                    ),
                }
            )
    except VerificationError as exc:
        errors.append(f"ELI check: {exc}")

    # 3. CONSOLIDATIONS — the highest-value check in this script. A consolidated
    #    version we have not accounted for means an amendment has been folded
    #    into the operative text while our corpus is still the original, which is
    #    exactly the R316 failure. Unlike the amenders query, this one has a
    #    machine-readable follow-through: each consolidation carries an fmx4
    #    (Formex XML) manifestation that downloads cleanly, so a NEW row here is
    #    directly actionable rather than merely informational.
    try:
        live_cons = _values(
            _sparql(Q_CONSOLIDATIONS % OFFICIAL_CELEX), "consCelex"
        )
        if not live_cons:
            errors.append(
                "consolidations query returned ZERO rows — Cellar previously "
                "returned 10. Treated as COULD-NOT-VERIFY."
            )
        else:
            # Only consolidations OF THIS ACT matter; the query also returns the
            # sibling regulations the AI Act amends.
            mine = {c for c in live_cons if c.startswith("02024R1689")}
            unknown = mine - KNOWN_CONSOLIDATIONS
            checks.append(
                {
                    "name": "consolidated_versions",
                    "status": "DRIFT" if unknown else "ok",
                    "pinned": sorted(KNOWN_CONSOLIDATIONS),
                    "live": sorted(mine),
                    "detail": (
                        f"UNACCOUNTED consolidation(s): {sorted(unknown)}. A new "
                        "consolidated text exists that this repo has not "
                        "reviewed. Each carries an fmx4 manifestation — fetch it "
                        "and diff the article inventory before asserting any "
                        "applicability date or article existence."
                        if unknown
                        else "every consolidation is known and deliberately "
                        "not incorporated (R316 pins the pre-Omnibus original)"
                    ),
                }
            )
    except VerificationError as exc:
        errors.append(f"consolidations check: {exc}")

    return checks, errors


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()

    checks, errors = run_checks()
    drifted = [c for c in checks if c["status"] == "DRIFT"]

    if args.json:
        print(json.dumps({"checks": checks, "errors": errors}, indent=2))
    else:
        print(f"Legal-version drift check — pinned CELEX {OFFICIAL_CELEX}")
        print(f"  endpoint: {CELLAR_SPARQL}\n")
        for c in checks:
            mark = "OK  " if c["status"] == "ok" else "DRIFT"
            print(f"  [{mark}] {c['name']}")
            print(f"          pinned: {c['pinned']}")
            print(f"          live:   {c['live']}")
            print(f"          {c['detail']}")
        for e in errors:
            print(f"  [FAIL ] COULD NOT VERIFY — {e}")
        print()

    if errors:
        print(
            "RESULT: COULD NOT VERIFY. The pins are NOT confirmed. This is a "
            "network/endpoint failure, not a clean run — re-run before trusting "
            "the corpus version.",
            file=sys.stderr,
        )
        return 2
    if drifted:
        print(
            f"RESULT: DRIFT DETECTED in {len(drifted)} check(s). The pinned legal "
            "version no longer matches Cellar.",
            file=sys.stderr,
        )
        return 1
    print("RESULT: no drift. Every pinned value still agrees with Cellar.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
