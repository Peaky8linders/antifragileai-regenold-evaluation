# Regenold EU AI Act RAG

For coding-agent onboarding and fresh-session handoff context, start with `CLAUDE.md` (see the `Fresh session plug-in` section).

Grounded EU AI Act Q&A — a FastAPI service that answers regulatory questions with verifiable Article / Annex references against EUR-Lex 2024/1689 and the May 2026 Digital Omnibus political agreement.

It mounts both the partner integration endpoint (`/api/v1/regenold/eu-ai-act/ask`) and a human-facing interactive compliance chat assistant UI called **Lexy** at the root path (`/`).

---

## Architecture

The service implements a hybrid, additive neuro-symbolic retrieval and generation pipeline. The entire system is designed to be fail-soft: if downstream graph databases or LLMs are unreachable or error out, the pipeline automatically falls back to an ultra-fast deterministic rule-based path to guarantee high-availability answers.

```
┌──────────────────────────────────────────────────────────────────┐
│ POST /api/v1/regenold/eu-ai-act/ask                              │
│      messages (OpenAI/LiteLLM history) → answer + references     │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                  ┌──────────▼──────────┐
                  │ Scope gate          │  app/integrations/regenold/scope.py
                  │ • Prompt-injection  │  • prior-user-turn anchors only
                  │ • Out-of-regulation │  • plural Articles N supported
                  │ • Coref rescue      │  • hard refusals never flipped
                  └──────────┬──────────┘
                             │
                  ┌──────────▼──────────┐
                  │ Multi-turn query    │  app/routes/regenold.py
                  │ de-noiser           │  • Standalone-query LLM rewrite
                  │                     │  • 1.0s fail-fast, falls back to
                  │                     │    history-concat on any error
                  └──────────┬──────────┘
                             │
                  ┌──────────▼──────────┐
                  │ Intent + qtype      │  app/llm/intent_classifier.py
                  │ classifier          │  app/engines/sentence_index.py
                  │ • Davvetas 4-task   │  • 8-way deterministic shape
                  │ • Fail-soft         │    (DEFINITION / BOOLEAN / …)
                  │ • Request-cached    │  • drives templates + budgets
                  └──────────┬──────────┘
                             │
            ┌────────────────▼────────────────┐
            │ Retrieval pipeline (additive)   │
            │ ┌──────────────────────────────┐│  app/data/kb_search.py
            │ │ BM25 over 348-doc corpus     ││  • EUR-Lex full prose
            │ │ + typed-entity priority      ││  • source-weighted scoring
            │ │   boost (role/concept NER)   ││  • 8 roles × 24 concepts
            │ └──────────────────────────────┘│
            │ ┌──────────────────────────────┐│  app/engines/embeddings_index.py
            │ │ NumPy TF-IDF + SVD-128       ││  • 919 sentence index
            │ │ additive recall              ││  • sub-ms warm queries
            │ └──────────────────────────────┘│
            │ ┌──────────────────────────────┐│  app/engines/graph_*.py
            │ │ Neo4j: 2-hop xref expand     ││  • 113 articles + 13 annexes
            │ │ + Personalized PageRank      ││    + 180 recitals + 68 defs
            │ │ + PathRAG (Jaccard prune)    ││    + 351 typed edges
            │ └──────────────────────────────┘│
            │ ┌──────────────────────────────┐│  app/routes/regenold.py
            │ │ Deployer 1-hop expansion     ││  • deterministic 4-edge map
            │ │ (definitional + intent-gated)│  • Art. 26 → 13/14/9 etc.
            │ └──────────────────────────────┘│
            └────────────────┬────────────────┘
                             │
            ┌────────────────▼────────────────┐
            │ Engine (graph_rag.py)           │
            │ • Stage-1 deterministic parse   │  always lands an answer
            │ • CLARA neuro-symbolic verdict  │  37 boolean tags → tier
            │ • Prohibited Gatekeeper (Art. 5)│  TAI Scan Layer C
            │ • Stage-2 Sonnet 4.6 polish     │  BLUF contrastive prompt
            │   (optional, fail-soft)         │  cross-ref grounding
            └────────────────┬────────────────┘
                             │
            ┌────────────────▼────────────────┐
            │ Post-engine pipeline            │  app/routes/regenold.py
            │ • Smallest-cover ref dedup      │  drops parents when child cited
            │ • Sub-point emission            │  Art. 5 → Art. 5.1.f
            │ • Per-intent ref budget         │  definitional=2 … scenario=8
            │ • Closed-world refusal gate     │  empty refs ⇒ no-match
            │ • Per-intent answer template    │  length cap by question shape
            │ • Per-ref description augmenter │  every cited article described
            │ • Tone guard + preamble strip   │  imperative regulator voice
            │ • Citation guard (optional)     │  sentence-level token overlap
            │ • Confidence-gated LRU cache    │  no-poison contract (R78.1)
            └────────────────┬────────────────┘
                             │
            ┌────────────────▼────────────────┐
            │ Hash-chained audit store        │  app/evidence/store.py
            │ (in-memory / SQLite / Postgres) │  every Q&A round-trip persisted
            └────────────────┬────────────────┘
                             │
                  ┌──────────▼──────────┐
                  │ RegenoldAskResponse │
                  │ { answer,           │
                  │   references,       │
                  │   reasoning }       │
                  └─────────────────────┘
```

