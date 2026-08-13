"""Regression coverage for ``InMemoryAuditStore.verify_chain``.

The store is backed by ``deque(maxlen=max_records)``. Verification used to seed
``prev_hash = ""`` — the genesis entry's sentinel — and walk forward. That is
correct only while the genesis row is still retained. Once the deque evicts it,
``rows[0].previous_hash`` is a real hash, the ``""`` seed mismatches on the very
first row, and a HEALTHY chain reports ``is_valid=False`` — a false tamper alarm
that fires only after sustained production load, i.e. never in a short test.

``verify_chain`` had NO test coverage at all before this file, on either the
happy path or the eviction path.
"""
from __future__ import annotations

import pytest

from app.evidence.store import InMemoryAuditStore


def _fill(store: InMemoryAuditStore, n: int) -> None:
    for i in range(n):
        store.record(
            entry_type="regenold_question",
            payload={"i": i, "q": f"question {i}"},
            article_ref=f"Article {i % 10 + 1}",
        )


class TestVerifyChain:
    def test_empty_chain_is_trivially_valid(self) -> None:
        status = InMemoryAuditStore(max_records=8).verify_chain()

        assert status.is_valid
        assert status.total_entries == 0

    def test_intact_chain_verifies(self) -> None:
        store = InMemoryAuditStore(max_records=64)
        _fill(store, 10)

        status = store.verify_chain()

        assert status.is_valid, status.message
        assert status.total_entries == 10

    def test_survives_genesis_eviction(self) -> None:
        """The regression: overflow the cap so genesis is dropped."""
        store = InMemoryAuditStore(max_records=5)
        _fill(store, 25)  # 5x the cap — genesis is long gone

        status = store.verify_chain()

        assert status.is_valid, (
            f"healthy chain reported broken after eviction: {status.message}"
        )
        assert status.total_entries == 5

    def test_exactly_at_cap_still_verifies(self) -> None:
        """Boundary: the last size at which genesis is still retained."""
        store = InMemoryAuditStore(max_records=6)
        _fill(store, 6)

        status = store.verify_chain()

        assert status.is_valid, status.message

    def test_one_past_cap_still_verifies(self) -> None:
        """Boundary: the first size at which genesis has just evicted."""
        store = InMemoryAuditStore(max_records=6)
        _fill(store, 7)

        status = store.verify_chain()

        assert status.is_valid, status.message

    # ── Tamper evidence must SURVIVE the eviction fix ──────────────────────

    def test_payload_tampering_is_still_detected(self) -> None:
        """Relaxing the genesis seed must not blind the hash check."""
        store = InMemoryAuditStore(max_records=64)
        _fill(store, 10)

        rows = list(store.get_chain(limit=100, ascending=True))
        rows[4].payload["q"] = "TAMPERED"

        status = store.verify_chain()

        assert not status.is_valid
        assert status.first_broken_at == 4

    def test_payload_tampering_detected_after_eviction_too(self) -> None:
        """The evicted-genesis path must not become a tamper blind spot."""
        store = InMemoryAuditStore(max_records=5)
        _fill(store, 25)

        rows = list(store.get_chain(limit=100, ascending=True))
        rows[3].payload["q"] = "TAMPERED"

        status = store.verify_chain()

        assert not status.is_valid
        assert status.first_broken_at == 3

    def test_prefix_deletion_is_detected(self) -> None:
        """Truncating history must not verify clean.

        Seeding verification from ``rows[0].previous_hash`` would let the
        oldest surviving row vouch for itself, making arbitrary deletion
        indistinguishable from natural eviction — in a store that documents
        itself as tamper-evident.
        """
        store = InMemoryAuditStore(max_records=64)
        _fill(store, 10)
        assert store.verify_chain().is_valid

        for _ in range(4):  # delete the first four rows outright
            store._records.popleft()

        status = store.verify_chain()

        assert not status.is_valid, "history truncation verified clean"

    def test_prefix_deletion_detected_after_eviction_too(self) -> None:
        store = InMemoryAuditStore(max_records=8)
        _fill(store, 30)  # genesis long evicted
        assert store.verify_chain().is_valid

        store._records.popleft()
        store._records.popleft()

        assert not store.verify_chain().is_valid

    def test_broken_linkage_is_still_detected(self) -> None:
        store = InMemoryAuditStore(max_records=64)
        _fill(store, 10)

        rows = list(store.get_chain(limit=100, ascending=True))
        rows[6].previous_hash = "0" * 64

        status = store.verify_chain()

        assert not status.is_valid
        assert status.first_broken_at == 6


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
