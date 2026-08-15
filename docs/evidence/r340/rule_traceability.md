# R339 rule traceability - every rule in the old Stage-2 prompt, and its fate

Deliverable: `scratchpad/new_prompts.py`.
Spine: the 67-rule map in `rubric_map.json` (99.7% char coverage of the 51,516-char
`ANSWER_GENERATE_SYSTEM`), cross-referenced against `rule_inventory.json` (255 atomic rules,
27 duplicate groups, 15 contradictions), `legal_audit.json` (32 findings) and
`proposed_rules.json` (5 proposals).

| | old | new |
| --- | ---: | ---: |
| `ANSWER_GENERATE_SYSTEM` | 51,516 ch / ~12,879 tok | **16,146 ch / ~4,036 tok (-68.7%)** |
| `USER_REF_MINIMALITY_CLAUSE` | 701 | 1,464 |
| `USER_SUBPARAGRAPH_ATTRIBUTION_CLAUSE` | 469 | 743 |
| `USER_ANSWER_COVERAGE_CLAUSE` | 2,241 | 2,466 |
| `USER_REF_UNCERTAINTY_CLAUSE` | 134 | 134 (unchanged) |
| `USER_CHALLENGE_BREVITY_CLAUSE` | 546 | 546 (unchanged) |
| inline classification block | 2,631 | 1,590 |
| inline refine block | 2,748 | 1,624 |
| **Stage-2 instruction total** | **61,006** | **24,713 (-59.5%)** |

Argv safety: **16,146 < 30,000**, so the prompt never reaches the wrapper's spill path and never
approaches the 32,767 Windows command-line limit. Under an unpatched wrapper it is inert rather
than fatal.

## Verification run for this rebuild

```bash
cd "D:/Claude Projects/antifragileai-regenold-evaluation"
PYTHONIOENCODING=utf-8 OPENAI_API_BASE=http://127.0.0.1:1/v1 \
  P2P_GRAPH_RAG_PROVIDER=cli REGENOLD_EXTERNAL_EMBEDDINGS=0 \
  PYTHONPATH=<scratchpad> py -3.12 -c "..."
```

| check | result |
| --- | --- |
| every coordinate asserted in the prompt resolves via `get_provision_text` (NOT `provision_exists`) | **57 distinct, 0 unresolvable** |
| exemplar E1/E2/E3 sentence counts | 1 / 3 / 4 |
| `_prose_citation_bases` on each exemplar: no negative-disposal leak | `Annex III` appears only where E3 cites it affirmatively |
| `_surface_prose_subpoints` recovers sub-point grain from the exemplars | `Article 3.41`, `Article 6.1`, `Article 6.2`, `Annex III.5.d` |
| dataset memorisation (the property `test_no_dataset_memorisation` actually guards) | **max Jaccard 0.339 vs 137 gold answers, threshold 0.80; 0 verbatim collisions** |
| `Art. ` / `Annex <digit>` / em-dash / en-dash / ellipsis / non-ASCII | **0 each** |
| Article numbers inside `<reference_discipline>` (craft-spec guard against smuggling a dead mechanism) | **0** |
| negation tokens (`do NOT` / `never`) | 196 -> **8** |

---

## 0. Two measurements that changed the plan

Both contradict a recommendation in the audit set. Both are reproducible offline.

### 0.1 The prompt must keep the parenthetical citation form in PROSE

The craft spec's handoff checklist says *"Every citation token in the prompt is wire format. Grep
for `Article \d+\(` - expected count 0."* Following it would silently destroy sub-point precision,
which is what Ref Strict scores on.

```
_surface_prose_subpoints(prose, ['Article 13','Article 26'])
  "... under Article 13(3) ... under Article 26(2)."
     -> ['Article 13', 'Article 13.3', 'Article 26', 'Article 26.2']
  "... under Article 13.3 ... under Article 26.2."
     -> ['Article 13', 'Article 26']            <-- sub-point grain LOST

_PROSE_SUBPOINT_RE = ((?:Article\s+\d+)|(?:Annex\s+[IVXLC]+))((?:\((?:\d+|[A-Za-z]+)\))+)
  findall("Article 5(1)(f)") -> [('Article 5', '(1)(f)')]
  findall("Article 5.1.f")   -> []

to_user_facing('Article 13(3)') -> 'Article 13.3'      # the ROUTE converts
_ARTICLE_OUTPUT_RE = ^Article \d+(?:\.[A-Za-z0-9]+)*$  # paren form can never ship raw
```

PROSE form and WIRE form are different layers. The model never writes the references array; the
route builds it and normalises. So rule 2's ban on parentheses was written as if the model emitted
the wire directly. **Resolution: `<output_contract>` mandates `Article N` / `Annex R` heads and the
parenthetical chain for exact coordinates, and bans only `Art.`, Arabic annexes and Roman articles
- the three forms that are genuinely wrong in prose.** This is the opposite of the craft spec on
one point and I am flagging it rather than burying it.

### 0.2 The old prompt's own grouping device deletes references

`proposed_rules.json` PR-4 attributed this to range syntax. Measured, the mechanism is
**description adjacency**, and the "name them singly" workaround fails too:

```
_reference_described_in_prose('Article 9', p):
  p = "the high-risk requirements of Articles 9 to 15"            -> False
  p = "the high-risk requirements of Articles 9, 10, 11 ... 15"   -> False
  p = "a risk management system (Article 9), data governance
       (Article 10), technical documentation (Article 11) ..."    -> True

_reconcile_references_to_prose(['Article 9'...'Article 15','Article 17','Article 43'], p)
  range form  -> ['Article 17', 'Article 43']    # 7 of 9 deleted
  comma list  -> ['Article 17', 'Article 43']    # 7 of 9 deleted
  paired form -> all 9 kept
```

