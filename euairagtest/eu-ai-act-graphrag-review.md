# EU AI Act GraphRAG — Deep-Dive Review, Divergences & Fixes

**Date:** 2026-07-23
**Scope:** initial architecture (`eu-ai-act-graphrag-plan.md`) vs. current implementation
(`eu-ai-act-graphrag/` package + `eu-ai-act-benchmark/`).
**Method:** parallel adversarial review + skeptical verification — every candidate
finding was actively probed against the real corpus/tests to *disprove* it before
acting. Findings are labelled CONFIRMED / REFUTED / `[unverified]`.
**Live evaluation:** **not run** — per your instruction, benchmark evals are handled
separately. No CLI/API calls were made.

---

## 1. Ground-truth counts (verified by probe, not asserted from the plan)

| Fact | Plan said | Verified actual | Source |
|---|---|---|---|
| Edge types | 18 | **16** (6 deterministic + 10 enrichment; disjoint, exhaustive) | `schema.py`, test-enforced |
| Node types | 14 | **14** | `schema.py` |
| Benchmark items | 84 | **84** (42 easy + 42 hard) | `eu_ai_act_bench_*.json` |
| Distinct gold provision_ids | 136 | **137** | benchmark JSON |
| Total gold_citation entries | — | **237** | benchmark JSON |
| Gold ids reachable as graph nodes | 136/136 | **137/137** | `data/graph.json` |
| Gold ids present as corpus rows | 132/136 | **133/137** (4 annex-root exceptions) | `data/provisions.json` |
| `data/graph.json` size | 1,397 / 5,941 | **1,387 / 5,899** | `data/graph.json` |
| Article node span | Art. 1–114 | **Art. 1–113** (over-range refs now dropped) | `data/graph.json` |
| Package tests | 482 | **594** pass (+34 scorer) | `pytest` |

