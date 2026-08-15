# R346 — Live Bedrock A/B readiness: provider-following paraphrase transport + harness checkpointing/pacing

Status: **blocked on a valid Bedrock ABSK key** — everything else is shipped and proven.

## 1. The transport fix (query expansion no longer rides the tunnel)

`app/engines/query_expansion.py` hard-routed its Haiku 4.5 paraphrase call through
the Claude-Max wrapper (`get_openai_wrapper_provider()`). Under
`P2P_GRAPH_RAG_PROVIDER=bedrock` that would still send every expanded request
through the cloudflared tunnel — the transport the operator keeps exclusively
for the live re-evaluation — and mix providers mid-A/B.

**R346**: the paraphrase transport now follows the active Stage-2 provider:

* `P2P_GRAPH_RAG_PROVIDER=bedrock` + Bedrock credentials present → Bedrock's own
  Sonnet 4.6 via `complete_with_fallback`, with a separate timeout budget
  (`REGENOLD_QUERY_EXPANSION_BEDROCK_TIMEOUT`, default 8 s — Bedrock carries
  cold-start latency the local wrapper does not, and a 2 s budget would fail
  every paraphrase and read as an inert lever).
* Every other provider keeps the historical wrapper path, byte-identical.

**R346.2 — no Haiku on the live path.** The paraphrase model is the frontier
4.6 tier: `claude-sonnet-4-6` by default (the judge tier — a paraphrase is a
light task, Opus buys nothing), pinned up with
`REGENOLD_QUERY_EXPANSION_MODEL=claude-opus-4-6` for the generation tier.
The intent-classifier fallback default also moved off Haiku to
`claude-sonnet-4-6` (the live Stage-0 uses Groq per R94 regardless). The
model env is registered in `_engine_cache_key` (R334 drift guard green).

Gate-off (`REGENOLD_QUERY_EXPANSION=0`) is byte-identical by construction.
The timeout env var is registered in `_engine_cache_key` (the R334 drift guard
caught it on the first full-suite run — fixed, guard green).

## 2. Harness checkpointing + pacing

`evals/harness/dynamic_ab.py`:

* **Batch-level checkpoints** — the sidecar (`evals/bench/results/dynamic-ab-<label>.json`)
  is now written after EVERY batch, so a live run (tens of minutes per arm)
  survives a crash with the rows it completed. The final write overwrites the
  checkpoint with the complete state.
* **`--min-call-gap`** — minimum seconds between POSTs. The Cohere rerank A/B
  must run against a **Trial key (10 calls/min)**: without pacing every rerank
  429s, fails soft, and the A/B reports INERT for a working feature. `6.5` is
  the floor for 10/min.

## 3. Live verification done (checkpoint 0 + smoke)

* **R340 rerank fires against the real Cohere API**: `rerank_stats()` →
  `attempts=1, reordered=1, failed=0`; the cross-encoder moved
  `Art. 73` ahead of `Art. 72` on a provider-obligations question. Deterministic
  across calls.
* **Harness mechanics**: `provider=cli` smoke (6 rows) proved transport, fire
  check, the R336 probe-sensitivity control (moved 4/6 rows), the honest INERT
  verdict, and checkpoint sidecar writes. Sidecar:
  `evals/bench/results/dynamic-ab-r346-smoke-cli.json`.

## 4. THE BLOCKER — Bedrock credentials are dead on this machine

