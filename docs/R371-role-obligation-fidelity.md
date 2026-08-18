# R371 — the role × risk-class obligation layer, and what the AIRO/DPV proposal is actually worth

Round question: *"Adopt the industry-standard off-the-shelf ontology stack —
AIRO + DPV-EU-AIAct — for deterministic classification, role→obligation
mapping, and Cypher-verified generation."*

Answer: **most of it is already built here, the headline claims are factually
false about what those ontologies contain, and the parts that are neither were
already measured and refuted in this repo.** One genuine gap survived, it is in
the graph rather than the code, and this round closes it.

---

## 1. The proposal, claim by claim

### 1.1 Factually false about the outside world

Each fetched directly, then independently re-fetched by a second agent.

| Claim | Measured |
| --- | --- |
| "AIRO defines exact OWL 2 classes for `AISystem`, `HighRiskAISystem`, `ProhibitedPractice`, `RiskControl`" | **2 of the 4 do not exist.** AIRO defines `AISystem` and `RiskControl`. There is no `HighRiskAISystem` and no `ProhibitedPractice` class. |
| "a knowledge graph query traverses Annex III taxonomy deterministically" | **AIRO contains no Annex III enumeration.** High-risk status is modelled as combinations of *five competency questions*, not a taxonomy of individuals. |
| "DPV-EU-AIAct … linking each [role] to mandatory compliance artifacts" | **DPV-EU-AIAct defines exactly three properties**: `hasChangeCategory`, `hasChangeDescription`, `hasRiskLevel`. Roles and obligation concepts exist as *separate, unconnected* taxonomies. The spec states it "does not define the requirements for compliance itself". |
| "Coverage: Articles 3–55" | Articles **3–27**, "with varying depth". Articles 28–55 are explicitly marked *not in scope*. |
| "directly importable into Neo4j via neosemantics" | **neosemantics is not available on Neo4j Aura** — which is this repo's graph. |
| ELI / Akoma Ntoso "recitals-to-article linkage" | Cellar's RDF for CELEX `32024R1689` is document-level only: 55 predicates, no article resources, ELI is a literal not a node. Already recorded as a dead idea here. |
| "Hudock AI Ontology" | **No such ontology exists.** Zero findable hits under that name. |

Licensing the proposal did not mention: AIRO and VAIR are **CC-BY 4.0**
(attribution to Golpayegani / Pandit / Lewis, ADAPT Centre); DPV-EU-AIAct is
under the **W3C Community Final Specification Agreement**.

### 1.2 Already built here — and richer than the ontology it is compared to

This is the load-bearing finding. On the two axes the proposal names as its
wins, the in-repo hand-authored ontology is **strictly more expressive** than
the off-the-shelf stack:

| Concept | This repo | AIRO / DPV-EU-AIAct |
| --- | --- | --- |
| Role → obligation | `ontology.py::ROLE_OBLIGATIONS` — 8 roles × 7 risk classes → **90 article/annex bindings**, plus `obligations_for()` and `validate_legal_triple()` | **zero** role→obligation edges |
| Annex III use cases | `ANNEX_III_REGISTRY` ×8, and 8 live `AnnexIIICategory` nodes in Aura | not enumerated |
| Prohibited practices | `PRACTICE_REGISTRY` ×8 | no `ProhibitedPractice` class |

C4a (entity linking) is `_deterministic_parse`. C4b (context fusion) is
`app/engines/kg_context.py`. Both shipped.

A **prior version of this same proposal** already ran here:
`docs/ontology/AIRO_EU_AI_ACT_ONTOLOGY_DEEPDIVE.md`, implemented as `938933a`.
Its outcome is on the record — the six registries shipped default-ON with no
`dynamic_ab` verdict and 9/110 measured context regressions, and the
`trustgraph-integration/ontology/*.ttl` files plus
`app/data/ontology_mapping_full.py` are **orphaned: zero importers anywhere**.

### 1.3 Already measured and refuted here

