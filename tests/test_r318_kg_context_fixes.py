"""R318 — the kg_context defects, pinned.

``app/engines/kg_context.py`` is the ONE graph path that reaches a live answer.
Every other Neo4j consumer is short-circuited by R252 (KB-primary retrieval),
gated off by a code default (2-hop / graph-aware), or structurally discarded at
the R295 fusion budget. So a defect here is a defect in the only thing the
hosted Aura instance actually contributes.

Three defects are pinned below, each measured against the live instance before
being fixed:

1. ORDERING — ``Paragraph.number`` is a STRING, so ``ORDER BY u.number`` sorted
   lexicographically. Because ``collect(...)[..$max_units]`` is applied AFTER
   the sort, the cap took the first N *alphabetically*, not the first N
   provisions. Article 3 (68 definitions, the only node above the cap) therefore
   silently dropped 3(4) 'deployer', 3(5) 'authorised representative',
   3(6) 'importer', 3(7) 'distributor' and 3(8) 'operator'.

2. TIMEOUT / BREAKER BYPASS — both fetchers called ``client.execute_read``
   directly, bypassing the R294 budget AND circuit breaker, so a dark Aura could
   park a request for ~99 s (3 render passes x 2 queries x ~16.5 s of driver
   retry) with nothing to stop it and nothing recording the failures.

3. ROUND-TRIP DUPLICATION — ``_build_context_references_block`` is invoked three
   times per request with identical arguments, so a warm request paid 6 network
   round-trips (~250 ms) for two distinct queries.

These are pure-unit tests: they stub the graph client, so they run offline and
do not need Aura credentials.
"""
from __future__ import annotations

import pytest

import app.engines.kg_context as kg
from app.graph import timeouts


@pytest.fixture(autouse=True)
def _clean_state(monkeypatch):
    """Each test starts with an empty memo and a closed-circuit breaker."""
    kg.reset_kg_context_memo()
    timeouts.reset_graph_circuit()
    monkeypatch.setenv("REGENOLD_KG_CONTEXT", "1")
    yield
    kg.reset_kg_context_memo()
    timeouts.reset_graph_circuit()


#: A citation no other test module fetches, so a memo entry for it can only
#: have come from the test that is currently asserting on it.
_MEMO_PROBE_REF = "Article 97"


class TestExecutorIsolation:
    """kg_context must not share a thread pool with graph_expand_2hop.

    Found by this suite, not by inspection: sharing the 2-hop's 2-worker pool
    made a trivial submit take 1274 ms under full-suite ordering, because R294's
    timed-out futures keep running in their workers. kg_context's 500 ms budget
    then expired before its query started and the graph block silently vanished
    — head-of-line blocking that turns a slow graph into NO graph.
    """

    def test_kg_context_has_its_own_executor(self):
        from app.engines import graph_expand_2hop as g2h

        assert kg._get_kg_executor() is not g2h._get_executor(), (
            "kg_context is sharing the 2-hop thread pool; an abandoned 2-hop "
            "query will starve the one graph consumer that reaches an answer"
        )

    def test_saturated_2hop_pool_does_not_block_kg_context(self, monkeypatch):
        """The exact production failure mode, reproduced deterministically."""
        import threading

        from app.engines import graph_expand_2hop as g2h

        release = threading.Event()
        pool = g2h._get_executor()
        # Occupy every 2-hop worker with an abandoned task, as a timed-out
        # 2-hop query does.
        hogs = [pool.submit(release.wait) for _ in range(4)]
        try:
            rows = [{"id": "article_97", "cite": "Article 97", "title": "t", "units": []}]
            client = _install(monkeypatch, _StubClient(rows=rows))
            out = kg.fetch_provision_hierarchy([_MEMO_PROBE_REF])
            assert len(client.calls) == 1, "kg_context blocked by the 2-hop pool"
            assert out == rows
        finally:
            release.set()
            for h in hogs:
                h.cancel()


class _StubClient:
    """Minimal stand-in for ``app.graph.client`` with a call counter."""

    def __init__(self, rows=None, raises=None, hang_s=0.0):
        self.enabled = True
        self.calls: list[tuple[str, dict]] = []
        self._rows = rows if rows is not None else []
        self._raises = raises
        self._hang_s = hang_s

    def execute_read(self, cypher, params=None, **_kw):
        self.calls.append((cypher, dict(params or {})))
        if self._hang_s:
            import time

            time.sleep(self._hang_s)
        if self._raises:
            raise self._raises
        return list(self._rows)


def _install(monkeypatch, client):
    monkeypatch.setattr(
        "app.graph.client.get_graph_client", lambda: client, raising=True
    )
    return client


# ── 1. Ordering ──────────────────────────────────────────────────────────────


