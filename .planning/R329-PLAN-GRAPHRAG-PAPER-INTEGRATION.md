# R329 — plan: what the NICD graph-RAG paper actually gives us

Source: Wedge, Stutter, Dixon & Cala, *Reducing Hallucinations in Complex
Question Answering using Simple Graph-based Retrieval-Augmented Generation
(long version)*, National Innovation Centre for Data / Newcastle University.
Local copy: `nicd-reducing-hallucinations-graphrag.pdf` (read via `pdftotext
-layout`; 1,582 lines including Appendix B — 10 hand-written Cypher queries —
and Appendix C — the agent and CRAG judge prompts verbatim).

Written 2026-08-13 at `13d83c7`. Read [`CLAUDE.md`](../CLAUDE.md) first.

⚠ **The working tree is dirty with unrelated in-flight work** — the R328.2
Bedrock review-fix pass (`app/llm/bedrock_client.py`, judge `--provider
bedrock`, Bedrock keys added to `_engine_cache_key`, evidence-store genesis
eviction), driven by
[`docs/reviews/main-2026-08-13-13d83c7.md`](../docs/reviews/main-2026-08-13-13d83c7.md).
Nothing in this plan touches those files. Land or stash that pass first.

---

## 0. What the paper establishes, and what we already took

**Result.** On 510 MoNaCo complex-QA questions × 3 runs, vector+graph RAG beat
vector-only RAG: factual correctness precision and recall both **more than
doubled**, answer relevancy **0.35 → 0.61**, fine-grained truthfulness **35 →
63 (+80%)**, at a modest token increase. Against zero-shot, hallucinated
answers roughly halved (coarse truthfulness −127 → −49).

**Mechanism — and this is the part that matters.** The gain did *not* come from
putting more context in front of the model. It came from **outline-first,
targeted reading**. The tool-usage distribution (Fig. 6) is unambiguous about
which tools carried the load:

| carried the load | measured near-dead |
| --- | --- |
| chunk vector search | article text (whole document) |
| title vector search | window paragraph / window section |
| **section titles + infoboxes** | get backlinks |
| **get sections** (targeted read) | shortest path (never called at all) |
| | article neighbourhood, calculator |

The winning loop is `title search → section titles → get_sections`: read the
*skeleton* of a document, choose the parts that matter, then read only those.
The paper is explicit that reading whole articles was the failure mode it had
to prompt its way out of.

**Already imported here.** R327 lifted query **B.2** — the per-parent roll-up
idiom — into `_FOCUS_CYPHER`, credited in-code at
[graph_semantic.py:229](../app/engines/graph_semantic.py:229). The repo has
always used hand-written parameterised Cypher rather than LLM-generated Cypher,
which is the paper's §3.3 recommendation. `evals/judge/grounded.py` already
decomposes answers into atomic Legal Data Points, which is the Ragas
claim-decomposition idea. **Do not re-propose any of these.**

---

## 1. The finding this exercise actually produced

Tracing the citation pipeline end-to-end against the paper's prompt design
yields a mechanistic explanation of the repo's #1 open problem — why wrong-rate
climbs by rank (1 → 0.22, 2 → 0.45, 3 → 0.60, 5 → 0.88).

**The head of the reference list is retrieval. The tail is parametric recall.**

1. `candidates` are rank-sorted by `(type_priority, -specificity)` with a stable
   tiebreak that preserves engine retrieval order
   ([regenold.py:7666](../app/routes/regenold.py:7666)).
2. The budget slice `candidates[:_effective_max_refs]`
   ([:8402](../app/routes/regenold.py:8402)) is a **prefix cut of that
   rank-ordered list** — so the head is retrieval-confident by construction.
3. Then **four** prose-mining passes append **at the tail**, in prose-mention
   order rather than retrieval confidence: R134 `_add_prose_named_refs`, R138
   cite-consistency, R133 `_surface_prose_subpoints`, and **Component D**
   ([:9209-9324](../app/routes/regenold.py:9209)).
4. Component D's promotion gate is **`ARTICLE_EXISTENCE` only** — catalog
   existence, not retrieval grounding — because
   `REGENOLD_COMPONENT_D_CITABLE_ONLY` is **default OFF**
   ([:3231](../app/routes/regenold.py:3231)). A provision retrieval never
   surfaced reaches the wire purely because the model named it in prose.
5. And the model is *pushed* to name provisions: rule 10 — "Unmentioned
   citations are severely penalized"
   ([graph_rag_prompts.py:78](../app/data/graph_rag_prompts.py:78)) — while
   `MINIMAL_COMPOSER_SYSTEM` rule 4 explicitly licenses drawing on parametric
   knowledge when the supplied references are thin
   ([:300-303](../app/data/graph_rag_prompts.py:300)).