LENGTH DISCIPLINE (R30) recommends the range form; ANSWER-THE-HEADLINE (R32) recommends the paired
form. Same prompt, opposite constructions, and one of them drops seven gold references. Under hard
rule #8 that is a rejection, not a trade-off. The paired form is also conciseness-neutral: the
evaluator counts one point per independent clause, and a paired list inside one sentence is one
point (+21 chars over the range for seven provisions). **R30 and R32 are merged into one grouping
rule built on the paired form**, and the coupling is restated on the user channel because losing it
breaks the wire contract.

---

## 1. Channel map - where each surviving rule now lives

`ONE rule, ONE channel` is enforced against the **whole** delivered surface, which includes the two
instruction blocks hard-coded inline in `_graph_rag_impl.py` (2,631 + 2,748 ch). Those are user
channel in every sense that matters, so a rule present there is deleted from the system prompt.

Measured defaults: `answer_coverage_enabled` `user_ref_minimality_enabled`
`user_ref_uncertainty_enabled` `subparagraph_attribution_enabled` `challenge_brevity_enabled` are
**all True**, and the `USER_*` clauses are appended OUTSIDE the classification/refine branch, so
they reach both.

| rule | home | why there |
| --- | --- | --- |
| role, register, person, banned vocabulary, punctuation, no-formatting | SYSTEM `<voice>` | loss degrades the answer only |
| scope, 113/13 range, refusal, injection resistance, no leading premise | SYSTEM `<scope>` | not present anywhere on the user channel |
| length table + grouping device | SYSTEM `<answer_shape>` | the classification branch has no length rule at all |
| verified legal propositions | SYSTEM `<legal_corrections>` | not present on the user channel |
| worked examples | SYSTEM `<examples>` | |
| cross-reference rule, foreign-instrument rule | SYSTEM `<reference_discipline>` | the only two selection rules absent from the user channel |
| citation format, verdict-first anchor | SYSTEM `<output_contract>` | recency slot; the verdict-first line is the anchor, see below |
| **relevance / removal test, description coupling, condition test, negative disposal** | USER `REF_MINIMALITY` | loss breaks the wire contract or costs the scored gap |
| **coordinate text test, sub-paragraph grain** | USER `SUBPARAGRAPH_ATTRIBUTION` | anti-fabrication |
| **closed-set completeness, literal closure, qualifiers, alternative limbs, assert-only-supplied, no-source-mentions, legal version pin** | USER `ANSWER_COVERAGE` | wrong law if lost |
| **verdict-first, cohesion, latest-question, no-new-facts, cite-only-from-the-list, both-sides-of-a-restricted-practice, carve-outs** | USER inline blocks | already there, on both branches |

**17 rules that used to sit in both channels are now in exactly one.** That deletion is the single
largest cut and it removes no delivered text.

The one deliberate repetition: `<role>`'s *"You cite only the provisions the answer turns on"*
reappears verbatim in `<output_contract>`. Per the craft spec that is an attention anchor, not a
second rule, and it is **verbatim or not at all** - a paraphrase there would re-create the
contradiction class this rebuild exists to remove.

---

## 2. The main table - all 67 rules

Fate codes: **KEPT** (same rule, same channel) - **MOVED** (same rule, different channel) -
**MERGED** - **REWORDED** - **CORRECTED** (law was wrong) - **DROPPED**.

