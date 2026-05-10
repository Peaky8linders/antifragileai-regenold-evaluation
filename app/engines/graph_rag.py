"""
Graph RAG Compliance Q&A Engine — Conversational interface over the compliance graph.

Architecture (two-stage):
  1. PARSE: Natural language question → structured GraphQuery (LLM)
  2. RETRIEVE: GraphQuery → Cypher queries against Neo4j → GraphContext
  3. GENERATE: Question + GraphContext → cited answer (LLM)

Falls back to KB-only mode when Neo4j is unavailable.
Falls back to deterministic answers when Anthropic API key is not set.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any

from app.models import (
    AssessmentAnswer,
    CitationNode,
    GraphRAGRequest,
    GraphRAGResponse,
)

logger = logging.getLogger(__name__)


# ─── Robust JSON extraction for LLM responses ────────────────────────────────
#
# Sonnet 4.6 in particular ships markdown-fenced JSON with explanatory prose
# despite "Respond with valid JSON only. No markdown, no explanation." in the
# system prompt. The original stripper at the _llm_parse_query call site only
# handled the case where the ENTIRE response was wrapped in a fenced block —
# Sonnet's prose-before-JSON / prose-after-JSON / multiple-fences cases all
# slipped to the deterministic fallback, losing 2 simple-question scenarios
# on the eval baseline. This helper closes those holes by walking three
# strategies in order of strictness.

_JSON_FENCE_RE = re.compile(
    r"```(?:json5?|jsonc)?\s*\n?(.*?)\n?```",
    re.IGNORECASE | re.DOTALL,
)
# Match the first balanced JSON object span. Greedy on closing brace so
# nested objects are absorbed. Falls back to non-greedy if greedy fails.
_JSON_OBJECT_GREEDY_RE = re.compile(r"\{.*\}", re.DOTALL)
_JSON_OBJECT_NONGREEDY_RE = re.compile(r"\{.*?\}", re.DOTALL)
_TRAILING_COMMA_RE = re.compile(r",\s*(?=[}\]])")


def _strip_trailing_commas(text: str) -> str:
    """Strip ``,}`` / ``,]`` Sonnet sometimes emits despite a strict JSON ask."""
    return _TRAILING_COMMA_RE.sub("", text)


def _try_parse(candidate: str) -> dict | None:
    """Best-effort json.loads; return None on any failure (incl. non-dict)."""
    candidate = candidate.strip()
    if not candidate:
        return None
    try:
        result = json.loads(candidate)
    except (ValueError, TypeError):
        try:
            result = json.loads(_strip_trailing_commas(candidate))
        except (ValueError, TypeError):
            return None
    return result if isinstance(result, dict) else None


def _extract_json_object(text: str) -> dict | None:
    """Extract a parseable JSON object from an arbitrary LLM response.

    Strategy (first hit wins):

    1. **Direct parse**: the response is already valid JSON (the happy
       path — no markdown, no prose).
    2. **Fenced-block extraction**: walk every ```` ``` ```` fenced span
       (with optional ``json``/``json5``/``jsonc`` language tag) and try
       to parse each one's body. Picks the first parsable hit so prose
       intermixed with multiple code blocks still resolves to the right
       JSON payload.
    3. **Brace-span fallback**: if no fence parses, hunt for the first
       balanced ``{...}`` span in the raw text. Greedy first (absorbs
       nested objects), non-greedy as a last resort (Sonnet occasionally
       emits a short JSON block sandwiched between two long prose
       paragraphs that contain stray ``{``/``}`` glyphs).

    Returns the parsed dict on success, or ``None`` if every strategy
    failed — the caller raises so the deterministic-parse fallback fires.
    """
    if not text:
        return None
    cleaned = text.strip()

    # 1. Direct parse — strict JSON response.
    direct = _try_parse(cleaned)
    if direct is not None:
        return direct

    # 2. Fenced-block extraction — find every fenced span and try each.
    for match in _JSON_FENCE_RE.finditer(cleaned):
        candidate = match.group(1).strip()
        result = _try_parse(candidate)
        if result is not None:
            return result

    # 3. Brace-span fallback — first balanced {...} block.
    greedy = _JSON_OBJECT_GREEDY_RE.search(cleaned)
    if greedy is not None:
        result = _try_parse(greedy.group(0))
        if result is not None:
            return result
    nongreedy = _JSON_OBJECT_NONGREEDY_RE.search(cleaned)
    if nongreedy is not None:
        result = _try_parse(nongreedy.group(0))
        if result is not None:
            return result

    return None


def _graph_rag_provider() -> str:
    """Resolve the graph-RAG LLM provider per call.

    Honours an explicit ``P2P_GRAPH_RAG_PROVIDER=mistral`` /
    ``=anthropic``. When the toggle is unset or set to ``auto``, picks
    Mistral if ``MISTRAL_API_KEY`` is present in the process env, else
    falls back to the historical Anthropic path. Read on every call so a
    Railway env-var rebind takes effect on the next request.
    """
    from app.llm import resolve_provider

    return resolve_provider(
        os.getenv("P2P_GRAPH_RAG_PROVIDER"),
        default_when_auto="anthropic",
    )


def _mistral_complete_for_graph_rag(
    *, system: str, user: str, max_tokens: int, temperature: float
) -> str | None:
    """One Mistral call for graph-RAG. ``None`` on any error so callers fall back."""
    from app.llm import MistralRequest, get_mistral_provider, is_mistral_enabled

    if not is_mistral_enabled():
        return None
    try:
        from app.config import settings
        # Reuse the model knob the deploy already configures for the
        # Anthropic path so an operator who pinned a model gets a
        # Mistral-equivalent rather than a silently-different one.
        configured = settings.graph_rag.model
    except Exception:  # noqa: BLE001 — soft-fail; we'll just use the provider default
        configured = ""
    model = (
        configured if configured.startswith("mistral-") else "mistral-large-latest"
    )
    response = get_mistral_provider().complete(
        MistralRequest(
            system=system,
            user=user,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )
    )
    if response.error:
        logger.warning("graph_rag.mistral_call_failed: %s", response.error[:200])
        return None
    return response.text


def _openai_wrapper_complete_for_graph_rag(
    *, system: str, user: str, max_tokens: int, temperature: float
) -> str | None:
    """One OpenAI-compatible call (Claude Max via wrapper, etc.).

    Returns ``None`` on any error so callers fall back to deterministic.
    The model picks up the deploy's ``graph_rag.model`` knob; defaults
    to ``claude-sonnet-4-6`` when unset or set to a Mistral model.
    """
    from app.llm.openai_wrapper_provider import (
        OpenAIWrapperRequest,
        get_openai_wrapper_provider,
    )

    try:
        from app.config import settings
        configured = settings.graph_rag.model
    except Exception:  # noqa: BLE001
        configured = ""
    model = (
        configured
        if (configured and not configured.startswith("mistral-"))
        else "claude-sonnet-4-6"
    )

    response = get_openai_wrapper_provider().complete(
        OpenAIWrapperRequest(
            system=system,
            user=user,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )
    )
    if response.error:
        logger.warning("graph_rag.openai_wrapper_call_failed: %s", response.error[:200])
        return None
    return response.text


# ─── Internal data structures ────────────────────────────────────────────────

@dataclass
class GraphQuery:
    """Structured query extracted from a natural language question."""
    intent: str = "general_compliance"
    entities: list[str] = field(default_factory=list)
    risk_context: str | None = None
    dimension_hint: str | None = None
    keywords: list[str] = field(default_factory=list)
    raw_question: str = ""


@dataclass
class GraphContext:
    """Structured context retrieved from the compliance graph."""
    obligations: list[dict] = field(default_factory=list)
    gaps: list[dict] = field(default_factory=list)
    satisfied: list[dict] = field(default_factory=list)
    dimension_info: list[dict] = field(default_factory=list)
    cross_framework: dict = field(default_factory=dict)
    article_info: list[dict] = field(default_factory=list)
    transitive_deps: list[dict] = field(default_factory=list)
    nodes_traversed: int = 0
    edges_followed: int = 0


# ─── LLM Integration ────────────────────────────────────────────────────────

def _get_anthropic_client():
    """Lazy-load Anthropic client. Returns None if not configured."""
    try:
        from app.config import settings
        api_key = settings.graph_rag.api_key
        if not api_key:
            return None
        import anthropic
        return anthropic.Anthropic(api_key=api_key.get_secret_value())
    except ImportError:
        logger.warning("anthropic package not installed — Graph RAG LLM features disabled")
        return None
    except Exception as exc:
        logger.warning("Anthropic client init failed: %s", exc)
        return None


def _llm_parse_query(question: str) -> GraphQuery:
    """Use LLM to parse natural language question into structured query."""
    provider = _graph_rag_provider()
    try:
        from app.config import settings
        from app.data.graph_rag_prompts import QUERY_PARSE_SYSTEM

        from app.security.prompt_guard import PROMPT_HARDENING_PREFIX, sanitize_for_llm

        sanitized_question = sanitize_for_llm(question, context_type="query")
        system_prompt = PROMPT_HARDENING_PREFIX + QUERY_PARSE_SYSTEM

        if provider == "mistral":
            text_raw = _mistral_complete_for_graph_rag(
                system=system_prompt,
                user=sanitized_question,
                max_tokens=512,
                temperature=0.0,
            )
            if text_raw is None:
                return _deterministic_parse(question)
            text = text_raw.strip()
        elif provider == "openai_wrapper":
            text_raw = _openai_wrapper_complete_for_graph_rag(
                system=system_prompt,
                user=sanitized_question,
                max_tokens=512,
                temperature=0.0,
            )
            if text_raw is None:
                return _deterministic_parse(question)
            text = text_raw.strip()
        else:
            client = _get_anthropic_client()
            if client is None:
                return _deterministic_parse(question)
            response = client.messages.create(
                model=settings.graph_rag.model,
                max_tokens=512,
                temperature=0.0,
                system=system_prompt,
                messages=[{"role": "user", "content": sanitized_question}],
            )
            if not response.content:
                raise ValueError("Anthropic returned empty content block")
            text = response.content[0].text.strip()
        # Robust JSON extraction (regenold-eu-ai-act-rag follow-up #2):
        # the original stripper only handled the case where the WHOLE
        # response was wrapped in ```` ```json ... ``` ````. Claude Sonnet
        # 4.6 in particular ships markdown-fenced JSON with explanatory
        # prose before AND/OR after the block. The new helper handles:
        #   1. Full-response fenced JSON (the original happy path).
        #   2. Prose before/after the fenced block.
        #   3. Multiple fenced blocks (picks the first JSON-parsable one).
        #   4. Language tag after the backticks ("```json" / "```JSON5" / "```jsonc").
        #   5. No fences at all but a `{...}` block embedded in prose.
        #   6. Trailing commas (Sonnet occasionally emits these even when
        #      told strict JSON — strip before parsing).
        parsed = _extract_json_object(text)
        if parsed is None:
            raise ValueError(
                f"LLM returned non-parsable JSON. First 200 chars: {text[:200]!r}"
            )
        return GraphQuery(
            intent=parsed.get("intent", "general_compliance"),
            entities=parsed.get("entities", []),
            risk_context=parsed.get("risk_context"),
            dimension_hint=parsed.get("dimension_hint"),
            keywords=parsed.get("keywords", []),
            raw_question=question,
        )
    except Exception as exc:
        logger.warning("LLM query parse failed, falling back to deterministic: %s", exc)
        return _deterministic_parse(question)


