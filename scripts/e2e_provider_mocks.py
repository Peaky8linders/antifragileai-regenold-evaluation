"""Local wire-protocol mocks for the Stage-2 providers (OpenRouter + Bedrock).

WHY THIS EXISTS. Every provider-routing defect this repo has shipped was
invisible to the test suite because the tests mocked the *seam* rather than the
*wire*: a ``MagicMock`` on ``provider.complete`` cannot show that the reasoning
budget was dropped from the JSON body, that the model name on the wire was not
the model in the config, or that a "fallback" never fired because the gate
above it returned False first. See CLAUDE.md, "the instrument trap" and
"KEYED BUT FROZEN is worse than UNKEYED".

These servers speak the REAL wire protocols on ``127.0.0.1`` and record every
request byte-for-byte, so an end-to-end run through the FastAPI route can be
asserted on what actually reached the provider:

* :class:`MockOpenRouter` — OpenAI-spec ``POST /api/v1/chat/completions``
  (the shape ``_OpenAIWrapperProvider`` posts to OpenRouter).
* :class:`MockBedrock`    — ``POST /model/{modelId}/converse`` (the shape
  botocore posts to ``bedrock-runtime``). Point boto3 at it with
  ``AWS_ENDPOINT_URL_BEDROCK_RUNTIME``.

Both are stdlib-only, thread-per-request, and scriptable: ``behaviour`` decides
whether a call succeeds, errors, throttles or returns a truncated stream, so the
rollover chains and truncation guards can be driven deliberately.
"""

from __future__ import annotations

import json
import threading
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

__all__ = ["MockOpenRouter", "MockBedrock", "RecordedCall"]


class RecordedCall(dict):
    """One recorded request: ``path``, ``headers``, ``body`` (parsed JSON)."""


def _make_handler(server_obj: _RecordingServer) -> type[BaseHTTPRequestHandler]:
    class _Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *_args: Any) -> None:  # noqa: D102 — silence stderr spam
            return

        def do_POST(self) -> None:  # noqa: N802 — BaseHTTPRequestHandler API
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b""
            try:
                body = json.loads(raw.decode("utf-8")) if raw else {}
            except Exception:  # noqa: BLE001
                body = {"_unparsed": raw.decode("utf-8", "replace")}
            call = RecordedCall(
                path=self.path,
                headers={k.lower(): v for k, v in self.headers.items()},
                body=body,
            )
            with server_obj.lock:
                server_obj.calls.append(call)
                index = len(server_obj.calls) - 1
            status, payload = server_obj.respond(call, index)
            encoded = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

    return _Handler


class _RecordingServer:
    """Shared start/stop + call-recording machinery."""

    def __init__(self) -> None:
        self.calls: list[RecordedCall] = []
        self.lock = threading.Lock()
        self._httpd: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self.port = 0

    def respond(self, call: RecordedCall, index: int) -> tuple[int, dict[str, Any]]:
        raise NotImplementedError

    def start(self) -> _RecordingServer:
        handler = _make_handler(self)
        self._httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.port = self._httpd.server_address[1]
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
            self._httpd = None

    def reset(self) -> None:
        with self.lock:
            self.calls.clear()

    def __enter__(self) -> _RecordingServer:
        return self.start()

    def __exit__(self, *_exc: Any) -> None:
        self.stop()


