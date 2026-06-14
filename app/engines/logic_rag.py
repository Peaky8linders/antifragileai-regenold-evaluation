import json
import logging
import os
import re
from typing import Any, Dict, List, Set

from app.engines.graph_rag import (
    GraphContext,
    _deterministic_parse,
    _retrieve_from_graph,
    _build_context_references_block,
)
from app.integrations.regenold.reasoning_trace import record_note
from app.llm.openai_wrapper_provider import (
    OpenAIWrapperRequest,
    get_openai_wrapper_provider,
    is_openai_wrapper_enabled,
)
from app.llm.prompts_logic import (
    DAG_DECOMPOSITION_PROMPT_SYSTEM,
    DAG_DECOMPOSITION_USER_TEMPLATE,
    CONTEXT_PRUNING_PROMPT_SYSTEM,
    CONTEXT_PRUNING_USER_TEMPLATE,
)

logger = logging.getLogger(__name__)

def _call_llm(system: str, user: str, max_tokens: int = 1024, temperature: float = 0.0) -> str:
    """Helper to call the wrapper LLM."""
    if not is_openai_wrapper_enabled():
        logger.warning("LogicRAG: openai_wrapper not enabled. Returning empty.")
        return ""
    
    prov = get_openai_wrapper_provider()
    # Use a faster reasoning model to minimize latency.
    model = os.getenv("REGENOLD_LOGIC_RAG_MODEL", "claude-sonnet-4-6")
    
    try:
        resp = prov.complete(
            OpenAIWrapperRequest(
                system=system,
                user=user,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout_seconds=120.0,
            )
        )
        if resp.error:
            logger.error(f"LogicRAG LLM Error: {resp.error}")
            return ""
        return resp.text or ""
    except Exception as e:
        logger.error(f"LogicRAG LLM Exception: {e}")
        return ""


def _decompose_to_dag(query: str) -> List[Dict[str, Any]]:
    """Decompose query into a DAG of subqueries."""
    fallback = [{"id": 1, "query": query, "dependencies": []}]
        
    user_prompt = DAG_DECOMPOSITION_USER_TEMPLATE.format(q=query)
    response_text = _call_llm(DAG_DECOMPOSITION_PROMPT_SYSTEM, user_prompt)
    
    fallback = [{"id": 1, "query": query, "dependencies": []}]
    if not response_text:
        return fallback
        
    try:
        # Extract JSON block
        text = response_text.strip()
        
        # Look for markdown JSON block first
        match = re.search(r'```(?:json)?\s*(.*?)\s*```', text, re.DOTALL)
        if match:
            text = match.group(1).strip()
            
        # Try to parse whatever we have as JSON
        dag = json.loads(text)
        
        # If it's a list, validate it
        if isinstance(dag, list) and len(dag) > 0:
            for node in dag:
                if not isinstance(node, dict) or "id" not in node or "query" not in node:
                    raise ValueError("Invalid DAG node structure (missing 'id' or 'query')")
            return dag
        else:
            # It answered the question instead of decomposing, fallback gracefully without logging an error if it's a dict
            if isinstance(dag, dict):
                logger.debug("Model returned a JSON object instead of a DAG list. Falling back to single query.")
                return fallback
            raise ValueError("Parsed JSON is not a list")
            
    except json.JSONDecodeError:
        # Fallback to regex search for array if json loads fails
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            try:
                dag = json.loads(match.group(0))
                if isinstance(dag, list) and len(dag) > 0:
                    for node in dag:
                        if not isinstance(node, dict) or "id" not in node or "query" not in node:
                            raise ValueError("Invalid DAG node structure (missing 'id' or 'query')")
                    return dag
            except Exception as e:
                logger.error(f"Failed to parse extracted DAG array: {e}. Raw response: {response_text}")
        else:
            logger.error(f"Failed to find JSON array in response. Raw response: {response_text}")
            
    except Exception as e:
        logger.error(f"Failed to parse DAG JSON or invalid structure: {e}. Raw response: {response_text}")
    
    return fallback