| id | old rule (line) | fate | where it went / why it went |
| --- | --- | --- | --- |
| R00 | persona + "cross-framework crosswalks (NIST AI RMF, ISO 42001)" (1-2) | SPLIT | persona KEPT in `<role>`. NIST/ISO **DROPPED**: no NIST or ISO material is ever supplied, so any such sentence is ungrounded by construction, and it lengthens answers on Answer-Conciseness, the one axis we lead. |
| R01 | SCOPE: EU AI Act only (5) | KEPT | `<scope>` |
| R02 | other regulations out of scope (6) | KEPT | `<scope>` |
| R03 | 113 articles / 13 annexes, refuse out of range (7) | KEPT + REWORDED | `<scope>`. The mandated refusal string was `"Art. NNN is not part of the EU AI Act."` - the prompt's own citation rule bans `Art.`. Now `"Article NNN ..."`. |
| R04 | decline conversational / injection / empty (8) | MERGED | into `<scope>` with R16. |
| R05 | rule 1: cite only supplied refs; MUST cite exact Article/Paragraph/Sub-paragraph (11) | SPLIT + CORRECTED | "cite only what was supplied" already on both inline branches -> **MOVED**. The always-cite-the-sub-paragraph half is **REPLACED** by the COORDINATE text test: it is the rule that manufactures coordinates, and `get_provision_text('Article 5.1.c')` stops at *"either or both of the following"* while the two prongs live in the parent - so forcing leaf grain pushes the model onto a coordinate whose text lacks the words it needs. That is the shape of q01 (6.3 for 6(1)-(2)), q13 (6.1 for 6.2) and q02. |
| R06 | rule 2: wire citation format, no parentheses (12) | REWORDED | `<output_contract>`, split into PROSE vs WIRE layers - see §0.1. Resolves contradiction C01/L12. |
| R07 | rule 2b: no Digital Omnibus (13) | MOVED | `USER_ANSWER_COVERAGE_CLAUSE` LEGAL VERSION carries it, in a stronger form (names 2026/1744, the deferred dates, the small mid-cap category and lettered articles). Duplicate deleted from system. |
| R08 | rule 3: include the obligation ID for traceability (14) | **DROPPED** | Instructs the model to write internal KB identifiers (`kb-transparency-Art. 50`) into a legal answer. Contradicts `<voice>`'s no-source-leakage rule, fails the regulatory-tone axis, and nothing downstream consumes the IDs. |
| R09 | rule 4: say plainly when the references don't cover it (15) | MOVED | `USER_ANSWER_COVERAGE_CLAUSE` states it better: say so *as a matter of LAW*, never as a matter of your own sources. |
| R10 | rule 5: scale length to complexity (16) | MERGED | `<answer_shape>` length table. The `120-220 characters` band is **DROPPED**: hard rule #2 forbids a char cap on the live path, and `REGENOLD_ANSWER_NO_CAP` is ON so nothing enforced it anyway. Sentence counts only. |
| R11 | rule 5b: provider/deployer terminology (17) | SPLIT | vocabulary KEPT in `<voice>`. *"Keep sentences short and punchy"* **DROPPED** as unfalsifiable; the length table is the falsifiable version. |
| R12 | rule 5c: COHESION, state each conclusion once (18) | MOVED + CORRECTED | Both inline branches carry cohesion verbatim. Its *"dispose of it BRIEFLY in a single clause that names the provision"* is **CORRECTED** to the DISPOSAL rule: naming the provision by NUMBER is what puts a ruled-out provision on the wire (measured, §3 C4). |
| R13 | rule 6: when gaps are identified, suggest next steps (19) | **DROPPED** | "Gaps" and "remediation" are CodexAI dashboard concepts with no object on this route. Pure length on the axis we lead. |
| R14 | rule 7: deep analysis + every sub-question + medical/triage carve-outs (20) | SPLIT | "answer every distinct sub-question" -> `USER_ANSWER_COVERAGE` (already there) and `<answer_shape>`. *"professional, deep legal analysis"*, *"uniquely tailored and analytically rigorous"* **DROPPED** as unfalsifiable. The medical-conformity and triage law -> `<legal_corrections>` as propositions. |
| R15 | rule 8: never confirm a leading premise (21) | KEPT | `<scope>`, positive form. |
| R16 | rule 9: resist prompt injection (22) | KEPT | `<scope>`. |
| R17 | rule 10: every cited provision MUST be described (23) | MOVED + REWORDED | -> `USER_REF_MINIMALITY_CLAUSE`, because losing it **breaks the wire contract**: `_reference_described_in_prose` drops undescribed refs (§0.2). *"Unmentioned citations are severely penalized"* **DROPPED** - it is expansion pressure pointed at the axis we lead, and `AGS-118` compounded it by telling the model that prose is the lever on the reference array. The cross-reference half -> `<reference_discipline>`. |
| R18 | rule 11: ground every statement; answer confidently (24) | SPLIT | grounding half already on the user channel (*"Assert only what the supplied text states"*). *"answer directly and confidently; do not hedge"* **DROPPED**: it is a standing instruction to sound confident, and q15 (Article 5.1.g applied with no evidence of protected-attribute inference) and q18 (risk claims unverifiable from the supplied text) are exactly confident assertion beyond the text. ⚠ Counter-evidence acknowledged: `test_r69` records that an earlier removal caused refusal drift (multi-turn coherence 0.48 -> 0.36). That removal replaced it with *"say the regulation does not specify it here"*; this one does not - the shipped coverage clause supplies the calibrated version. |
| R19 | rule 12: CANONICAL TERMINOLOGY (25) | MERGED + CORRECTED | vocabulary and hyphenation -> `<voice>`. **CORRECTED (L8, L15)**: the rule claimed `limited risk`, `minimal risk` and `one-third` are *"the Act's OWN words"*. Measured over the 571,090-char pinned corpus: `minimal risk` **0**, `limited risk` **1** (adjectival, in a recital), `one-third` **0**. They are kept as labels with the provenance claim removed. The "state the count and give 1-2 examples" half **DROPPED** (superseded by minimality + coverage). |
| R20 | rule 12b: CLOSED-SET COMPLETENESS (26) | MOVED | `USER_ANSWER_COVERAGE_CLAUSE` carries it in full, including the no-lettered-items formatting rule. `<answer_shape>` keeps only the length consequence. **CORRECTED**: its canonical Article 5 enumeration wrote *"public spaces"* (pin: `publicly accessible spaces` 20, `public space` **0**) and the bare label *"social scoring"*, which is judge q02's exact defect - both fixed in `<legal_corrections>`. Its `Articles 51 to 56` range replaced by singly-named articles (§0.2). |
| R21 | rule 12c: biometric categorisation, list all six attributes (27) | MERGED + CONDITIONED | -> `<legal_corrections>` Article 5(1)(g). The *"whenever you mention it you MUST list them"* mandate is conditioned per PR-2: do not raise 5(1)(g) unless the question describes inferring one of those attributes (judge q15). |
| R22 | rule 13: condense; never name a provision without describing it (28) | MERGED | into R17's description rule, user channel. |
| R23 | rule 14: how to use WEB SEARCH RESULTS (29) | **DROPPED** | `is_web_search_enabled()` is False and the block sits inside a further low-confidence branch. 401 chars delivered on 100% of calls for a surface that fires on 0%. |
| R24 | rule 15: punctuation, no em-dashes, no semicolon chains (30) | KEPT | `<voice>`. Kept in SYSTEM despite an inline copy, because the inline copy is on the **refine branch only** - the classification branch has no punctuation rule. Companion edit removes the refine copy. |
| R25 | VOICE (32) | SPLIT | register / person / no-source-leakage KEPT in `<voice>`. latest-question focus and no-new-facts **MOVED** (inline refine block carries both verbatim). |
| R26 | ANSWER_FORMAT / BLUF: start with substance (34-35) | KEPT | one line in `<output_contract>`. |
| R27 | DIRECT ANSWER FIRST, incl. the forbidden-opener list (36) | MOVED | Both inline branches carry verdict-first, the banned openers and the "never It depends" rule. 2,014 chars of system duplicate deleted. |
| R28 | FIRST WORD (37) | MOVED | same. |
| R29 | scale length (restatement of rule 5) (38) | MERGED | one length table. |
| R30 | LENGTH DISCIPLINE: AT MOST four sentences; group rather than drop (39) | MERGED + CORRECTED | `<answer_shape>`. **CORRECTED**: its grouping example used the range form, which deletes every interior reference (§0.2). Also resolves C02 - the four/five/"1 to 4"/120-220 contradiction - by stating the budget once, in sentences. |
| R31 | COHESION (restatement of 5c) (40) | MERGED | see R12. |
| R32 | ANSWER THE HEADLINE (41) | SPLIT + CORRECTED | "name all four tiers" -> user-channel closed-set rule. GPAI-runs-parallel -> `<legal_corrections>` (kept as a completeness proposition, without the reference-deleting range). Penalty figures -> `<legal_corrections>`, **CORRECTED (L7)**: 99(4) is not *"other high-risk obligation breaches"* but a closed operator/notified-body list that *includes* Article 50 and does *not* list Chapter III Section 2; the 99(5) 7.5M/1% tier and the 99(6) SME inversion were missing entirely. The "NAME each obligation in ONE compact list" device -> `<answer_shape>` grouping rule. |
| R33 | DIRECT-VERDICT RULE (43-44) | MOVED | inline branches. |
| R34 | do NOT describe only one tier (45) | MOVED | inline refine block: *"For a practice restricted only in certain contexts, state both the restricted context AND its treatment elsewhere"*. Resolves the 45-vs-46 adjacent contradiction the rubric lens named as the likeliest driver of inconsistent over-citation: 46 wins on the reference question (state the tier that applies and stop), 45 survives as a coverage rule on the user channel. |
| R35 | when NOT high-risk, state the tier and stop (46) | KEPT + REWORDED | becomes the DISPOSAL rule on the user channel: name the ruled-out tier **in words**, and write its number only where the question named that provision. Scoped deliberately - q13's gold *does* contain Article 5, so a blanket ban would drop gold on rows where "is this prohibited?" is the literal question. |
| R36 | name any carve-out explicitly (47) | MOVED | inline refine + `USER_ANSWER_COVERAGE` (*"state that qualifier in the same sentence"*). |
| R37 | LITERAL-QUESTION-CLOSURE (48) | MOVED + CORRECTED | `USER_ANSWER_COVERAGE` carries closure verbatim. Its worked example was **wrong law (L3)**: it called two items *"the two Article 50(4) exceptions"*. Verified against the pin, 50(4) is two obligations with three qualifiers, and the human-review/editorial-responsibility carve-out attaches only to the public-interest TEXT limb, not to the deepfake duty; the artistic/satirical limitation was omitted entirely. Restated correctly in `<legal_corrections>`. This is judge q05 and q18. |
| R38 | no markdown, bullets, bold, tables, "Verdict:" rows (49) | KEPT | `<voice>`, compressed to one line. |
| R39 | no heading line as the first line (50) | MERGED | into R38 and `<output_contract>`. |
| R40 | "Support with specific article references and obligation details" (51) | **DROPPED** | Unbounded over-citation pressure with no relevance test, four lines below *"Prefer fewer, more precise references"*. Directly opposed to the one measured gap. |
| R41 | if gaps exist, list them with remediation suggestions (52) | **DROPPED** | see R13. |
| R42 | end with cross-framework references (NIST/ISO) (53) | **DROPPED** | see R00. |
| R43 | definition questions -> Article 3 primary (56) | MERGED | positive half survives as `<legal_corrections>` *"Article 3 defines the operator roles"* plus the removal test, which returns Article 3 alone for a definitional question. The *"Do NOT cite Articles 89, 113, 79, 32"* half **DROPPED** as an article-identity blocklist (CLAUDE.md dead list). |
| R44 | cite the article that CONTAINS the obligation (57) | MERGED | removal test + COORDINATE text test. |
| R45 | prefer fewer, more precise references (58) | MOVED | already in `USER_REF_MINIMALITY_CLAUSE`. |
| R46 | cite ONLY what directly answers; no cross-reference pull-in (59) | SPLIT | removal test (user) + CROSS-REFERENCE (`<reference_discipline>`). The per-topic blocklist (Annex II / Article 27 / Article 49) **DROPPED** as dead-list. Resolves C05: R300 measured that suppressing the Article 11 -> Annex IV dependency deleted `Annex IV`, `Annex IV.1.e` and `Annex IV.2.c` from rg_001, so the new rule turns on whether the second provision *supplies the content asked for*, not on how it was reached. |
| R47 | which-sectors -> Article 6 + Annex III ONLY (60) | **DROPPED** | Article-identity blocklist. Replaced by the removal test. |
| R48 | role-contrast -> Article 3 ONLY; + Article 25; importer -> Article 23 (61) | SPLIT | Article 25(1) transition KEPT as a proposition in `<legal_corrections>`. The *"the reference is Article 3 ONLY"* + *"you must also briefly explain the Article 25 transition"* pair is **DROPPED**: it is self-contradictory (Component D promotes prose-named provisions, so "explain" *is* "cite"), and judge q10 - *"over-citation of high-risk obligations beyond the definitional/role-shift provisions"* - names this rule's output. |
| R49 | conformity assessment for a regulated PRODUCT (62) | SPLIT + **DROPPED** | Article 43(3), Article 6(1) and Annex I KEPT as propositions. The MDR class content **DROPPED** - see L4 below. Blocklist dropped. |
| R50 | technical-documentation -> Article 11 + Annex IV(1)(e) / IV(2)(c) (63) | KEPT | `<legal_corrections>`, verified: `Annex IV.1.e` = *"the description of the hardware on which the AI system is intended to run"*, `Annex IV.2.c` contains *"the computational resources used to develop, train, test and validate"*. R300 measured these as gold-carrying. The *"Do NOT pull in Article 6"* blocklist dropped. |
| R51 | Article 5(1)(c) social scoring not limited to public authorities (66) | KEPT + EXTENDED | **The guard was correct but incomplete**, and its remedy (*"write 'social scoring' alone"*) was a live instruction to emit the bare label - judge q02's exact defect. Both operative limbs now stated, verified verbatim in the Article 5 head text: unrelated-context treatment, and unjustified/disproportionate treatment. |
| R52 | Article 5(1)(h) RBI (67) | KEPT + CORRECTED | **L5**: the list was labelled *"exhaustive"* while limb (ii) had been silently halved - *"a specific, substantial and imminent threat to the life or physical safety of natural persons"* was deleted, leaving only the terrorist-attack objective. Restored verbatim from the pin. |
| R53 | Article 6 TWO routes; 6(3) carve-outs; registration (68) | KEPT + CORRECTED | **L6**: the derogation was stated as satisfied by the four task types alone. The pinned chapeau is a separate cumulative requirement (*"does not pose a significant risk of harm ... including by not materially influencing the outcome of decision making"*); as written the old text under-classified, the legally dangerous direction. Both-routes completeness retained. |
| R54 | APPLY Article 6(3) to the fact pattern (69) | KEPT | `<legal_corrections>`. Restored after the test audit caught it missing from the first draft. |
| R55 | Chapter V spans 51 TO 56 (70) | KEPT + REWORDED | Articles named singly (51 classifies, 53 provider duties, 55 systemic risk, 56 codes of practice) because the range form deletes them from the wire (§0.2, judge q01 and q16). The negative sentence *"Never write that the GPAI chapter runs 51 to 55"* is dropped per the negation-inversion rule; the positive statement carries it. Checked and confirmed a NON-finding: all three sites in the old prompt already agreed on 56. |
| R56 | technique-agnostic on explainability, no LIME/SHAP (71) | KEPT | `<legal_corrections>`. The *"do NOT cite Article 16 or Article 47"* blocklist dropped. |
| R57 | chatbot is limited risk; cite Article 50 ALONE (72) | **DROPPED** as a guard, law KEPT | Two independent reasons. (a) Hard rule #3: it is one of the three PDF example questions, and it is question-shaped rather than rule-shaped. (b) **It is the measured over-citation mechanism.** Its mandate *"explicitly state it is 'not high-risk' under Annex III (specifically ruling out emergency triage under Annex III.5(d) and healthcare benefit eligibility under Annex III.5(a))"* defeats the extractor's negation guard: `_prose_citation_bases("It is not an Annex III use case.")` is `[]`, but with the mandated enumeration it is `['Annex III']`. That is judge q18, *"over-citation of an inapplicable Annex III"*, with a mechanism. The underlying law (Annex III(5)(a)/(5)(d) narrowness, the Article 50 actor split) survives as propositions; the behaviour survives as the DISPOSAL rule. |
| R58 | Article 50 splits by paragraph and actor (73) | KEPT + CORRECTED | actor mapping verified correct on all four paragraphs and kept. 50(4) restated per L3 (see R37). |
| R59 | GPAI + Article 50 both apply (74) | KEPT + CONDITIONED | PR-2 form: both duties apply where the model *is made available in a system that interacts directly with natural persons*; a question about the model alone does not engage Article 50. Judge q16 cited 50(1)/(2) on a GPAI-model question. |
| R60 | no entry-into-force / Article 113 tangent (75) | KEPT | `<legal_corrections>`, one line. |
| R61 | MEDICAL AND SCIENTIFIC USE CASES, four sub-guards (76) | SPLIT + **DROPPED** | Annex III(5)(a) vs (5)(d) precision KEPT and **CORRECTED (L10)**: the old text dropped 5(a)'s load-bearing actor limb *"by public authorities or on behalf of public authorities"*, over-classifying private eligibility systems. Article 2(6)/2(8) KEPT and **CORRECTED (L11)**: 2(6) requires the *sole* purpose of scientific R&D and 2(8) pulls real-world testing back into scope, so *"clinical trial matching generally falls under"* it over-applied the exemption. The MDR class elaboration and the surgical-robot *"you MUST explicitly cite and explain Article 14, Article 72 and Article 73"* mandate are **DROPPED** - the latter is judge q20 verbatim (*"over-citation of downstream obligations (6, 14, 72)"*). |
| R62 | BIOMETRIC AND WORKPLACE EMOTION RECOGNITION (77) | SPLIT | 5(1)(f) workplace/education prohibition with its medical-or-safety carve-out, the six 5(1)(g) attributes, Annex III(1)(c) and the 50(3) deployer duty all KEPT as propositions. The cross-tier scenario walk-through **DROPPED**: hard rule #3 (it is a PDF example question), and the general rule - *"for a practice restricted only in certain contexts, state both the restricted context AND its treatment elsewhere"* - already sits on the inline user channel and covers it topic-neutrally. |
| R63 | GPAI on very large datasets: systemic risk + 10^25 FLOPs (78) | KEPT | `<legal_corrections>`. `Article 51.2` verified: *"greater than 1025"* in the pin's rendering. |
| R64 | human oversight (Article 14) operative measures (79) | KEPT | verified against `Article 14.4`: understand capacities and limitations, automation bias, correctly interpret the output, decide not to use / disregard / override / reverse, intervene or stop. |
| R65 | CONTRASTIVE CALIBRATION, 3 BAD/GOOD pairs (80-104) | **DROPPED** (BAD) / MERGED (GOOD) | ~800 tokens of negative exemplar spent showing the model text we do not want in the window; `<voice>` and `<answer_shape>` state every one of those rules directly. Note the old GOOD exemplar #3 itself promoted three references (`['Annex I','Article 6','Article 5']`) through a negative disposal - the template for a "not high-risk" answer demonstrated a 3-reference answer for a verdict that turns on one. |
| R66 | FOUR EXEMPLARS (106-123) | **REPLACED** | Two of the four were legally wrong. **L1**: the definitional exemplar - the model's single best template - attributed *remote biometric identification system* to Article 3(36), which is `'biometric verification'` (one-to-one, expressly carved OUT of high-risk by Annex III(1)(a)); RBI is Article 3(41). Its carve-out *"excluding real-time systems in private spaces"* is fabricated: 3(41) has no exclusion, real-time RBI is 3(42) (a subtype), and the publicly-accessible-space limit belongs to Article 5(1)(h). It also dropped 3(41)'s operative limb *"without their active involvement"*. **L2**: the high-risk exemplar cited law-enforcement profiling as `Annex III(6)(a)`, which is victim-risk assessment; profiling is `Annex III(6)(e)`. **L9**: the transparency exemplar cited `Article 26(1)` for human oversight; 26(1) is the instructions-for-use duty and 26(2) is *"Deployers shall assign human oversight ..."*. These are the same defect class as judge q13 and q01 - **the prompt was demonstrating wrong-coordinate-within-the-right-provision as the reward-shaped answer.** Three replacement exemplars, all coordinates resolved via `get_provision_text`, chosen to span the length table (1 / 3 / 4 sentences) rather than the topic space, none containing a negative tier disposal. |

