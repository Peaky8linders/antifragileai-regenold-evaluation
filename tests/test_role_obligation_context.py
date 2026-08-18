"""R371 — the role x risk-class Stage-2 context block.

These tests pin the failure modes this repo has actually been burned by, not
just the happy path:

* **KEYED BUT FROZEN** — a flag registered in ``_engine_cache_key`` but read at
  import is strictly worse than an unkeyed one: the key makes the arms
  cache-distinct so the engine genuinely re-runs, live Stage-2 is
  non-deterministic so the outputs differ, the fire check PASSES, and the
  harness prints a confident axis table for a value that was identical in both
  arms. So: assert the read is fresh per call.
* **UNKEYED** — an engine-level flag missing from ``_engine_cache_key`` makes
  any in-process A/B measure nothing.
* **"Budget the thing you just added"** — a new context block that renders last
  and is not in the reserved-markers list deletes itself under budget pressure.
* **Hard rule #10** — the graph is additive context only, never a citation.
"""

from __future__ import annotations

import inspect

import pytest

from app.engines import kg_context

FLAG = "REGENOLD_ROLE_OBLIGATION_CONTEXT"


# ── Gate semantics ────────────────────────────────────────────────────────


def test_default_is_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(FLAG, raising=False)
    assert kg_context.role_obligation_context_enabled() is False


@pytest.mark.parametrize("value", ["1", "true", "yes", "on", "ON", "True"])
def test_truthy_values_enable(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv(FLAG, value)
    assert kg_context.role_obligation_context_enabled() is True


@pytest.mark.parametrize("value", ["0", "false", "no", "off", "", "banana"])
def test_falsy_values_disable(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv(FLAG, value)
    assert kg_context.role_obligation_context_enabled() is False


def test_read_is_fresh_per_call(monkeypatch: pytest.MonkeyPatch) -> None:
    """KEYED BUT FROZEN is the worst case — the fire check passes on noise."""
    monkeypatch.setenv(FLAG, "0")
    assert kg_context.role_obligation_context_enabled() is False
    monkeypatch.setenv(FLAG, "1")
    assert kg_context.role_obligation_context_enabled() is True
    monkeypatch.setenv(FLAG, "0")
    assert kg_context.role_obligation_context_enabled() is False


def test_flag_is_read_inside_a_function_not_at_import() -> None:
    """The mechanical form of the same guarantee: the env read must live in the
    function body, so opening the module proves it rather than the test."""
    src = inspect.getsource(kg_context.role_obligation_context_enabled)
    assert f'os.getenv("{FLAG}"' in src


# ── Cache-key registration ────────────────────────────────────────────────


def test_flag_is_registered_in_engine_cache_key() -> None:
    """Unkeyed engine-level flag => the in-process A/B measures nothing."""
    from app.routes import regenold

    src = inspect.getsource(regenold._engine_cache_key)
    assert f'"{FLAG}"' in src, (
        f"{FLAG} is engine-level (it changes Stage-2 input) and MUST be in "
        "_engine_cache_key, or arm B is served arm A's cached answer"
    )


# ── The master gate still wins ────────────────────────────────────────────


def test_master_kg_gate_disables_it(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(FLAG, "1")
    monkeypatch.setenv("REGENOLD_KG_CONTEXT", "0")
    assert kg_context.fetch_role_risk_class_context(["Article 43"]) == []


def test_returns_empty_when_flag_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REGENOLD_KG_CONTEXT", "1")
    monkeypatch.setenv(FLAG, "0")
    assert kg_context.fetch_role_risk_class_context(["Article 43"]) == []


def test_returns_empty_on_no_refs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REGENOLD_KG_CONTEXT", "1")
    monkeypatch.setenv(FLAG, "1")
    assert kg_context.fetch_role_risk_class_context([]) == []


def test_fails_soft_on_transport_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """A graph outage must never break the request — every other fetcher here
    fails soft and so must this one."""
    monkeypatch.setenv("REGENOLD_KG_CONTEXT", "1")
    monkeypatch.setenv(FLAG, "1")
    kg_context.reset_kg_context_memo()

    def _boom(*_a: object, **_k: object) -> None:
        raise RuntimeError("aura down")

    monkeypatch.setattr(kg_context, "_bounded_execute_read", _boom)
    assert kg_context.fetch_role_risk_class_context(["Article 43"]) == []


# ── Budget / self-deletion ────────────────────────────────────────────────


def test_block_marker_is_reserved() -> None:
    """The block renders LAST. Without reserved capacity a large hierarchy
    consumes the ceiling and the feature silently removes itself."""
    assert any(
        "ROLE x RISK-CLASS DUTIES" in m for m in kg_context._R326_RESERVED_MARKERS
    )


# ── Hard rule #10 ─────────────────────────────────────────────────────────


def test_cypher_is_constrained_to_already_cited_provisions() -> None:
    """The query must match only on ``$ids``. If it could reach a provision
    that was not already cited, the graph would become a citation source."""
    cypher = kg_context._ROLE_RISK_CLASS_CYPHER
    assert "$ids" in cypher
    assert "DELETE" not in cypher.upper()
    assert "MERGE" not in cypher.upper()
    assert "CREATE" not in cypher.upper()
    assert "SET " not in cypher.upper()


def test_rendered_block_tells_the_model_not_to_cite_from_it() -> None:
    src = inspect.getsource(kg_context.render_kg_context)
    assert "ROLE x RISK-CLASS DUTIES" in src
    assert "do NOT cite" in src


def test_render_survives_a_dead_graph(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REGENOLD_KG_CONTEXT", "1")
    monkeypatch.setenv(FLAG, "1")
    kg_context.reset_kg_context_memo()
    monkeypatch.setattr(
        kg_context,
        "fetch_role_risk_class_context",
        lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("down")),
    )
    # Must not raise.
    kg_context.render_kg_context(["Article 43"], "who must do conformity assessment?")


def test_block_renders_from_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    """The lever must actually FIRE — a flat A/B and a dead feature look the
    same, so prove the block appears when rows come back."""
    monkeypatch.setenv("REGENOLD_KG_CONTEXT", "1")
    monkeypatch.setenv(FLAG, "1")
    kg_context.reset_kg_context_memo()
    monkeypatch.setattr(
        kg_context,
        "fetch_role_risk_class_context",
        lambda *_a, **_k: [
            {
                "cite": "Article 43",
                "role": "Provider",
                "risk_classes": ["high_risk_annex_iii", "high_risk_annex_i"],
            }
        ],
    )
    parts = kg_context.render_kg_context(["Article 43"], "conformity assessment?")
    blob = "\n".join(parts)
    assert "ROLE x RISK-CLASS DUTIES" in blob
    assert "Article 43" in blob
    assert "Provider" in blob
    assert "high risk annex iii" in blob