def _llm_generate_answer(
    question: str,
    context: GraphContext,
    system_description: str | None = None,
) -> str:
    """Use LLM to generate a cited answer from retrieved EU AI Act references."""
    provider = _graph_rag_provider()
    try:
        from app.config import settings
        from app.data.graph_rag_prompts import ANSWER_GENERATE_SYSTEM

        # Build context message
        context_parts = []
        if context.obligations:
            context_parts.append(
                f"APPLICABLE OBLIGATIONS ({len(context.obligations)} found):\n"
                + "\n".join(
                    f"- [{o.get('id', 'N/A')}] {o.get('text', '')} (Article: {o.get('article', 'N/A')})"
                    for o in context.obligations[:20]
                )
            )
        if context.gaps:
            context_parts.append(
                f"\nCOMPLIANCE GAPS ({len(context.gaps)} found):\n"
                + "\n".join(
                    f"- [{g.get('obligation_id', g.get('id', 'N/A'))}] {g.get('text', '')} "
                    f"(Reason: {g.get('reason', 'N/A')}, Severity: {g.get('severity', 'N/A')})"
                    for g in context.gaps[:15]
                )
            )
        if context.satisfied:
            context_parts.append(
                f"\nSATISFIED OBLIGATIONS ({len(context.satisfied)} found):\n"
                + "\n".join(
                    f"- [{s.get('obligation_id', s.get('id', 'N/A'))}] {s.get('text', '')} "
                    f"(Satisfied by: {', '.join(s.get('satisfied_by', []))})"
                    for s in context.satisfied[:10]
                )
            )
        if context.cross_framework:
            context_parts.append(
                f"\nCROSS-FRAMEWORK COVERAGE:\n"
                f"- NIST AI RMF: {context.cross_framework.get('nist_covered', 0)} refs covered\n"
                f"- ISO 42001: {context.cross_framework.get('iso_covered', 0)} refs covered"
            )
        if context.dimension_info:
            context_parts.append(
                "\nDIMENSION DETAILS:\n"
                + "\n".join(
                    f"- {d.get('dim_name', d.get('dim_id', 'N/A'))}: "
                    f"{d.get('question_count', 0)} questions, "
                    f"{d.get('obligation_count', 0)} obligations"
                    for d in context.dimension_info
                )
            )
        if context.transitive_deps:
            context_parts.append(
                f"\nTRANSITIVE DEPENDENCIES ({len(context.transitive_deps)} found):\n"
                + "\n".join(
                    f"- [{t.get('id', 'N/A')}] {t.get('text', '')} (blocked by gap)"
                    for t in context.transitive_deps[:10]
                )
            )

        context_text = "\n".join(context_parts) if context_parts else "No EU AI Act references match this query."

        from app.security.prompt_guard import PROMPT_HARDENING_PREFIX, sanitize_for_llm, validate_llm_output

        sanitized_question = sanitize_for_llm(question, context_type="query")
        user_message = f"QUESTION: {sanitized_question}\n\n"
        if system_description:
            sanitized_desc = sanitize_for_llm(system_description, context_type="system_description")
            user_message += f"SYSTEM DESCRIPTION: {sanitized_desc}\n\n"
        # Label intentionally reads "EU AI ACT REFERENCES" — earlier
        # "GRAPH CONTEXT:" wording made the LLM cheerfully echo "based
        # on the graph context" / "the graph context lacks…" in the
        # answer, leaking implementation detail into user-facing prose.
        # Talking about references trains the model to write as the
        # regulation expert, not as a graph-querying agent.
        user_message += f"EU AI ACT REFERENCES:\n{context_text}"

        full_system = PROMPT_HARDENING_PREFIX + ANSWER_GENERATE_SYSTEM

        if provider == "mistral":
            text_raw = _mistral_complete_for_graph_rag(
                system=full_system,
                user=user_message,
                max_tokens=settings.graph_rag.max_tokens,
                temperature=settings.graph_rag.temperature,
            )
            if text_raw is None:
                return _deterministic_answer(question, context)
            return validate_llm_output(text_raw.strip())

        if provider == "openai_wrapper":
            text_raw = _openai_wrapper_complete_for_graph_rag(
                system=full_system,
                user=user_message,
                max_tokens=settings.graph_rag.max_tokens,
                temperature=settings.graph_rag.temperature,
            )
            if text_raw is None:
                return _deterministic_answer(question, context)
            return validate_llm_output(text_raw.strip())

        client = _get_anthropic_client()
        if client is None:
            return _deterministic_answer(question, context)
        response = client.messages.create(
            model=settings.graph_rag.model,
            max_tokens=settings.graph_rag.max_tokens,
            temperature=settings.graph_rag.temperature,
            system=full_system,
            messages=[{"role": "user", "content": user_message}],
        )

        if not response.content:
            raise ValueError("Anthropic returned empty content block")
        raw_answer = response.content[0].text.strip()
        return validate_llm_output(raw_answer)
    except Exception as exc:
        logger.warning("LLM answer generation failed, falling back to deterministic: %s", exc)
        return _deterministic_answer(question, context)