class TestOrderingFix:
    def test_cypher_sorts_numerically_not_lexicographically(self):
        """The load-bearing assertion: a bare ``u.number`` sort is the bug."""
        cy = kg._HIERARCHY_CYPHER
        assert "toInteger(u.number)" in cy, (
            "ORDER BY must coerce the STRING number to an integer; a bare "
            "u.number sort orders Article 3 as 1,10,11,...,29,3,30 and the "
            "[..max_units] slice then DROPS definitions 3(4)-3(8)"
        )
        # The slice must still come after the sort (that ordering is what makes
        # the sort load-bearing at all), and the sort must not be the old form.
        assert "ORDER BY a.id, u.number" not in cy
        assert "[..$max_units]" in cy

    def test_ordering_is_null_safe_for_letter_numbered_units(self):
        """A future seed hanging a letter-numbered unit off an Article must not
        null the comparison — those sort last, alphabetically."""
        cy = kg._HIERARCHY_CYPHER
        assert "coalesce(toInteger(u.number)" in cy
        # tiebreak on the raw string so letter units have a deterministic order
        assert cy.count("u.number") >= 2

    def test_unit_cap_ceiling_covers_article_3(self, monkeypatch):
        """The cap was clamped to 30, making it UNTUNABLE for the one node that
        exceeds it (Article 3 has 68 definitions)."""
        monkeypatch.setenv("REGENOLD_KG_MAX_UNITS", "68")
        assert kg._int_env("REGENOLD_KG_MAX_UNITS", 24, 1, 70) == 68

    def test_default_unit_cap_covers_the_longest_provision(self, monkeypatch):
        """R328.4 — the default MOVED, 24 -> 70, on an explicit operator call.

        This test previously pinned 24 with the rationale: "The DEFAULT must not
        move: raising it adds Stage-2 prompt budget on Answer-Conciseness (the
        one rubric axis with zero headroom) with no A/B." That reasoning is
        still live and is NOT retracted — it is why the pin existed, and why the
        change is recorded here rather than quietly deleted.

        What overrode it: an operator directive (2026-08-13) that no stage may
        receive truncated context. At 24 the graph rendered Article 3 as 24 of
        its 68 definitions under a heading reading "PROVISION STRUCTURE" — with
        3(4)-3(8) absent, i.e. deployer / authorised representative / importer /
        distributor / operator, the five role definitions the role-obligation
        questions turn on. Silently. 70 covers the longest provision.

        The conciseness cost this pin was protecting is REAL and UNMEASURED at
        the new default. It needs an `ab_judge` run; `_DEFAULT_MAX_UNITS = 24`
        restores the old behaviour exactly if that run goes against us.
        """
        monkeypatch.delenv("REGENOLD_KG_MAX_UNITS", raising=False)
        assert kg._DEFAULT_MAX_UNITS == 70
        assert kg._int_env("REGENOLD_KG_MAX_UNITS", kg._DEFAULT_MAX_UNITS, 1, 70) == 70

    def test_article_3_definitions_are_not_silently_cut(self):
        """The concrete regression the raised cap fixes.

        68 definitions must not render as 24 with no marker — a reader (or the
        model) cannot tell a complete list from a truncated one.
        """
        assert kg._DEFAULT_MAX_UNITS >= 68


# ── 2. Budget + breaker ──────────────────────────────────────────────────────


class TestBoundedRead:
    def test_open_circuit_short_circuits_without_querying(self, monkeypatch):
        client = _install(monkeypatch, _StubClient(rows=[{"id": "article_6"}]))
        monkeypatch.setattr(timeouts, "graph_circuit_open", lambda: True)
        assert kg._bounded_execute_read("RETURN 1", {}) == []
        assert client.calls == [], "breaker open but the query still ran"

    def test_driver_error_is_swallowed_and_recorded(self, monkeypatch):
        _install(monkeypatch, _StubClient(raises=RuntimeError("aura down")))
        assert kg._bounded_execute_read("RETURN 1", {}) == []

    def test_repeated_failures_open_the_breaker(self, monkeypatch):
        """The R290 DNS-dead scenario: a sustained outage must stop being paid
        for on every request."""
        _install(monkeypatch, _StubClient(raises=RuntimeError("dns dead")))
        for _ in range(timeouts.GRAPH_BREAKER_THRESHOLD):
            kg._bounded_execute_read("RETURN 1", {})
        assert timeouts.graph_circuit_open(), (
            "breaker did not open after "
            f"{timeouts.GRAPH_BREAKER_THRESHOLD} consecutive failures"
        )

    def test_timeout_is_bounded_by_the_budget(self, monkeypatch):
        """A hung backend must bound the CALLER. (It cannot bound the backend —
        a timed-out future keeps running in the worker thread, per R294.)"""
        import time

        monkeypatch.setenv("REGENOLD_GRAPH_TIMEOUT_MS", "50")
        _install(monkeypatch, _StubClient(rows=[{"id": "x"}], hang_s=3.0))
        t0 = time.perf_counter()
        out = kg._bounded_execute_read("RETURN 1", {})
        elapsed = time.perf_counter() - t0
        assert out == []
        assert elapsed < 1.5, f"caller was not bounded by the budget ({elapsed:.2f}s)"

    def test_disabled_client_returns_empty(self, monkeypatch):
        client = _StubClient()
        client.enabled = False
        _install(monkeypatch, client)
        assert kg._bounded_execute_read("RETURN 1", {}) == []
        assert client.calls == []


