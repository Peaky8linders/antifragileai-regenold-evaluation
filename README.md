# Regenold EU AI Act RAG — Partner Transparency Bundle

> Grounded EU AI Act Q&A — extracted as a standalone Python package so partners can audit, reproduce, and run the same retrieval + scope + reference-formatting logic that powers the Regenold competition entry under `legit-ai`.

---

## Why this repo exists

The Regenold partner integration in the parent CodexAI / `legit-ai` codebase has grown a substantial purpose-built surface — a scope filter, a reference parser/formatter, a multi-turn coreference engine, an EU AI Act existence catalog (113 articles + 13 annexes), an answer-normalisation pipeline, a Graph-RAG retrieval engine, and a categorised eval harness.

For transparency with the Regenold review team this slice has been lifted into a **standalone, self-contained repo** with:

- The full `app/integrations/regenold/` module (auth, models, scope, route).
- The Graph RAG engine that backs it (`app/engines/graph_rag.py`) with its prompts (`app/data/graph_rag_prompts.py`).
- The EU AI Act surface catalog (`app/data/article_existence.py`) + a minimal KB stub so the engine's KB-fallback path resolves cleanly.
- The full eval harness under `evals/regenold/` with 25 baseline scenarios + 200 expanded scenarios (100 multi-conversation + 100 tricky/misleading).
- Snapshot eval results from the rounds run inside `legit-ai` (`evals/regenold_results_round*.json`).
- The integration + partner-facing docs from `docs/partners/regenold/`.

What was deliberately **stubbed** rather than copied:

- The full audit-chain (`app/evidence/store.py`) — replaced with a no-op recorder. The wire shape of audit entries is preserved; nothing is persisted to disk.
- Neo4j graph client (`app/graph/client.py`) — replaced with a disabled stub so the engine takes the KB-fallback path. Restoring Neo4j is a one-file swap.
- The Mistral provider (`app/llm/mistral_provider.py`) — replaced with a thin shape-only adapter. To run the engine with a real LLM, plug in your own Anthropic / Mistral key via `app/config.py::GraphRAGSettings` or `MISTRAL_API_KEY` env var.
- The 24-dimension Knowledge Base — only `KB_VERSION` + a minimal 4-dimension stub is shipped. The full KB lives in CodexAI's product KB and is not regulator-defensible by itself.

## Origin

Extracted from `legit-ai` (`Peaky8linders/legit-ai`) — the CodexAI EU AI Act Path-to-Production compliance platform — at version **1.2.132** (2026-05-10).

Module structure mirrors the parent repo 1:1 so the file paths in `CLAUDE.md` verification entries still resolve here.

## Two follow-up engineering fixes shipped in this repo

After the extraction, two concrete fixes were applied on top of the parent-repo snapshot:

1. **`app/integrations/regenold/scope.py::_live_question_borrows_anchor`** — extended `follow_markers` with `"are these"`, `"how often"`, and `"what if we re-train"`. Closes 3 multi-conversation eval refusals where a short follow-up that mentioned a concrete data/process question was previously being rejected as "no anchor".

2. **`app/engines/graph_rag.py::_llm_parse_query`** — robust JSON cleanup. The original markdown-fence stripper only handled the case where the entire response was wrapped in ```` ```json ... ``` ````. The new helper tolerates prose-before-JSON, prose-after-JSON, multiple fences, language tags after backticks, and the `{...}`-block extraction fallback. Closes 2 simple-question reference-misses where Claude Sonnet 4.6 returned markdown-fenced JSON with explanatory prose.

Both fixes carry regression tests under `tests/test_regenold_followup_fixes.py`.

## Layout