6. **The citable universe is named by a block that now contains non-citable
   material.** The user-channel citation instruction is
   ([_graph_rag_impl.py:7324](../app/engines/_graph_rag_impl.py:7324)):

   > *"Cite only articles, annexes and obligations that appear in the EU AI ACT
   > REFERENCES block…"*

   But `_build_context_references_block`
   ([:6419](../app/engines/_graph_rag_impl.py:6419)) renders **inside that same
   block**: cross-regulatory bridging (GDPR/MDR), synthesized multi-hop
   analysis, legal-AST evaluations, all three knowledge-graph sections, the
   semantic layers, verbatim provision text, and referenced annexes/recitals.
   Each sub-block carries its own "do NOT cite" clause — so the model must
   resolve a permissive top-level scope statement against a stack of per-block
   prohibitions. That is a prompt-structure defect, and it sits directly
   upstream of the prose the tail-append passes then mine.

Compare the paper's vector-RAG prompt (Appendix C.1.2), which does the opposite
in two sentences — *"answer the questions based only on information you have
retrieved… Do not rely on any prior knowledge"* — and derives references
mechanically from the nodeIDs of the chunks actually used, never from a prose
scope description.

**Confirmed: no reference is validated against retrieved or grounding text at
any point in the default pipeline.** Every existing check is either existence
(`ARTICLE_EXISTENCE`) or self-consistency against the model's own prose. The
one mechanism that *would* answer "was this actually retrieved" —
`_stage2_citable_reference_bases` — gates only `_add_prose_named_refs` by
default; Component D bypasses it.

### 1b. A prompt-delivery asymmetry between the instrument and production

The Stage-2 **system** prompt is dropped by the Claude Max wrapper (measured
2026-08-03; the code comment at
[_graph_rag_impl.py:7448-7460](../app/engines/_graph_rag_impl.py:7448) records
it and states it is the reason nearly all rule content — citation scope, length,
tone, verdict-first — is **deliberately duplicated onto the user message**). So
the user channel is not bare. But Bedrock **honours** the system slot
([evals/judge/runner.py:251-257](../evals/judge/runner.py:251)), which means the
system-only residue — `ANSWER_GENERATE_SYSTEM` rules 1, 4, 10, 11, 12b, the
worked examples — fires on **production (Bedrock)** and not on the **eval path
(wrapper)**.

Consequence for this plan: any prompt-level result measured on the wrapper is
measured against a *smaller* rule set than production runs. That is not fatal —
it is directional — but it must be stated on every prompt A/B, and it is a
reason to prefer changes to the **user** channel, where both paths agree.

---

## 2. Ranked proposals

Every item below is env-gated, default-OFF in code, with an off-switch — per
the standing validation policy.

### Wave 0 — measurement only, no code risk

**P6. Run `--mode hard`.** Free, ~40-70 min, still never run, and it is *the
graded turn*. `_run_hard` issues two live requests per row inside a rolling
multi-turn conversation and grades the **post-pushback** answer, recording
`conceded`, `ref_heads_changed`, `pushback_ref_jaccard` — none of which easy
mode produces. Every optimisation decision on the table has been made on the
easy turn. Do this first, in parallel with Wave 1.

**Re-verify the baseline reproduces** before grading anything (CLAUDE.md's
authoritative block; `--assert-baseline` works again after R327).

### Wave 1 — the instrument. Nothing below can be gated without this.

**P0. Implement `gold_dropped` in `evals/harness/easyhard_ab.py`.**
Hard rule #8 — *"a reference change must drop ZERO gold; measure `gold_dropped`
FIRST"* — is **currently unenforceable: the field does not exist anywhere in the
repo.** It appears only in prose (CLAUDE.md, two route comments, two test
comments, the R327 write-up, which says outright that it is unmeasured).
`easyhard_ab` is the right home: its `ProbeRow.expected_refs` carries sub-point
grain and it already uses the `*_exact_coord` formulas.
Emit per arm, at both head and exact-coordinate grain:
`gold_dropped = Σ |set(expected_refs) − set(predicted_refs)|`, plus the per-row
list so a regression is diagnosable. ~30 lines.

**P0b. Add `ref_crag_fine` — a new metric name, not a rebinding.**
The paper's fine-grained CRAG scale (Appendix C.2.2), applied to the *reference
set* rather than answer claims:

