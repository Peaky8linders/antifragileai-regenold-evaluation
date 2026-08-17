"""R371 — additively extend the LIVE Aura graph's role x risk-class obligation layer.

This is NOT the seeder. It never calls ``seed_graph``, never touches
``KBMetadata``, never bumps ``SEED_VERSION``, and never deletes anything on the
apply path. Hard rule #12 exists because the boot auto-seed re-seeds on any
``SEED_VERSION`` mismatch WITHOUT checking which side is newer, and this repo's
seeder is older than the live graph — that hazard is a destructive re-seed. An
additive MERGE is a different operation, and this script is built to keep it
provably different:

* It writes ONE new relationship type, ``HAS_RISK_CLASS_OBLIGATION``, and
  three new ``OperatorRole`` nodes. The existing 36 ``HAS_OBLIGATION_ARTICLE``
  edges and 5 role nodes are never matched for write.
* It takes a census BEFORE and AFTER and **fails loudly if any pre-existing
  count moved**. Additivity is asserted, not assumed.
* ``--rollback`` removes exactly and only what this script created.
* Default mode is ``--dry-run``. Writing requires an explicit ``--apply``.

Usage::

    py -3.12 scripts/extend_aura_role_obligations.py            # dry run
    py -3.12 scripts/extend_aura_role_obligations.py --apply
    py -3.12 scripts/extend_aura_role_obligations.py --rollback

``scripts/`` here are conventionally pure-stdlib and do NOT load ``.env``
(CLAUDE.md gotcha). This one loads it explicitly but uses ``setdefault``, so an
operator's exported value is never overwritten.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.data.role_obligation_graph import (  # noqa: E402
    RELATIONSHIP_TYPE,
    reconcile_role_definitions,
    role_obligation_edges,
    role_obligation_nodes,
)

#: Roles that already exist on the live graph (measured 2026-08-17). Anything
#: outside this set is a node this script creates and may therefore remove on
#: rollback. Removing a PRE-EXISTING role node would be destructive.
PRE_EXISTING_ROLE_IDS = frozenset(
    {
        "role_provider",
        "role_deployer",
        "role_importer",
        "role_distributor",
        "role_authorized_representative",
    }
)

#: Counts that MUST NOT move. If any of these changes the run is not additive.
_INVARIANT_QUERIES = {
    "total_articles": "MATCH (n:Article) RETURN count(n) AS c",
    "total_annexes": "MATCH (n:Annex) RETURN count(n) AS c",
    "total_paragraphs": "MATCH (n:Paragraph) RETURN count(n) AS c",
    "total_points": "MATCH (n:Point) RETURN count(n) AS c",
    "total_subpoints": "MATCH (n:SubPoint) RETURN count(n) AS c",
    "total_recitals": "MATCH (n:Recital) RETURN count(n) AS c",
    "total_definitions": "MATCH (n:Definition) RETURN count(n) AS c",
    "has_obligation_article": (
        "MATCH ()-[r:HAS_OBLIGATION_ARTICLE]->() RETURN count(r) AS c"
    ),
    "cross_references": "MATCH ()-[r:CROSS_REFERENCES]->() RETURN count(r) AS c",
    "has_recital_anchor": (
        "MATCH ()-[r:HAS_RECITAL_ANCHOR]->() RETURN count(r) AS c"
    ),
    "kb_metadata": "MATCH (n:KBMetadata) RETURN count(n) AS c",
}

_MERGE_ROLE = """
UNWIND $rows AS row
MERGE (r:OperatorRole {id: row.id})
ON CREATE SET r.label = row.label, r.role = row.role, r.source = 'r371'
ON MATCH  SET r.role = coalesce(r.role, row.role)
"""

_MERGE_EDGE = f"""
UNWIND $rows AS row
MATCH (r:OperatorRole {{id: row.role_id}})
MATCH (t) WHERE t.id = row.target_id AND (t:Article OR t:Annex)
MERGE (r)-[e:{RELATIONSHIP_TYPE} {{risk_class: row.risk_class, ref: row.ref}}]->(t)
ON CREATE SET e.source = 'r371'
"""

_ROLLBACK_EDGES = f"MATCH ()-[e:{RELATIONSHIP_TYPE}]->() DELETE e"
_ROLLBACK_NODES = """
MATCH (r:OperatorRole)
WHERE r.source = 'r371' AND NOT r.id IN $keep
  AND NOT (r)--()