# ─── Deterministic fallbacks (no LLM required) ──────────────────────────────

def _deterministic_parse(question: str) -> GraphQuery:
    """Parse question using keyword matching when LLM is unavailable."""
    q_lower = question.lower()

    # Detect intent
    intent = "general_compliance"
    if any(w in q_lower for w in ["gap", "missing", "lacking", "need"]):
        intent = "gap_analysis"
    elif any(w in q_lower for w in ["obligation", "require", "must", "need to"]):
        intent = "obligation_check"
    elif any(w in q_lower for w in ["article", "art."]):
        intent = "article_lookup"
    elif any(w in q_lower for w in ["risk", "classify", "classification"]):
        intent = "risk_assessment"
    elif any(w in q_lower for w in ["nist", "iso", "framework", "cross"]):
        intent = "cross_framework"

    # Extract article references
    import re
    entities = re.findall(r"Art\.?\s*(\d+)", question, re.IGNORECASE)
    entities = [f"Art. {n}" for n in entities]

    # Detect risk context
    risk_context = None
    if "high" in q_lower and "risk" in q_lower:
        risk_context = "high"
    elif "limited" in q_lower:
        risk_context = "limited"
    elif "minimal" in q_lower:
        risk_context = "minimal"
    elif "unacceptable" in q_lower or "prohibited" in q_lower:
        risk_context = "unacceptable"

    # Detect dimension hints
    dimension_hint = None
    dim_keywords = {
        "data_gov": ["data governance", "training data", "bias"],
        "risk_mgmt": ["risk management", "risk assessment"],
        "tech_docs": ["technical documentation", "annex iv", "documentation"],
        "logging": ["record-keeping", "logging", "audit trail"],
        "transparency": ["transparency", "disclosure", "explainability"],
        "human_oversight": ["human oversight", "override", "human-in-the-loop"],
        "security": ["security", "robustness", "accuracy", "adversarial"],
        "deployer_obligations": ["deployer", "fria", "fundamental rights"],
        "conformity_assessment": ["conformity", "ce marking", "declaration"],
        "quality_management": ["quality management", "qms"],
        "decision_governance": ["decision", "behavioral rule", "interception"],
    }
    for dim_id, keywords in dim_keywords.items():
        if any(kw in q_lower for kw in keywords):
            dimension_hint = dim_id
            break

    return GraphQuery(
        intent=intent,
        entities=entities,
        risk_context=risk_context,
        dimension_hint=dimension_hint,
        keywords=question.lower().split()[:10],
        raw_question=question,
    )


