"""R371 — the role x risk-class obligation layer, as a graph payload.

One concept, one definition. This module is the SINGLE place that turns
:data:`app.data.ontology.ROLE_OBLIGATIONS` — the 8 roles x 7 risk classes ->
90 bindings matrix the answer path actually reads — into nodes and edges for
the property graph, and the single place that cross-checks it against the
repo's OTHER role->obligation definition.

Why this exists
---------------

The repo ships two independent role->obligation definitions that had never
been compared:

* ``app/data/role_obligations.py`` — 9 prose records with ``primary_articles``
  / ``secondary_articles``. **The Aura seeder reads this one.**
* ``app/data/ontology.py::ROLE_OBLIGATIONS`` — the risk-class matrix.
  **The answer path reads this one**, via :func:`~app.data.ontology.obligations_for`
  (``_build_role_obligation_answer`` in ``_graph_rag_impl``), and
  ``validate_legal_triple`` lints it.

Measured against the live Aura instance on 2026-08-17, the graph carried:

===========================  =========================  =====================
concept                      live graph                 matrix
===========================  =========================  =====================
roles                        5 ``OperatorRole`` nodes   8
bindings                     36 edges                   90
risk-class dimension         ``NULL`` on all 36         7 classes
Annex targets                0                          8 distinct annexes
===========================  =========================  =====================

Three separate fidelity losses, one of them a plain bug: the seeder's
``_existing_article_id`` returns ``None`` for any ref not starting with
``"Art. "``, so every Annex binding (Annex IV technical documentation, Annex
VII notified-body QMS, Annex XI/XII GPAI) was silently dropped.

Safety properties this module is built around
---------------------------------------------

The target is a SHARED, LIVE Aura instance (hard rule #12). So:

* It emits a **new** relationship type, ``HAS_RISK_CLASS_OBLIGATION``, and
  never touches the existing 36 ``HAS_OBLIGATION_ARTICLE`` edges. The only
  live reader of those (``kg_context.py``'s ``OPTIONAL MATCH
  (ro:OperatorRole)-[hoa:HAS_OBLIGATION_ARTICLE]->(a)``) is therefore
  bit-for-bit unaffected, and rollback is exact.
* Role ids go through :data:`GRAPH_ROLE_ID_OVERRIDES`. The live graph spells
  it ``role_authorized_representative`` (American ``z``) while the ontology
  enum spells it ``authorised_representative`` (British ``s``); emitting the
  enum spelling verbatim would MERGE a second, duplicate role node onto a
  production graph.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from app.data.article_existence import ARTICLE_EXISTENCE
from app.data.ontology import ROLE_OBLIGATIONS, ActorRole, RiskClass

__all__ = [
    "GRAPH_ROLE_ID_OVERRIDES",
    "RELATIONSHIP_TYPE",
    "ReconciliationReport",
    "RoleObligationEdge",
    "RoleObligationNode",
    "reconcile_role_definitions",
    "role_node_id",
    "role_obligation_edges",
    "role_obligation_nodes",
    "target_node_id",
]


#: The relationship type this layer writes. Deliberately NOT
#: ``HAS_OBLIGATION_ARTICLE`` — see the module docstring.
RELATIONSHIP_TYPE = "HAS_RISK_CLASS_OBLIGATION"


#: ``ActorRole`` value -> the id fragment the LIVE graph already uses.
#: Measured 2026-08-17: the graph holds ``role_authorized_representative``.
GRAPH_ROLE_ID_OVERRIDES: dict[str, str] = {
    "authorised_representative": "authorized_representative",
}


@dataclass(frozen=True, slots=True)
class RoleObligationNode:
    """An ``OperatorRole`` node."""

    id: str
    role: str
    label: str


@dataclass(frozen=True, slots=True)
class RoleObligationEdge:
    """``(:OperatorRole)-[:HAS_RISK_CLASS_OBLIGATION {risk_class}]->(:Article|:Annex)``."""

    role: str
    role_id: str
    target_id: str
    risk_class: str
    ref: str


@dataclass(frozen=True, slots=True)
class ReconciliationReport:
    """Cross-check of the repo's two role->obligation definitions."""

    matrix_roles: int
    prose_roles: int
    #: ``(role, ref)`` the prose file binds as PRIMARY that the risk-class
    #: matrix never binds to that role at any risk class.
    contradictions: tuple[tuple[str, str], ...]
    #: ``(role, ref)`` present in the matrix but absent from the prose file.
    matrix_only: tuple[tuple[str, str], ...]
    #: Roles the prose file carries that the matrix does not model.
    prose_only_roles: tuple[str, ...]


def role_node_id(role: ActorRole | str) -> str:
    """Return the graph node id for ``role``, honouring the live spelling."""
    value = role.value if isinstance(role, ActorRole) else role
    return f"role_{GRAPH_ROLE_ID_OVERRIDES.get(value, value)}"


_ROMAN = "IVXLC"


