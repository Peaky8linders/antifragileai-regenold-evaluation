"""Regenold ask-API eval harness.

Categorised scenarios + a deterministic runner that exercises the route
end-to-end via FastAPI ``TestClient``. The runner does NOT call a real
LLM — under test the engine falls back to deterministic parse +
deterministic answer, so we measure the **route-level** behaviours that
the recent hardening targets:

* scope filtering (off-topic regulations, conversational, nonsense)
* non-existent-article refusal
* multi-turn coreference (entity carry-over from prior turns)
* tricky / leading question handling
* prompt-injection refusal

Hallucination at the LLM layer is a separate concern handled via prompt
tightening + the existing ``reference_from_article_ref`` validator; this
harness pins the deterministic invariants that hold under both LLM and
no-LLM paths.

Use:
    py -3.12 -m evals.regenold.runner            # human-readable report
    py -3.12 -m pytest tests/test_regenold_eval.py -v   # CI gate
"""
