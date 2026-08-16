# R354 — The six live-answers veto rows: deep-dive and targeted fix

**Run:** `dynamic-ab-r350-live-answers.json` — 81 rows, branch = R350.2 full
stack (`REGENOLD_COHERE_RERANK=1`, `REGENOLD_RERANK_KG_CANDIDATES=1`,
`REGENOLD_QUERY_EXPANSION=1`) vs the shipped baseline.

**Veto:** harness-grain `gold_dropped_head` base 72 → branch 76 (+4). Six rows
regress; everything else is equal or better. Per the R352 fork decision, the
KG-citability *projection* arm was already deleted — but the base R347 KG
candidate pool (`REGENOLD_RERANK_KG_CANDIDATES`) is still live in this stack.

---

## The six rows, with their actual wire refs

| row | gold | base refs | branch refs | base→branch dropped |
|---|---|---|---|---|
| la_q87 | Annex I, Annex III, Art. 5, Art. 50, Art. 6 | 6.1, 50.1, Annex III.4.a, Annex I | 6.1, 6.2, Annex III.4.a, Annex I | 1 → 2 (Art. 5, Art. 50) |
| la_q20 | Art. 16, Art. 26 | 74, 16, 26 | 74.12, 78 | 0 → 2 |
| la_q51 | Art. 1, 10, 8, 9 | 1, 42, 8 | 42, 55, 16 | 2 → 4 |
| la_q73 | Annex I, Art. 6 | 43, 6, Annex I | 43, 6, 27, 49 | 0 → 1 (Annex I) |
| la_q84 | Annex I, III, 10, 13, 15, 16, 17, 19, 25, 49, 6, 9 | 15, 9, 16, 54, 96, 10, 13 | 47, 16, 94, 71, 49, 80, 17 | 7 → 9 |
| la_q52 | Art. 17, 56 | 63, 56, 83 | 111, 8, 86 | 1 → 2 |

---

## Per-row mechanism (read from the actual answers, not the metric)

### la_q87 — generation-level citation drift (the R350.2 signature)

Both arms answer the same question correctly. The BASE answer's prose says
"the system carries the **Article 50(1)** transparency obligation where it
interacts directly with natural persons" — so Component D promotes Art. 50
to the wire. The BRANCH answer restructures around the Article 6(1)/(2)
routes and never mentions Article 50 in prose — so Component D has nothing to
promote, and Art. 50 falls off the wire. The retrieval was identical; the
**answer prose changed what got cited**. This is the mechanism the R350.2
post-mortem called generation-level drift, and it confirms R351's anchor
fix cannot close it: the wire refs are answer-driven.

### la_q20 — the branch is MORE correct, and the gold penalizes it

The base answer claims "the Regulation does not expressly mandate… standing
remote access" — which is **legally wrong**. The branch answer cites Article
74(12), which genuinely requires market-surveillance authorities to be
granted access to documentation and training/validation/test datasets,
including via remote-access means. The graded gold is `[16, 26]` — so the
branch's *better* answer loses both gold refs. **This row is a gold-coverage
gap, not a retrieval regression.** Any fix that "improves" this row would
make the answer legally worse.

### la_q51 — topic drift: compliance question answered with GPAI content

"What should my company do to comply with AI rules in Europe?" The base
answer holds the Art. 1 / Art. 8 core. The branch answer adds a block of
GPAI systemic-risk content (Art. 55, 56) that the question never asked for,
and the wire follows the prose: 55 replaces 8/9/10. The KG candidate pool
surfaced GPAI-adjacent provisions and Stage-2 wrote them in.

### la_q73 — retrieval displacement, exposed by a gated pass (the cleanest bug)

Branch wire refs are `[43, 6, 27, 49]` — **Article 43 is not in the branch
answer's prose at all, while Annex I appears twice** ("…the Union
harmonisation legislation **listed in Annex I**…" ×2). We replayed the
pipeline: the R72 reconcile (drop refs prose never names) and the R138
prose-consistency pass (add refs prose names) would restore Annex I and drop
Article 43 — **but both are Stage-2-gated, and this row's answer is the
deterministic/curated path**, so neither ran. The raw retrieval candidates
shipped as-is. This is the concrete, fixable defect.

### la_q84 — obligation-chain displacement on a big lifecycle question

Gold is a 12-ref obligation chain (9, 10, 13, 15, 16, 17, 19, 25, 49, 6 +
Annex I/III). The base arm holds the Section-2 core (9, 10, 13, 15, 16).
The branch arm's retrieval shifted toward conformity/registration provisions
(47, 71, 49, 80, 94) and dropped the data-governance / transparency /
risk-management core. Both arms miss many gold refs (7 vs 9), but the KG
pool changed *which* refs were retrieved, and the shift cost the Section-2
chain.