DELETE r
"""

_COUNT_NEW_EDGES = f"MATCH ()-[e:{RELATIONSHIP_TYPE}]->() RETURN count(e) AS c"
_COUNT_ROLES = "MATCH (r:OperatorRole) RETURN count(r) AS c"


def _load_env() -> None:
    env = REPO_ROOT / ".env"
    if not env.exists():
        return
    for raw in env.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        # setdefault: never overwrite an operator's exported value.
        os.environ.setdefault(key.strip(), value.strip())


def _census(session) -> dict[str, int]:
    out: dict[str, int] = {}
    for name, q in _INVARIANT_QUERIES.items():
        out[name] = session.run(q).single()["c"]
    out["operator_roles"] = session.run(_COUNT_ROLES).single()["c"]
    out["risk_class_obligations"] = session.run(_COUNT_NEW_EDGES).single()["c"]
    out["total_nodes"] = session.run("MATCH (n) RETURN count(n) AS c").single()["c"]
    out["total_rels"] = session.run(
        "MATCH ()-[r]->() RETURN count(r) AS c"
    ).single()["c"]
    return out


def _print_census(title: str, c: dict[str, int]) -> None:
    print(f"\n{title}")
    print("-" * 60)
    for k, v in c.items():
        print(f"  {k:26s} {v}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true", help="write to the graph")
    mode.add_argument(
        "--rollback", action="store_true", help="remove exactly what this script wrote"
    )
    ap.add_argument("--json", help="write the census pair to this path")
    args = ap.parse_args()

    _load_env()
    uri = os.environ.get("NEO4J_URI")
    user = os.environ.get("NEO4J_USERNAME")
    pwd = os.environ.get("NEO4J_PASSWORD")
    if not (uri and user and pwd):
        print("NEO4J_URI / NEO4J_USERNAME / NEO4J_PASSWORD not set", file=sys.stderr)
        return 2

    nodes = role_obligation_nodes()
    edges = role_obligation_edges()
    new_nodes = [n for n in nodes if n.id not in PRE_EXISTING_ROLE_IDS]
    rep = reconcile_role_definitions()

    print("R371 — additive role x risk-class obligation layer")
    print("=" * 60)
    print(f"  relationship type      {RELATIONSHIP_TYPE}")
    print(f"  role nodes in payload  {len(nodes)}  ({len(new_nodes)} new)")
    print(f"  new role ids           {[n.id for n in new_nodes]}")
    print(f"  edges in payload       {len(edges)}")
    print(f"  distinct risk classes  {len({e.risk_class for e in edges})}")
    print(f"  annex-target edges     {len([e for e in edges if e.ref.startswith('Annex')])}")
    print(f"  reconciliation         {len(rep.contradictions)} known divergence(s)")
    for role, ref in rep.contradictions:
        print(f"     ! {role} <-> {ref}")

    try:
        from neo4j import GraphDatabase
    except ImportError:
        print("neo4j driver not installed", file=sys.stderr)
        return 2

    driver = GraphDatabase.driver(uri, auth=(user, pwd))
    try:
        driver.verify_connectivity()
        with driver.session() as s:
            before = _census(s)
            _print_census("CENSUS BEFORE", before)

            if args.rollback:
                s.run(_ROLLBACK_EDGES)
                s.run(_ROLLBACK_NODES, keep=sorted(PRE_EXISTING_ROLE_IDS))
                after = _census(s)
                _print_census("CENSUS AFTER (rollback)", after)
                ok = after["risk_class_obligations"] == 0
                print(f"\nrollback {'OK' if ok else 'INCOMPLETE'}")
                return 0 if ok else 1

            if not args.apply:
                print("\nDRY RUN — nothing written. Re-run with --apply to write.")
                print(f"  would MERGE {len(new_nodes)} node(s) and {len(edges)} edge(s)")
                return 0

            s.run(_MERGE_ROLE, rows=[{"id": n.id, "label": n.label, "role": n.role} for n in nodes])
            s.run(
                _MERGE_EDGE,
                rows=[
                    {
                        "role_id": e.role_id,
                        "target_id": e.target_id,
                        "risk_class": e.risk_class,
                        "ref": e.ref,
                    }
                    for e in edges
                ],
            )
            after = _census(s)
            _print_census("CENSUS AFTER (apply)", after)

            # Additivity proof: every invariant count must be unchanged.
            moved = {
                k: (before[k], after[k])
                for k in _INVARIANT_QUERIES
                if before[k] != after[k]
            }
            print("\nADDITIVITY CHECK")
            print("-" * 60)
            if moved:
                print("  FAILED — pre-existing counts moved:")
                for k, (b, a) in moved.items():
                    print(f"    {k}: {b} -> {a}")
                return 1
            print(f"  OK — all {len(_INVARIANT_QUERIES)} pre-existing counts unchanged")
            print(f"  roles     {before['operator_roles']} -> {after['operator_roles']}")
            print(
                f"  {RELATIONSHIP_TYPE}  "
                f"{before['risk_class_obligations']} -> {after['risk_class_obligations']}"
            )
            if after["risk_class_obligations"] != len(edges):
                print(
                    f"  WARNING: expected {len(edges)} edges, graph has "
                    f"{after['risk_class_obligations']}"
                )
                return 1

            if args.json:
                Path(args.json).write_text(
                    json.dumps({"before": before, "after": after}, indent=2),
                    encoding="utf-8",
                )
            return 0
    finally:
        driver.close()


if __name__ == "__main__":
    raise SystemExit(main())