Both ABSK keys available (main `.env`, modified today 18:01, and the sibling
repo's `.env`) fail **authentication**, not entitlement:

```
ListFoundationModels -> AccessDeniedException:
  Authentication failed: Please make sure your API Key is valid.
```

`check_connectivity_and_permissions` → `api_access_denied_403` for **all nine**
Claude tiers (opus-5 / opus-4-8 / opus-4-7 / opus-4-6 / opus-4-5 / sonnet-5 /
sonnet-4-6 / sonnet-4-5 / haiku-4-5). The R328.2-documented invocable tiers
(opus-4-6-v1 / sonnet-4-6) are 403 today. This matches the documented doctrine:
"a Bedrock API key carries an IAM policy fixed at creation, and granting model
access afterwards does not widen an existing key — re-mint the key."

Also degraded on this machine: Groq (TPM limit reached, 429), Gemini
("prepayment credits depleted", 429), Cohere (Trial key, 10 calls/min).

**Remediation (operator-side, no code change needed):** re-mint the
`AWS_BEARER_TOKEN_BEDROCK` ABSK key with access to the EU inference profiles
(`eu.anthropic.claude-opus-4-6-v1`, `eu.anthropic.claude-sonnet-4-6`,
`eu.anthropic.claude-haiku-4-5-20251001-v1:0`), then run the three commands
below. The code pins (`REGENOLD_BEDROCK_* = claude-opus-4-6`) resume the
requested tier with zero code change.

## 5. Resume — the three live A/Bs (one command each, in order)

All runs load the operator `.env` and force the Bedrock-only overrides
(`provider=bedrock`, wrapper fallback OFF, embedded graph, local dense
embeddings). The launcher prefix below is self-contained — the env block is
repeated in each command. Serialize the runs — never two live runs at once.

```bash
# The launcher prefix (valid ABSK key exported/loaded from the operator .env):
#   python -c "from dotenv import load_dotenv; load_dotenv('<your .env>', override=False)"
# then force:
#   P2P_GRAPH_RAG_PROVIDER=bedrock
#   REGENOLD_BEDROCK_WRAPPER_FALLBACK=0
#   REGENOLD_GRAPH_BACKEND=embedded
#   REGENOLD_EXTERNAL_EMBEDDINGS=0
#   REGENOLD_BEDROCK_MODEL=claude-opus-4-6
#   REGENOLD_BEDROCK_STAGE2_MODEL=claude-opus-4-6
#   REGENOLD_BEDROCK_COMPLEX_MODEL=claude-opus-4-6

# A/B 1 — Cohere rerank (branch ON vs OFF). Pacing floors the Trial key.
py -3.12 -c "
import os
from dotenv import load_dotenv
load_dotenv(r'<your .env>', override=False)
os.environ.update({'P2P_GRAPH_RAG_PROVIDER':'bedrock',
    'REGENOLD_BEDROCK_WRAPPER_FALLBACK':'0',
    'REGENOLD_GRAPH_BACKEND':'embedded',
    'REGENOLD_EXTERNAL_EMBEDDINGS':'0',
    'REGENOLD_BEDROCK_MODEL':'claude-opus-4-6',
    'REGENOLD_BEDROCK_STAGE2_MODEL':'claude-opus-4-6',
    'REGENOLD_BEDROCK_COMPLEX_MODEL':'claude-opus-4-6'})
import sys
sys.argv=['dynamic_ab','--flag','REGENOLD_COHERE_RERANK',
          '--label','r346-live-rerank','--max-rows','60','--batch','12',
          '--min-call-gap','6.5']
import runpy
runpy.run_module('evals.harness.dynamic_ab', run_name='__main__')
"

# A/B 2 — multi-query expansion (branch ON vs OFF): same env block,
#   sys.argv=['dynamic_ab','--flag','REGENOLD_QUERY_EXPANSION',
#             '--label','r346-live-expansion','--max-rows','60','--batch','12']

# A/B 3 — V1-vs-V2 prompt (baseline = V2 default ON; branch = V1): same env
#   block, sys.argv=['dynamic_ab','--branch-env','REGENOLD_PROMPT_V2=0',
#             '--label','r346-live-v1-vs-v2','--max-rows','60','--batch','12']
```

Fire checks, probe sensitivity, the gold_dropped veto, and per-arm latency
(the sidecar records `latency_ms` per row) are all asserted/reported by the
harness; each run writes its checkpoint sidecar to `evals/bench/results/`.

## 6. RESULTS — three live A/Bs, 2026-08-15 (60 rows, Bedrock Opus 4.6 Stage-2)

All runs on the re-minted ABSK key, `P2P_GRAPH_RAG_PROVIDER=bedrock`,
`REGENOLD_BEDROCK_* = claude-opus-4-6`, wrapper fallback OFF, embedded graph.
0 errors in every arm. Sidecars: `evals/bench/results/dynamic-ab-r346-*.json`.

### A/B 1 — REGENOLD_COHERE_RERANK (ON vs OFF), paced 6.5 s

| axis | baseline | branch | delta | 95% CI | verdict |
|---|---|---|---|---|---|
| ref_loose | 0.8278 | 0.8194 | −0.0083 | [−0.0667, +0.0417] | UNDERPOWERED |
| ref_strict | 0.6706 | 0.6646 | −0.0060 | [−0.0515, +0.0463] | UNDERPOWERED |
| ref_conc | 0.5215 | 0.5384 | +0.0168 | [−0.0470, +0.0808] | UNDERPOWERED |
| kw_recall | 0.8787 | 0.8682 | −0.0106 | [−0.0511, +0.0278] | UNDERPOWERED |
| gold_dropped_head | 17 | 17 | **+0** | — | no veto |

FIRED 49/60 rows (refs 31, answers 49). Latency: 10.4 → 11.4 s mean
(+1.0 s ≈ +10%, the Cohere round-trip), p50 10.0 → 11.1 s.

The lever provably moves rows but this 60-row probe cannot resolve whether
that movement helps; deltas are inside noise. ref_conc is the only positive.

### A/B 2 — REGENOLD_QUERY_EXPANSION (ON vs OFF)

| axis | baseline | branch | delta | 95% CI | verdict |
|---|---|---|---|---|---|
| ref_loose | 0.8278 | 0.8667 | +0.0389 | [−0.0083, +0.0944] | UNDERPOWERED |
| ref_strict | 0.6273 | 0.6265 | −0.0008 | [−0.0325, +0.0292] | UNDERPOWERED |
| ref_conc | 0.4576 | 0.4328 | −0.0248 | [−0.0678, +0.0125] | UNDERPOWERED |
| kw_recall | 0.7860 | 0.8151 | +0.0292 | [−0.0069, +0.0681] | UNDERPOWERED |
| gold_dropped_head | 17 | 14 | **−3** | — | no veto (branch BETTER) |

FIRED 37/60 rows (refs 25, answers 37). Latency flat: 11.1 → 10.4 s mean.

Directionally the strongest arm: ref_loose +0.039 and kw_recall +0.029 with
their CIs mostly above zero, and the branch DROPS FEWER gold refs (−3).
Exactly what the paraphrase-recall lever was built for; needs more rows to
resolve. The Bedrock paraphrase transport (R346) held up with zero failures
(this run predates R346.2 — it used the Haiku paraphrase tier; a re-run on
the frontier Sonnet 4.6 tier is the follow-up measurement).

### A/B 3 — REGENOLD_PROMPT_V2=0 (V1 branch) vs V2 default

| axis | baseline(V2) | branch(V1) | delta | 95% CI | verdict |
|---|---|---|---|---|---|
| ref_loose | 0.8528 | 0.8444 | −0.0083 | [−0.0583, +0.0500] | UNDERPOWERED |
| ref_strict | 0.5806 | 0.5660 | −0.0146 | [−0.0491, +0.0153] | UNDERPOWERED |
| ref_conc | 0.3657 | 0.3503 | −0.0154 | [−0.0554, +0.0171] | UNDERPOWERED |
| kw_recall | 0.6852 | 0.6866 | +0.0014 | [−0.0500, +0.0569] | UNDERPOWERED |
| gold_dropped_head | 15 | 16 | **+1** | — | **HARD RULE #8 VETO** |

FIRED 13/60 rows (refs 12, answers 13). Latency: 5.7 → 5.0 s mean (V1 is
faster — 51.5 K vs 16.1 K char prompt).

REJECTED: the V1 branch drops a gold reference. Per hard rule #8 the veto
is decisive regardless of the other axes — V2 stays the live default, which
confirms the R340 prompt-rebuild decision with a live measurement.

### Reading the three together

* All three levers FIRED (13–49 changed rows) — none inert, none blind.
* No axis reached a resolved verdict on 60 rows; every CI spans zero
  (UNDERPOWERED). The retrieval levers need more rows (or a harder probe
  subset) to resolve; the veto grain is the only decisive signal at this n.
* The only veto fired against V1 — the V2 default is safe to keep.
* Expansion is the arm worth more rows: positive direction on the recall
  axes and it reduced gold drops, at flat latency.
* Every arm ran at 0 HTTP errors — the Bedrock path (Opus 4.6 Stage-2,
  Haiku paraphrase, Cohere rerank) is healthy end-to-end.
