"""RushDB KB seeder for the Regenold EU AI Act RAG bundle.

Pushes the bundle's deterministic KB surface into RushDB.
"""
from __future__ import annotations

import argparse
import logging
import os
import re
import sys
from datetime import datetime, timezone
import json
from typing import Any

from app.data.article_existence import ARTICLE_EXISTENCE
from app.data.definitions import _DEFINITIONS
from app.data.eu_ai_act_corpus import ARTICLE_FULL_TEXT, ARTICLE_TITLE, RECITALS
from app.data.kb import EC_CHECKER_OBLIGATION_MAP, KB_VERSION
from app.data.kb_xrefs import MANUAL_XREFS, _build_xref_graph
from app.data.ontology import ANNEX_III_REGISTRY
from app.data.role_obligations import ROLE_OBLIGATIONS
from app.integrations.regenold.refs import to_user_facing as _ref_to_user_facing

from app.data.eu_ai_act_tree import _split_paragraphs_article, _split_annex_items

logger = logging.getLogger(__name__)

SEED_VERSION = "2026-05-27-rushdb-v2"

# Hybrid RAG metadata (Hybrid_RAG_Guide.md) — Article/Annex labels, not DOC.
_HYBRID_REGULATION_META: dict[str, str] = {
    "sourceType": "regulation",
    "jurisdiction": "EU",
    "framework": "EU_AI_ACT",
    "authority": "official",
    "version": "2024-06-13",
    "sourceUrl": "https://ai-act-service-desk.ec.europa.eu/",
}

_EXPECTED_ARTICLE_COUNT = 113
_EXPECTED_ANNEX_COUNT = 13
_EXPECTED_RECITAL_COUNT = 180
_EXPECTED_DEFINITION_COUNT = 68
_EXPECTED_OPERATOR_ROLE_COUNT = 5
_EXPECTED_RISK_LEVEL_COUNT = 4

# Payload bucket keys → RushDB record labels (must match app/graph/rushdb_client.py).
RUSHDB_LABEL_MAP: dict[str, str] = {
    "ARTICLE": "Article",
    "ANNEX": "Annex",
    "RECITAL": "Recital",
    "DEFINITION": "Definition",
    "OBLIGATION": "Obligation",
    "ANNEX_III_CATEGORY": "AnnexIIICategory",
    "RISK_LEVEL": "RiskLevel",
    "OPERATOR_ROLE": "OperatorRole",
    "KB_METADATA": "KB_METADATA",
}


def rushdb_label_for_bucket(bucket: str) -> str:
    return RUSHDB_LABEL_MAP.get(bucket, bucket)


def _ensure_ai_indexes(db) -> None:
    """Create semantic indexes for hybrid retrieval (fail-soft)."""
    if not hasattr(db, "ai") or not hasattr(db.ai, "indexes"):
        return
    for spec in (
        {"label": "Article", "propertyName": "content"},
        {"label": "Article", "propertyName": "text"},
        {"label": "Annex", "propertyName": "content"},
        {"label": "Annex", "propertyName": "text"},
        {"label": "Definition", "propertyName": "text"},
    ):
        try:
            db.ai.indexes.create(spec)
            logger.info(
                "RushDB AI index created label=%s property=%s",
                spec["label"],
                spec["propertyName"],
            )
        except Exception as exc:  # noqa: BLE001 — index may already exist
            logger.debug("RushDB AI index skip label=%s: %s", spec.get("label"), exc)

RISK_LEVELS: tuple[dict[str, str], ...] = (
    {
        "id": "risk_prohibited",
        "label": "prohibited",
        "description": "Art. 5 prohibited AI practices.",
    },
    {
        "id": "risk_high",
        "label": "high-risk",
        "description": "Annex I safety-component + Annex III use-case high-risk systems per Art. 6.",
    },
    {
        "id": "risk_limited",
        "label": "limited",
        "description": "Transparency-only obligations under Art. 50.",
    },
    {
        "id": "risk_minimal",
        "label": "minimal",
        "description": "Out-of-scope systems carrying voluntary code-of-conduct obligations only.",
    },
)

_ART_NUMBER_RE = re.compile(r"^Art\.\s*(\d{1,3})$")
_ANNEX_NUMBER_RE = re.compile(r"^Annex\s+([IVXLC]+)$", re.IGNORECASE)