* **C1** — the broad risk-classification triad on "is X high-risk?": R352,
  exact over all 297 probe rows, **12% precision, `Art. 6` at 0%** (0 gold
  gained, 61 non-gold added). Gold cites the *list*, never the rule that points
  at the list.
* **C4b on the wire** — KG neighbours as citations: **1.2% precision** (18 gold
  of 1,502 proposed; `Art. 98`, comitology, proposed 50 times), and two hard
  rule #8 vetoes (`gold_dropped_head` 25→27, then 46→49).

### 1.4 What survived

**C4c** (graph-based verification of generated output) has no existing analogue
— an adversarial verifier specifically **refuted** the claim that it is covered
by `REGENOLD_COMPLETENESS_VERIFIER` / `REF_PARTITION` / `FINAL_REF_CLAMP`,
which are prompt-level and lexical, not graph verification. It is *unmeasured*,
not dead. Hard rule #10's literal scope ("never a ranker, never a wire
citation") does not forbid it. **Not built this round** — it is a genuine
candidate needing its own gate.

---

## 2. The one genuine gap: the graph never carried the matrix

### 2.1 Two definitions of one concept, never cross-checked

| definition | shape | consumer |
| --- | --- | --- |
| `app/data/role_obligations.py` | list of **9** prose records (`primary_articles` / `secondary_articles`) | **the Aura seeder** |
| `app/data/ontology.py::ROLE_OBLIGATIONS` | dict, **8 roles × 7 risk classes → 90 bindings** | **the answer path** (`obligations_for` → `_build_role_obligation_answer`), and `validate_legal_triple` |

### 2.2 Measured on the live Aura instance, 2026-08-17

The graph carried **40% of the matrix**, with three separate losses:

| concept | live graph | matrix |
| --- | --- | --- |
| roles | 5 `OperatorRole` nodes | 8 |
| bindings | 36 `HAS_OBLIGATION_ARTICLE` edges | 90 |
| risk-class dimension | **`NULL` on all 36** | 7 classes |
| Annex targets | **0** | 8 distinct annexes |

The Annex loss is a plain bug: the seeder's `_existing_article_id` returns
`None` for any ref not starting with `"Art. "`, so Annex IV (technical
documentation), Annex VII (notified-body QMS) and Annex XI/XII (GPAI) were
silently dropped. The 3 missing roles are `downstream_provider`,
`notified_body`, `affected_person`.

⚠ **CLAUDE.md is wrong about this graph.** It records "1758 nodes / 1979 edges
across 18 labels … this repo has never written to it". Measured: **1786 / 2076
/ 24 labels**, the delta being exactly the six AIRO families from `938933a`
(+28 nodes), `seeded_at 2026-08-14`. The annex/SubPoint layer survived, so no
downgrade occurred — but the "never written" claim is false.

### 2.3 What shipped

`app/data/role_obligation_graph.py` — **one** definition of the graph payload,
projected from the matrix the answer path actually reads.

`scripts/extend_aura_role_obligations.py` — additive extension of the **live**
Aura instance. Hard rule #12 exists because the boot auto-seed re-seeds on any
`SEED_VERSION` mismatch *without checking which side is newer*; that hazard is
a **destructive re-seed**. This script is built to be provably a different
operation:

* writes ONE new relationship type, `HAS_RISK_CLASS_OBLIGATION`, and never
  matches the existing 36 `HAS_OBLIGATION_ARTICLE` edges for write — so
  `kg_context`'s live reader of those is bit-for-bit unaffected, and rollback
  is exact;
* never touches `KBMetadata`, never bumps `SEED_VERSION`, never calls the seeder;
* takes a census **before and after** and **fails loudly if any pre-existing
  count moves** — additivity is asserted, not assumed;
* `--dry-run` is the default; writing needs `--apply`; `--rollback` removes
  exactly what it created.

**Applied 2026-08-17. All 11 invariant counts unchanged:**