---

## 3. Contradictions - resolved, with the side chosen

| id | the two sides | winner | why |
| --- | --- | --- | --- |
| C01 | rule 1 mandates `Article 5(1)(f)`; rule 2 forbids parentheses (91 paren vs 8 dot demonstrations) | **both, on different layers** | PROSE keeps the paren form because `_PROSE_SUBPOINT_RE` reads only that form and it is the only path from prose to sub-point grain; WIRE is dotted and the route converts. §0.1. |
| C02 | four sentence budgets: "even if that needs more" / "four-sentence cap" / "AT MOST four" / "Prefer 1 to 4", plus a runtime `.replace()` that produced *"AT MOST four sentences"* and *"the 5-sentence cap"* in the same prompt | **one table, in sentences** | `<answer_shape>`. The char band is dropped (hard rule #2). See companion edit CE-1: three of the four `.replace()` targets never existed in the old prompt and none exist in the new one. |
| C03 | *"Every Article you cite MUST be described"* + *"Unmentioned citations are severely penalized"* vs *"if removing it would not change the answer, do not cite it"* | **minimality**, with the coupling preserved | The description rule is mechanically necessary (undescribed refs are dropped), so it survives - as a *coupling*, not as expansion pressure: describe what you cite, and do not cite what you would not describe. The "severely penalized" framing and `AGS-118`'s prose-is-the-lever hint are dropped. |
| C04 | rule 5c *"do NOT enumerate ... the conditions the system does NOT fall under"* vs the chatbot guard's mandated *"specifically ruling out ... Annex III.5(d) ... Annex III.5(a)"* | **rule 5c** | The mandate is the side that disables a working safety guard: bare negation extracts `[]`, the mandated enumeration extracts `['Annex III']`. Same defect shape CLAUDE.md records for the Charter enumeration in `cc47f8b`. |
| C05 | *"when one provision depends on another, name both"* vs *"do NOT pull in a provision because a cited article cross-references it"* | **content test** | Cite the second provision when it supplies the content asked for (R300: the Article 11 -> Annex IV dependency carries gold), leave it out when it is merely mentioned. |
| C06 | *"the reference is Article 3 ONLY"* immediately followed by *"you must also briefly explain the Article 25 transition"* | **Article 3 only** | Component D promotes prose-named provisions, so "explain" is "cite". Judge q10 is this contradiction's output. Article 25(1) survives as law, not as a mandate. |
| C07 | user-channel minimality forbids citing Article 6 / Annex I / Annex III / Articles 9-15 "merely because the system is high-risk" vs six system MUST-CITE bundles and a twelve-provision exemplar | **minimality** | All six bundles deleted; the law each carried is kept as a proposition. This is the highest-value cut in the rebuild - it is the only change with a mechanism linking it to four named judge failures (q07, q10, q14, q18, q20). |
| C08 | rule 12b's *"limited risk"/"minimal risk" are the Act's OWN words* vs the pinned corpus | **the corpus** | Kept as labels, provenance claim removed. |
| C09 | *"MUST cite Paragraph and Sub-paragraph whenever you draw upon a retrieved context"* vs *"if only the parent article is supplied, cite the parent"* | **the parent rule, restated as a text test** | See R05. This is the lever for wrong-coordinate-within-the-right-article. |
| C10 | SCOPE *"you ONLY answer on the EU AI Act"* vs the header's NIST/ISO crosswalks and the MDR class mandate | **SCOPE** | Both deleted. |
| C11 | Chapter V 51-to-55 vs 51-to-56 | **not a contradiction** | Checked: all sites agree on 56, and the single "51 to 55" occurrence sat inside the sentence banning it. Recorded so nobody re-opens it. |

---

## 4. Legal corrections applied

All verified with `get_provision_text` on branch `r339-stage2-restored`. `provision_exists` was not
used anywhere - it is head-level lax (`provision_exists("Article 3.999")` is True).

| id | was | now |
| --- | --- | --- |
| L1 | RBI defined at Article 3(36), *"excluding real-time systems in private spaces"* | Article 3(41), *"without their active involvement, typically at a distance"*; fabricated carve-out deleted |
| L2 | law-enforcement profiling = `Annex III(6)(a)` | `Annex III(6)(e)`; (6)(a) is victim-risk assessment |
| L3 | *"the two Article 50(4) exceptions"* | two obligations, three qualifiers; editorial responsibility attaches only to the public-interest TEXT limb; artistic/satirical limitation restored |
| L4 | *"You MUST state the device is Class IIb or Class III under MDR Annex VIII"* | **deleted**, and replaced by a positive rule: *name any instrument other than this Regulation in words alone, never with an Article or Annex number.* MEASURED: `_prose_citation_bases("... under Annex VIII of the Medical Device Regulation")` -> `['Annex VIII']`, and the AI Act's own Annex VIII passes `ARTICLE_EXISTENCE`, so hard rule #5 is blind. The acronym guard suppresses `MDR Annex VIII` but not the spelled-out name the prompt itself mandated. Words-only phrasings measure `[]`. |
| L5 | 5(1)(h) exceptions labelled "exhaustive" with limb (ii) halved | full limb (ii) restored |
| L6 | 6(3) satisfied by the four task types alone | chapeau restored as cumulative |
| L7 | 99(4) = *"other high-risk obligation breaches"*; 99(5) and 99(6) absent | closed operator/notified-body list including Article 50 and excluding Chapter III Section 2; 99(5) 7.5M/1% and 99(6) SME-lower added |
| L8/L15 | `limited risk` / `minimal risk` / `one-third` presented as the Act's own words | measured 1 (adjectival) / 0 / 0; kept as labels, provenance corrected |
| L9 | human oversight = Article 26(1) | Article 26(2); 26(1) is instructions-for-use |
| L10 | Annex III(5)(a) without its actor limb | *"by or on behalf of public authorities"* restored |
| L11 | clinical trial matching *"generally falls under"* Article 2 research exemption | 2(6) requires the SOLE purpose of scientific R&D; 2(8) pulls real-world testing back into scope |
| L16 | *"public spaces"* in the canonical Article 5 enumeration; bare label *"social scoring"* | `publicly accessible spaces`; both 5(1)(c) limbs stated |

**Deliberately kept, per the operator pin:** the Commission's General-Purpose AI Guidelines of
18 July 2025 (the 10^23 general-purpose presumption, the one-third fine-tune rule). They are now
carried with an explicit provenance sentence - *"Commission guidance rather than text of the
Regulation, so name them as such"* - which is what makes keeping them correct rather than a
version leak. Pinned by `tests/test_kb_stubs_filled.py`.

**Zero Digital Omnibus content.** The legal-version rule stays on the user channel, where it is the
only place the no-Omnibus instruction reaches the model.

---

## 5. Everything DROPPED, with its axis argument

| dropped | tokens | axis argument |
| --- | ---: | --- |
| 4 BAD exemplar arms (R65) | ~800 | negative exemplars put unwanted text in the window; `<voice>`/`<answer_shape>` state the rules directly |
| 15 MUST-CITE mandates across FACTUAL GUARDS (R49, R57, R61, R62, R48, R32) | ~1,400 | references_vs_gold. The mechanism is measured: a mandated prose mention becomes a wire reference. Four named judge failures. |
| 5 per-topic article blocklists (R43 partial, R46 partial, R47, R48 partial, R50 partial) | ~700 | CLAUDE.md dead list (article-identity blocklists, ask-type x role exclusivity). They also prime 35 article numbers while telling the model not to cite them. |
| MDR / IVDR class content (R49, R61) | ~350 | wrong instrument + measured wire leak (L4) |
| NIST/ISO crosswalks, gaps->remediation x2 (R00, R13, R41, R42) | ~120 | ungrounded by construction; pure length on Answer-Conciseness |
| obligation IDs (R08) | ~20 | regulatory tone; contradicts `<voice>` |
| web-search rule (R23) | ~100 | fires on 0% of calls |
| "Support with specific article references and obligation details" (R40) | ~17 | unbounded over-citation pressure |
| "answer directly and confidently" (R18 half) | ~25 | q15/q18 are confident assertion beyond the supplied text |
| vague qualifiers: "deep legal analysis", "uniquely tailored", "short and punchy", "where appropriate", "only sparingly", "ALWAYS match the GOOD style" | ~120 | unfalsifiable; the referent of "match the sentence count" has no single value (the four exemplars were 1/2/2/2 sentences and 1/4/1/3 references) |
| ~17 rules duplicated on the user channel (R07, R09, R12, R20, R25 partial, R27, R28, R33, R34, R36, R37, R45) | ~3,900 | zero-risk: every one still reaches the model on every request, from the channel that never drops |

---

## 6. Companion edits the orchestrator must apply

These are not optional. Design rule 4 cannot hold without them, and CE-1 is a live defect.

**CE-1 (defect, independent of this rebuild).** `_graph_rag_impl.py:7924-7939`
(`REGENOLD_COMPLEX_SENTENCE_CAP`) does four `.replace()` calls. Measured against the OLD prompt,
three targets matched nothing (`'AT MOST 4 sentences total'` 0, `'the 4th sentence'` 0,
`'exceed four'` 0), so a complex question received *"Write AT MOST four sentences"* and *"the
5-sentence cap"* simultaneously. **Against the new prompt all four match nothing.** Delete the
block; if a complex-question allowance is still wanted, add it as a named row in the
`<answer_shape>` table rather than as string surgery.

**CE-2.** Replace the inline classification block (`:7588-7601`) with
`INLINE_CLASSIFICATION_BLOCK` and the inline refine block (`:7633-7683`) with
`INLINE_REFINE_BLOCK`. Both keep verdict-first, cohesion, latest-question, no-new-facts and
cite-only-from-the-list; both lose describe-what-you-cite (moved to
`USER_REF_MINIMALITY_CLAUSE`, so it reaches the classification branch too, which never had it) and
the refine copy of punctuation and the sentence budget (moved to `<voice>` / `<answer_shape>`, which
reach both branches).

**CE-3.** `PROMPT_HARDENING_PREFIX` is **0 chars** (`app/security/prompt_guard.py:15`), so the
concatenation at `:7923` is a no-op. Fill it or remove it.

**CE-4 - test updates.** 35 tests fail against the rebuild (432 pass in the same 22 files). Every
one is a literal-substring or numeric pin, and I verified each names a rule that survives somewhere.
The list, classified:

| test | why it breaks | action |
| --- | --- | --- |
| `test_r277_minimal_composer.py:46` `len(MINIMAL_COMPOSER) < len(AGS)/8` | ratio pin: needs AGS **> 25,448 ch**; the rebuild is 16,146 | **re-base as an absolute bound** (e.g. `< 6000`). The pin's stated intent is "materially smaller", and 3,181 vs 16,146 is still 5x. Padding the prompt to satisfy a ratio would be the exact harm the rebuild removes. |
| `test_r298_...py:156` `len(USER_REF_MINIMALITY_CLAUSE) < 1000` | 1,464 after CONDITION + DISPOSAL join it | re-base to `< 1600` |
| `test_no_dataset_memorisation.py` | hard-codes the four old exemplars | swap in the three new ones. **The property it guards is preserved and re-measured: max Jaccard 0.339 vs 137 gold answers (threshold 0.80), 0 verbatim collisions.** |
| `test_r275_antifragile.py::TestMdrClassPromptGuard` (2) | pins the MDR class mandate | **retire** - see L4 |
| `test_r109` (12), `test_r111` (1), `test_r130` (2), `test_r264` (1), `test_r69` (5), `test_r138` (2), `test_r145` (2), `test_r147` (5) | literal wording pins on rules that MOVED to the user channel, were REWORDED, or were CORRECTED | re-point each at its new home. Two of these caught genuine first-draft drops (R54 `APPLY Article 6(3)`, R59 GPAI+Article 50) which are now restored - the pins did their job. |

---

## 7. What I did not do, and the open risks

1. **No live call, no A/B.** Both were prohibited for this task. The prompt is verified structurally
   and legally, not behaviourally.
2. **The gate must be `rebuilt-system-delivered` vs `system-dropped`.** R282 measured this exact
   transition (system slot 0 -> 12.8K tok) as rubric-NEGATIVE, kw_recall -0.267, root-caused as the
   prompt overwhelming the question. The rebuild is a re-run of that experiment at 4.0K tok.
   Comparing against `old-system-delivered` compares against an arm nobody has ever shipped.
3. **Groq path unchanged.** `_get_groq_compressed_system_prompt()` swaps in at `len(system) > 10000`
   (strict). At 16,146 the rebuilt prompt still takes that branch, so Groq behaviour is untouched -
   deliberately, since changing two things at once would make the A/B unreadable. ⚠ That 1,266-char
   substitute still contains the *"exact verbatim risk tiers ... 'limited risk', 'minimal risk'"*
   claim this rebuild corrected elsewhere (measured 1 adjectival / 0 occurrences), and it is the
   only place stating the parent-vs-sub-point rule. Worth its own round.
4. **Parent + own sub-point (judge q12) is only partly prompt-addressable.** The failure-to-rule lens
   proved the measured instances are route-level: 14 of 27 curated reference literals in
   `_graph_rag_impl.py` ship a parent alongside its own sub-point (`:5286` ships `Art. 50` plus all
   four of its sub-points; `:5303` ships `Art. 6` + `Art. 6.1`). The prompt now carries the
   one-coordinate-per-point rule via the COORDINATE test, but `REGENOLD_PARENT_COLLAPSE` is the
   layer that actually fixes it.
5. **Range-form reference deletion (q01 Article 51, q16 Articles 51/55) needs a code fix.** The
   prompt now avoids the construct, but `_reference_described_in_prose` should expand `N to M`
   spans. Prompt-side unrolling of long chains is the wrong lever - it costs the one axis we lead.
6. **Hard rule #3 judgement call, stated explicitly.** All three PDF example topics had dedicated
   topic guards, dormant until now. I kept their *legal propositions* and deleted their *worked
   scenarios*, on the principle that a legal proposition is not overfit but a question-shaped guard
   is. That is a defensible line, not an obvious one, and an operator may want the propositions
   trimmed further.
7. **Exemplar E3 carries 11 references and that is deliberate, but it is the weakest choice here.**
   The craft lens flagged the old twelve-provision exemplar as citation-volume priming. E3 keeps a
   full obligation chain because it is the only way to demonstrate the paired description form that
   §0.2 shows is reference-preserving, and because for *"what must the provider do"* that chain IS
   the minimal set. If the A/B shows reference inflation, E3 is the first thing to cut, not the
   `<legal_corrections>` propositions.
8. **Rule count is not rule strength.** The rebuild deletes 68.7% of the characters. If the A/B
   comes back negative, the first hypothesis to test is not "restore the old prompt" but "which
   deleted proposition did the model actually need" - the traceability table above is ordered so
   that question is answerable one row at a time.