def _slug_term(term: str) -> str:
    s = term.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s or "anon"

def _article_id(ref: str) -> str:
    m = _ART_NUMBER_RE.match(ref)
    if m:
        return f"article_{m.group(1)}"
    m = _ANNEX_NUMBER_RE.match(ref)
    if m:
        return f"annex_{m.group(1).upper()}"
    return ref.replace(" ", "_").replace(".", "")

def _article_number(ref: str) -> str:
    m = _ART_NUMBER_RE.match(ref)
    if m:
        return m.group(1)
    m = _ANNEX_NUMBER_RE.match(ref)
    if m:
        return m.group(1).upper()
    return ref

def _is_annex(ref: str) -> bool:
    return bool(_ANNEX_NUMBER_RE.match(ref))

def _short_title(ref: str) -> str:
    title = ARTICLE_TITLE.get(ref)
    if title:
        return title.replace("\xa0", " ").strip()
    body = ARTICLE_FULL_TEXT.get(ref, "")
    if body:
        first = re.split(r"(?<=[.!?])\s", body, maxsplit=1)[0]
        return first.replace("\xa0", " ").strip()[:200]
    return ref

def _classify_risk_for_article(num: str) -> str | None:
    try:
        n = int(num)
    except (TypeError, ValueError):
        return None
    if n == 5: return "risk_prohibited"
    if n == 4: return "risk_minimal"
    if n == 50: return "risk_limited"
    if 6 <= n <= 49: return "risk_high"
    return None


def _risk_tier_label(risk_id: str | None) -> str | None:
    """Map internal risk node id to Hybrid_RAG_Guide riskTier string."""
    if risk_id == "risk_prohibited":
        return "prohibited"
    if risk_id == "risk_high":
        return "high-risk"
    if risk_id == "risk_limited":
        return "limited"
    if risk_id == "risk_minimal":
        return "minimal"
    return None


def _article_summary_text(ref: str, body: str) -> str:
    """Prefer KB obligation summary; fall back to opening EUR-Lex prose."""
    entry = EC_CHECKER_OBLIGATION_MAP.get(ref) or {}
    summary = str(entry.get("summary") or "").strip()
    if summary:
        return summary[:3000]
    if body:
        first = re.split(r"(?<=[.!?])\s", body, maxsplit=1)[0]
        return first.replace("\xa0", " ").strip()[:2000]
    return ref


