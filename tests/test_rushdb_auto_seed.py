"""Tests for the RushDB auto-seed startup hook in ``app/main.py``."""
from __future__ import annotations

import logging
import threading
import time
from typing import Any
from unittest.mock import MagicMock

import pytest


@pytest.fixture(autouse=True)
def _reset_env(monkeypatch: pytest.MonkeyPatch):
    for k in (
        "RUSHDB_AUTH_TOKEN",
        "RUSHDB_API_KEY",
        "REGENOLD_SKIP_STARTUP_LOG",
    ):
        monkeypatch.delenv(k, raising=False)
    yield


def _call_hook() -> None:
    from app.main import _maybe_auto_seed_rushdb
    _maybe_auto_seed_rushdb()


class TestRushdbAutoSeed:
    def test_disabled_by_default(self, monkeypatch, caplog):
        # By default, RUSHDB_AUTH_TOKEN is not set
        import app.main as _main
        caplog.set_level(logging.INFO, logger=_main.__name__)
        
        # Ensure client get_metadata is not called
        get_meta_mock = MagicMock()
        monkeypatch.setattr("app.graph.rushdb_client.get_metadata", get_meta_mock)
        
        _call_hook()
        
        get_meta_mock.assert_not_called()

    def test_skip_startup_log_short_circuits(self, monkeypatch):
        monkeypatch.setenv("REGENOLD_SKIP_STARTUP_LOG", "1")
        monkeypatch.setenv("RUSHDB_AUTH_TOKEN", "fake-token")
        
        get_meta_mock = MagicMock()
        monkeypatch.setattr("app.graph.rushdb_client.get_metadata", get_meta_mock)
        
        _call_hook()
        
        get_meta_mock.assert_not_called()

    def test_seed_current_skips_seed(self, monkeypatch, caplog):
        import app.main as _main
        from scripts.seed_rushdb_kb import SEED_VERSION
        from app.data.kb import KB_VERSION
        
        monkeypatch.setenv("RUSHDB_AUTH_TOKEN", "fake-token")
        monkeypatch.setattr("app.graph.rushdb_client.is_enabled", lambda: True)
        
        meta = {"seed_version": SEED_VERSION, "kb_version": KB_VERSION}
        monkeypatch.setattr("app.graph.rushdb_client.get_metadata", lambda: meta)
        
        run_seed_mock = MagicMock()
        monkeypatch.setattr("scripts.seed_rushdb_kb.run_seed", run_seed_mock)
        
        caplog.set_level(logging.INFO, logger=_main.__name__)
        _call_hook()
        
        assert "rushdb_seed_current" in caplog.text
        run_seed_mock.assert_not_called()

    def test_seed_needed_triggers_thread(self, monkeypatch, caplog):
        import app.main as _main
        
        monkeypatch.setenv("RUSHDB_AUTH_TOKEN", "fake-token")
        monkeypatch.setattr("app.graph.rushdb_client.is_enabled", lambda: True)
        
        # Outdated metadata
        meta = {"seed_version": "outdated", "kb_version": "old"}
        monkeypatch.setattr("app.graph.rushdb_client.get_metadata", lambda: meta)
        
        run_seed_mock = MagicMock(return_value={"status": "ok", "counts": {"Article": 113}})
        monkeypatch.setattr("scripts.seed_rushdb_kb.run_seed", run_seed_mock)
        
        caplog.set_level(logging.INFO, logger=_main.__name__)
        _call_hook()
        
        assert "rushdb_seed_started" in caplog.text
        
        # Wait for daemon thread
        deadline = time.perf_counter() + 2.0
        while time.perf_counter() < deadline:
            alive = any(t.is_alive() and t.name == "regenold-auto-seed-rushdb" for t in threading.enumerate())
            if not alive:
                break
            time.sleep(0.01)
            
        run_seed_mock.assert_called_once_with(dry_run=False)
        assert "rushdb_seed_completed" in caplog.text
        assert "status=ok" in caplog.text
