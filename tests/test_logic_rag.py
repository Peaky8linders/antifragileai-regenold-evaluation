"""R117 — LogicRAG hardening regression tests.

LogicRAG (``app/engines/logic_rag.py``) is the LLM-driven retrieval-replacement
engine wired into ``ask_compliance_question`` and default-ON in production
(``railway.toml`` REGENOLD_LOGIC_RAG=1). Before R117 it shipped with ZERO test
coverage, was unguarded (any exception 500'd the route), hardcoded a 120s
timeout, and dropped ``risk_level``. These tests pin the R117 hardening:

  * fail-soft DAG / JSON parsing (empty, garbage, object-not-list, fenced);
  * topological sort ranks + cycle safety (must terminate);
  * context-merge de-duplication by id;
  * ``execute_logic_rag`` returns a valid GraphContext with the wrapper off and
    threads ``risk_level`` through to retrieval;
  * THE GUARD — ``ask_compliance_question`` never raises when LogicRAG explodes
    (it falls back to the deterministic retrieval path), and LogicRAG is NOT
    invoked when REGENOLD_LOGIC_RAG is unset.
"""

from app.engines import logic_rag
from app.engines.graph_rag import GraphContext, ask_compliance_question
from app.engines.logic_rag import (
    _decompose_to_dag,
    _merge_contexts,
    _topological_sort,
    execute_logic_rag,
)
from app.models import GraphRAGRequest

_COMPLEX_Q = "We are both a provider and a deployer of a high-risk AI system; what are our obligations under Article 16 versus Article 26?"


class TestDecomposeFailSoft:
    def test_empty_output_falls_back_to_single_node(self, monkeypatch):
        monkeypatch.setattr(logic_rag, "_call_llm", lambda *a, **k: "")
        assert _decompose_to_dag("What is Article 5?") == [
            {"id": 1, "query": "What is Article 5?", "dependencies": []}
        ]

    def test_garbage_output_falls_back(self, monkeypatch):
        monkeypatch.setattr(logic_rag, "_call_llm", lambda *a, **k: "not json at all {[")
        assert _decompose_to_dag("Q") == [{"id": 1, "query": "Q", "dependencies": []}]

    def test_json_object_not_list_falls_back(self, monkeypatch):
        monkeypatch.setattr(logic_rag, "_call_llm", lambda *a, **k: '{"answer": "42"}')
        assert _decompose_to_dag("Q") == [{"id": 1, "query": "Q", "dependencies": []}]

    def test_valid_dag_parsed(self, monkeypatch):
        monkeypatch.setattr(
            logic_rag,
            "_call_llm",
            lambda *a, **k: '[{"id":1,"query":"a","dependencies":[]},{"id":2,"query":"b","dependencies":[1]}]',
        )
        dag = _decompose_to_dag("Q")
        assert len(dag) == 2 and dag[1]["dependencies"] == [1]

    def test_markdown_fenced_json_parsed(self, monkeypatch):
        monkeypatch.setattr(
            logic_rag,
            "_call_llm",
            lambda *a, **k: '```json\n[{"id":1,"query":"a","dependencies":[]}]\n```',
        )
        assert _decompose_to_dag("Q") == [{"id": 1, "query": "a", "dependencies": []}]


class TestTopologicalSort:
    def test_linear_deps_split_into_ordered_ranks(self):
        dag = [
            {"id": 1, "query": "a", "dependencies": []},
            {"id": 2, "query": "b", "dependencies": [1]},
        ]
        ranks = _topological_sort(dag)
        assert [n["id"] for n in ranks[0]] == [1]
        assert [n["id"] for n in ranks[1]] == [2]

    def test_independent_nodes_same_rank(self):
        dag = [
            {"id": 1, "query": "a", "dependencies": []},
            {"id": 2, "query": "b", "dependencies": []},
        ]
        ranks = _topological_sort(dag)
        assert len(ranks) == 1 and {n["id"] for n in ranks[0]} == {1, 2}

    def test_cycle_terminates_and_surfaces_all_nodes(self):
        dag = [
            {"id": 1, "query": "a", "dependencies": [2]},
            {"id": 2, "query": "b", "dependencies": [1]},
        ]
        ranks = _topological_sort(dag)  # must NOT hang
        assert {n["id"] for rank in ranks for n in rank} == {1, 2}


class TestMergeContexts:
    def test_dedup_article_info_by_id(self):
        base = GraphContext()
        base.article_info = [{"id": "A"}]
        new = GraphContext()
        new.article_info = [{"id": "A"}, {"id": "B"}]
        _merge_contexts(base, new)
        assert [a["id"] for a in base.article_info] == ["A", "B"]


class TestExecuteLogicRag:
    def test_wrapper_off_returns_valid_context(self, monkeypatch):
        # Wrapper disabled -> _call_llm returns "" -> single-node DAG ->
        # deterministic retrieve. No network, no exception.
        monkeypatch.setattr(logic_rag, "is_openai_wrapper_enabled", lambda: False)
        ctx = execute_logic_rag(
            "What are the obligations of a provider of a high-risk AI system?"
        )
        assert isinstance(ctx, GraphContext)
        assert ctx.retrieval_path == "logic_rag"

    def test_risk_level_threaded_to_retrieval(self, monkeypatch):
        seen = {}

        def fake_retrieve(parsed, risk_level=None, answers=None):
            seen["risk_level"] = risk_level
            return GraphContext()

        monkeypatch.setattr(logic_rag, "is_openai_wrapper_enabled", lambda: False)
        monkeypatch.setattr(logic_rag, "_retrieve_from_graph", fake_retrieve)
        execute_logic_rag("Q", {}, risk_level="risk_high")
        assert seen["risk_level"] == "risk_high"


class TestLogicRagGuard:
    def test_exception_falls_back_to_deterministic(self, monkeypatch):
        """The critical R117 fix: a LogicRAG exception must NOT propagate (no 500)."""
        monkeypatch.setenv("REGENOLD_LOGIC_RAG", "1")
        monkeypatch.setattr(
            "app.engines.question_complexity.is_complex_question", lambda *a, **k: True
        )

        def boom(*a, **k):
            raise RuntimeError("LogicRAG exploded")

        monkeypatch.setattr(logic_rag, "execute_logic_rag", boom)
        res = ask_compliance_question(GraphRAGRequest(question=_COMPLEX_Q))
        assert res is not None
        assert res.answer  # deterministic fallback produced a real answer

    def test_disabled_does_not_invoke_logic_rag(self, monkeypatch):
        monkeypatch.delenv("REGENOLD_LOGIC_RAG", raising=False)

        def boom(*a, **k):
            raise AssertionError("LogicRAG must NOT run when REGENOLD_LOGIC_RAG is unset")

        monkeypatch.setattr(logic_rag, "execute_logic_rag", boom)
        res = ask_compliance_question(GraphRAGRequest(question=_COMPLEX_Q))
        assert res is not None
