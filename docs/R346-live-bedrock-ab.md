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
  Haiku 4.5 (`eu.anthropic.claude-haiku-4-5-20251001-v1:0`) via
  `complete_with_fallback`, with a separate timeout budget
  (`REGENOLD_QUERY_EXPANSION_BEDROCK_TIMEOUT`, default 8 s — Bedrock carries
  cold-start latency the local wrapper does not, and a 2 s budget would fail
  every paraphrase and read as an inert lever).
* Every other provider keeps the historical wrapper path, byte-identical.

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
