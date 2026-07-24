"""Graph RAG Compliance Q&A Engine Package.

Provides transparent module proxying using Python custom ModuleType subclassing,
ensuring unittest.mock.patch on app.engines.graph_rag synchronizes with _graph_rag_impl.
"""

from __future__ import annotations

import sys
import types
import app.engines._graph_rag_impl as _impl

# Sub-package re-exports
from app.engines.graph_rag.models import GraphQuery, GraphContext
from app.engines.graph_rag.config import config, GraphRAGConfig
from app.engines.graph_rag.parser import (
    deterministic_parse,
    llm_parse_query,
    extract_json_object,
)
from app.engines.graph_rag.risk_engine import (
    is_prohibited_inquiry,
    is_harmonized_product_inquiry,
    is_annex_iii_inquiry,
    is_article_6_3_inquiry,
    evaluate_ast_exemptions,
    is_gpai_inquiry,
    is_transparency_inquiry,
)
from app.engines.graph_rag.medtech import (
    MEDTECH_STANDARD_MAP,
    is_medtech_inquiry,
)
from app.engines.graph_rag.retrieval import enrich_context
from app.engines.graph_rag.generators import extract_citations
from app.engines.graph_rag.pipeline import compute_confidence

# Copy initial attributes from _impl into module globals
_g = globals()
for _k, _v in _impl.__dict__.items():
    if not _k.startswith("__"):
        _g[_k] = _v


class _GraphRAGModule(types.ModuleType):
    """Module proxy that intercepts setattr/getattr to keep _graph_rag_impl in sync."""

    def __getattr__(self, name: str):
        try:
            return _impl.__dict__[name]
        except KeyError:
            raise AttributeError(f"module '{self.__name__}' has no attribute '{name}'") from None

    def __setattr__(self, name: str, value: object):
        super().__setattr__(name, value)
        if hasattr(_impl, name) or not name.startswith("__"):
            _impl.__dict__[name] = value


sys.modules[__name__].__class__ = _GraphRAGModule