### Core Pipeline Stages

1. **Scope Gate (`app/integrations/regenold/scope.py`)**: Protects the system from prompt injections and filters out-of-regulation prompts. It uses prior-turn anchors and coreference rescue, ensuring out-of-scope refusals are never flipped.
2. **Query De-Noiser (`app/routes/regenold.py`)**: Rewrites multi-turn conversation logs into a dense standalone search query under 1.0s, eliminating conversational bloat and keeping term-frequency metrics sharp.
3. **Intent Classifier (`app/llm/intent_classifier.py`)**: Classifies incoming questions into an 8-way deterministic shape (e.g. DEFINITION, BOOLEAN, SCENARIO) to drive length budgets and response templates.
4. **Additive Retrieval (`app/data/kb_search.py`)**: Combines lexical BM25 with typed-entity Named Entity Recognition (NER), SVD-128 dense TF-IDF recall, and Neo4j PageRank / PathRAG cross-reference expansions.
5. **Neuro-Symbolic Engine (`app/engines/graph_rag.py`)**: Integrates a deterministic Stage-1 parser with the CLARA logical engine (processing 37 boolean compliance tags) and gates prohibited practices (Art. 5). A Stage-2 LLM pass provides final professional polish and verbatim citation alignment.
6. **Post-Engine Refinement (`app/routes/regenold.py`)**: Deduplicates hierarchical references, applies tone and style guards, strips preambles, and serves answers from a confidence-gated LRU cache.

---

## Wire Contract

### Request
```bash
curl -X POST http://localhost:8002/api/v1/regenold/eu-ai-act/ask \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"What does Art. 13 require?"}]}'
```

### Response
```json
{
  "answer": "Article 13(1) requires high-risk AI providers to design their systems to be sufficiently transparent for deployers to understand the system's output and use it appropriately. Article 13(2) requires accompanying instructions for use that include the provider's identity, the system's intended purpose, its capabilities and limitations, expected lifetime, and necessary maintenance.",
  "references": ["Article 13.1", "Article 13.2"],
  "reasoning": ""
}
```

*Note: Append `?include_reasoning=true` to the URL to receive a full step-by-step diagnostic trace in the `reasoning` block.*

---

## Local Setup and Running the UI

Follow these steps to set up the codebase and run the Lexy compliance interface locally.

### Step 1: Environment and Virtualenv
The service requires Python 3.12+. Set up a virtual environment:
```bash
# Windows
py -3.12 -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python3.12 -m venv .venv
source .venv/bin/activate
```

### Step 2: Install Dependencies
Install the package and all engine requirements in editable mode:
```bash
pip install -e .
```

### Step 3: Configure Environment Variables
Copy the template and adjust env variables as needed. The pipeline uses environment keys like `P2P_GRAPH_RAG_PROVIDER` to resolve LLM calls, falling back gracefully to the offline deterministic path if none are configured.
```bash
cp .env.example .env
```

### Step 4: Run the UI and API locally
Launch the development server with `uvicorn`:
```bash
python -m uvicorn app.main:app --reload --port 8002
```

Once running:
- **Interactive Web UI (Lexy)**: Open `http://localhost:8002/` in your browser. This serves the premium chat-assistant dashboard which persists your custom configuration client-side in `localStorage`.
- **API Endpoint**: Accessible at `http://localhost:8002/api/v1/regenold/eu-ai-act/ask`.
- **Interactive API Documentation**: Reachable at `http://localhost:8002/docs`.
- **Health Probes**: `/healthz` for basic uptime, `/healthz/llm` for downstream model checks, and `/healthz/graph` for database stats.

