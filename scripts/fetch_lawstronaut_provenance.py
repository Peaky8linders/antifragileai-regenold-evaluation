"""Live fetch of official EU AI Act legal provenance from the Lawstronaut API.

Sibling of ``scripts/fetch_official_eu_ai_act.py``. Where that script fetches
the regulatory TEXT from the EU Publications Office Cellar, this one fetches
the authoritative **legal provenance metadata** (CELEX / ELI / effective date
/ portal) plus the registry of official Commission guidance documents, from
the Lawstronaut legal corpus — and, critically, **validates the repo's pinned
article text against Lawstronaut's copy of the same official act**.

Why this exists
---------------
The R-Lawstronaut first cut hardcoded CELEX ``02024R1689-20260727`` into the
Stage-2 prompt, the ontology and all 126 Neo4j Article/Annex nodes. That CELEX
is the **post-Digital-Omnibus consolidation**: it carries 69 EUR-Lex ``M1``
amendment markers pointing at CELEX ``32026R1744`` (Regulation (EU) 2026/1744
of 8 July 2026), Article 113 deferred to 2 December 2027 / 2 August 2028, and
the new Article 3(14a)/(14b) SME / small-mid-cap definitions.

This repo's corpus is the **pre-Omnibus original**, CELEX ``32024R1689``.
Asserting a post-Omnibus provenance over pre-Omnibus text is a hard-rule-#4
false claim, so the provenance pinned here is the ORIGINAL act, and the
Omnibus amending act is recorded separately as *known but NOT incorporated*.

Design
------
Build-time only. The Lawstronaut bearer token expires in **1800 seconds**, so
a runtime dependency on it is unserviceable: any long-lived process would
spend most of its life holding an expired token. We therefore fetch, validate
and PIN — exactly the pattern ``fetch_official_eu_ai_act.py`` established —
and the request path never touches the network.

Pure stdlib only — no pip deps (matches the sibling fetcher; note the app is
httpx-only and does NOT ship ``requests``).

Credentials (build machine only, never needed at runtime)::

    LAWSTRONAUT_EMAIL=you@example.com     # or --email
    LAWSTRONAUT_PASS=...                  # required for the login flow

Outputs::

    app/data/lawstronaut_provenance.py       # generated Python module
    app/data/_lawstronaut_pin.json           # SHA pin + metadata sidecar

Run::

    py -3.12 scripts/fetch_lawstronaut_provenance.py
    py -3.12 scripts/fetch_lawstronaut_provenance.py --validate-only
    py -3.12 scripts/fetch_lawstronaut_provenance.py --force
"""
from __future__ import annotations

import argparse
import datetime as _dt
import difflib
import hashlib
import json
import os
import pathlib
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

AUTH_BASE = "https://filerskeepersapi.co"
API_BASE = "https://api.lawstronaut.com/v2"

#: The PRE-Digital-Omnibus original act as published in the OJ.
#: CELEX 32024R1689, effective 2024-08-01. This is what our corpus contains.
DOC_ID_AI_ACT_ORIGINAL = 5466154

#: The POST-Omnibus consolidation. Fetched only to detect drift; NEVER pinned
#: as our provenance while the corpus is pre-Omnibus.
DOC_ID_AI_ACT_CONSOLIDATED = 47256354

#: Regulation (EU) 2026/1744 — the Digital Omnibus amending act.
DOC_ID_OMNIBUS_AMENDING_ACT = 46775963

#: Official Commission guidance. These are NOT the Regulation: they may inform
#: grounding context but must never be emitted as a wire citation (hard rule
#: #1 — only ``Article N`` / ``Annex X``).
GUIDELINE_DOCS: tuple[dict, ...] = (
    {
        "id": "guideline_prohibited_practices",
        "doc_id": 47041422,
        "issuing_authority": "European Commission",
        "interprets": ("Art. 5",),
    },
    {
        "id": "guideline_gpai_obligations",
        "doc_id": 47037650,
        "issuing_authority": "European Commission",
        "interprets": ("Art. 51", "Art. 52", "Art. 53", "Art. 54", "Art. 55"),
    },
    {
        "id": "guideline_ai_system_definition",
        "doc_id": 47034676,
        "issuing_authority": "European Commission",
        "interprets": ("Art. 3",),
    },
    {
        "id": "guideline_serious_incidents",
        "doc_id": 47020525,
        "issuing_authority": "European Commission",
        "interprets": ("Art. 73",),
    },
)

