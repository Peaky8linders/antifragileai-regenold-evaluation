# Regenold ↔ Antifragile AI — Partner Quick-Start

A grounded EU AI Act Q&A endpoint your agent can call to fetch obligations + paragraph-level citations from our compliance knowledge base. Returns formatted regulation references (`Article 13.1.a`, `Annex IV.2`), a confidence score, and the retrieval path used so you can decide what to do with low-confidence answers.

> **TL;DR:** It's an OpenAI-style `messages` POST. Auth is optional. Hallucinated articles are filtered out before they reach you. Below is everything you need.

---

## Endpoint

```
POST https://app.antifragile-ai.net/api/v1/regenold/eu-ai-act/ask
Content-Type: application/json
```

No SDK install required — anything that can POST JSON works.

---

## Auth

Auth is **optional**. Two tiers:

| Tier | How | Rate limit |
|------|-----|------------|
| Anonymous | Just POST, no header | 30 req / min per IP |
| Partner | Send `X-Regenold-Api-Key: YOUR-API-KEY` | 60 req / min per key |

The two tiers use **disjoint rate-limit buckets** — public traffic can never exhaust your partner budget.

If you send the header but the value doesn't match, you get **403** (not a silent downgrade) so a typo'd or stale key fails loudly instead of silently moving you to the lower tier. We can issue a partner key on request — DM the contact at the bottom of this doc.

---

## Request

