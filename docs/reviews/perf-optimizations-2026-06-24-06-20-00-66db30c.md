# Deep Code Review: perf-optimizations

**Date:** 2026-06-24 06:20:00
**Branch:** perf-optimizations -> main
**Commit:** 66db30c
**Files changed:** 4 | **Lines changed:** +60 / -18
**Diff size category:** Medium

## Executive Summary

The initial `perf-optimizations` branch introduced several significant regressions in logic, data shape integrity, and intent classification while resolving the metric failures. A parallel multi-agent review successfully identified unsafe string substring matching, broken regex boundaries, undirected graph traversals leading to hub-article explosions, and orphaned code. I have verified these findings and implemented fixes for all critical issues locally.

## Critical Issues

### [C1] Substring Matching Causes Incorrect Reference Prioritization
- **File:** `app/engines/graph_rag.py:2392`
- **Bug:** The `_sort_key` function used a simple substring check (`s in low`) for prioritizing references. Because `"art. 3"` was used as a key, it inadvertently matched `"Art. 30"`, `"Art. 39"`, etc. `"annex i"` incorrectly matched `"Annex II"` and `"Annex III"`.
- **Impact:** Scrambled the order of obligations retrieved and crowded out intended high-priority references, disrupting context.
- **Suggested fix:** Used exact matching and prefix checking with parentheses/colons/spaces.
- **Confidence:** High
- **Found by:** Logic & Correctness, Error Handling & Edge Cases

### [C2] Intent Detection Silent Misclassification via Substrings
- **File:** `app/engines/graph_rag.py:1413`
- **Bug:** Intent keywords lacked word boundaries (`w in q_lower`). `"gap"` matched `"Singapore"`, `"iso"` matched `"poisoning"`, and `"need"` matched before `"need to"`.
- **Impact:** Misclassified valid user queries containing overlapping substrings into incorrect intents (`gap_analysis`, `cross_framework`), yielding broken answers.
- **Suggested fix:** Replaced substring matching with word-boundary `re.search()` matching.
- **Confidence:** High
- **Found by:** Error Handling & Edge Cases

### [C3] Undirected Graph Traversal Explosion
- **File:** `app/data/graph_rag_prompts.py:212`
- **Bug:** Cypher template used an undirected relationship (`-(b:Article)`).
- **Impact:** Fetched obligations in both directions, pulling in massive obligation chains for hub articles like Art. 16, destroying precision and overflowing context.
- **Suggested fix:** Made traversal directed (`->(b:Article)`).
- **Confidence:** High
- **Found by:** Contract & Integration

### [C4] Unsafe Generic Trigger Breaking Definitional Safeguards
- **File:** `app/engines/graph_rag.py:1520`
- **Bug:** Inserted an unconditional generic trigger `what is a` / `what is an` for definition lookups.
- **Impact:** Rendered `role_definitional_term` protections useless by blindly capturing almost any query shape (e.g. "what is an importer's..."), injecting Art. 3 incorrectly.
- **Suggested fix:** Removed the new generic trigger block.
- **Confidence:** High
- **Found by:** Contract & Integration

### [C5] Code vs Comment Drift (Hub Article Explosion)
- **File:** `app/engines/graph_rag.py:3399`
- **Bug:** `cross_refs` function limit bumped to `10` directly violating adjacent block comment warning about hub-article explosion limit of 2.
- **Impact:** Cascades into massive context bloat during fallback KB retrieval.
- **Suggested fix:** Reverted to `limit=2`.
- **Confidence:** High
- **Found by:** Contract & Integration

### [C6] Non-Deterministic Order in Cypher Template
- **File:** `app/data/graph_rag_prompts.py:210`
- **Bug:** Used `RETURN DISTINCT` without an explicit `ORDER BY`.
- **Impact:** Non-deterministic result ordering breaks LLM semantic caching and creates unstable retrieval outputs.
- **Suggested fix:** Added `ORDER BY o.article_ref, o.paragraph_ref, o.id`.
- **Confidence:** High
- **Found by:** Concurrency & State

## Important Issues

### [I1] Dead / Orphaned Code Let After Early Return
- **File:** `app/routes/regenold.py:2600`
- **Bug:** Inserted an unconditional `return references` but left 7 lines of complex post-processing code below it untouched.
- **Impact:** Incomplete refactoring. If the early return is ever removed, code crashes via `NameError: name 'described' is not defined`.
- **Suggested fix:** Deleted the dead code block entirely.
- **Confidence:** High
- **Found by:** Logic & Correctness, Contract & Integration

### [I2] Medical Device Acronym Regex Lacks Boundaries
- **File:** `app/engines/_graph_rag_data.py:1100`
- **Bug:** Acronyms like `mri`, `ecg`, `ivd` lack `\b` boundaries in `annex_i_safety_component` regex.
- **Impact:** Erroneous classification when substrings exist in larger words (e.g., "smriti" matching "mri").
- **Suggested fix:** Added `\b` boundaries to the group.
- **Confidence:** High
- **Found by:** Error Handling & Edge Cases

## Suggestions
- None

## Review Metadata

- **Agents dispatched:** Logic & Correctness, Error Handling & Edge Cases, Contract & Integration, Concurrency & State, Security
- **Scope:** Diff of perf-optimizations + surrounding functions
- **Raw findings:** 8
- **Verified findings:** 8
- **Filtered out:** 0
- **Steering files consulted:** CR-SKILL.md
- **Plan/design docs consulted:** none found
