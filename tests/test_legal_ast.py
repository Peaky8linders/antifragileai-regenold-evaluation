import pytest
from app.engines.legal_ast import (
    Condition,
    ExceptionClause,
    LogicalAnd,
    LogicalOr,
    evaluate_ast,
    parse_article_to_ast,
)

def test_condition():
    cond = Condition("Subliminal", "subliminal")
    assert evaluate_ast(cond, {"subliminal": True}) is True
    assert evaluate_ast(cond, {"subliminal": False}) is False
    assert evaluate_ast(cond, {}) is None

def test_logical_and():
    ast = LogicalAnd([Condition("A", "a"), Condition("B", "b")])
    assert evaluate_ast(ast, {"a": True, "b": True}) is True
    assert evaluate_ast(ast, {"a": True, "b": False}) is False
    assert evaluate_ast(ast, {"a": True}) is None

def test_logical_or():
    ast = LogicalOr([Condition("A", "a"), Condition("B", "b")])
    assert evaluate_ast(ast, {"a": False, "b": True}) is True
    assert evaluate_ast(ast, {"a": False, "b": False}) is False
    assert evaluate_ast(ast, {"a": False}) is None

def test_exception_clause():
    ast = ExceptionClause(Condition("Base", "base"), Condition("Exc", "exc"))
    assert evaluate_ast(ast, {"base": True, "exc": False}) is True
    assert evaluate_ast(ast, {"base": True, "exc": True}) is False
    assert evaluate_ast(ast, {"base": False, "exc": False}) is False

def test_parse_article():
    ast = parse_article_to_ast("Art. 5")
    assert ast is not None
    assert evaluate_ast(ast, {"subliminal": True, "medical_exception": False}) is True
    # If one exception is met, but we don't know about the others, the OR evaluates to None
    assert evaluate_ast(ast, {"subliminal": True, "medical_exception": True}) is None
    assert evaluate_ast(ast, {"vulnerability": True}) is True
