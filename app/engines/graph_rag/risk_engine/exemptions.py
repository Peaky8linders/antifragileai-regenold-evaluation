"""Article 6(3) Derogations & AST Normative Condition Evaluation."""

from __future__ import annotations

import re
import logging
from app.engines.graph_rag.models import GraphContext, GraphQuery

logger = logging.getLogger(__name__)


def is_article_6_3_inquiry(question: str) -> bool:
    """Detect if question is asking specifically about Article 6(3) high-risk derogation."""
    q_low = question.lower()
    return "article 6(3)" in q_low or "article 6.3" in q_low or "article 6 (3)" in q_low or "art. 6(3)" in q_low


def evaluate_ast_exemptions(query: GraphQuery, context: GraphContext, answer_dict: dict) -> None:
    """Evaluate user assessment answers against Article 6(3) condition logic."""
    if not answer_dict:
        return

    ast_scenario = {}
    for k, v in answer_dict.items():
        val_str = getattr(v, "value", str(v))
        val = str(val_str).lower().strip()
        if val in ("yes", "true", "1"):
            ast_scenario[k] = True
        elif val in ("no", "false", "0"):
            ast_scenario[k] = False
        else:
            ast_scenario[k] = None

    if (
        "Annex III" in query.entities
        or "Art. 6" in query.entities
        or query.risk_context in ("high", "high_risk_annex_iii")
        or is_article_6_3_inquiry(query.raw_question)
    ):
        try:
            from app.graph.client import get_graph_client
            client = get_graph_client()
            if client.enabled:
                cypher = """
                MATCH (a:Article {id: 'article_6'})-[:HAS_PARAGRAPH]->(p:Paragraph {id: 'article_6_3'})-[:HAS_POINT]->(pt:Point)
                RETURN pt.id AS point_id, pt.letter AS letter, pt.text AS text
                """
                results = client.execute_read(cypher)
                for rec in results:
                    letter = rec.get("letter")
                    text = rec.get("text", "")
                    point_id = rec.get("point_id")

                    condition_met = ast_scenario.get(point_id) is True
                    if not condition_met:
                        for k, v in ast_scenario.items():
                            if v is True and text and isinstance(k, str) and len(k) >= 4 and (k.lower() in text.lower() or text.lower() in k.lower()):
                                condition_met = True
                                break

                    if condition_met:
                        internal_citation = f"Art. 6(3)({letter})"
                        exact_citation = f"Article 6(3)({letter})"
                        verdict_str = f"{exact_citation} logical evaluation: Practice exempt / Condition met for '{text}'."
                        if not hasattr(context, "ast_evaluations"):
                            context.ast_evaluations = []
                        if verdict_str not in context.ast_evaluations:
                            context.ast_evaluations.append(verdict_str)

                        if not any(a.get("id") == point_id for a in context.article_info):
                            context.article_info.append({
                                "id": point_id,
                                "article": internal_citation,
                                "text": f"Exception to high-risk classification under {exact_citation}: The system performs a {text}."
                            })
                            context.nodes_traversed += 3
                            context.edges_followed += 2
        except Exception as exc:
            logger.debug("ast evaluation skipped: %s", exc)
