# SQL Agent Toolkit

This repo contains AI agent definitions for reviewing, comparing, and optimizing SQL code across database engines. Built for a department of data engineers.

## Current Engine Support

- **Amazon Redshift** (16-node ra3.16xlarge, 256 slices) — fully supported
- **MySQL, Postgres** — planned

## Severity Definitions

All agents use the same severity scale regardless of database engine:

- **CRITICAL:** Will cause incorrect results, data loss, severe performance degradation (10x+ slower), or transaction safety issues. Must be fixed before deployment.
- **WARNING:** Causes meaningful performance degradation (2-10x slower), violates team standards, or creates maintenance burden. Should be fixed before deployment.
- **INFO:** Minor optimization opportunities, style suggestions, or best practice recommendations. Fix at engineer's discretion.

## Agent Routing

When a user asks to review, optimize, or compare SQL, **always delegate to the appropriate specialized agent** using the Agent tool. Never handle these tasks directly in the main conversation — the agents have access to engine-specific skills, templates, and phased workflows that the main conversation does not.

| User request | Agent to invoke |
|---|---|
| Review, audit, check, validate SQL | `sql-reviewer` |
| Optimize, speed up, fix performance | `sql-optimizer` |
| Compare two SQL versions, diff, check changes | `sql-comparator` |
| Validate a review/optimization/comparison report | `sql-review-validator` |

Pass the file path(s) and any user context (intent, constraints, specific concerns) to the agent. The agent will handle metadata gathering, EXPLAIN generation, analysis, and report writing autonomously.

### Two-Layer Validation Workflow

Every SQL review, optimization, and comparison report goes through two layers of validation before being delivered to the user.

**Layer 1 — Self-validation (built into each agent):**
After analysis but before writing the report, the originating agent re-examines every CRITICAL and WARNING finding against the full query context. This catches false positives from block-by-block analysis that missed join context, distribution collocation, or logic-breaking rewrites. See PHASE 2.5 (reviewer), PHASE 3.5 (optimizer), or PHASE 4.5 (comparator) in each agent's definition.

**Layer 2 — Independent validation (separate agent):**
After the originating agent writes its report, the main conversation automatically invokes the `sql-review-validator` agent. The validator receives the report file path, the SQL file path, and any metadata previously provided. It challenges every finding from a fresh perspective, writes a `_validation.md` report, and applies corrections to the original report.

**Orchestration sequence:**

1. User requests review/optimization/comparison
2. Main conversation invokes the originating agent (`sql-reviewer`, `sql-optimizer`, or `sql-comparator`)
3. Originating agent completes PHASE 0 (metadata gathering — STOP and WAIT for user input)
4. User provides metadata
5. Originating agent completes analysis phases **including self-validation (Layer 1)** — self-validation modifies findings in-place with no visible trace in the report
6. Originating agent writes report to disk — the report reads as a single authoritative analysis with no revision history
7. Originating agent returns to main conversation
8. **Main conversation automatically invokes `sql-review-validator`** with the report path, SQL path, and metadata reference
9. Validator **edits the original report in place** — adjusting severities, incorporating mitigating factors naturally into findings, removing false positives entirely (no "Excluded" section), and adding missing findings. **No "Validation Summary" section is appended. No annotations like "(adjusted per validation: ...)" are added. The report must read as a single-pass analysis with no revision history visible.**
10. Validator returns to main conversation with a verbal summary (counts of confirmed/adjusted/removed findings)
11. Main conversation informs the user: report path and the validator's summary (N findings confirmed, M adjusted, K removed) — this meta-information appears only in chat, never in the report file

**Skipping validation:** If the user explicitly requests skipping validation (e.g., "quick review, skip validation"), the main conversation may skip steps 8-10 and note this in the response.

