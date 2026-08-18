"""R371 — the role x risk-class obligation layer, as graph payload.

The repo carries TWO independent role->obligation definitions and they have
never been cross-checked:

* ``app/data/role_obligations.py`` — 9 prose records, ``primary_articles`` /
  ``secondary_articles``. **This is what the Aura seeder writes.**
* ``app/data/ontology.py::ROLE_OBLIGATIONS`` — 8 roles x 7 risk classes -> 74
  article/annex bindings. **This is what the answer path reads** via
  :func:`obligations_for` and what ``validate_legal_triple`` lints.

R371.6 trimmed 16 direction-inverted bindings (90 -> 74): Art. 13 off the
DEPLOYER sets (it binds the provider; the deployer mirror is Art. 26(1)),
Art. 23/24 off IMPORTER/DISTRIBUTOR x limited risk (high-risk-only duties),
Art. 56 off PROVIDER x GPAI systemic (AI Office codes of practice), Art.
53/55/89/Annex XII off DOWNSTREAM_PROVIDER (GPAI-model-provider duties +
AI Office monitoring; downstream providers hold rights, not Chapter V
duties), and Art. 85/86 off AFFECTED_PERSON (rights, not obligations — the
Art. 86 explanation duty sits on the deployer).

Measured on the live Aura instance 2026-08-17: 5 ``OperatorRole`` nodes, 36
``HAS_OBLIGATION_ARTICLE`` edges, ``risk_class`` NULL on all 36. So the graph
carries 40% of the matrix with the risk-class dimension collapsed, is missing 3
of 8 roles, and drops every Annex target (the seeder's ``_existing_article_id``
returns ``None`` for anything not starting with ``"Art. "``).

This module is the single definition of that payload. These tests pin the
invariants that make writing it to a SHARED, LIVE graph safe.
"""

from __future__ import annotations

import pytest

from app.data.ontology import ROLE_OBLIGATIONS, ActorRole, RiskClass, obligations_for
from app.data.role_obligation_graph import (
    GRAPH_ROLE_ID_OVERRIDES,
    RoleObligationEdge,
    reconcile_role_definitions,
    role_node_id,
    role_obligation_edges,
    role_obligation_nodes,
)


# ── The spelling collision ────────────────────────────────────────────────


def test_authorised_representative_maps_onto_the_existing_graph_node() -> None:
    """The live graph spells it ``authorized`` (z); the ontology spells it
    ``authorised`` (s). Emitting the ontology spelling verbatim would MERGE a
    SECOND role node alongside the existing one — a silent duplicate on a
    shared production graph."""
    assert (
        role_node_id(ActorRole.AUTHORISED_REPRESENTATIVE)
        == "role_authorized_representative"
    )
    assert GRAPH_ROLE_ID_OVERRIDES["authorised_representative"] == (
        "authorized_representative"
    )


def test_every_other_role_uses_the_plain_convention() -> None:
    for role in ActorRole:
        if role is ActorRole.AUTHORISED_REPRESENTATIVE:
            continue
        assert role_node_id(role) == f"role_{role.value}"


# ── Edge payload fidelity ─────────────────────────────────────────────────


def test_edges_cover_every_binding_in_the_matrix() -> None:
    """No binding may be dropped. The seeder drops all 8 Annex refs; this
    payload must not."""
    expected = sum(
        len(refs) for m in ROLE_OBLIGATIONS.values() for refs in m.values()
    )
    assert expected == 74, "matrix changed; update the pinned count deliberately"
    assert len(role_obligation_edges()) == expected


def test_annex_targets_survive() -> None:
    """The exact fidelity bug in the seeder: Annex refs silently vanish."""
    annex_edges = [e for e in role_obligation_edges() if e.ref.startswith("Annex")]
    assert annex_edges, "Annex bindings were dropped — the seeder's bug"
    targets = {e.target_id for e in annex_edges}
    assert targets <= {
        "annex_I", "annex_III", "annex_IV", "annex_VI",
        "annex_VII", "annex_XI", "annex_XII", "annex_XIII",
    }
    # Uppercase Roman, matching the live graph's `annex_IV` convention.
    for t in targets:
        assert t.startswith("annex_")
        assert t.split("_", 1)[1].isupper()


def test_every_edge_carries_its_risk_class() -> None:
    """The dimension the live graph collapsed to NULL."""
    for e in role_obligation_edges():
        assert e.risk_class, f"{e} has no risk_class"
        assert e.risk_class in {rc.value for rc in RiskClass}


def test_edge_targets_are_graph_id_shaped() -> None:
    for e in role_obligation_edges():
        assert e.target_id.startswith(("article_", "annex_")), e.target_id


def test_edges_agree_with_obligations_for() -> None:
    """The payload must be a faithful projection of the function the answer
    path actually calls — not a parallel re-derivation."""
    by_pair: dict[tuple[str, str], set[str]] = {}
    for e in role_obligation_edges():
        by_pair.setdefault((e.role, e.risk_class), set()).add(e.ref)
    for role in ActorRole:
        for rc in RiskClass:
            refs = set(obligations_for(role, rc))
            assert by_pair.get((role.value, rc.value), set()) == refs


def test_edges_are_unique() -> None:
    seen = {(e.role, e.target_id, e.risk_class) for e in role_obligation_edges()}
    assert len(seen) == len(role_obligation_edges())


def test_edges_are_deterministic() -> None:
    assert role_obligation_edges() == role_obligation_edges()


# ── Node payload ──────────────────────────────────────────────────────────


