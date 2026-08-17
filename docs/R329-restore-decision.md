# R329 restore — evidence-based decision (2026-08-17)

**Question:** keep the R329 CITABLE PROVISIONS Stage-2 block + P3b clauses restored
after R364.5 (b07afa4) deleted them, or revert?

**Decision: KEEP the restore.** The deletion was an undocumented silent rider on an
unrelated commit; the restore is byte-faithful and fully test-validated.

---

## Evidence — the deletion was accidental, not deliberate

1. **Commit message silent.** `b07afa4` ("R364.5 — surgical-strip query-expansion
   guard + bedrock model fix + cache-key completeness (#54)") lists query expansion,
   the bedrock model fix, cache-key registration, tests and docs. It never mentions
   the R329 citable-universe block or the P3b clauses. It is the exact
   "undisclosed rider" pattern R300 caught with the wrapper model alias.
2. **Decision doc silent.** `docs/R364-5-guard-relaxation-decision.md` is entirely
   about the retrieval-surface strip for query expansion. No Stage-2 prompt surgery
   is documented.
3. **Rider scale.** b07afa4 changed **1,605 lines** in `_graph_rag_impl.py` (2,584
   insertions across 10 files) — a commit about query expansion carrying a massive
   Stage-2 prompt deletion.
4. **Contradicts the documented contract.** CLAUDE.md:1058 documents
   `REGENOLD_CITABLE_UNIVERSE_BLOCK` as **ON** (R329 P3a — "emits an explicit
   `CITABLE PROVISIONS:` list and repoints the citation instruction at it").
5. **Broke a green, pinned contract.** R329 test files were green at R361
   (82916f9) and red from R364.5 (b07afa4). Four rounds (R365→R369) re-labelled
   the failures "pre-existing" — true against each round's own parent, false
   against the last green commit (`docs/R369-fixes.md:148`).
6. **Keyed-but-dead trap.** Both flags stayed registered in `_engine_cache_key`
   (regenold.py:1750-1751) after the deletion — an A/B of the feature would fire
   its trigger check and print an axis table for a feature that no longer exists
   (the R350-documented trap).
7. **The deletion fought the R369 goals.** The R369 root-cause analysis named
   prose-driven citation over-emission as ref_corr's biggest lever (~35 rows). The
   citable-universe block is precisely the mechanism that constrains Stage-2
   citations to the retrieved whitelist. Its absence in R364.5→R369 is consistent
   with the low ref precision measured in the live runs.

## Evidence — the restore is faithful

8. `_citable_universe_enabled` / `_citable_universe_refs` / `_citable_universe_block`
   + constants + regexes are **byte-identical** to `b07afa4~1` (extracted and
   compared programmatically).
9. Call-site logic (emission + `_cite_scope_phrase` antecedent for both branches)
   identical to pre-deletion.
10. P3b clauses restored: `USER_REF_UNCERTAINTY_CLAUSE` emission
    (`REGENOLD_REF_UNCERTAINTY`), `user_answer_coverage_clause()` V1/V2 selector,
    `user_ref_minimality_clause()` V1/V2 selector.
11. **131 tests pass** across the 4 R329 test files, including the byte-identity
    guards ("on-minus-addition reconstructs the off prompt exactly").
12. Defaults: `REGENOLD_CITABLE_UNIVERSE_BLOCK` default ON; both flags live in the
    cache key again.

## Separate issues — NOT evidence against the restore

13. **R328/R342/R344 (14 failures)** were already failing at R361 — an OLDER
    regression, not caused by b07afa4, not fixed by the R329 restore (verified by
    checking out the R361 tests: same 14 failures). Separate track.
14. Remaining HEAD failures (bedrock-fallback wiring, intent pruning,
    r115/r130/r133/r268/r274 wire-pinning, regenold integration) are the
    collapse/promote granularity-contract conflicts + dead Bedrock credentials.
    Separate track.

## Verification commands

- `git show b07afa4 --format=... --no-patch` — commit message (silent on R329)
- `git show b07afa4 --stat` — 1,605-line `_graph_rag_impl.py` rider
- Function fidelity: extract-and-compare vs `b07afa4~1` → identical
- `py -3.12 -m pytest tests/test_r329_*.py` → 131 passed
- R361 checkout of R328/R342/R344 tests → same 14 failures (pre-existing, older)