| condition | score |
| --- | --- |
| predicted set == gold set | **+1** |
| predicted ⊂ gold, no extras | **+0.5** |
| no references emitted | 0 |
| some gold hit, but extras present | **−0.5** |
| no gold hit | −1 |

Why this and not precision or F1: precision alone rewards citing nothing (the
hard-rule-#8 hazard the R327 write-up flags); F1 blunts the asymmetry. The
repo's own measurements say an extra wrong reference costs more than a missing
one, and **no current metric encodes that**. This is the ruler the over-citation
work has been missing.
⚠ Ship it under a **new name**, reported alongside and never replacing the
canonical axes — R327's lesson: *if you change a formula, change its NAME.*

### Wave 2 — cheapest, highest confidence

**P1. Ground Component D: gate `REGENOLD_COMPONENT_D_CITABLE_ONLY` ON.**
This is the paper's "answer only from what you retrieved" principle, already
implemented in this repo, sitting OFF. It restricts Component D's promotions to
`_stage2_citable_reference_bases` — the retrieval-derived candidate set.

⚠ **Read the measured table correctly.** `regenold.py:1190-1194` reports, for
each over-citation cause, *what removing it wholesale would cost*:

| cause | wrong removed | correct lost | % correct |
| --- | --- | --- | --- |
| parent alongside its own sub-point | 9 | 1 | 10% |
| everything at rank 4+ | 17 | 14 | 45% |
| ref named in the prose (Component D) | **79** | **145** | **65%** |
| the ref is itself a sub-point | 5 | 28 | **85%** |

Component D is the largest source of wrong refs **and by far the largest source
of right ones**. Deleting it is strongly net-negative. P1 is not deletion — it
removes only the *ungrounded subset*, which is why it is not a member of the
five dead trimmer families (it is a grounding predicate, not a positional,
identity, or prose-shape rule).
Gate: `easyhard_ab` with `gold_dropped` + `ref_crag_fine`. Hard rule #8 applies.
Risk to measure, not assume: some of the 145 correct are parametric-but-right.

**P2. Emit the legal coordinate in the constrained semantic block.**
New flag `REGENOLD_SEMANTIC_COORDINATES`, default OFF.

Today `_FOCUS_CYPHER` binds
`(a)-[:HAS_PARAGRAPH|HAS_POINT|HAS_SUBPOINT*1..3]->(node)` but collects only
`{uid, layer, text, score}`
([graph_semantic.py:238](../app/engines/graph_semantic.py:238)), and renders
`- Article 12 [paragraph para_12_1]: <text>`
([kg_context.py:822](../app/engines/kg_context.py:822)). **The block built to
attribute a duty to the right sub-provision cannot express a sub-provision
citation.** It shows the model sub-provision *text* under a *head-level* cite.

The last row of the table above is the argument: **references that are
themselves sub-points are the most accurate citation shape the system emits —
85% correct against an overall precision of 0.696.** And both the grounded judge
and easyhard gold score at sub-point grain.

And the *instruction* for this already ships: `REGENOLD_SUBPARAGRAPH_ATTRIBUTION`
is **default ON** ([graph_rag_prompts.py:540](../app/data/graph_rag_prompts.py:540)),
putting a sub-paragraph attribution discipline on the user channel. So the model
is asked for sub-paragraph attribution while the block that holds the
sub-paragraph text withholds its coordinate. **The instruction exists; the data
does not.**

Fix: bind the path (`MATCH path = (a)-[...]->(node)`), reconstruct the
coordinate from `nodes(path)` (`p.number` / `pt.letter` / `s.roman` — the same
properties `_SUBPOINT_CYPHER` already reads), render `- Article 12.1: <text>`.
One query, no extra hop, no new data.
Pairs with `REGENOLD_PARENT_COLLAPSE`, which becomes both more valuable and more
necessary — more sub-point cites means more head+child pairs on the wire.
Gate: `easyhard_ab` (already on exact-coord formulas) + `gold_dropped`.

⚠ **Scope limit, decided deliberately: P2 changes the rendered LABEL only, not
citability.** These blocks are explicitly framed non-citable, and hard rule #10
says the graph is additive context and **never a wire citation**. Emitting a
coordinate *and* relaxing the framing would put the graph directly on the wire.
The label change alone is still useful: it feeds R133's `_surface_prose_subpoints`
rescue, which is a route-level, retrieval-grounded path, and it lets the model
describe the duty at the grain the judge scores at.
Relaxing the framing — "a sub-point coordinate of an ALREADY-CITED provision may
be cited in place of its parent" — is defensible (the provision came from
retrieval; the graph only refines the grain) but it is a **separate flag and a
separate gate**, not part of P2.

### Wave 3 — the prompt