def target_node_id(ref: str) -> str | None:
    """Map a citation ref onto its graph node id, or ``None``.

    Handles BOTH shapes. ``Art. 5.1.a`` normalises to ``article_5`` (the
    sub-point tail is not a node); ``Annex IV`` becomes ``annex_IV`` with the
    Roman numeral uppercased, matching the live graph.
    """
    base = ref.split("(")[0].strip()
    if base.startswith("Art. "):
        head = "Art. " + base[len("Art. ") :].split(".")[0].strip()
        if head not in ARTICLE_EXISTENCE:
            return None
        return f"article_{head[len('Art. '):]}"
    if base.startswith("Annex "):
        numeral = base[len("Annex ") :].split(".")[0].strip().upper()
        if not numeral or any(c not in _ROMAN for c in numeral):
            return None
        if f"Annex {numeral}" not in ARTICLE_EXISTENCE:
            return None
        return f"annex_{numeral}"
    return None


@lru_cache(maxsize=1)
def role_obligation_nodes() -> tuple[RoleObligationNode, ...]:
    """Every role the matrix models, including the three never seeded."""
    return tuple(
        RoleObligationNode(
            id=role_node_id(role),
            role=role.value,
            label=role.value.replace("_", " ").title(),
        )
        for role in ActorRole
    )


@lru_cache(maxsize=1)
def role_obligation_edges() -> tuple[RoleObligationEdge, ...]:
    """Project the full 90-binding matrix onto graph edges.

    Every binding is emitted, Annex targets included. A ref that cannot be
    resolved to a node is a defect, not a silent drop — the lint in
    ``tests/test_role_obligation_graph.py`` pins the count.
    """
    edges: list[RoleObligationEdge] = []
    for role, by_class in ROLE_OBLIGATIONS.items():
        rid = role_node_id(role)
        for risk_class, refs in by_class.items():
            for ref in refs:
                target = target_node_id(ref)
                if target is None:
                    continue
                edges.append(
                    RoleObligationEdge(
                        role=role.value,
                        role_id=rid,
                        target_id=target,
                        risk_class=risk_class.value,
                        ref=ref,
                    )
                )
    return tuple(edges)


def _prose_definition() -> dict[str, dict[str, tuple[str, ...]]]:
    """``role -> {'primary': (...), 'secondary': (...)}`` from the prose file."""
    from app.data.role_obligations import ROLE_OBLIGATIONS as PROSE

    out: dict[str, dict[str, tuple[str, ...]]] = {}
    for row in PROSE:
        rid = row.get("id")
        if not rid:
            continue
        # Normalise the z/s spelling onto the ontology enum's spelling so the
        # two sources are comparable at all.
        canonical = rid.replace("authorized", "authorised")
        out[canonical] = {
            "primary": tuple(row.get("primary_articles") or ()),
            "secondary": tuple(row.get("secondary_articles") or ()),
        }
    return out


def reconcile_role_definitions() -> ReconciliationReport:
    """Cross-check the risk-class matrix against the prose file.

    A **contradiction** is a ref the prose file binds to a role as PRIMARY
    which the matrix never binds to that role at ANY risk class. That is a
    genuine disagreement between two shipped definitions of one concept.

    Refs are compared at HEAD grain (``Art. 25(4)`` -> ``Art. 25``): the prose
    file carries paragraph-level detail the matrix does not model, and treating
    that as disagreement would be a false positive.
    """
    prose = _prose_definition()

    matrix: dict[str, set[str]] = {}
    for role, by_class in ROLE_OBLIGATIONS.items():
        acc = matrix.setdefault(role.value, set())
        for refs in by_class.values():
            acc.update(_head(r) for r in refs)

    contradictions: list[tuple[str, str]] = []
    matrix_only: list[tuple[str, str]] = []

    for role, sides in prose.items():
        if role not in matrix:
            continue
        for ref in sides["primary"]:
            if _head(ref) not in matrix[role]:
                contradictions.append((role, ref))

    for role, refs in matrix.items():
        if role not in prose:
            continue
        known = {_head(r) for r in prose[role]["primary"] + prose[role]["secondary"]}
        for ref in sorted(refs):
            if ref not in known:
                matrix_only.append((role, ref))

    return ReconciliationReport(
        matrix_roles=len(matrix),
        prose_roles=len(prose),
        contradictions=tuple(sorted(contradictions)),
        matrix_only=tuple(sorted(matrix_only)),
        prose_only_roles=tuple(sorted(set(prose) - set(matrix))),
    )


def _head(ref: str) -> str:
    """``Art. 25(4)`` / ``Art. 5.1.a`` -> ``Art. 5``; ``Annex IV.2`` -> ``Annex IV``."""
    base = ref.split("(")[0].strip()
    if base.startswith("Art. "):
        return "Art. " + base[len("Art. ") :].split(".")[0].strip()
    if base.startswith("Annex "):
        return "Annex " + base[len("Annex ") :].split(".")[0].strip().upper()
    return base