# ── 3. Per-request memo ──────────────────────────────────────────────────────


class TestRequestMemo:
    def test_repeated_identical_fetches_hit_the_graph_once(self, monkeypatch):
        # ``_MEMO_PROBE_REF`` rather than a common article: the memo is a
        # ContextVar, and pytest runs same-thread tests in ONE context, so any
        # earlier test in the suite that fetched the same node id leaves an
        # entry this test would then read as a hit — measured, it made this
        # assertion see 0 round-trips instead of 1 under full-suite ordering
        # while passing in isolation. Using a ref no other test touches makes
        # the isolation structural rather than dependent on fixture ordering.
        # The contract under test (3 identical fetches -> 1 round-trip) is
        # unchanged.
        rows = [{"id": "article_97", "cite": "Article 97", "title": "t", "units": []}]
        client = _install(monkeypatch, _StubClient(rows=rows))
        for _ in range(3):
            kg.fetch_provision_hierarchy([_MEMO_PROBE_REF])
        assert len(client.calls) == 1, (
            f"expected 1 round-trip for 3 identical fetches, got {len(client.calls)}"
        )

    def test_memo_keys_on_the_full_argument_set_not_just_refs(self, monkeypatch):
        """A partial key is how a memo silently breaks the R113 guard/prompt
        parity fix. Different caps are different queries."""
        rows = [{"id": "article_6", "cite": "Article 6", "title": "t", "units": []}]
        client = _install(monkeypatch, _StubClient(rows=rows))
        monkeypatch.setenv("REGENOLD_KG_MAX_UNITS", "10")
        kg.fetch_provision_hierarchy(["Article 6"])
        monkeypatch.setenv("REGENOLD_KG_MAX_UNITS", "20")
        kg.fetch_provision_hierarchy(["Article 6"])
        assert len(client.calls) == 2, "cap change must not be served from the memo"

    def test_hierarchy_and_recitals_do_not_share_a_memo_slot(self, monkeypatch):
        client = _install(monkeypatch, _StubClient(rows=[]))
        kg.fetch_provision_hierarchy(["Article 5"])
        kg.fetch_recital_anchors(["Article 5"])
        assert len(client.calls) == 2
        assert client.calls[0][0] != client.calls[1][0]

    def test_different_refs_are_not_conflated(self, monkeypatch):
        rows = [{"id": "article_6", "cite": "Article 6", "title": "t", "units": []}]
        client = _install(monkeypatch, _StubClient(rows=rows))
        kg.fetch_provision_hierarchy(["Article 6"])
        kg.fetch_provision_hierarchy(["Article 26"])
        assert len(client.calls) == 2

    def test_reset_clears_the_memo(self, monkeypatch):
        rows = [{"id": "article_6", "cite": "Article 6", "title": "t", "units": []}]
        client = _install(monkeypatch, _StubClient(rows=rows))
        kg.fetch_provision_hierarchy(["Article 6"])
        kg.reset_kg_context_memo()
        kg.fetch_provision_hierarchy(["Article 6"])
        assert len(client.calls) == 2

    def test_empty_results_are_memoised_too(self, monkeypatch):
        """A miss is a result. Not caching it would keep re-paying the RTT for
        provisions the graph simply has no hierarchy for."""
        client = _install(monkeypatch, _StubClient(rows=[]))
        for _ in range(3):
            kg.fetch_provision_hierarchy(["Article 6"])
        assert len(client.calls) == 1


# ── Fail-soft contract (unchanged by R318) ───────────────────────────────────


class TestFailSoftContractHolds:
    def test_gate_off_never_touches_the_graph(self, monkeypatch):
        client = _install(monkeypatch, _StubClient(rows=[{"id": "x"}]))
        monkeypatch.setenv("REGENOLD_KG_CONTEXT", "0")
        assert kg.fetch_provision_hierarchy(["Article 6"]) == []
        assert kg.fetch_recital_anchors(["Article 6"]) == []
        assert kg.render_kg_context(["Article 6"]) == []
        assert client.calls == []

    def test_unparseable_refs_short_circuit(self, monkeypatch):
        client = _install(monkeypatch, _StubClient(rows=[{"id": "x"}]))
        assert kg.fetch_provision_hierarchy(["not a citation"]) == []
        assert client.calls == []

    def test_render_returns_a_list_on_every_failure_path(self, monkeypatch):
        _install(monkeypatch, _StubClient(raises=RuntimeError("boom")))
        out = kg.render_kg_context(["Article 6"])
        assert isinstance(out, list)