The plan's `eu-ai-act-graphrag-plan.md` §Phase-1/§Phase-2 status blocks were updated
to these verified numbers, and the stale "spurious `Art. 261`/`Art. 290`" nit was
marked resolved (the builder's `≤113` range guard drops them).

---

## 2. CONFIRMED issues — fixed

### 2.1 External-instrument regex blind to issuer-prefixed forms `[CONFIRMED, latent]`
**Files:** `src/euaiact/graph/citations.py`, `src/euaiact/baselines/extract.py`

The `EXTERNAL_QUALIFIER_RE` only matched an instrument keyword sitting *immediately*
after the article number. Issuer-prefixed instruments slipped through:

- `"Article 9 of Council Directive 2016/680"` → mis-extracted as internal `art_9`
- `"Article 5 of Commission Implementing Regulation (EU) 2019/1234"` → internal `art_5`

Because `art_9`/`art_5` are ≤113 they pass the builder's range check and would create
**phantom `CROSS_REFERENCES_INTERNAL` edges** to the wrong provision.

**Reachability (skeptical check):** ran the current extractor over all **1,318**
corpus provisions → **0** phantom edges. The Act's own text uses *plain* phrasing
("Article 10 of Directive (EU) 2016/…", "Article 30 of Regulation (EU) 2019/…"),
which the old regex already handled; the 5 "Council Directive"/"Commission Regulation"
mentions are standalone repeals in recitals/annexes, never in `Article N of …` position.
**So corpus impact today is zero.** The fix is defensive hardening + it *does* matter on
the LLM-prose path (`extract.py`), where model output phrasing is not controlled.

**Fix:** added an optional issuer prefix (`Council|Commission|European Parliament|
Framework|Implementing|Delegated`, 0–3 tokens) *before* the instrument keyword, and
added `Regulation No`/`Decision No`/`Treaty`. A terminal instrument keyword is still
**required**, so bare "of the Commission guidelines" stays internal (no new
false-positives). `extract.py`'s look-ahead window widened 24→48 chars to fit multi-word
prefixes. Verified against all pre-existing external/internal tests + new cases.

**Tests added:** `test_graph.py` (Council Directive, Commission Implementing Regulation,
issuer-word-without-instrument) and `test_baselines.py` (issuer-prefixed not laundered
into an internal cite; issuer-word-without-instrument stays internal).

### 2.2 `Provision` citation/eli_uri could disagree with its own id `[CONFIRMED, latent]`
**File:** `src/euaiact/models.py`

The model documents "`provision_id` is the single source of truth … a row can never
disagree with its own ID," and derives every structural field unconditionally — **except**
`citation` and `eli_uri`, which used `self.x = self.x or pid.x`. A hand-set wrong value
(e.g. `citation="Art. 999(9)"`) survived.

**Fix:** derive `citation`/`eli_uri` unconditionally, matching every other derived field.
`parent_id` keeps its `is None` guard (an explicit parent override is treated as
intentional — conservative).

**Safety (skeptical check):** grepped all of `src/` + `tests/` — **nothing** constructs a
`Provision` with a custom `citation=`/`eli_uri=`, and JSON round-trips through
`model_validate` reproduce identical values. New `tests/test_models.py` (7 tests) pins
this, including the overwrite regression.

### 2.3 Scorer `_truncate` collapsed sub-grain citations to root `[CONFIRMED, real]`
**File:** `eu-ai-act-benchmark/scorer.py`

`_truncate(pid, grain)` fell back to `depth = 1` (root) when a gold citation had no
segment of the target grain. A paragraph-level gold under `--oracle point` was truncated
to the *article*, making the finer `point` oracle score **below** the coarser `para`
oracle — a non-monotone diagnostic.

**Proof (disprove-check):** with the buggy branch, oracle soft-F1 = root 0.417,
para 0.833, **point 0.750**, full 1.0 — point < para. With the fix (`depth =
len(pid.segments)`, i.e. keep as-is), the order is monotone.

**Fix:** `else: depth = len(pid.segments)`. `tests/test_scorer.py` gains a `Truncate`
unit class + an `OracleMonotonicity` test that fails on the old code and passes on the new.

### 2.4 Enrichment LLM tier diverged from plan §10 `[CONFIRMED divergence — declarative]`
**File:** `src/euaiact/graph/enrich.py`

`EnrichmentConfig.llm_tier` defaulted to `"sonnet"`; plan §10 assigns KG extraction to the
correctness-compounding **Opus** tier. Deontic extraction builds KG nodes/edges, so it
belongs on Opus.

**Honest caveat:** the field is **currently unread** (only its definition exists anywhere
in `src`/`tests`), so this is a *declarative* alignment with **zero runtime effect** on the
benchmark or any live path. If the author intended a two-stage "Sonnet-extract + Opus-audit"
design (the original inline comment hinted at it), this one-liner is trivially reversible.

**Fix:** `llm_tier: str = "opus"` + comment citing plan §10.

### 2.5 Silent no-op CRAG verification `[CONFIRMED, minor UX]`
**File:** `src/euaiact/baselines/cli.py`

`--verify {lexical,nli}` with the default `--verify-keep 0 --verify-abstain 0` drops/abstains
nothing — a silent no-op that looks like verification ran.

**Fix:** emit a `stderr` warning when `--verify != none` but both thresholds are 0. No
behavior change; the underlying pass-through was already intentional.

---

## 3. REFUTED / investigated-and-left-unchanged (skeptical pass)

These *looked* like bugs but the "obvious fix" was wrong or unsafe. Left unchanged, by design.

- **`ingest/points.py` roman sub-point heuristic (`points.py:81`)** — REFUTED as CRITICAL.
  The proposed guard (`(i)` is a sub-point only when the previous letter is `h`) would
  **drop legitimate roman sub-points** under other letters (e.g. `(b): (i)…(ii)…`). The
  existing "(i) is a sub-point iff (ii) follows, attach to the last letter" heuristic is
  defensible. **No change.**
- **`extract.py` `_ARTICLE_RE` drops space-separated "Art. 5 (1) (a)"** — REFUTED as unsafe
  to fix. Widening the group to `[^)]+` would slurp parenthetical asides like
  "(see Article 6)" into the citation. **No change.**
- **`enrich.py apply_deontic_extractions` per-provision counter reset + unguarded
  `GROUNDED_IN`** — real only under *incremental* multi-call usage; the normal single-call
  pipeline is correct, and the "obvious" fix breaks the idempotency test. It's an optional,
  currently-unwired ML layer. **Documented, no change.**
- **`ingest/points.py split_annex_item` drops `_subs`** — `[unverified]` whether any annex
  has 3-level nesting in the real corpus. **Documented, no change.**
- **`ingest/loader.py`** `_TAG_MAP` gaps (`chp`/`sec`), no row-dedup, non-numeric passthrough
  in `_articles_to_eids` — defensive/speculative; the real corpus doesn't trigger them.
  **No change.**
- **`baselines/verify.py CragThresholds(0,0)`** — documented no-op; addressed via the
  `cli.py` warning (2.5) rather than changing a default that would alter behavior.

---

## 4. `[unverified]` / deferred

- **`llm.py DEFAULT_MODEL = "claude-opus-4-8"`** — the exact frontier model id is
  `[unverified]` (no primary source to confirm the string). It is `--model`-overridable and
  the eval is deferred, so it does not affect anything now.
- **`enrich.py llm_tier="opus"`** — declarative only; behavior when the enrichment models are
  eventually wired is `[unverified]`.
- **Live CLI/API evaluation** — not run (your call to handle separately). To wire your
  "other way" cleanly, `FrontierLLMBaseline` already supports dependency injection: pass a
  custom `client=` (any object with `.messages.create(...)`) or override the
  `_make_client` staticmethod — no need to touch the baseline logic. A subprocess-backed
  `claude`-CLI client was **not** built, because it could not be verified against the real
  CLI in this environment (sandbox blocks `~/.claude.json`), and shipping an untested shim
  would violate the "don't assert what you can't verify" bar.

---

## 5. Verification

- `eu-ai-act-graphrag`: **594 passed** (`pytest -q`).
- `eu-ai-act-benchmark`: **34 passed** (`pytest test_scorer.py`).
- Every fix ships with a regression test; the scorer and models fixes were additionally
  proven to *fail* on the pre-fix code.
- No live model calls; no changes to `eu-ai-act-benchmark/_strata/*.json`.

## 6. Files changed

| File | Change |
|---|---|
| `src/euaiact/graph/citations.py` | issuer-prefix hardening of `_EXTERNAL_QUALIFIER_RE` |
| `src/euaiact/baselines/extract.py` | same hardening + `Treaty`, window 24→48 |
| `src/euaiact/models.py` | authoritative `citation`/`eli_uri` derivation |
| `src/euaiact/graph/enrich.py` | `llm_tier` `sonnet`→`opus` (plan §10) |
| `src/euaiact/baselines/cli.py` | no-op `--verify` stderr warning |
| `eu-ai-act-benchmark/scorer.py` | `_truncate` keep-as-is else-branch |
| `tests/test_models.py` | **new** — Provision source-of-truth tests |
| `tests/test_graph.py`, `tests/test_baselines.py` | issuer-prefixed external tests |
| `eu-ai-act-benchmark/test_scorer.py` | `Truncate` + `OracleMonotonicity` tests |
| `eu-ai-act-graphrag-plan.md` | reconciled stale counts (§1) |
