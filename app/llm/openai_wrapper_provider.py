"""OpenAI-compatible-endpoint provider — Claude-Max-via-wrapper bridge.

Targets the local ``claude-code-openai-wrapper`` (an OpenAI Chat
Completions facade over a Claude Max subscription / Anthropic API key).
Default endpoint: ``http://127.0.0.1:8000/v1`` per the wrapper's
upstream defaults.

Activate via env:
    P2P_GRAPH_RAG_PROVIDER=openai_wrapper
    OPENAI_API_BASE=http://127.0.0.1:8000/v1   (optional override)
    OPENAI_API_KEY=dummy                       (any non-empty string)

Why this exists in the bundle:
The Regenold eval round-5 plan A/Bs Sonnet 4.6 against the deterministic
+ Mistral paths. A regulator + a partner can plug in their own
``OPENAI_API_BASE`` (any OpenAI-spec endpoint — OpenAI, OpenRouter,
the wrapper, etc.) and exercise the same eval suite end-to-end.
"""
from __future__ import annotations

import logging
import os
import time

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class OpenAIWrapperRequest(BaseModel):
    system: str = ""
    user: str = Field(min_length=1)
    model: str = "claude-sonnet-4-6"
    max_tokens: int = 1024
    temperature: float = 0.0


class OpenAIWrapperResponse(BaseModel):
    text: str = ""
    error: str | None = None
    model: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    elapsed_ms: int = 0


def is_openai_wrapper_enabled() -> bool:
    """The wrapper is enabled when any non-empty base URL OR a non-default
    OPENAI_API_KEY is present. We don't network-probe at import time —
    callers will hit ``error`` on a missing endpoint.
    """
    return bool(
        os.getenv("OPENAI_API_BASE", "").strip()
        or os.getenv("OPENAI_API_KEY", "").strip()
    )


class _OpenAIWrapperProvider:
    """OpenAI Chat Completions client. One pooled httpx.Client per process."""

    def __init__(self) -> None:
        self._base_url = (
            os.getenv("OPENAI_API_BASE", "").strip().rstrip("/")
            or "http://127.0.0.1:8000/v1"
        )
        self._api_key = os.getenv("OPENAI_API_KEY", "dummy")
        self._timeout = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "60"))
        # Pooled client — see mistral_provider.py for the rationale.
        self._client = httpx.Client(
            base_url=self._base_url,
            timeout=self._timeout,
            limits=httpx.Limits(
                max_keepalive_connections=10,
                max_connections=20,
            ),
        )
        import atexit
        atexit.register(self._close)

    def _close(self) -> None:
        try:
            self._client.close()
        except Exception:  # noqa: BLE001 — atexit best-effort
            pass

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def complete(self, req: OpenAIWrapperRequest) -> OpenAIWrapperResponse:
        body = {
            "model": req.model,
            "messages": [
                {"role": "system", "content": req.system} if req.system else None,
                {"role": "user", "content": req.user},
            ],
            "max_tokens": req.max_tokens,
            "temperature": req.temperature,
            "stream": False,
        }
        body["messages"] = [m for m in body["messages"] if m is not None]

        start = time.perf_counter()
        try:
            response = self._client.post(
                "/chat/completions",
                headers=self._headers(),
                json=body,
            )
        except httpx.HTTPError as exc:
            return OpenAIWrapperResponse(
                error=f"network_error: {exc!s}"[:200],
                model=req.model,
                elapsed_ms=int((time.perf_counter() - start) * 1000),
            )

        if response.status_code != 200:
            return OpenAIWrapperResponse(
                error=f"api_status_{response.status_code}: {response.text[:200]}",
                model=req.model,
                elapsed_ms=int((time.perf_counter() - start) * 1000),
            )

        try:
            payload = response.json()
            choice = payload["choices"][0]
            text = choice["message"]["content"]
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            return OpenAIWrapperResponse(
                error=f"decode_error: {exc!s}"[:200],
                model=req.model,
                elapsed_ms=int((time.perf_counter() - start) * 1000),
            )

        # The wrapper sometimes ships sentinel responses like
        # ``"Not logged in · Please run /login"`` with HTTP 200. Surface
        # those as errors so the engine falls back to deterministic
        # instead of shipping the sentinel as the answer text.
        if "Not logged in" in text or "Please run /login" in text:
            return OpenAIWrapperResponse(
                error=f"wrapper_not_logged_in: {text[:120]}",
                model=req.model,
                elapsed_ms=int((time.perf_counter() - start) * 1000),
            )

        usage = payload.get("usage") or {}
        return OpenAIWrapperResponse(
            text=text,
            model=payload.get("model", req.model),
            prompt_tokens=int(usage.get("prompt_tokens", 0)),
            completion_tokens=int(usage.get("completion_tokens", 0)),
            elapsed_ms=int((time.perf_counter() - start) * 1000),
        )


_SINGLETON: _OpenAIWrapperProvider | None = None


def get_openai_wrapper_provider() -> _OpenAIWrapperProvider:
    global _SINGLETON
    if _SINGLETON is None:
        _SINGLETON = _OpenAIWrapperProvider()
    return _SINGLETON