def validate_payload(payload: dict[str, list[dict]]) -> list[str]:
    """Return validation errors; empty list means payload is sane."""
    errors: list[str] = []

    articles = payload.get("ARTICLE", [])
    annexes = payload.get("ANNEX", [])
    recitals = payload.get("RECITAL", [])
    definitions = payload.get("DEFINITION", [])
    roles = payload.get("OPERATOR_ROLE", [])
    risks = payload.get("RISK_LEVEL", [])

    if len(articles) != _EXPECTED_ARTICLE_COUNT:
        errors.append(
            f"ARTICLE count {len(articles)} != expected {_EXPECTED_ARTICLE_COUNT}"
        )
    if len(annexes) != _EXPECTED_ANNEX_COUNT:
        errors.append(
            f"ANNEX count {len(annexes)} != expected {_EXPECTED_ANNEX_COUNT}"
        )
    if len(recitals) != _EXPECTED_RECITAL_COUNT:
        errors.append(
            f"RECITAL count {len(recitals)} != expected {_EXPECTED_RECITAL_COUNT}"
        )
    if len(definitions) != _EXPECTED_DEFINITION_COUNT:
        errors.append(
            f"DEFINITION count {len(definitions)} != expected {_EXPECTED_DEFINITION_COUNT}"
        )
    if len(roles) != _EXPECTED_OPERATOR_ROLE_COUNT:
        errors.append(
            f"OPERATOR_ROLE count {len(roles)} != expected {_EXPECTED_OPERATOR_ROLE_COUNT}"
        )
    if len(risks) != _EXPECTED_RISK_LEVEL_COUNT:
        errors.append(
            f"RISK_LEVEL count {len(risks)} != expected {_EXPECTED_RISK_LEVEL_COUNT}"
        )

    article_ids = {row["id"] for row in articles}
    annex_ids = {row["id"] for row in annexes}
    all_node_ids = article_ids | annex_ids
    all_node_ids |= {row["id"] for row in recitals}
    all_node_ids |= {row["id"] for row in definitions}
    all_node_ids |= {row["id"] for row in payload.get("OBLIGATION", [])}
    all_node_ids |= {row["id"] for row in payload.get("ANNEX_III_CATEGORY", [])}
    all_node_ids |= {row["id"] for row in roles}
    all_node_ids |= {row["id"] for row in risks}

    for row in articles + annexes:
        for target in row.get("cross_refs") or []:
            if target not in all_node_ids:
                errors.append(
                    f"dangling cross_ref {row['id']!r} -> {target!r}"
                )

    for ref in sorted(
        (r for r in ARTICLE_EXISTENCE if r.startswith("Art. ")),
        key=lambda r: int(_article_number(r)),
    ):
        art_id = _article_id(ref)
        body = ARTICLE_FULL_TEXT.get(ref, "")
        if not body.strip():
            errors.append(f"missing ARTICLE_FULL_TEXT for {ref!r}")
        matched = next((r for r in articles if r["id"] == art_id), None)
        if matched is None:
            errors.append(f"ARTICLE_EXISTENCE {ref!r} not in payload")
        elif matched.get("content") != body.replace("\xa0", " ").strip():
            if body and len(matched.get("content", "")) < len(body.strip()) - 1:
                errors.append(
                    f"truncated content for {ref!r} "
                    f"({len(matched.get('content', ''))} < {len(body.strip())})"
                )

    for ref in sorted(r for r in ARTICLE_EXISTENCE if r.startswith("Annex ")):
        art_id = _article_id(ref)
        body = ARTICLE_FULL_TEXT.get(ref, "")
        if not body.strip():
            errors.append(f"missing ARTICLE_FULL_TEXT for {ref!r}")
        matched = next((r for r in annexes if r["id"] == art_id), None)
        if matched is None:
            errors.append(f"ARTICLE_EXISTENCE {ref!r} not in payload")

    return errors


def _self_check() -> None:
    """Import-time lint: payload must cover full Act + pass validate_payload."""
    payload = build_payload()
    errors = validate_payload(payload)
    if errors:
        raise RuntimeError(
            "seed_rushdb_kb payload self-check failed: " + "; ".join(errors[:5])
        )