def _deterministic_answer(question: str, context: GraphContext) -> str:
    """Generate a structured answer without LLM, using graph data directly."""
    parts: list[str] = []

    if context.obligations:
        parts.append(
            f"The EU AI Act sets out {len(context.obligations)} "
            f"obligations relevant to your query."
        )
        for obl in context.obligations[:5]:
            parts.append(
                f"- **{obl.get('article', 'N/A')}**: {obl.get('text', 'N/A')} "
                f"[{obl.get('id', '')}]"
            )

    if context.gaps:
        parts.append(
            f"\n**Compliance Gaps** ({len(context.gaps)} identified):"
        )
        for gap in context.gaps[:5]:
            parts.append(
                f"- {gap.get('text', 'N/A')} ({gap.get('article', '')}) — "
                f"Severity: {gap.get('severity', 'N/A')}"
            )

    if context.satisfied:
        parts.append(
            f"\n**Satisfied Obligations**: {len(context.satisfied)} of "
            f"{len(context.obligations) + len(context.gaps)} total."
        )

    if context.cross_framework:
        nist = context.cross_framework.get("nist_covered", 0)
        iso = context.cross_framework.get("iso_covered", 0)
        if nist or iso:
            parts.append(
                f"\n**Cross-Framework Coverage**: "
                f"NIST AI RMF: {nist} refs, ISO 42001: {iso} refs."
            )

    # KB-projected answer surface. The compliance knowledge graph is a
    # projection of the shipped KB (articles + dimensions + obligations +
    # risk levels + crosswalks); Neo4j is just a cache layer over it.
    # When the cache is cold, dimension_info is still populated from the
    # KB itself — rather than pretending we have no data, we surface
    # those dimensions directly.
    if not parts and context.dimension_info:
        parts.append(
            f"Under the EU AI Act, {len(context.dimension_info)} "
            f"compliance dimensions are in scope for this question:"
        )
        for d in context.dimension_info[:8]:
            parts.append(
                f"- **{d.get('dim_name', d.get('dim_id', 'N/A'))}** — "
                f"{d.get('question_count', 0)} questions"
            )

    if not parts:
        parts.append(
            "No matching obligation found in the EU AI Act for this question. "
            "Try rephrasing with a specific Art. reference (e.g. 'Art. 11'), a "
            "risk level ('high-risk'), or a compliance dimension ('transparency')."
        )

    return "\n".join(parts)