**Relaying agent output:** Agents run in a sub-context whose output is not directly visible to the user. When an agent produces SQL that the user must run (metadata harvester queries, EXPLAIN statements, diagnostic queries, validation scripts), the main conversation **must include that SQL in full** in its response to the user as copy-paste-ready code blocks. Never summarize, abbreviate, or omit runnable SQL — the user needs to copy it directly into their database client. The structural scan (table of contents) and any clarifying questions from the agent must also be relayed in full. When the validator agent completes, relay its verbal summary (confirmed/adjusted/removed counts) to the user. The validator edits the original report in place with no visible trace — there is only one clean report file on disk, with no validation annotations, excluded-findings sections, or appended summaries.

## Universal Behavioral Rules

These rules apply to all agents across all engines:

1. **Always ask for metadata first — and WAIT for results.** Never review SQL without understanding the table design. Use the metadata harvester template from the engine-specific skill's reference files. Render it fully — fill in actual schema-qualified object names from the SQL file under review into the template's designated placeholders. **List every object referenced — tables, views, and materialized views alike. Do not pre-resolve views to base tables; the harvester does this automatically when the engine supports it.** **Never write ad-hoc metadata queries as a substitute for the harvester template.** After the rendered harvester, also provide **ready-to-run EXPLAIN statements** — one per standalone SELECT and one per extracted SELECT from each DML statement (INSERT...SELECT, UPDATE...FROM, DELETE...USING). EXPLAIN the query as written (with view references intact) — most engines expand views automatically. Follow engine-specific EXPLAIN rules from the loaded skill. **Do not generate EXPLAIN statements for queries that reference temporary tables created earlier in the same script.** These temp tables will not exist when the user tries to run the EXPLAIN, causing errors. Instead, note which queries were skipped and why (e.g., "EXPLAIN skipped — depends on temp table created at line N"). Do not render the SQL block even with prerequisite instructions — only provide EXPLAIN SQL that the user can paste and run directly. After rendering both the harvester and the EXPLAIN statements **in full in the chat response as code blocks**, STOP and wait for the user to provide the results before proceeding to analysis. Do NOT proceed with `[NEEDS METADATA]` placeholders. If the user explicitly asks you to proceed without metadata, you may do so, but warn them that findings may be inaccurate.

   **Reading the harvester output (don't substitute Grep for a full pass).** Harvester results can run hundreds of lines / tens of thousands of tokens — larger than a single Read call. After the user provides the results:
   - **Read every section sequentially**, paginating with offset/limit until the entire file is covered. Do not skip sections.
   - **Do NOT use Grep as the initial sweep.** Grep returns only matching lines and silently hides everything else. If you grep for `DISTKEY` and `skew_rows`, you miss every row whose attribute name isn't in your pattern — including the very red-flag rows the engine skill cares about. Grep is the wrong tool for "tell me what's in this file."
   - **Use Grep only for targeted lookup AFTER the initial full pass** — confirming a specific column's type, finding a constraint by name, etc.
   - **Build a one-paragraph internal summary** before starting analysis, covering: which objects are in scope and their kinds, resolution paths for views, the storage attributes for each physical table (engine-specific), and every CRITICAL/WARNING item from the harvester's red-flag sections. This summary is for your own working memory — it does not go in the report. If you cannot produce it, you have not finished reading.

   **View handling (engine-agnostic principle).** When the harvester output contains views or materialized views, the agent must:
   - Identify which inputs are views vs physical tables, and which derived base tables were resolved by the harvester (the engine skill specifies how this is surfaced — section names, result-set layout, late-binding flags).
   - Read view definitions (DDL text) to build a mental view-column → base-column map. **All storage-related checks (distribution/partition collocation, sort-key / index utilization, encoding, skew) must be applied at the base-table level, not the view level** — a view has no physical storage to check directly. Engine skills define which storage attributes apply.
   - When the engine cannot resolve every view automatically (engine-specific limitations vary), follow the engine skill's documented follow-up flow before proceeding to analysis.
   - If any input is reported as not found, stop and ask the user to verify spelling, schema, or permissions before proceeding.

   The engine-specific skill's metadata-harvester reference is the source of truth for *how* this metadata is surfaced (section names, result-set count, follow-up syntax). The agent's job is to consume it correctly, not to know the engine's catalog internals.
2. **Always provide rewrites.** Never just flag an issue — always show the corrected SQL.
3. **Always provide line references.** Every finding must reference approximate line numbers in the source file.
4. **Always explain the diagnostic query AND what it reveals.** When asking the user to run a query, explain why and what the result tells you.
5. **Provide copy-paste-ready SQL.** Never leave placeholders like `<table>` — fill in actual names from the file under review.
6. **For large files (> 500 lines), use chunked analysis.** See the Large File Handling Protocol below.
7. **When in doubt, ask.** If something is ambiguous, ask the engineer rather than guessing.
8. **Respect the user's stated intent.** "Refactor" vs "intentional change" vs "not sure" dramatically affects how findings are classified.
9. **Write all output to a Markdown file on disk.** Never output the final report to chat/stdout. Use the Write tool to create the report as a `.md` file in the same directory as the SQL file under review. Naming convention: `{sql_filename}_review.md` (code reviews), `{sql_filename}_optimization.md` (optimizer), or `{v2_filename}_comparison.md` (version comparisons). After creating the file, post a brief confirmation message in chat with the file path — do NOT reproduce the report contents in chat. After the report is written, the main conversation will invoke the `sql-review-validator` agent for independent validation — see the Two-Layer Validation Workflow above. **Note:** This rule applies only to the final analysis report. Pre-analysis SQL that the user needs to run (metadata harvester, EXPLAIN statements, diagnostic queries) must always be rendered in full in chat — see rule 1 and the Agent Routing relay guidance above.
10. **No fabricated diagnostics.** Every diagnostic claim — EXPLAIN operator, cost number, row estimate, distribution label, runtime measurement, I/O figure — must come from the input the user provided (harvester output, EXPLAIN plan they pasted, runtime data they shared). **Never invent plan operators, costs, or measurements that were not in the input.** When stating a fact, name the source: "From EXPLAIN plan", "From metadata", "From static analysis of the SQL". When tempted to fabricate (because a finding feels stronger with a number, or the user expects detail), prefer "I don't have that data — recommend running EXPLAIN ANALYZE / the engine's diagnostic feature" over invention. Static inferences from the SQL text are fine; inventing detailed plans with numeric costs is not.
11. **Static analysis is mandatory when EXPLAIN coverage is partial or absent.** If the user provided EXPLAIN for some statements but not others (common cause: queries depend on temp tables created earlier), do not skip the uncovered statements. Analyze them via static analysis using the engine skill's pattern catalog and the harvested metadata. State explicitly which statements were analyzed via EXPLAIN versus static analysis.

## Large File Handling Protocol

SQL files in this environment can be **1,000-5,000+ lines**. All agents must handle them reliably:

1. **First pass — Structural scan:** Read the entire file and produce a table of contents listing every logical block (CREATE statements, COPY commands, INSERT...SELECT blocks, CTEs, transaction boundaries, comments/section markers). Number each block with line ranges.
2. **Second pass — Block-by-block analysis:** Process each logical block sequentially. For each block, produce findings tagged with severity and line numbers. Only flag items that are actually violated — do not repeat the full checklist for every block.
3. **Third pass — Cross-block analysis:** After all blocks are reviewed, analyze cross-cutting concerns: transaction boundaries, table reuse patterns, dependency order, naming consistency across the entire script.
4. **Final output — Consolidated summary:** Produce one unified report with all findings organized by severity, including line number references. This is the deliverable the engineer acts on.

**Never skip sections of a large file.** The structural scan ensures every block is accounted for. If the file is too large for a single context pass, explicitly tell the user which sections you have analyzed and which remain, then continue.
