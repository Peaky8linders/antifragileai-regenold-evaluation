"""Legal Abstract Syntax Tree (AST) definitions and evaluator.

This module models legal conditions and exceptions explicitly.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

@dataclass
class ASTNode:
    pass

@dataclass
class Condition(ASTNode):
    text: str
    condition_id: str

@dataclass
class LogicalAnd(ASTNode):
    operands: list[ASTNode]

@dataclass
class LogicalOr(ASTNode):
    operands: list[ASTNode]

@dataclass
class ExceptionClause(ASTNode):
    base_clause: ASTNode
    exception_condition: ASTNode

def evaluate_ast(node: ASTNode, scenario: dict[str, Any]) -> bool | None:
    """Evaluate AST against a scenario. Returns True, False, or None (Unknown)."""
    if isinstance(node, Condition):
        return scenario.get(node.condition_id, None)
    elif isinstance(node, LogicalAnd):
        results = [evaluate_ast(op, scenario) for op in node.operands]
        if False in results: return False
        if None in results: return None
        return True
    elif isinstance(node, LogicalOr):
        results = [evaluate_ast(op, scenario) for op in node.operands]
        if True in results: return True
        if None in results: return None
        return False
    elif isinstance(node, ExceptionClause):
        base_res = evaluate_ast(node.base_clause, scenario)
        exc_res = evaluate_ast(node.exception_condition, scenario)
        if base_res is False: return False
        if exc_res is True: return False
        if base_res is None or exc_res is None: return None
        return True
    return None

def parse_article_to_ast(article_ref: str, tree_nodes: list[Any] = None) -> ASTNode | None:
    """A heuristic parser that converts structured list of paragraphs to AST.
    
    In a fully realized system, this might use an LLM pre-processor to 
    map strings like 'Art. 5(1)(a)' to conditions. Here we provide a
    stubbed representation mapping explicit articles to their AST.
    """
    if "Art. 5" in article_ref:
        return LogicalOr([
            ExceptionClause(
                Condition("Subliminal manipulation", "subliminal"),
                Condition("Medical treatment exception", "medical_exception")
            ),
            Condition("Vulnerability exploitation", "vulnerability"),
            ExceptionClause(
                Condition("Real-time RBI in public", "real_time_rbi"),
                Condition("Law enforcement exception", "law_enforcement_rbi")
            )
        ])
    return None