# ─── Graph Retrieval ─────────────────────────────────────────────────────────

def _retrieve_from_graph(
    query: GraphQuery,
    risk_level: str | None = None,
    answers: dict[str, Any] | None = None,
) -> GraphContext:
    """Query the Neo4j graph based on the structured query."""
    from app.graph.client import get_graph_client

    client = get_graph_client()
    context = GraphContext()

    if not client.enabled:
        # Fall back to KB-based context
        return _retrieve_from_kb(query, risk_level)

    effective_risk = query.risk_context or risk_level or "high"
    answer_dict = answers or {}
    answer_strs = {
        k: (v.value if isinstance(v, AssessmentAnswer) else str(v))
        for k, v in answer_dict.items()
        if v is not None
    }

    try:
        # Get obligations for risk level
        from app.data.graph_rag_prompts import CYPHER_TEMPLATES

        obligations = client.execute_read(
            CYPHER_TEMPLATES["obligations_for_risk_level"],
            {"risk_level": effective_risk},
        )
        context.obligations = obligations
        context.nodes_traversed += len(obligations)

        # If specific article is mentioned, get article-specific obligations
        for entity in query.entities:
            if entity.startswith("Art."):
                art_id = entity.replace("Art. ", "art").replace("Art.", "art")
                art_obls = client.execute_read(
                    CYPHER_TEMPLATES["obligations_for_article"],
                    {"article_id": art_id},
                )
                if art_obls:
                    context.article_info.extend(art_obls)
                    context.nodes_traversed += len(art_obls)

        # If dimension hint, get dimension details
        if query.dimension_hint:
            dim_info = client.execute_read(
                CYPHER_TEMPLATES["dimension_summary"],
                {"dimension_id": query.dimension_hint},
            )
            if dim_info:
                context.dimension_info = dim_info
                context.nodes_traversed += len(dim_info)

        # If answers provided, run gap reasoning
        if answer_strs and query.intent in ("gap_analysis", "obligation_check", "general_compliance"):
            from app.graph.reasoning import reason_compliance
            reasoning = reason_compliance(client, effective_risk, answer_strs)
            if reasoning.get("status") == "completed":
                context.gaps = reasoning.get("gaps", [])
                context.satisfied = reasoning.get("satisfied", [])
                context.cross_framework = reasoning.get("cross_framework", {})
                context.transitive_deps = reasoning.get("transitive_gaps", [])
                context.edges_followed += reasoning.get("total_obligations", 0)

    except Exception as exc:
        logger.warning("Graph retrieval failed: %s", exc)

    return context


