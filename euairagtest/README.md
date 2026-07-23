# SQL Agent Toolkit

AI agents for reviewing, comparing, and optimizing SQL code. Built for Claude with engine-specific skills. Currently supports Amazon Redshift; MySQL and Postgres planned.

---

## Business Value

- Reduces time spent on manual code reviews of complex, large-scale SQL scripts
- Catches performance issues and coding standard violations before they reach production
- Frees up senior engineers to focus on higher-value work instead of line-by-line reviews

---

## AI Tech / Tools Used

- **AI Model:** Anthropic Claude Opus 4.5
- **What we built:** 3 specialized AI agents:
  - **SQL Reviewer** — checks code quality and standards compliance
  - **SQL Optimizer** — identifies and fixes performance bottlenecks
  - **SQL Comparator** — validates changes between script versions
- **Built for:** Amazon Redshift (our core data warehouse). The engine-agnostic agent architecture is designed to be extensible to other SQL engines (MySQL, Postgres, and others) in the future.

---

## How It Looks, How It Works

1. Engineer submits a SQL script for review
2. The agent reads the script and generates a metadata harvester query that gathers table design information from the database — **the engineer executes this script against the database and provides the results back to the agent**
3. It analyzes the code block by block — flagging issues, explaining why they matter, and providing corrected SQL
4. A second agent independently validates every finding to ensure accuracy
5. Engineer receives a structured report with prioritized findings and ready-to-use fixes

---

## Agents

| Agent | Purpose |
|---|---|
| `sql-reviewer` | Reviews SQL for performance, correctness, and team standard compliance |
| `sql-comparator` | Compares two SQL versions, detects semantic differences and regressions |
| `sql-optimizer` | Analyzes slow queries with EXPLAIN plans and suggests optimizations |
| `sql-review-validator` | Independent validation of review/optimization/comparison reports — challenges findings for false positives, overstated severities, and unsafe rewrites |

Agents are engine-agnostic. Engine-specific knowledge is loaded via skills at runtime.

---

## Repository Structure

```
sql-agents/
├── CLAUDE.md                                    # Agent routing, severity definitions, behavioral rules
├── .claude/
│   ├── agents/
│   │   ├── sql-reviewer.md                      # Code review agent
│   │   ├── sql-comparator.md                    # Version comparison agent
│   │   ├── sql-optimizer.md                     # Query optimization agent
│   │   └── sql-review-validator.md              # Independent report validation agent
│   └── skills/
│       ├── redshift-conventions/
│       │   ├── SKILL.md                         # Cluster specs, permissions, design standards
│       │   └── references/
│       │       ├── metadata-harvester.md        # Metadata collection template
│       │       ├── design-and-internals.md      # Encoding, distribution, sort key reference
│       │       └── team-data-model-standards.md # Naming, layers, auditing columns
│       └── redshift-review-checklist/
│           └── SKILL.md                         # Structured review checklist (DDL, DML, COPY, ETL)
├── README.md
└── prompt-examples.md                           # Invocation templates
```

### Architecture

- **Engine-agnostic agents** — agents contain no engine-specific logic. They load skills based on the SQL dialect detected.
- **Skills as knowledge packs** — each engine gets a conventions skill (cluster specs, standards, metadata harvester) and a review checklist skill. Adding a new engine means adding new skills, not new agents.
- **CLAUDE.md as router** — defines which agent handles which request, universal behavioral rules, severity scale, and the large file protocol.
- **Reports written to disk** — agents write final output as Markdown files alongside the SQL under review, not to chat.

### Two-Layer Validation

Every report goes through two layers of validation before delivery:

1. **Self-validation (Layer 1)** — The originating agent re-examines every CRITICAL and WARNING finding against the full query context before writing the report. Catches false positives from block-by-block analysis.
2. **Independent validation (Layer 2)** — After the report is written, a separate `sql-review-validator` agent challenges every finding from a fresh perspective, adjusts severities, and edits the original report in place.

See [`CLAUDE.md`](CLAUDE.md) for the full orchestration sequence.

---

## Quick Start

Ask Claude to review, compare, or optimize a SQL file. CLAUDE.md routes to the correct agent automatically.

```
review load_bet_selection.sql — production ETL, runs daily
```

```
compare load_bet_selection_v2.sql with load_bet_selection.sql — refactor, same output expected
```

```
this query takes 45 minutes, target is under 5 — here's the EXPLAIN plan
```

Each agent will generate a metadata harvester query, wait for results, then deliver findings with rewrites.

---

## Extending to a New Engine

1. Create `skills/{engine}-conventions/SKILL.md` with cluster specs, permissions, diagnostic templates, and team standards
2. Create `skills/{engine}-review-checklist/SKILL.md` with the engine-specific checklist
3. Add reference files under `skills/{engine}-conventions/references/`

No changes needed to agents or CLAUDE.md — skill triggers handle routing.

---

## Constraints

- **READ-ONLY access** — agents never suggest running write operations directly; DDL/VACUUM/ANALYZE are framed as recommendations for the pipeline owner.
- **Large file support** — files up to 5,000+ lines handled via chunked analysis (structural scan → block-by-block → cross-cutting → consolidated report).
- **Current cluster** — 16-node ra3.16xlarge, 256 slices. COPY file counts should be multiples of 256.

---

## See Also

- [`prompt-examples.md`](prompt-examples.md) — Invocation templates
- [`CLAUDE.md`](CLAUDE.md) — Routing rules and behavioral constraints
