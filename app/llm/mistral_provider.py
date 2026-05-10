"""Mistral provider — real httpx-backed implementation.

The full CodexAI provider uses the official ``mistralai`` SDK; this
bundle ships a minimal httpx wrapper so partners can run the engine
against Mistral without a separate SDK dependency. The wire shape is
preserved so swapping in the SDK is a one-file change later.

Required env: ``MISTRAL_API_KEY``. Optional: ``MISTRAL_BASE_URL``
(default ``https://api.mistral.ai``).
"""
from __future__ import annotations

import atexit
import logging
import os
import time

import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class MistralRequest(BaseModel):
    """Wire-shape model for one Mistral chat-completions call.

    The ``user`` field is intentionally NOT length-constrained at this
    layer — the route's ``RegenoldAskRequest`` already enforces the
    live-user-message non-empty rule, and the engine's ``sanitize_for_llm``
    pass can legitimately shrink an input. Re-checking here previously
    raised a Pydantic ValidationError that surfaced as a generic 500
    instead of a clean deterministic-fallback.
    """

    system: str = ""
    user: str = ""
    model: str = "mistral-large-latest"
    max_tokens: int = 1024
    temperature: float = 0.0


class MistralResponse(BaseModel):
    text: str = ""
    error: str | None = None
    model: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    elapsed_ms: int = 0


def is_mistral_enabled() -> bool:
    """Truthy iff a non-empty ``MISTRAL_API_KEY`` is present in the env."""
    return bool(os.getenv("MISTRAL_API_KEY", "").strip())


class _HttpxMistralProvider:
    """Thin httpx wrapper around ``POST /v1/chat/completions``.

    Single retry on transient 429/5xx + network blips; fail-fast on 4xx
    auth. Never raises — caller path consumes ``MistralResponse.error``
    and falls back to deterministic.
    """

    def __init__(self) -> None:
        self._base_url = os.getenv("MISTRAL_BASE_URL", "https://api.mistral.ai").rstrip("/")
        self._timeout = float(os.getenv("MISTRAL_TIMEOUT_SECONDS", "30"))
        # Long-lived client = one TLS handshake + persistent connection
        # pool. Per-request `httpx.post` opens a fresh TLS handshake
        # (~50-200ms over the public internet) AND leaks sockets in
        # TIME_WAIT under concurrent load. Eng-review round-6 finding —
        # measurable savings on 251-scenario eval runs.
        self._client = httpx.Client(
            base_url=self._base_url,
            timeout=self._timeout,
            limits=httpx.Limits(
                max_keepalive_connections=10,
                max_connections=20,
            ),
        )
        atexit.register(self._close)

    def _close(self) -> None:
        try:
            self._client.close()
        except Exception:  # noqa: BLE001 — atexit best-effort
            pass

    def _headers(self) -> dict[str, str]:
        key = os.getenv("MISTRAL_API_KEY", "").strip()
        return {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def complete(self, req: MistralRequest) -> MistralResponse:
        if not is_mistral_enabled():
            return MistralResponse(error="mistral_api_key_not_set", model=req.model)
        if not (req.user or "").strip():
            # Defensive — the route layer enforces non-empty user input,
            # but if the engine's sanitize-for-LLM pass shrinks an input
            # to empty whitespace we fall back gracefully instead of
            # round-tripping a malformed payload to Mistral.
            return MistralResponse(error="empty_user_after_sanitise", model=req.model)

        body = {
            "model": req.model,
            "messages": [
                {"role": "system", "content": req.system} if req.system else None,
                {"role": "user", "content": req.user},
            ],
            "max_tokens": req.max_tokens,
            "temperature": req.temperature,
        }
        body["messages"] = [m for m in body["messages"] if m is not None]

        start = time.perf_counter()
        for attempt in (1, 2):
            try:
                response = self._client.post(
                    "/v1/chat/completions",
                    headers=self._headers(),
                    json=body,
                )
            except httpx.HTTPError as exc:
                logger.warning("mistral_provider.network_error attempt=%s err=%s", attempt, exc)
                if attempt == 1:
                    time.sleep(0.5)
                    continue
                return MistralResponse(
                    error=f"network_error: {exc!s}"[:200],
                    model=req.model,
                    elapsed_ms=int((time.perf_counter() - start) * 1000),
                )

            if response.status_code in {429, 500, 502, 503, 504} and attempt == 1:
                logger.warning(
                    "mistral_provider.transient_status attempt=%s status=%s",
                    attempt,
                    response.status_code,
                )
                time.sleep(0.5)
                continue

            if response.status_code != 200:
                logger.warning(
                    "mistral_provider.api_error status=%s body=%s",
                    response.status_code,
                    response.text[:200],
                )
                return MistralResponse(
                    error=f"api_status_{response.status_code}: {response.text[:200]}",
                    model=req.model,
                    elapsed_ms=int((time.perf_counter() - start) * 1000),
                )

            try:
                payload = response.json()
            except ValueError as exc:
                return MistralResponse(
                    error=f"decode_error: {exc!s}"[:200],
                    model=req.model,
                    elapsed_ms=int((time.perf_counter() - start) * 1000),
                )

            try:
                choice = payload["choices"][0]
                text = choice["message"]["content"]
            except (KeyError, IndexError, TypeError) as exc:
                return MistralResponse(
                    error=f"shape_error: {exc!s}"[:200],
                    model=req.model,
                    elapsed_ms=int((time.perf_counter() - start) * 1000),
                )

            usage = payload.get("usage") or {}
            return MistralResponse(
                text=text,
                model=payload.get("model", req.model),
                prompt_tokens=int(usage.get("prompt_tokens", 0)),
                completion_tokens=int(usage.get("completion_tokens", 0)),
                elapsed_ms=int((time.perf_counter() - start) * 1000),
            )

        # Defensive — loop guarantees we return inside, but keep mypy happy.
        return MistralResponse(error="exhausted_attempts", model=req.model)


_SINGLETON: _HttpxMistralProvider | None = None


def get_mistral_provider() -> _HttpxMistralProvider:
    global _SINGLETON
    if _SINGLETON is None:
        _SINGLETON = _HttpxMistralProvider()
    return _SINGLETON