def build_payload() -> dict[str, list[dict]]:
    """Build the full seed payload from the in-process KB modules."""
    payload: dict[str, list[dict]] = {
        "ARTICLE": [],
        "ANNEX": [],
        "RECITAL": [],
        "DEFINITION": [],
        "OBLIGATION": [],
        "ANNEX_III_CATEGORY": [],
        "RISK_LEVEL": [],
        "OPERATOR_ROLE": [],
    }

    xref_graph = _build_xref_graph()
    
    # Recital anchors
    recital_re = re.compile(r"\bRecital\s+(\d{1,3})\b", re.IGNORECASE)
    recital_anchors: dict[int, list[str]] = {}
    for ref, entry in EC_CHECKER_OBLIGATION_MAP.items():
        if ref not in ARTICLE_EXISTENCE: continue
        summary = entry.get("summary", "")
        if not summary: continue
        for match in recital_re.finditer(summary):
            n = int(match.group(1))
            if n not in RECITALS: continue
            art_id = _article_id(ref)
            if n not in recital_anchors:
                recital_anchors[n] = []
            if art_id not in recital_anchors[n]:
                recital_anchors[n].append(art_id)

    # Articles
    for ref in sorted((r for r in ARTICLE_EXISTENCE if r.startswith("Art. ")), key=lambda r: int(_article_number(r))):
        num = _article_number(ref)
        art_id = _article_id(ref)
        
        cross_refs = list({_article_id(t) for t in xref_graph.get(ref, []) if t in ARTICLE_EXISTENCE and t != ref})
        
        body = ARTICLE_FULL_TEXT.get(ref, "")
        chunks = []
        blocks = _split_paragraphs_article(body)
        for i, (p_num, p_text) in enumerate(blocks, start=1):
            if not p_text.strip(): continue
            chunk_id = f"{art_id}_p_{p_num}" if p_num is not None else f"{art_id}_p_solo"
            chunks.append({
                "chunkId": chunk_id,
                "chunkIndex": i,
                "heading": f"Paragraph {p_num}" if p_num is not None else None,
                "text": p_text,
                "article": num,
            })
            
        risk_id = _classify_risk_for_article(num)
        risk_tier = _risk_tier_label(risk_id)
        payload["ARTICLE"].append({
            "id": art_id,
            "number": num,
            "title": _short_title(ref),
            "text": _article_summary_text(ref, body),
            "content": body.replace("\xa0", " ").strip(),
            "cross_refs": cross_refs,
            "kb_version": KB_VERSION,
            "legal_type": "Article",
            "strict_citation": _ref_to_user_facing(f"Art. {num}"),
            "article": num,
            "topic": _short_title(ref).lower(),
            "appliesTo": ["provider", "deployer"],
            "riskTier": risk_tier,
            "CHUNK": json.dumps(chunks),
            **_HYBRID_REGULATION_META,
        })

    # Annexes
    for ref in sorted(r for r in ARTICLE_EXISTENCE if r.startswith("Annex ")):
        roman = _article_number(ref)
        art_id = _article_id(ref)
        
        cross_refs = list({_article_id(t) for t in xref_graph.get(ref, []) if t in ARTICLE_EXISTENCE and t != ref})
        
        body = ARTICLE_FULL_TEXT.get(ref, "")
        chunks = []
        blocks = _split_annex_items(body)
        for i, (item_num, item_text) in enumerate(blocks, start=1):
            if not item_text.strip(): continue
            chunk_id = f"{art_id}_p_{item_num}" if item_num is not None else f"{art_id}_p_preamble"
            chunks.append({
                "chunkId": chunk_id,
                "chunkIndex": i,
                "heading": f"Item {item_num}" if item_num is not None else "Preamble",
                "text": item_text,
                "article": roman,
            })
            
        payload["ANNEX"].append({
            "id": art_id,
            "number": roman,
            "title": _short_title(ref),
            "text": _article_summary_text(ref, body),
            "content": body.replace("\xa0", " ").strip(),
            "cross_refs": cross_refs,
            "kb_version": KB_VERSION,
            "legal_type": "Annex",
            "strict_citation": _ref_to_user_facing(f"Annex {roman}"),
            "article": roman,
            "topic": _short_title(ref).lower(),
            "CHUNK": json.dumps(chunks),
            **_HYBRID_REGULATION_META,
        })

    # Recitals
    for n in sorted(RECITALS.keys()):
        text = RECITALS[n].replace("\xa0", " ").strip()
        payload["RECITAL"].append({
            "id": f"recital_{n}",
            "recital_number": str(n),
            "text": text[:3000],
            "article_anchor": recital_anchors.get(n, []),
        })

    # Definitions
    for defn in _DEFINITIONS:
        slug = _slug_term(defn.term)
        payload["DEFINITION"].append({
            "id": f"def_{slug}",
            "term": defn.term,
            "term_slug": slug,
            "text": defn.description,
            "article_number": "3",
        })

    # Obligations
    for ref, entry in EC_CHECKER_OBLIGATION_MAP.items():
        if _is_annex(ref) or ref not in ARTICLE_EXISTENCE: continue
        num = _article_number(ref)
        risk_id = _classify_risk_for_article(num)
        payload["OBLIGATION"].append({
            "id": f"obl_{num}",
            "article_ref": num,
            "text": entry.get("summary", "")[:3000],
            "mandatory": True,
            "risk_levels": [risk_id] if risk_id else [],
            "dimension": entry.get("dimension", ""),
        })

    # Annex III
    for cat_id, cat in ANNEX_III_REGISTRY.items():
        payload["ANNEX_III_CATEGORY"].append({
            "id": f"annex_iii_{cat_id}",
            "label": cat.short_name,
            "number": cat.number,
            "description": cat.description[:2000],
            "article_ref": "6",
        })

    # Risk Levels
    for row in RISK_LEVELS:
        payload["RISK_LEVEL"].append(dict(row))

    # Operator Roles
    canonical = {"provider", "deployer", "importer", "distributor", "authorized_representative"}
    for row in ROLE_OBLIGATIONS:
        if row.get("id") not in canonical: continue
        payload["OPERATOR_ROLE"].append({
            "id": f"role_{row['id']}",
            "label": row.get("label", row["id"]),
            "art_3_definition": row.get("art_3_definition", ""),
            "summary": row.get("summary", "")[:1500],
            "primary_article": "",
        })

    return payload