def _topological_sort(dag: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
    """Sort the DAG into ranks (lists of subqueries that can be executed in parallel)."""
    # Create lookup map
    nodes = {n["id"]: n for n in dag}
    
    # Track resolved dependencies
    resolved = set()
    ranks = []
    
    max_iters = len(nodes) + 1
    iters = 0
    
    while len(resolved) < len(nodes) and iters < max_iters:
        current_rank = []
        for node_id, node in nodes.items():
            if node_id in resolved:
                continue
            
            deps = set(node.get("dependencies", []))
            # If all deps are in the resolved set, we can execute this node
            if deps.issubset(resolved):
                current_rank.append(node)
                
        if not current_rank:
            # Cycle detected or missing dependency
            logger.warning("LogicRAG: Cycle detected in DAG or missing dependency.")
            # Force add remaining nodes to avoid infinite loop
            remaining = [n for nid, n in nodes.items() if nid not in resolved]
            ranks.append(remaining)
            break
            
        ranks.append(current_rank)
        for n in current_rank:
            resolved.add(n["id"])
            
        iters += 1
        
    return ranks


def _merge_contexts(base: GraphContext, new_ctx: GraphContext) -> None:
    """In-place merge of new_ctx into base."""
    # We want to keep citations intact.
    seen_articles = {a.get("id", "") for a in base.article_info}
    for a in new_ctx.article_info:
        if a.get("id", "") not in seen_articles:
            base.article_info.append(a)
            seen_articles.add(a.get("id", ""))
            
    base.nodes_traversed += new_ctx.nodes_traversed
    base.edges_followed += new_ctx.edges_followed
    if new_ctx.degraded:
        base.degraded = True


def execute_logic_rag(query: str, request_answers: dict = None) -> GraphContext:
    """
    Implements LogicRAG methodology:
    1. Query Logic Dependency Graph Construction
    2. Graph Reasoning Linearization (topological sort)
    3. Greedy Retrieval with Context/Graph Pruning
    """
    record_note("LogicRAG: Starting execution")
    
    dag = _decompose_to_dag(query)
    record_note(f"LogicRAG: DAG generated with {len(dag)} nodes")
    
    ranks = _topological_sort(dag)
    record_note(f"LogicRAG: Topologically sorted into {len(ranks)} ranks")
    
    rolling_memory = ""
    accumulated_context = GraphContext()
    
    # Graph Pruning: Subqueries at the same rank are processed together
    for rank_idx, rank_nodes in enumerate(ranks):
        if not rank_nodes:
            continue
            
        # Unified query construction
        unified_query_str = " AND ".join([n["query"] for n in rank_nodes])
        record_note(f"LogicRAG Rank {rank_idx}: Unified Query: {unified_query_str}")
        
        # Retrieve context
        parsed_query = _deterministic_parse(unified_query_str)
        rank_ctx = _retrieve_from_graph(
            parsed_query, 
            risk_level=None, 
            answers=request_answers or {}
        )
        
        _merge_contexts(accumulated_context, rank_ctx)
        
        if len(ranks) == 1:
            record_note("LogicRAG: Single rank DAG, skipping context pruning to save latency.")
            continue
        
        # Format the newly retrieved context into text
        new_context_text = _build_context_references_block(rank_ctx)
        
        # Context Pruning via Rolling Memory Update
        if not rolling_memory:
            # First rank: just seed the memory with a summarized version of the context
            user_prompt = CONTEXT_PRUNING_USER_TEMPLATE.format(
                q=query, 
                memory="None yet.", 
                subq=unified_query_str, 
                context=new_context_text[:4000]  # truncate to fit
            )
        else:
            user_prompt = CONTEXT_PRUNING_USER_TEMPLATE.format(
                q=query, 
                memory=rolling_memory, 
                subq=unified_query_str, 
                context=new_context_text[:4000]
            )
            
        updated_memory = _call_llm(CONTEXT_PRUNING_PROMPT_SYSTEM, user_prompt, max_tokens=512)
        if updated_memory:
            rolling_memory = updated_memory
            record_note(f"LogicRAG: Updated rolling memory (len={len(rolling_memory)})")
            
    # Inject the final rolling memory into the accumulated context 
    # so that the downstream Stage 2 Generator uses it.
    if rolling_memory:
        accumulated_context.semantically_relevant_statements.append(
            f"LOGIC_RAG_MEMORY: {rolling_memory}"
        )
        # Also add it as a mock article so deterministic Stage 1 generator sees it
        accumulated_context.article_info.append({
            "id": "LogicRAG Synthesis",
            "article": "LogicRAG Synthesis",
            "topic": "Synthesized Multi-hop Memory",
            "text": rolling_memory
        })
        
    accumulated_context.retrieval_path = "logic_rag"
    return accumulated_context