```
total_articles 113   total_annexes 13   paragraphs 658   points 421
subpoints 37   recitals 180   definitions 68   kb_metadata 1
has_obligation_article 36   cross_references 248   has_recital_anchor 5

operator_roles              5 ->   8
HAS_RISK_CLASS_OBLIGATION   0 ->  90
total_nodes              1786 -> 1789
total_rels               2076 -> 2166
```

### 2.4 The reconciliation lint caught three real divergences

A 20-line cross-check between the two definitions found three, each then
verified against the pinned statute with `get_provision_text` rather than
reasoned from memory:

| divergence | statute | verdict |
| --- | --- | --- |
| prose binds `deployer → Art. 72` | Art. 72(1): "**Providers** shall establish and document a post-market monitoring system" | **the prose file is legally wrong** |
| matrix lacks `provider → Art. 73` | Art. 73(1): "**Providers** … shall report any serious incident" | **matrix gap** |
| matrix lacks `provider → Art. 25(4)` | Art. 25(4): "The **provider** … shall, by written agreement, specify …" | **matrix gap** |

**Deliberately not auto-fixed.** Editing the matrix changes `obligations_for`,
which feeds `_build_role_obligation_answer` — a deterministic *answer* path —
so it is a reference-affecting change that owes hard rule #8 a `gold_dropped`
reading first. They are pinned as `KNOWN_DIVERGENCES`; a **fourth** fails the
build, and healing one of the three also fails until the constant is updated.

---

## 3. The lever

`REGENOLD_ROLE_OBLIGATION_CONTEXT` — **default OFF**, engine-level, registered
in `_engine_cache_key`, fresh env read per call.

It renders the new edges as a **non-citable** Stage-2 block. The existing
`KNOWLEDGE-GRAPH REGULATORY CLASSIFICATION` block says *which* role bears a
provision; this one says *under which risk class* — the dimension the older
edge collapsed to `NULL`. The Cypher matches only on `$ids`, so it can only
describe provisions **already cited** and can never introduce one (hard rule
#10). Its marker is in `_R326_RESERVED_MARKERS`, or as the last-rendered block
it would delete itself under budget pressure.

### Live fire check (real Aura, not a mock)

```
ARM A (OFF): 0 rows, 27,992 chars, block absent
ARM B (ON) : 5 rows, 28,669 chars, block present   (+677 chars)

Annex VII    Notified Body   ['high_risk_annex_i', 'high_risk_annex_iii']
Article 26   Deployer        ['high_risk_annex_i', 'high_risk_annex_iii']
Article 43   Provider        ['high_risk_annex_i', 'high_risk_annex_iii']
Article 47   Provider        ['high_risk_annex_i', 'high_risk_annex_iii']
Article 48   Provider        ['high_risk_annex_i', 'high_risk_annex_iii']

VERDICT: FIRES
```

The first row is the whole point: `Annex VII → Notified Body` is a binding the
old edge type **could not express at all** — annex targets were dropped and
`notified_body` was never seeded. Both fidelity losses closed in one row.

---

## 4. What is NOT measured

The lever is **unmeasured on answer quality**. It ships default OFF for exactly
that reason: it is prompt budget on Answer-Conciseness, the one rubric axis
this system leads. The owed gate is

```bash
py -3.12 -m evals.harness.dynamic_ab --flag REGENOLD_ROLE_OBLIGATION_CONTEXT --label r371
```

with the `gold_dropped` veto as the gate. Do not flip the default until that
run exists.

---

## 5. Closed / opened

**Closed.** "Adopt AIRO + DPV-EU-AIAct" as stated — the ontologies do not
contain the two things the proposal buys them for, and this repo's own tables
already exceed them there. Re-propose only with a specific, fetched class or
property that this repo lacks.

**Opened.**
1. The 3 statute-verified role→obligation divergences (§2.4) need a measured fix.
2. C4c — graph verification of generated output — is genuinely unmeasured.
3. `HAS_RECITAL_ANCHOR` is still 5 edges; 111 of 113 articles have none.
4. CLAUDE.md's graph census, and its "this repo has never written to it", are
   both stale (§2.2).