OUT_MODULE = REPO_ROOT / "app" / "data" / "lawstronaut_provenance.py"
OUT_PIN = REPO_ROOT / "app" / "data" / "_lawstronaut_pin.json"

ROMAN = ("I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII", "XIII")

#: Markers that prove a text carries the Digital Omnibus amendments.
OMNIBUS_MARKERS = ("2 December 2027", "small mid-cap", "32026R1744")


# ─────────────────────────── auth ───────────────────────────────────────────


class LawstronautAuth:
    """Login + refresh against the filerskeepers auth service.

    The bearer token lives 1800s. This helper transparently re-logs in when it
    lapses. The token value is never printed or persisted.
    """

    def __init__(self, email: str, password: str, *, timeout: float = 45.0) -> None:
        self._email = email
        self._password = password
        self._timeout = timeout
        self._token = ""
        self._expires_at = 0.0

    def _post(self, path: str, payload: dict) -> dict:
        req = urllib.request.Request(
            AUTH_BASE + path,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self._timeout) as resp:
            return json.loads(resp.read().decode("utf-8", "replace"))

    def _store(self, token_obj: dict) -> bool:
        tok = (token_obj or {}).get("refresh_token")
        if not tok:
            return False
        self._token = tok
        # Renew a little early so an in-flight request cannot straddle expiry.
        self._expires_at = time.time() + float(token_obj.get("expires_in", 1800)) - 120.0
        return True

    def login(self) -> None:
        data = self._post("/auth/login", {"email": self._email, "password": self._password})
        if not self._store((data.get("data") or {}).get("token") or {}):
            raise SystemExit(f"Lawstronaut login failed: {data.get('message') or data}")

    def token(self) -> str:
        if self._token and time.time() < self._expires_at:
            return self._token
        if self._token:
            try:
                data = self._post("/auth/refresh-token", {"token": self._token})
                if self._store((data.get("data") or {}).get("token") or {}):
                    return self._token
            except Exception:  # noqa: BLE001 - fall through to a full login
                pass
        self.login()
        return self._token


# ─────────────────────────── API ────────────────────────────────────────────