⚠ **Do not re-propose a minimality clause.** `USER_REF_MINIMALITY_CLAUSE`
([graph_rag_prompts.py:493-504](../app/data/graph_rag_prompts.py:493)) is
already on the user channel and **default ON since R298**, shipped on a live
grounded-judge A/B: multi-turn ref precision **0.423 → 0.735**, recall **0.909 →
0.966**, answer correctness 0.471 → 0.647. It already tells the model the
references block is "over-retrieved candidate context, NOT an agenda". The
minimality argument is made and it works. Two narrower gaps remain.

**P3a. Make the citable universe an explicit enumerated list.**
New flag `REGENOLD_CITABLE_UNIVERSE_BLOCK`, default OFF.

This is §1 point 6, fixed at its source. Rather than pointing the model at a
block that now contains seven kinds of explicitly non-citable material, emit a
short standalone list immediately before the instruction:

```
CITABLE PROVISIONS (the ONLY values that may appear in a citation):
Article 5, Article 6, Annex III
```

and rewrite the instruction to name *that* list rather than "the EU AI ACT
REFERENCES block". The set already exists in code —
`_stage2_citable_reference_bases`, the same retrieval-derived set P1 uses — so
this is rendering, not new retrieval. It is also the paper's own design:
references are derived mechanically from the identifiers of the material
actually used, never from a prose description of scope.
Expected interaction: this makes P1 largely redundant at the *prompt* level
while P1 remains the enforcement backstop at the *route* level. Run them as
separate arms before bundling.

**P3b. Add the CRAG asymmetry — the one thing minimality does not say.**
Fold into the same flag or its own; keep it to one sentence on the user channel:

> If you are not certain a provision is on point, omit it: an incorrect
> citation costs more than a missing one.

Minimality argues *relevance* ("if removing it would not change the answer");
the paper's safe-refusal design argues *uncertainty*, which is a different and
unstated axis. This is the mechanism behind its halved hallucination rate.
⚠ It pulls against rule 10 ("Unmentioned citations are severely penalized"),
which exists because the reconcile pass drops refs the prose does not name.
Measure the reconcile drop rate in the same arm.
Gate: `ab_judge` (these move answer and tone) **and** `easyhard_ab` for refs.

**P3c. Free fix — `USER_ANSWER_COVERAGE_CLAUSE` is appended twice.**
[_graph_rag_impl.py:7488-7508](../app/engines/_graph_rag_impl.py:7488) contains
the same `try/except` block verbatim twice; both fire when
`REGENOLD_ANSWER_COVERAGE` (default ON) is set, so the clause lands twice in
every live prompt. Delete the duplicate. Cache-inert (one flag drives both), so
it is a clean no-risk edit — but it should be its own commit and its own A/B,
because removing a duplicated instruction can change emphasis.

### Wave 4 — the paper's core mechanism

**P4. Outline-first context: a `PROVISION OUTLINE` block.**
New flag `REGENOLD_PROVISION_OUTLINE`, default OFF.