### la_q52 — topic drift on a general "help me understand" question

Base holds Art. 56 (Code of Practice). The branch answer goes to
transitional provisions (Art. 111, 86) — retrievably correct, entirely
beside the question. Both gold refs (17, 56) fall off.

---

## Three mechanisms, one pattern

1. **Topic drift from the KG pool (la_q51, la_q84, la_q52, la_q20)** — the
   candidate pool surfaces adjacent-but-wrong provisions; Stage-2 writes
   them into prose; the wire follows the prose.
2. **Generation-level citation drift (la_q87)** — same retrieval, different
   prose, different citations.
3. **A real pipeline bug (la_q73)** — prose-consistency (R72/R138) is
   Stage-2-gated, so a deterministic answer ships raw retrieval candidates:
   Article 43 cited without being described, Annex I described twice without
   being cited.

Pattern: **on the wire, retrieval only matters insofar as it shapes the
answer prose.** The veto is not one bug; it is the KG-pool lever changing
what Stage-2 writes, plus one gating bug that lets raw candidates ship.

---

## The targeted fix (measured before code)

### Fix A — run prose-consistency on the deterministic path too (fixes la_q73)

The R138 `_add_prose_named_refs` pass (and R72 reconcile) is gated on
`_stage2_landed`. Extend the R265 deterministic-reconcile predicate — which
already runs R72 on the curated path for 11 intercept shapes — with the R138
ADD direction on the same deterministic path. Effect measured over the whole
81-row branch arm:

**11/81 branch rows have a gold ref the prose names but the wire lacks —
11 gold heads restorable, all existence-gated and cross-instrument-guarded.**
Concretely: la_q17 (Art. 5), la_q29 (Annex III), la_q46 (Art. 5), la_q51
(Art. 10), la_q53 (Art. 51), la_q71 (Annex III), la_q73 (Annex I), la_q74
(Art. 13), la_q78 (Art. 3), la_q8 (Art. 43), la_q84 (Art. 25).

Veto impact, measured row-by-row on the six regressions:

| row | branch dropped | Fix A restores | result |
|---|---|---|---|
| la_q87 | Art. 5, 50 | — (prose never names them) | **unfixed — generation drift** |
| la_q20 | Art. 16, 26 | — (prose cites 74.12/78) | **unfixed — gold gap, don't touch** |
| la_q51 | Art. 1, 10, 8, 9 | Art. 10 | 4 → 3 |
| la_q73 | Annex I | Annex I | 1 → 0 ✅ |
| la_q84 | 9 refs | Art. 25 | 9 → 8 |
| la_q52 | Art. 17, 56 | — (prose cites 111/86) | **unfixed — topic drift** |

The pass is strictly additive (existence-gated, cross-instrument-guarded,
never invents) and the R72 drop side is precision-safe (never empties,
floor-protected) — the same guarantees already A/B-accepted for the
Stage-2 path. No new flag: reuse `REGENOLD_REFS_RECONCILE` +
`REGENOLD_CITE_CONSISTENCY` gates.

### Fix B — do NOT touch la_q20 (documented as a gold-coverage gap)

Fixing la_q20 means citing 16/26 instead of the correct 74(12). Leave the
row; flag it in the probe gold as a known coverage gap so the veto book
stops counting it as a regression. This is a **gold edit, not a code edit**.

### Fix C — the KG-pool lever itself (la_q51, la_q84, la_q52, la_q87)

These four are the R350.2 veto mechanism: the KG candidate pool changes
what Stage-2 writes. The R352 decision deleted the projection arm but the
candidate pool stayed on. The clean experiment — rerank × expansion WITHOUT
`REGENOLD_RERANK_KG_CANDIDATES` on this exact 81-row probe — is the decisive
measurement (expansion alone had the only positive live evidence, R346: gold
17→14). One command, no code:
`REGENOLD_COHERE_RERANK=1 REGENOLD_QUERY_EXPANSION=1` (KG candidates off),
rerun the 81-row live-answers A/B, veto-compare.

---

## Recommended sequence

1. Ship Fix A (deterministic prose-consistency) — closes the one true bug,
   11/81 rows, zero risk to the Stage-2 path, davidath byte-identical
   (no Stage-2 on the bench, curated-intercept-only trigger).
2. Run the Fix C isolation A/B (KG off) on the 81-row probe with the judge.
   If the veto clears, the KG candidate pool is the load-bearing cause and
   it gets the R352 treatment (flag + branch deleted). If it persists, the
   cause is the rerank/expansion pair and they get measured separately.
3. Edit the la_q20 gold (or annotate it) so the veto book stops penalizing
   the legally-correct answer.