def api_get(auth: LawstronautAuth, path: str, timeout: float = 180.0, **params) -> dict:
    """GET an API path, retrying once on a 401 with a fresh token."""
    url = API_BASE + path
    if params:
        url += "?" + urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    last = None
    for attempt in (0, 1):
        req = urllib.request.Request(
            url,
            headers={
                "authorization": f"Bearer {auth.token()}",
                "Accept": "application/json",
                "User-Agent": "regenold-eu-ai-act-rag/1.0 (build-time provenance fetch)",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as exc:
            last = exc
            if exc.code == 401 and attempt == 0:
                auth.login()
                continue
            raise SystemExit(f"Lawstronaut GET {path} -> HTTP {exc.code}") from exc
    raise SystemExit(f"Lawstronaut GET {path} failed: {last}")


def fetch_metadata(auth: LawstronautAuth, doc_id: int) -> dict:
    data = api_get(auth, "/contents", iso="EU", document_id=doc_id).get("data") or []
    if not data:
        raise SystemExit(f"Lawstronaut returned no metadata for document_id={doc_id}")
    return data[0]


def fetch_markdown(auth: LawstronautAuth, doc_id: int) -> str:
    data = api_get(auth, "/contents/markdown", iso="EU", document_id=doc_id).get("data") or []
    if not data:
        raise SystemExit(f"Lawstronaut returned no markdown for document_id={doc_id}")
    return data[0].get("content_markdown") or ""


# ─────────────────────────── text handling ──────────────────────────────────

_BS = chr(92)


def normalise(text: str) -> str:
    """Flatten Lawstronaut markdown+HTML into comparable plain prose."""
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", text, flags=re.S | re.I)
    text = re.sub(r"</(p|tr|td|div|li|h\d)>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace(_BS, "").replace(" ", " ")
    text = text.replace("’", "'").replace("‘", "'")
    text = text.replace("“", '"').replace("”", '"')
    text = text.replace("‑", "-").replace("–", "-").replace("—", "-")
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)  # md link -> label
    return re.sub(r"\s+", " ", text).strip()


def parse_provisions(markdown: str) -> dict[str, str]:
    """Split the official markdown into ``Article N`` / ``Annex X`` bodies.

    A provision body ends at the next Article/Annex heading **or** at an
    intervening ``SECTION``/``CHAPTER`` heading — without the latter, a
    structural heading bleeds into the preceding article and manufactures a
    phantom text divergence (this bit the first-cut comparison on Article 87).
    """
    lines = markdown.split("\n")
    marks: list[tuple[int, str | None]] = []
    for idx, raw in enumerate(lines):
        stripped = raw.strip()
        m = re.fullmatch(r"(?:#+\s*)?Article\s+(\d{1,3})'?", stripped)
        if m and 1 <= int(m.group(1)) <= 113:
            marks.append((idx, f"Article {int(m.group(1))}"))
            continue
        m = re.fullmatch(r"(?:#+\s*)?ANNEX\s+([IVX]+)", stripped)
        if m and m.group(1) in ROMAN:
            marks.append((idx, f"Annex {m.group(1)}"))
            continue
        if re.fullmatch(r"(?:#+\s*)?(SECTION|CHAPTER)\s+[IVX0-9]+", stripped):
            marks.append((idx, None))  # structural boundary, not a provision

    out: dict[str, str] = {}
    for i, (line_no, key) in enumerate(marks):
        if key is None:
            continue
        end = marks[i + 1][0] if i + 1 < len(marks) else len(lines)
        body = normalise("\n".join(lines[line_no + 1:end]))
        # Article 113 is followed by the OJ signature block ("Done at Brussels
        # ... For the European Parliament ..."), which is not operative text.
        body = re.split(r"\bDone at Brussels\b", body)[0].strip()
        # The table of contents yields short duplicate hits; keep the longest.
        if len(body) > len(out.get(key, "")):
            out[key] = body
    return out


def validate_against_repo(live: dict[str, str]) -> dict:
    """Diff the live official text against the repo's pinned corpus."""
    from app.data.official_eu_ai_act import OFFICIAL_ARTICLE_TEXT

    try:
        from app.data.provision_text import get_provision_text
    except Exception:  # noqa: BLE001
        get_provision_text = None  # type: ignore[assignment]

    wanted = [f"Article {n}" for n in range(1, 114)] + [f"Annex {r}" for r in ROMAN]
    ratios: list[tuple[str, float]] = []
    missing_live: list[str] = []
    missing_repo: list[str] = []

    for key in wanted:
        live_text = live.get(key, "")
        if len(live_text) < 120:
            missing_live.append(key)
        repo_text = normalise(OFFICIAL_ARTICLE_TEXT.get(key, ""))
        if not repo_text:
            missing_repo.append(key)
        if not repo_text or not live_text:
            ratios.append((key, 0.0))
            continue
        ratio = difflib.SequenceMatcher(None, repo_text.lower(), live_text.lower()).quick_ratio()
        if ratio < 0.90 and get_provision_text is not None:
            # Retry against the PATCHED text (R94 restored Art. 113 numbering).
            ref = key.replace("Article ", "Art. ")
            try:
                patched = normalise(get_provision_text(ref) or "")
            except Exception:  # noqa: BLE001
                patched = ""
            if patched:
                ratio = max(
                    ratio,
                    difflib.SequenceMatcher(None, patched.lower(), live_text.lower()).quick_ratio(),
                )
        ratios.append((key, ratio))

    values = sorted(r for _, r in ratios)
    mean = sum(values) / len(values) if values else 0.0
    median = values[len(values) // 2] if values else 0.0
    return {
        "provisions_compared": len(ratios),
        "missing_in_live": missing_live,
        "missing_in_repo": missing_repo,
        "mean_similarity": round(mean, 4),
        "median_similarity": round(median, 4),
        "below_0_90": [k for k, r in ratios if r < 0.90],
        "min_similarity": round(values[0], 4) if values else 0.0,
    }


def detect_omnibus(text: str) -> list[str]:
    flat = normalise(text)
    return [m for m in OMNIBUS_MARKERS if m.lower() in flat.lower()]


# ─────────────────────────── emit ───────────────────────────────────────────


def _py(value) -> str:
    """Emit a PYTHON literal.

    ``json.dumps`` is wrong here: it renders ``false`` / ``true`` / ``null``,
    which are NameErrors in the generated module. ``repr`` round-trips every
    scalar and container we emit (str / int / bool / None / list / dict).
    """
    return repr(value)


def render_module(payload: dict) -> str:
    lines: list[str] = []
    add = lines.append
    add("# AUTOGENERATED by scripts/fetch_lawstronaut_provenance.py - do not edit by hand")
    add('"""Official EU AI Act legal provenance, live-fetched from Lawstronaut.')
    add("")
    add("Pinned to the PRE-Digital-Omnibus original act, CELEX 32024R1689, because")
    add("that is the text this repo's corpus contains. The post-Omnibus")
    add("consolidation (02024R1689-<date>, amended by CELEX 32026R1744) is recorded")
    add("in :data:`OMNIBUS_AMENDING_ACT` as known-but-NOT-incorporated, so a future")
    add("round can adopt it deliberately rather than by accident.")
    add("")
    add("Build-time artefact: the request path never calls the Lawstronaut API")
    add("(its bearer token lives 1800s, which no long-lived process can hold).")
    add('"""')
    add("from __future__ import annotations")
    add("")
    add(f"LAWSTRONAUT_FETCH_DATE: str = {_py(payload['fetch_date'])}")
    add(f"LAWSTRONAUT_SHA256: str = {_py(payload['sha256'])}")
    add("")
    add("#: CELEX of the act our corpus actually contains (pre-Digital-Omnibus).")
    add(f"OFFICIAL_CELEX: str = {_py(payload['celex'])}")
    add(f"OFFICIAL_ELI: str = {_py(payload['eli'])}")
    add(f"OFFICIAL_LEGAL_LINK: str = {_py(payload['legal_link'])}")
    add(f"OFFICIAL_TITLE: str = {_py(payload['title'])}")
    add(f"OFFICIAL_EFFECTIVE_DATE: str = {_py(payload['effective_date'])}")
    add(f"OFFICIAL_PORTAL: str = {_py(payload['portal_name'])}")
    add(f"OFFICIAL_DOC_ID: int = {payload['doc_id']}")
    add("")
    add("#: Short provenance line for audit surfaces. Deliberately NOT injected")
    add("#: into the answer prompt: a CELEX/ELI string in the model's context is")
    add("#: prompt budget spent on a token the wire may never cite (hard rule #1")
    add("#: allows only 'Article N' / 'Annex X').")
    _line = f"{payload['title']} (CELEX {payload['celex']})"
    add(f"OFFICIAL_PROVENANCE_LINE: str = {_py(_line)}")
    add("")
    add("#: The Digital Omnibus amending act. KNOWN, deliberately NOT incorporated.")
    add("OMNIBUS_AMENDING_ACT: dict[str, object] = {")
    for key, value in payload["omnibus"].items():
        add(f"    {_py(key)}: {_py(value)},")
    add("}")
    add("")
    add("#: Official Commission guidance. NOT the Regulation - usable as grounding")
    add("#: context only; never emit one as a wire citation.")
    add("OFFICIAL_GUIDELINES: tuple[dict[str, object], ...] = (")
    for guideline in payload["guidelines"]:
        add("    {")
        for key, value in guideline.items():
            add(f"        {_py(key)}: {_py(value)},")
        add("    },")
    add(")")
    add("")
    add("#: Result of diffing the repo's pinned article text against Lawstronaut's")
    add("#: copy of the same official act, at fetch time.")
    add("CORPUS_VALIDATION: dict[str, object] = {")
    for key, value in payload["validation"].items():
        add(f"    {_py(key)}: {_py(value)},")
    add("}")
    add("")
    return "\n".join(lines)


# ─────────────────────────── main ───────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--email", default=os.environ.get("LAWSTRONAUT_EMAIL", ""))
    parser.add_argument("--validate-only", action="store_true",
                        help="fetch + validate, do not write the pinned module")
    parser.add_argument("--force", action="store_true",
                        help="rewrite the module even when the SHA pin is unchanged")
    args = parser.parse_args(argv)

    password = os.environ.get("LAWSTRONAUT_PASS", "")
    email = args.email
    if not email or not password:
        print(
            "ERROR: set LAWSTRONAUT_EMAIL and LAWSTRONAUT_PASS (build-time only).",
            file=sys.stderr,
        )
        return 2

    auth = LawstronautAuth(email, password)

    print(f"Fetching the PRE-Omnibus original (document_id={DOC_ID_AI_ACT_ORIGINAL}) ...")
    meta = fetch_metadata(auth, DOC_ID_AI_ACT_ORIGINAL)
    markdown = fetch_markdown(auth, DOC_ID_AI_ACT_ORIGINAL)
    print(f"  {meta.get('source_identifier')} | {len(markdown):,} chars")

    stray = detect_omnibus(markdown)
    if stray:
        print(f"ABORT: the 'original' document carries Omnibus markers {stray}.", file=sys.stderr)
        print("Refusing to pin post-Omnibus provenance over a pre-Omnibus corpus.", file=sys.stderr)
        return 3
    print("  pre-Omnibus check: PASS (no Omnibus markers)")

    live = parse_provisions(markdown)
    print(f"  parsed {len(live)} provisions")

    validation = validate_against_repo(live)
    print(
        f"  corpus validation: median={validation['median_similarity']} "
        f"mean={validation['mean_similarity']} "
        f"below_0.90={validation['below_0_90'] or 'none'}"
    )
    if validation["missing_in_live"]:
        print(f"  WARNING missing in live text: {validation['missing_in_live']}", file=sys.stderr)

    guidelines: list[dict] = []
    for spec in GUIDELINE_DOCS:
        try:
            gmeta = fetch_metadata(auth, int(spec["doc_id"]))
        except SystemExit as exc:
            print(f"  guideline {spec['doc_id']}: unavailable ({exc})", file=sys.stderr)
            continue
        guidelines.append(
            {
                "id": spec["id"],
                "doc_id": int(spec["doc_id"]),
                "title": (gmeta.get("title") or "").strip(),
                "issuing_authority": spec["issuing_authority"],
                "legal_link": (gmeta.get("legal_link") or "").strip(),
                "interprets": list(spec["interprets"]),
            }
        )
        print(f"  guideline {spec['doc_id']}: {guidelines[-1]['title'][:70]}")
        time.sleep(0.3)

    try:
        omni_meta = fetch_metadata(auth, DOC_ID_OMNIBUS_AMENDING_ACT)
    except SystemExit:
        omni_meta = {}
    omnibus = {
        "celex": (omni_meta.get("source_identifier") or "32026R1744"),
        "title": (omni_meta.get("title") or "Regulation (EU) 2026/1744").strip(),
        "effective_date": (omni_meta.get("effective_date") or "")[:10],
        "legal_link": (omni_meta.get("legal_link") or "").strip(),
        "incorporated_in_corpus": False,
        "note": (
            "Digital Omnibus. In the consolidated text it defers Chapter III "
            "Sections 1-3 to 2 December 2027 for Annex III high-risk systems and "
            "to 2 August 2028 for Annex I systems, and adds the Article 3(14a) "
            "SME / 3(14b) small-mid-cap definitions. Our corpus is the "
            "pre-Omnibus original: do not state these deferred dates against it."
        ),
    }

    canonical = json.dumps(
        {"provisions": live, "guidelines": guidelines, "omnibus": omnibus},
        sort_keys=True, ensure_ascii=False,
    )
    sha = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    payload = {
        "fetch_date": _dt.date.today().isoformat(),
        "sha256": sha,
        "celex": (meta.get("source_identifier") or "32024R1689").strip(),
        "eli": (meta.get("source_secondary_identifier") or "").strip(),
        "legal_link": (meta.get("legal_link") or "").strip(),
        "title": (meta.get("title") or "").strip(),
        "effective_date": (meta.get("effective_date") or "")[:10],
        "portal_name": (meta.get("portal_name") or "").strip(),
        "doc_id": DOC_ID_AI_ACT_ORIGINAL,
        "guidelines": guidelines,
        "omnibus": omnibus,
        "validation": validation,
    }

    if args.validate_only:
        print("\n--validate-only: nothing written.")
        print(json.dumps({k: v for k, v in payload.items() if k != "guidelines"}, indent=2)[:1800])
        return 0

    if OUT_PIN.exists() and not args.force:
        try:
            prior = json.loads(OUT_PIN.read_text(encoding="utf-8"))
            if prior.get("sha256") == sha and OUT_MODULE.exists():
                print("already pinned (SHA unchanged) - nothing to do")
                return 0
        except Exception:  # noqa: BLE001
            pass

    OUT_MODULE.write_text(render_module(payload), encoding="utf-8")
    OUT_PIN.write_text(
        json.dumps(
            {
                "celex": payload["celex"],
                "eli": payload["eli"],
                "doc_id": payload["doc_id"],
                "fetch_date": payload["fetch_date"],
                "sha256": sha,
                "pre_omnibus": True,
                "omnibus_amending_act": omnibus["celex"],
                "guideline_count": len(guidelines),
                "validation": validation,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"\nwrote {OUT_MODULE.relative_to(REPO_ROOT)}")
    print(f"wrote {OUT_PIN.relative_to(REPO_ROOT)}")
    print(f"CELEX pinned: {payload['celex']} (pre-Omnibus)  sha256={sha[:16]}...")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