def _retrieve_from_kb(
    query: GraphQuery,
    risk_level: str | None = None,
) -> GraphContext:
    """Fallback: retrieve context from KB when Neo4j is unavailable."""
    from app.data.kb import (
        MATURITY_DIMENSIONS,
        EC_CHECKER_OBLIGATION_MAP,
        get_dimensions_for_risk_level,
    )

    context = GraphContext()
    effective_risk = query.risk_context or risk_level or "high"

    # Get applicable dimensions
    try:
        dims = get_dimensions_for_risk_level(effective_risk)
    except ValueError:
        dims = MATURITY_DIMENSIONS

    # If dimension hint, filter
    if query.dimension_hint:
        dims = tuple(d for d in dims if d.id == query.dimension_hint) or dims

    # Build obligation-like entries from KB
    for entity in query.entities:
        mapping = EC_CHECKER_OBLIGATION_MAP.get(entity)
        if mapping:
            context.obligations.append({
                "id": f"kb-{mapping['dimension']}",
                "text": mapping["summary"],
                "article": entity,
            })

    # Add dimension info
    for dim in dims[:10]:
        context.dimension_info.append({
            "dim_id": dim.id,
            "dim_name": dim.label,
            "question_count": len(dim.questions),
            "obligation_count": 0,
        })

    context.nodes_traversed = len(context.obligations) + len(context.dimension_info)
    return context