```
regenold-eu-ai-act-rag/
├── app/
│   ├── config.py                  # Minimal settings: Regenold + GraphRAG + Mistral.
│   ├── main.py                    # FastAPI app mounting just /regenold/eu-ai-act/ask.
│   ├── models.py                  # GraphRAGRequest / Response / CitationNode + risk enum.
│   ├── rate_limit.py              # slowapi limiter (per-tier buckets).
│   ├── data/
│   │   ├── article_existence.py   # 113 articles + 13 annexes catalog.
│   │   ├── graph_rag_prompts.py   # QUERY_PARSE_SYSTEM + ANSWER_GENERATE_SYSTEM + Cypher templates.
│   │   └── kb.py                  # KB_VERSION + 4-dimension stub.
│   ├── engines/
│   │   └── graph_rag.py           # Two-stage RAG: parse → retrieve → generate.
│   ├── evidence/
│   │   ├── models.py              # EvidenceEntryType.regenold_question.
│   │   └── store.py               # NO-OP recorder (in-memory).
│   ├── graph/
│   │   └── client.py              # Disabled stub (forces KB fallback).
│   ├── integrations/regenold/
│   │   ├── __init__.py
│   │   ├── auth.py                # X-Regenold-Api-Key dep (optional + required variants).
│   │   ├── models.py              # RegenoldAskRequest / Response, reference parser, answer normaliser.
│   │   ├── scope.py               # Conversation scope classifier + refusal copy.
│   │   └── mcp_stub.py            # Reference MCP-tool envelope (not enabled).
│   ├── llm/
│   │   ├── __init__.py            # resolve_provider helper.
│   │   └── mistral_provider.py    # Stub shape-only adapter.
│   ├── routes/
│   │   └── regenold.py            # POST /regenold/eu-ai-act/ask.
│   └── security/
│       └── prompt_guard.py        # sanitize_for_llm + validate_llm_output (minimal).
├── evals/
│   ├── __init__.py
│   ├── regenold/
│   │   ├── __init__.py
│   │   ├── scenarios.py           # 25 baseline + 200 expanded (multi-turn + tricky/misleading).
│   │   └── runner.py              # TestClient-driven harness with Regenold-rubric metrics.
│   └── regenold_results_*.json    # Snapshots from rounds run under legit-ai.
├── tests/
│   ├── test_regenold_integration.py
│   ├── test_regenold_scope.py
│   └── test_regenold_followup_fixes.py   # Regression guards for the 2 fixes shipped here.
├── docs/partners/regenold/
│   ├── INTEGRATION.md             # Wire contract + auth + telemetry.
│   ├── PARTNER-GUIDE.md           # Reference partner-side client example.
│   └── mcp-tool.json              # MCP envelope sample.
├── pyproject.toml
├── requirements.txt
├── .gitignore
├── .env.example
└── README.md
```

## Quick start

```bash
# Python 3.12+
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -e .          # runtime deps only
# OR for dev/test:
.venv\Scripts\python.exe -m pip install -e ".[dev]"

# Run the FastAPI app (KB-fallback mode — no LLM key required)
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8002

# In another terminal:
curl -X POST http://127.0.0.1:8002/api/v1/regenold/eu-ai-act/ask \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"What does Art. 13 require?"}]}'
```

### Port allocations

The bundle's FastAPI app binds to `8002` by convention (the parent `legit-ai` uses `8001`). The optional `claude-code-openai-wrapper` (Sonnet path) binds to `8000`. They never conflict because they listen on different ports.

### Reverse-proxy deployments

When deploying behind a CDN or reverse proxy (Railway, Cloudflare, nginx), set `REGENOLD_TRUST_PROXY=true` so the anonymous-tier rate limiter reads `X-Forwarded-For` instead of the direct socket address. **WARNING**: only enable when your proxy overwrites (not appends) XFF, otherwise an attacker can spoof their IP to bypass the per-IP bucket.

## Run the evals

```bash
# Run the full 225-scenario suite against the in-process app
.venv\Scripts\python.exe -m evals.regenold.runner --json evals/regenold_results_local.json

# With telemetry surfaced in the run report
.venv\Scripts\python.exe -m evals.regenold.runner --json evals/regenold_results_local.json --label baseline
```

By default the runner exercises the **deterministic-fallback** path (no LLM key required, fully reproducible). To run against a live LLM:

- **Mistral**: set `MISTRAL_API_KEY` and `P2P_GRAPH_RAG_PROVIDER=mistral` (the engine's auto-default picks Mistral when the key is present).
- **Anthropic**: set `ANTHROPIC_API_KEY` in `app/config.py::GraphRAGSettings.api_key` or via env.
- **Claude Code Max subscription** via the `claude-code-openai-wrapper`: start the wrapper at `127.0.0.1:8000`, then set `OPENAI_API_BASE=http://127.0.0.1:8000/v1` and `OPENAI_API_KEY=dummy`. See `docs/partners/regenold/SONNET_WRAPPER.md` for the full setup.

## Wire contract

`POST /api/v1/regenold/eu-ai-act/ask`

```json
{
  "messages": [
    {"role": "user", "content": "What does Art. 13 require for transparency?"}
  ]
}
```

Response (spec-clean default):

```json
{
  "answer": "Article 13(1) requires high-risk AI providers to design their systems to be sufficiently transparent for deployers to understand the system's output and use it appropriately. Article 13(2) requires accompanying instructions for use that include the provider's identity, the system's intended purpose, its capabilities and limitations, expected lifetime, and necessary maintenance.",
  "references": ["Article 13", "Article 13.1", "Article 13.2"],
  "reasoning": ""
}
```

Optional `?include_telemetry=true` query param exposes `confidence`, `retrieval_path`, `kb_version`, `nodes_traversed`, `obligations_found`, `gaps_found` for verifier-style flows.

See `docs/partners/regenold/INTEGRATION.md` for the full contract.

## License

Apache 2.0 — same as the parent project, granted for partner review + reproduction.
