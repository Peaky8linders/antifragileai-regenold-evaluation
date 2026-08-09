import os
os.environ["NEO4J_AUTO_SEED"] = "0"

import pytest
from app.engines.kg_context import (
    fetch_subpoint_detail,
    fetch_deontic_context,
    render_kg_context,
    reset_kg_context_memo,
)

def setup_function():
    reset_kg_context_memo()

def test_fetch_subpoint_detail_disabled_by_default():
    # Without real driver connected, returns empty list fail-softly
    res = fetch_subpoint_detail(["Art. 5"])
    assert isinstance(res, list)

def test_fetch_deontic_context_disabled_by_default():
    res = fetch_deontic_context(["Art. 5"])
    assert isinstance(res, list)

def test_render_kg_context_returns_list():
    res = render_kg_context(["Art. 5"])
    assert isinstance(res, list)