# ─── Main entry point ────────────────────────────────────────────────────────

def ask_compliance_question(request: GraphRAGRequest) -> GraphRAGResponse:
    """Main entry point: answer a natural language compliance question.

    1. Parse the question into a structured GraphQuery
    2. Retrieve relevant context from Neo4j (or KB fallback)
    3. Generate a cited answer using LLM (or deterministic fallback)
    4. Extract citations from the graph context
    """
    # Step 1: Parse
    query = _llm_parse_query(request.question)

    # Override risk context if provided in request
    if request.risk_level:
        query.risk_context = request.risk_level.value

    # Step 2: Retrieve
    answer_dict = {k: v for k, v in request.answers.items()} if request.answers else {}
    context = _retrieve_from_graph(
        query,
        risk_level=request.risk_level.value if request.risk_level else None,
        answers=answer_dict,
    )

    # Step 3: Generate
    reasoning_trace = [
        f"Intent: {query.intent}",
        f"Entities: {query.entities}",
        f"Risk context: {query.risk_context or 'not specified'}",
        f"Dimension hint: {query.dimension_hint or 'none'}",
        f"Graph nodes traversed: {context.nodes_traversed}",
        f"Graph edges followed: {context.edges_followed}",
    ]

    answer_text = _llm_generate_answer(
        request.question, context, request.system_description,
    )

    # Step 4: Extract citations
    citations: list[CitationNode] = []
    seen_ids: set[str] = set()

    for obl in (context.obligations + context.article_info)[:15]:
        oid = obl.get("id", obl.get("obligation_id", ""))
        if oid and oid not in seen_ids:
            seen_ids.add(oid)
            citations.append(CitationNode(
                node_type="Obligation",
                node_id=oid,
                text=obl.get("text", ""),
                article_ref=obl.get("article", ""),
            ))

    for gap in context.gaps[:10]:
        gid = gap.get("obligation_id", gap.get("id", ""))
        if gid and gid not in seen_ids:
            seen_ids.add(gid)
            citations.append(CitationNode(
                node_type="Gap",
                node_id=gid,
                text=gap.get("text", ""),
                article_ref=gap.get("article", ""),
            ))

    # Suggested follow-ups based on intent
    from app.data.graph_rag_prompts import SUGGESTED_QUESTIONS
    followups = _suggest_followups(query, context, SUGGESTED_QUESTIONS)

    # Confidence based on data richness
    confidence = _compute_confidence(context)

    return GraphRAGResponse(
        answer=answer_text,
        citations=citations,
        confidence=confidence,
        reasoning_trace=reasoning_trace,
        suggested_followups=followups,
        graph_stats={
            "nodes_traversed": context.nodes_traversed,
            "edges_followed": context.edges_followed,
            "obligations_found": len(context.obligations),
            "gaps_found": len(context.gaps),
            "satisfied_found": len(context.satisfied),
        },
    )


def _suggest_followups(
    query: GraphQuery,
    context: GraphContext,
    all_questions: list[str],
) -> list[str]:
    """Suggest 2-3 follow-up questions based on the current query and results."""
    followups: list[str] = []

    if context.gaps:
        followups.append("What remediation tasks should we prioritise for these gaps?")
    if query.intent == "obligation_check" and not context.cross_framework:
        followups.append("How do our compliance answers map to NIST AI RMF?")
    if query.intent == "gap_analysis":
        followups.append("Are there any transitive gaps blocking our compliance?")
    if query.dimension_hint and query.intent != "gap_analysis":
        followups.append(f"What gaps do we have in {query.dimension_hint}?")

    # Add a general suggestion if we don't have enough
    if len(followups) < 2:
        for q in all_questions:
            if q not in followups and q.lower() != query.raw_question.lower():
                followups.append(q)
                if len(followups) >= 3:
                    break

    return followups[:3]


def _compute_confidence(context: GraphContext) -> float:
    """Compute answer confidence based on graph data richness."""
    if context.nodes_traversed == 0:
        return 0.3  # No graph data — low confidence
    if context.nodes_traversed < 5:
        return 0.5  # Sparse data
    if context.gaps or context.satisfied:
        return 0.85  # Rich data with gap analysis
    return 0.7  # Moderate data