---

## Evaluation and Benchmarks

The system is continuously scored against official benchmarks using token-overlap and LLM-as-a-judge factual consistency evaluations.

### 1. GraphRAG-Paper Benchmark (n=30 Ground Truth)
This benchmark includes medtech scenarios (e.g. robotic surgery, patient triage) and advanced PDF examples.

| Axis | r103-live | Baseline | Improvement |
| --- | ---: | ---: | ---: |
| **Ref. Correctness (Loose)** | **0.946** | 0.500 | **+0.446** |
| **Ref. Correctness (Strict)** | **0.649** | 0.420 | **+0.229** |
| **Keyword Recall** | **0.580** | 0.130 | **+0.450** |
| **Regulatory Tone** | **1.000** | 1.000 | *Stable (Perfect)* |
| **Refusal Rate** | **0.000** | 0.000 | *Stable (Perfect)* |
| **Latency p50** | **20.5 s** | — | — |

### 2. Representative 100 Benchmark (r103-live)
A 100-row stratified live evaluation drawn from the 476-row competition benchmark:

- **Factual Accuracy (LLM Judge Pass Rate)**: **0.6500** (65% of evaluated rows passed strict correctness criteria)
- **Factual Consistency Score (LLM Judge Mean)**: **0.7554** (Factual consistency ratio: `correct / (correct + incorrect + missing)`)
- **Reference Accuracy (LLM Judge Pass Rate)**: **0.7800** (78% of evaluated rows cited highly accurate provisions)
- **Regulatory Tone (LLM Judge Pass Rate)**: **0.5400** (54% of evaluated rows satisfied strict tone compliance)
- **Conciseness (LLM Judge Pass Rate)**: **0.0000** (0% of evaluated rows satisfied length bounds due to verbatim provisions and detailed obligation stubs)
- **Ref. Correctness (Loose, Token overlap)**: **0.6150**
- **Ref. Correctness (Strict, Token overlap)**: **0.5729**
- **Ref. Conciseness (Token overlap)**: **0.5614**
- **Ans. Correctness (Strict, Token overlap)**: **0.2681** (Jaccard overlap baseline)
- **Latency p50**: **18.2 s**

### Running Evals Locally

You can execute the automated evaluation and check progress locally using the following scripts:

```bash
# Run the reproducible 476-item competition benchmark
python -m evals.bench.runner --label baseline

# Run the out-of-scope regression check (21 hard refusal probes)
python -m evals.regenold.runner_v2 --local --probe-oos --label oos

# Run the local scenario suite (276 categorized medtech & general scenarios)
python -m evals.regenold.runner

# Run the LLM-as-a-judge factual consistency runner
python -m evals.judge.runner --bench-sidecar evals/bench/results/representative-100-r103-live.json --label r103-live-factual
```

---

## Where to Look

| Feature | Module |
|---|---|
| API Contract & Models | [`app/integrations/regenold/models.py`](app/integrations/regenold/models.py) |
| Route Handling | [`app/routes/regenold.py`](app/routes/regenold.py) |
| Scope & Refusal Gates | [`app/integrations/regenold/scope.py`](app/integrations/regenold/scope.py) |
| Web UI Interface | [`app/web_ui.py`](app/web_ui.py) |
| GraphRAG Engine | [`app/engines/graph_rag.py`](app/engines/graph_rag.py) |
| Additive KB Search | [`app/data/kb_search.py`](app/data/kb_search.py) |
| Neo4j PPR & PathRAG | [`app/engines/graph_ppr.py`](app/engines/graph_ppr.py), [`app/engines/path_rag.py`](app/engines/path_rag.py) |
| Tone & Style Normalizers | [`app/integrations/regenold/tone_guard.py`](app/integrations/regenold/tone_guard.py), [`app/integrations/regenold/answer_normaliser.py`](app/integrations/regenold/answer_normaliser.py) |
| Knowledge Base Data | [`app/data/kb.py`](app/data/kb.py) |
| Evaluation Harnesses | [`evals/bench/`](evals/bench/), [`evals/judge/`](evals/judge/) |

---

## License

Apache 2.0.