def test_nodes_cover_all_eight_roles() -> None:
    nodes = role_obligation_nodes()
    assert len(nodes) == 8
    assert {n.id for n in nodes} >= {
        "role_provider", "role_deployer", "role_importer", "role_distributor",
        "role_authorized_representative",
    }


def test_the_three_missing_roles_are_present() -> None:
    """affected_person / downstream_provider / notified_body exist in the
    matrix but have never been seeded."""
    ids = {n.id for n in role_obligation_nodes()}
    assert {"role_affected_person", "role_downstream_provider",
            "role_notified_body"} <= ids


def test_nodes_never_collide_with_an_existing_node_under_a_new_spelling() -> None:
    ids = [n.id for n in role_obligation_nodes()]
    assert len(ids) == len(set(ids))
    assert "role_authorised_representative" not in ids


# ── Reconciliation: one concept, one definition ───────────────────────────


def test_reconciliation_reports_both_sources() -> None:
    rep = reconcile_role_definitions()
    assert rep.matrix_roles == 8
    assert rep.prose_roles == 9


#: The divergences between the repo's two role->obligation definitions, each
#: VERIFIED against the pinned statute via ``get_provision_text`` and then
#: MEASURED for wire impact over the whole 297-row probe pool (R371.1).
#:
#: RESOLVED at R371.1 — ``("deployer", "Art. 72")``
#:     ``role_obligations.py`` listed Art. 72 among the DEPLOYER's
#:     ``primary_articles``. Art. 72(1) reads "**Providers** shall establish and
#:     document a post-market monitoring system", so the obligation-bearer is
#:     the provider; the deployer reaches it only through the Art. 26(5)
#:     cross-reference ("inform providers in accordance with Article 72").
#:     Moved to ``secondary_articles`` — the tier the provider row already uses
#:     for related-but-not-borne provisions. Measured: **0 of 297 rows changed
#:     their wire references**, and the path is live (Art. 72 reaches the wire
#:     on 6 rows), so this is a real null, not an inert instrument.
#:
#: KEPT DELIBERATELY — the two matrix "gaps" below are LEGALLY real and
#: GOLD-WRONG, which is the repo's most expensive recurring lesson.
#: ``("provider", "Art. 73")``  — Art. 73(1) "Providers ... shall report any
#:     serious incident".
#: ``("provider", "Art. 25(4)")`` — Art. 25(4) "The provider ... shall, by
#:     written agreement, specify ...".
#:
#: Both were added to the matrix and measured exactly over the 297-row probe
#: pool: the role-obligation path fires on 11 rows, 4 of which the change
#: touched, yielding **0 gold gained, 8 non-gold added — 0% precision**. That
#: is the R352 result again ("Art. 6 is 0% precise ... the graded gold cites
#: the LIST, never the rule that points at the list"): **legally correct is not
#: gold-correct**. The change was reverted. Do not re-add them to
#: ``ROLE_OBLIGATIONS`` without a gold-carrying measurement that says otherwise
#: — hard rule #8 is a veto, not a trade-off.
KNOWN_DIVERGENCES = (
    ("provider", "Art. 25(4)"),
    ("provider", "Art. 73"),
)


def test_reconciliation_finds_only_the_known_divergences() -> None:
    """A CONTRADICTION is a ref the prose file binds to a role as PRIMARY that
    the risk-class matrix never binds to that role at any risk class.

    Three are known, statute-verified, and recorded above. A FOURTH means the
    two definitions have drifted further apart and must fail the build."""
    rep = reconcile_role_definitions()
    unexpected = tuple(c for c in rep.contradictions if c not in KNOWN_DIVERGENCES)
    assert unexpected == (), (
        "NEW disagreement between the two role->obligation definitions: "
        + "; ".join(f"{r}:{ref}" for r, ref in unexpected)
    )
    healed = tuple(c for c in KNOWN_DIVERGENCES if c not in rep.contradictions)
    assert healed == (), (
        "a known divergence was fixed — remove it from KNOWN_DIVERGENCES: "
        + "; ".join(f"{r}:{ref}" for r, ref in healed)
    )


def test_known_divergences_are_statute_verified() -> None:
    """Each recorded divergence must name a provision that actually exists and
    is quotable — the repo's own standard for a claim about law."""
    from app.data.provision_text import get_provision_text

    for _role, ref in KNOWN_DIVERGENCES:
        head = ref.split("(")[0].strip()
        assert get_provision_text(head), f"{head} is not quotable"


@pytest.mark.parametrize("role", [ActorRole.PROVIDER, ActorRole.DEPLOYER])
def test_core_roles_bind_their_signature_articles(role: ActorRole) -> None:
    """Guards against a payload that is structurally valid but legally empty."""
    refs = {
        e.ref
        for e in role_obligation_edges()
        if e.role == role.value
    }
    if role is ActorRole.PROVIDER:
        # Art. 43 conformity assessment / Art. 47 EU declaration / Art. 48 CE
        # marking are provider-only duties.
        assert {"Art. 43", "Art. 47", "Art. 48"} <= refs
    else:
        assert "Art. 26" in refs


def test_provider_only_duties_never_leak_onto_other_roles() -> None:
    """The exact class of silent bug ``validate_legal_triple`` was built to
    catch, now asserted over the graph payload too."""
    provider_only = {"Art. 43", "Art. 47", "Art. 48"}
    for e in role_obligation_edges():
        if e.ref in provider_only:
            assert e.role in {"provider", "downstream_provider"}, (
                f"{e.ref} leaked onto {e.role}"
            )


def test_edge_is_frozen() -> None:
    e = role_obligation_edges()[0]
    with pytest.raises(Exception):
        e.role = "mutated"  # type: ignore[misc]
    assert isinstance(e, RoleObligationEdge)