The request body is an OpenAI-style `messages` array. The final `user` message is treated as the question; any `system` messages are concatenated as optional context to ground the answer (e.g. a brief description of the AI system you're advising on).

### Primary form — array of messages

```bash
curl -sS -X POST https://app.antifragile-ai.net/api/v1/regenold/eu-ai-act/ask \
  -H 'Content-Type: application/json' \
  -d '[
    {"role":"system","content":"Hospital triage assistant, deployed in EU."},
    {"role":"user","content":"What does Art. 13(1)(a) require for transparency to deployers?"}
  ]'
```

### Alternative wire shapes (for client compatibility)

```jsonc
// Wrapper object (same content)
{ "messages": [{"role":"user","content":"…"}] }

// Legacy single question
{ "question": "What does Art. 13 require?" }
```

### Limits

- Each message's `content`: max **4 000 characters** (longer → 422 `regenold_invalid_input`).
- Internal retrieval prompt is truncated to 2 000 chars; system context to 1 000 chars. Anything beyond that wouldn't have improved retrieval anyway.

---

## Response — default (spec-clean)

By default we return exactly the three fields the Regenold competition spec lists:

```jsonc
{
  "reasoning": "",
  "answer": "Article 13(1)(a) requires providers of high-risk AI systems to design transparency mechanisms enabling deployer interpretation. The output must be sufficiently transparent for deployer-side use. Operators must follow the instructions for use. Records of operations must be retained.",
  "references": [
    "Article 13.1.a",
    "Article 13"
  ]
}
```

### Field reference

| Field | Meaning |
|-------|---------|
| `answer` | Short prose, **3-4 sentences max** (post-truncated server-side to enforce the cap regardless of LLM behaviour). |
| `references` | Formatted EU AI Act citations, sorted by **citation strength**: Articles before Annexes; more specific paragraph chains first (`Article 13.1.a` ranks above `Article 13.1`). **Capped at 5** ("minimal set" per spec). **Hallucinated articles never appear here** — every reference is validated against the canonical 113-article + 13-Annex catalog AND a strict per-spec output regex. |
| `reasoning` | Empty string by default (the spec note says it "*will not be considered and might increase latency*", so we don't burn tokens on it). Becomes a structured retrieval-telemetry one-liner when `?include_telemetry=true`. |

### Reference format (strict per spec)

Internal refs are always formatted in the spec-required shape:

| You'd cite as | Wire form |
|---------------|-----------|
| `Art. 13(1)(a)` | `Article 13.1.a` |
| `Art. 3(2)` | `Article 3.2` |
| `Art. 5` | `Article 5` |
| `Annex IV(2)` | `Annex IV.2` |
| `Annex III(1)(a)` | `Annex III.1.a` |
| `Annex IV` | `Annex IV` |

Rejected shapes (will never appear in `references`):
- `Annex 3` (Arabic where Roman required)
- `Annex 3(2)`, `Annex III-2`, `Annex III . 2` (wrong separator)
- `Article III`, `Article III.2` (Roman where Arabic required)
- `Article 3/2` (slash separator)

### Optional telemetry — `?include_telemetry=true`

Need the engine's retrieval signals (e.g. for a downstream verifier)? Append `?include_telemetry=true`:

```jsonc
{
  "reasoning": "Confidence: 0.83; KB 2024.1689.v2; retrieval: neo4j; references: 2",
  "answer": "...",
  "references": ["Article 13.1.a", "Article 13"],
  "confidence": 0.83,
  "kb_version": "2024.1689.v2",
  "retrieval_path": "neo4j",
  "nodes_traversed": 14,
  "obligations_found": 6,
  "gaps_found": 0
}
```

| Telemetry field | Meaning |
|-----------------|---------|
| `confidence` | `0.0 – 1.0`. Below `0.5` with no references triggers closed-world refusal. |
| `kb_version` | Version stamp of our knowledge base — invalidate caches when this changes. Today: `2024.1689.v2`. |
| `retrieval_path` | `neo4j` / `kb_fallback` / `deterministic` / `no_match`. |
| `nodes_traversed` | How many KG nodes we walked. |
| `obligations_found` | EU AI Act obligations matched in retrieval. |
| `gaps_found` | Compliance gaps the KG flagged. |

### Closed-world refusal

When retrieval finds nothing usable (`confidence < 0.5` AND empty references), the response **deterministically refuses** instead of fabricating prose. With telemetry off (the default), you'll see:

```jsonc
{
  "reasoning": "",
  "answer": "No matching obligation found in the EU AI Act for this question. Try rephrasing with a specific article reference (e.g. \"Art. 13\"), a risk level (e.g. \"high-risk\"), or a compliance dimension (e.g. \"transparency\").",
  "references": []
}
```

With `?include_telemetry=true` you also see `confidence: 0.0` and `retrieval_path: "no_match"`. Your agent can branch on either signal — the empty `references` array combined with the deterministic refusal string is a reliable detector even on the spec-clean response.

### Multi-turn conversations

Send the full conversation history; the API threads recent assistant + user turns into the retrieval prompt so follow-up questions resolve against prior context:

```jsonc
[
  {"role": "user", "content": "What does Art. 13 require for transparency?"},
  {"role": "assistant", "content": "Article 13(1) requires high-risk providers..."},
  {"role": "user", "content": "What about for deployers using third-party systems?"}
]
```

We thread up to the **last 4 non-system turns** before the live user question into the retrieval prompt under a `Conversation so far:` preamble. System messages (any number) become standing context for the retrieval engine.

---

## Error responses

| Status | `code` | Meaning |
|--------|--------|---------|
| 200 | — | Grounded answer (or closed-world refusal — still a 200). |
| 400 | varied | Malformed request (e.g. empty body). |
| 403 | `regenold_api_key_invalid` | You sent `X-Regenold-Api-Key` but it didn't match. |
| 422 | `regenold_invalid_input` | Message validation failed (e.g. content > 4 000 chars, malformed `role`). |
| 429 | `RATE_LIMIT_EXCEEDED` | Tier rate limit hit. Includes `Retry-After`. |

All errors return JSON of the form `{"detail": "...", "code": "...", "correlation_id": "..."}`. Capture `correlation_id` in your logs — we use it to trace requests through our audit chain.

---

## Verification recipes

### Smoke test (anonymous, spec-clean response)

```bash
curl -sS -X POST https://app.antifragile-ai.net/api/v1/regenold/eu-ai-act/ask \
  -H 'Content-Type: application/json' \
  -d '[{"role":"user","content":"What does EU AI Act Art. 26 require of deployers?"}]' | jq .
```

Expected: response carries exactly `{reasoning, answer, references}`. References should contain `Article 26…`-shaped strings.

### Smoke test with telemetry

```bash
curl -sS -X POST 'https://app.antifragile-ai.net/api/v1/regenold/eu-ai-act/ask?include_telemetry=true' \
  -H 'Content-Type: application/json' \
  -d '[{"role":"user","content":"What does EU AI Act Art. 26 require of deployers?"}]' \
  | jq '{ refs: .references, conf: .confidence, path: .retrieval_path }'
```

Expected: `path` is `neo4j` or `kb_fallback`, `conf > 0.5`.

### Closed-world refusal

```bash
curl -sS -X POST https://app.antifragile-ai.net/api/v1/regenold/eu-ai-act/ask \
  -H 'Content-Type: application/json' \
  -d '[{"role":"user","content":"zxqv mnbv asdf 12345"}]' | jq .answer
```

Expected: `"No matching obligation found in the EU AI Act for this question. ..."` (deterministic refusal string).

### Invalid key

```bash
curl -sS -i -X POST https://app.antifragile-ai.net/api/v1/regenold/eu-ai-act/ask \
  -H 'Content-Type: application/json' \
  -H 'X-Regenold-Api-Key: YOUR-API-KEY' \
  -d '[{"role":"user","content":"hi"}]' | head -5
```

Expected: `HTTP/2 403`.

---

## Reference Python client (zero-deps stdlib)

```python
import json
import urllib.request

URL = "https://app.antifragile-ai.net/api/v1/regenold/eu-ai-act/ask"


def ask(
    messages: list[dict],
    api_key: str | None = None,
    include_telemetry: bool = False,
) -> dict:
    """Ask the Regenold endpoint. ``messages`` is the OpenAI-style history.

    Set ``include_telemetry=True`` to get back the engine's
    confidence / KB version / retrieval path / graph stats alongside
    the spec-required ``reasoning`` / ``answer`` / ``references``.
    """
    qs = "?include_telemetry=true" if include_telemetry else ""
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-Regenold-Api-Key"] = api_key

    req = urllib.request.Request(
        URL + qs,
        data=json.dumps(messages).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


# Single-turn example (spec-clean response)
result = ask([
    {"role": "system", "content": "Hospital triage assistant deployed in the EU."},
    {"role": "user", "content": "Under Art. 26, what record-keeping does a deployer need?"},
])
print(result["answer"])
for ref in result["references"]:
    print(f"  - {ref}")

# Multi-turn example
followup = ask([
    {"role": "user", "content": "What does Art. 13 require for transparency?"},
    {"role": "assistant", "content": result["answer"]},
    {"role": "user", "content": "What about for deployers using third-party systems?"},
])
print(followup["answer"])
```

---

## Best practices

1. **Trust `references`, not the prose.** The prose is LLM-generated and capped at 4 sentences; citations are validated against the canonical EU AI Act catalog AND a strict per-spec output regex. The first reference is always the strongest match.
2. **Branch on empty `references` for refusal.** When retrieval finds nothing, we return a deterministic refusal answer + empty `references`. (Add `?include_telemetry=true` if you want the explicit `retrieval_path: "no_match"` signal.)
3. **Send the full conversation history.** Multi-turn questions are aware of the prior 4 turns — don't strip them client-side.
4. **Use `system` messages for standing context.** They become persistent retrieval bias for every turn in the conversation.
5. **Stay under 4 000 chars per message.** Anything longer is rejected at the validation layer.
6. **Cache by KB version when telemetry is on.** Our KB is immutable per `kb_version`; cache aggressively until it changes.

---

## Audit chain

Every request is recorded on our tamper-evident audit chain:

- **Authenticated requests** stamp `tenant_id="partner:regenold"` (no IP recorded — your hashed key already identifies the channel).
- **Anonymous requests** stamp `tenant_id="public:regenold-anon"` plus a 16-hex SHA-256 truncation of the client IP for forensic correlation under GDPR Art. 4(5) pseudonymisation. Raw IP is never persisted.

Each row contains: `question_hash` (full SHA-256), `references[:20]`, `answer_excerpt[:500]`, `confidence`, `retrieval_path`, `kb_version`, and the tier label. Question text is **never** stored verbatim.

---

## Contact

- **API issues / partner key requests:** [open an issue](https://github.com/Peaky8linders/legit-ai/issues) or email the address in your partnership contact.
- **Status:** `GET /healthz` (public) returns `{"status":"ok"}` when the API is up.
- **OpenAPI schema:** `GET /openapi.json` (full machine-readable contract).

— Antifragile AI / CodexAI