class MockOpenRouter(_RecordingServer):
    """OpenAI-spec Chat Completions server standing in for openrouter.ai.

    ``behaviour(call, index)`` returns one of:
      * ``("ok", text)``              — a normal 200 completion
      * ``("length", text)``          — 200 with ``finish_reason="length"``
      * ``("http", status, message)`` — a non-200 (e.g. 429 / 500)
      * ``("empty", None)``           — 200 with no choices
    Default: every call succeeds with a well-formed legal answer.
    """

    DEFAULT_TEXT = (
        "Yes — the system is high-risk under Article 6(2) read with Annex III, "
        "so the provider must meet the Chapter III Section 2 requirements. "
        "Article 9 requires a documented risk-management system across the "
        "lifecycle, and Article 11 requires the technical documentation in "
        "Annex IV before the system is placed on the market."
    )

    def __init__(
        self,
        behaviour: Callable[[RecordedCall, int], tuple] | None = None,
        base_path: str = "/api/v1",
    ) -> None:
        super().__init__()
        self.behaviour = behaviour
        self.base_path = base_path

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}{self.base_path}"

    def respond(self, call: RecordedCall, index: int) -> tuple[int, dict[str, Any]]:
        outcome: tuple = ("ok", self.DEFAULT_TEXT)
        if self.behaviour is not None:
            outcome = self.behaviour(call, index) or outcome
        kind = outcome[0]
        model = (call["body"] or {}).get("model", "mock-model")
        if kind == "http":
            status = int(outcome[1])
            return status, {"error": {"message": str(outcome[2]), "code": status}}
        if kind == "empty":
            return 200, {"id": "mock", "model": model, "choices": []}
        text = outcome[1] if len(outcome) > 1 else self.DEFAULT_TEXT
        finish = "length" if kind == "length" else "stop"
        message: dict[str, Any] = {"role": "assistant", "content": text}
        if kind == "reasoning":
            message["reasoning"] = outcome[2] if len(outcome) > 2 else "mock reasoning"
        return 200, {
            "id": "mock-openrouter",
            "object": "chat.completion",
            "model": model,
            "choices": [{"index": 0, "message": message, "finish_reason": finish}],
            "usage": {
                "prompt_tokens": 1000,
                "completion_tokens": max(1, len(text) // 4),
                "total_tokens": 1000 + max(1, len(text) // 4),
            },
        }


class MockBedrock(_RecordingServer):
    """``bedrock-runtime`` Converse server.

    Point botocore at it with
    ``AWS_ENDPOINT_URL_BEDROCK_RUNTIME=http://127.0.0.1:{port}``.

    ``behaviour(call, index)`` returns one of:
      * ``("ok", text)``                  — a normal Converse response
      * ``("max_tokens", text)``          — ``stopReason="max_tokens"``
      * ``("error", code, message)``      — an AWS error (e.g.
        ``AccessDeniedException``, ``ThrottlingException``)
    Default: every call succeeds.
    """

    DEFAULT_TEXT = (
        "Yes — Article 6(2) with Annex III makes the system high-risk, and "
        "Article 9 requires the risk-management system throughout the lifecycle."
    )

    _ERROR_STATUS = {
        "ThrottlingException": 429,
        "AccessDeniedException": 403,
        "ValidationException": 400,
        "ResourceNotFoundException": 404,
    }

    def __init__(
        self, behaviour: Callable[[RecordedCall, int], tuple] | None = None
    ) -> None:
        super().__init__()
        self.behaviour = behaviour

    @property
    def endpoint_url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def model_ids(self) -> list[str]:
        """The modelId of every recorded call, in order (parsed from the path)."""
        out: list[str] = []
        for call in self.calls:
            path = call["path"]
            if path.startswith("/model/") and path.endswith("/converse"):
                from urllib.parse import unquote

                out.append(unquote(path[len("/model/") : -len("/converse")]))
        return out

    def respond(self, call: RecordedCall, index: int) -> tuple[int, dict[str, Any]]:
        outcome: tuple = ("ok", self.DEFAULT_TEXT)
        if self.behaviour is not None:
            outcome = self.behaviour(call, index) or outcome
        kind = outcome[0]
        if kind == "error":
            code = str(outcome[1])
            message = str(outcome[2]) if len(outcome) > 2 else code
            status = self._ERROR_STATUS.get(code, 400)
            return status, {"__type": code, "message": message}
        text = outcome[1] if len(outcome) > 1 else self.DEFAULT_TEXT
        stop = "max_tokens" if kind == "max_tokens" else "end_turn"
        content: list[dict[str, Any]] = []
        if kind == "thinking":
            content.append(
                {"reasoningContent": {"reasoningText": {"text": "mock thinking"}}}
            )
        content.append({"text": text})
        return 200, {
            "output": {"message": {"role": "assistant", "content": content}},
            "stopReason": stop,
            "usage": {
                "inputTokens": 1000,
                "outputTokens": max(1, len(text) // 4),
                "totalTokens": 1000 + max(1, len(text) // 4),
            },
            "metrics": {"latencyMs": 5},
        }