def _payload_stats(payload: dict[str, list[dict]]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    total_nodes = 0
    total_edges = 0
    chunk_count = 0
    for label, rows in payload.items():
        counts[label] = len(rows)
        total_nodes += len(rows)
        for row in rows:
            if "cross_refs" in row:
                total_edges += len(row["cross_refs"])
            chunks = row.get("CHUNK") or []
            chunk_count += len(chunks)
            total_nodes += len(chunks)
    return {
        "counts": counts,
        "total_nodes": total_nodes,
        "total_edges": total_edges,
        "chunk_count": chunk_count,
    }


def run_seed(dry_run: bool = False) -> dict:
    """Returns {"status": "ok"|"skip"|"dry_run", "counts": {...}}."""
    payload = build_payload()
    validation_errors = validate_payload(payload)
    if validation_errors:
        return {
            "status": "error",
            "error": "payload validation failed",
            "validation_errors": validation_errors,
        }

    stats = _payload_stats(payload)

    if dry_run:
        return {
            "status": "dry_run",
            "seed_version": SEED_VERSION,
            "kb_version": KB_VERSION,
            **stats,
        }

    try:
        import rushdb  # noqa: F401
    except ImportError:
        return {"status": "error", "error": "rushdb package not installed"}

    from app.graph.rushdb_config import create_rushdb_client, is_configured

    if not is_configured():
        return {"status": "error", "error": "RUSHDB_AUTH_TOKEN or RUSHDB_API_KEY not set"}

    try:
        db = create_rushdb_client()
        if db is None:
            return {"status": "error", "error": "RushDB client could not be created"}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}

    # Check KB_METADATA idempotency
    try:
        meta_records = db.records.find({"labels": ["KB_METADATA"], "limit": 1})
        if meta_records and hasattr(meta_records, "data") and meta_records.data:
            meta = meta_records.data[0]
            if getattr(meta, "seed_version", None) == SEED_VERSION and getattr(meta, "kb_version", None) == KB_VERSION:
                return {"status": "skip"}
    except Exception as exc:
        logger.warning(f"RushDB metadata check failed: {exc}")

    counts = dict(stats["counts"])
    total_nodes = stats["total_nodes"]
    total_edges = stats["total_edges"]

    # Push all record types via db.records.set() (upsert by id).
    for bucket, rows in payload.items():
        if not rows:
            continue
        record_label = rushdb_label_for_bucket(bucket)
        try:
            for row in rows:
                db.records.create(
                    label=record_label,
                    data=row,
                )
            logger.info("Seeded RushDB label=%s count=%d", record_label, len(rows))
        except Exception as exc:
            logger.error("RushDB error seeding label=%s: %s", record_label, exc)
            return {"status": "error", "error": str(exc)}

    try:
        _ensure_ai_indexes(db)
    except Exception as exc:  # noqa: BLE001
        logger.warning("RushDB AI index setup failed (non-fatal): %s", exc)

    # Write KB_METADATA
    try:
        db.records.create(
            label=rushdb_label_for_bucket("KB_METADATA"),
            data={
                "seed_version": SEED_VERSION,
                "kb_version": KB_VERSION,
                "seeded_at": datetime.now(timezone.utc).isoformat(),
                "total_nodes": total_nodes,
                "total_edges": total_edges,
            }
        )
    except Exception as exc:
        logger.error(f"RushDB error writing KB_METADATA: {exc}")
        return {"status": "error", "error": str(exc)}

    return {"status": "ok", "counts": counts, "total_nodes": total_nodes, "total_edges": total_edges}


_self_check()

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="seed_rushdb_kb")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO)
    
    result = run_seed(dry_run=args.dry_run)
    print("Result:", result)
    return 0 if result.get("status") in ("ok", "skip", "dry_run") else 1

if __name__ == "__main__":
    raise SystemExit(main())