**There is no headings-only mode anywhere in this repo** — confirmed at both
layers. `render_kg_context` always calls `_flat(unit["text"], unit_chars)` and
always emits full (truncated) unit bodies; `eu_ai_act_tree.TreeNode` has no
title field distinct from `text`, so a paragraph's only identifier is a bare
integer. The `title` that does exist is article-level only
(`_HIERARCHY_CYPHER`'s `a.title`).

Proposal — the deterministic collapse of `section titles → get_sections`:
per cited provision, emit one line per paragraph/point giving **coordinate +
first-clause gist (≤120 chars, cut at the first `:`/`;`/sentence end)**, then
keep **full verbatim text only for the constrained-ANN-selected units**. No new
data source; the gist is derived from text the hierarchy query already returns.

Two reasons to expect this to help both axes rather than one:
- it is the exact mechanism behind the paper's doubled precision *and* recall;
- today's budgeting **tail-drops** — `_flat` cuts the end of a unit and
  `_fit_complete_lines` drops whole trailing rows
  ([kg_context.py:558, :711](../app/engines/kg_context.py:558)) — so a long
  provision currently reaches the model with its end silently deleted. An
  outline degrades far more gracefully than a truncated body.

⚠ Prompt budget competes with Answer-Conciseness, the one axis the official
scorecard says we lead. Watch answer length on every arm; any bound must be
sentence-only (hard rule #2).

### Wave 5

**P5. `CROSS_REFERENCES` backlinks as non-citable context** (the repo's own #6;
the paper's B.9 `get_backlinks`). 248 edges, real legal signal
(`article_50 ← [13, 26, 5, 96]`), never read as *context* — it is read today
only as a citation/candidate path by `graph_expand_2hop.py` and `path_rag.py`.

**Honest counter-evidence:** the paper measured `get_backlinks` as near-unused.
But that is a tool-*selection* result under an agentic loop — the agent never
called it, so its efficacy was never tested. Here it would be injected, not
chosen. Needs an incoming accessor: `kb_xrefs` exposes only `cross_refs()`
(outgoing) and an in-degree **count**; `all_edges()` exists and can be filtered
by target.
Rank last. Gate on its own flag, after P4 settles the budget question.

---

## 3. Do not propose these — the paper's other ideas are dead or already here

- **Any new trimmer, clamp, blocklist, or re-ranker.** Five families measured
  dead; R325 closed the ranker (nothing beats the engine's own `rank`, AUC
  0.703). P1 and P2 are deliberately *not* in that family.
- **LLM-generated Cypher.** The paper argues against it (prompt-injection
  surface; models won't write multi-hop Cypher). We already use hand-written
  parameterised queries.
- **A full agentic ReAct tool loop.** The paper's own data kills most of the
  toolset — windowing, shortest path (never called once), article
  neighbourhood, backlinks and the calculator were all near-dead. And latency is
  a scored axis here against a 12-17 s fixed wrapper floor *per call*.
- **Ragas claim decomposition for answer correctness.** `grounded.py` already
  does LDP decomposition; `evals/judge/prompts.py` does a LeMAJ variant.
- **Faithfulness / context-precision metrics.** The paper rejected them without
  golden contexts; the July-7 batch has `gold_coverage = 0.0` for the same
  reason.
- **A larger embedding model** (the paper used Harrier-0.6B). Railway is
  CPU-only and torch-free by design; the 128-dim TF-IDF→SVD encoder is a
  deliberate constraint. The repo has already measured that the embedding is a
  weak open-domain retriever — which is precisely why the *constrained access
  mode* matters more than the encoder.

---

## 4. Sequencing and measurement protocol

```
Wave 0  P6 --mode hard  +  baseline reproduce        (measurement, parallel)
Wave 1  P0 gold_dropped  +  P0b ref_crag_fine        (instrument — blocks 2-5)
Wave 2  P1 Component D grounding  ·  P2 coordinates  (cheap, high confidence)
Wave 3  P3a citable universe · P3b CRAG asymmetry · P3c dedupe coverage clause
Wave 4  P4 provision outline
Wave 5  P5 backlink context
```

Flags to register in `_engine_cache_key`'s env tuple
([regenold.py:1379-1861](../app/routes/regenold.py:1379), ~132 entries today):
`REGENOLD_SEMANTIC_COORDINATES`, `REGENOLD_PROVISION_OUTLINE`,
`REGENOLD_CITABLE_UNIVERSE_BLOCK` — all three change Stage-2 input, so all three
are engine-level. `REGENOLD_COMPONENT_D_CITABLE_ONLY` is route-level
post-processing and must stay **out** of the key; that asymmetry is what makes
the paired in-process A/B possible.

Protocol, adopting the paper's methodology on top of the standing policy:

1. **Three runs, report median with min/max**, for any gate deciding a
   reference axis. The paper does this for exactly the reason we have been
   burned twice: two runs with an *identical* baseline arm changed 20/40 rows'
   refs and sign-flipped all three reference axes.
2. **Check the branch arm's latency on every A/B** — the cheapest inert-A/B
   detector. See the flag registration note above.
3. **Prove each feature FIRES** before reading a flat result as safe —
   "byte-identical" is also what inert looks like.
4. `easyhard_ab` + `gold_dropped` is the gate for P1/P2; `ab_judge` for P3/P4
   (they move answers, not only references); the grounded judge on the July-7
   batch as the end-to-end read.
5. Warm the graph client before timing or grading anything.

## 5. Open risks

- **P1 could drop gold.** 145 of Component D's refs are correct; an unknown
  share are parametric-but-right and would be removed. `gold_dropped` is exactly
  the instrument for this, which is why P0 comes first.
- **P2 raises reference counts** before parent-collapse absorbs them. Measure
  the pair, not just P2.
- **P3b and rule 10 pull opposite ways.** Do not ship it without reading the
  reconcile pass's drop rate in the same arm.
- **P3a and P1 overlap.** One constrains the prompt, the other the route. Run
  them as separate arms first; bundling before measuring hides which one paid.
- **P4 spends prompt budget** on the one axis we lead.
- **Everything above is being decided on the easy turn** until P6 runs. That is
  why P6 is Wave 0.
