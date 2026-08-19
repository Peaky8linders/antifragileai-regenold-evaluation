"""Comprehensive tests for the AWS Bedrock provider.

Covers:
  * Credential parsing (composite API key, standard env, default chain)
  * Provider resolution (``resolve_provider("bedrock")``)
  * Converse API request building and response parsing
  * Error classification for all known Bedrock exception types
  * Singleton lifecycle and thread safety
  * Streaming event parsing and cleanup
  * Provider enable detection
  * Security: credential masking in ``__repr__``

All tests are offline — boto3 clients are mocked via ``unittest.mock``
and ``monkeypatch``. No AWS credentials required to run.
"""
from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

# ── Credential parsing ───────────────────────────────────────────────────────


class TestParseBedrockApiKey:
    def test_two_part_key_secret(self) -> None:
        from app.llm.bedrock_client import _parse_bedrock_api_key

        result = _parse_bedrock_api_key("AKIAIOSFODNN7EXAMPLE:wJalrXUtnFEMI")
        assert result["aws_access_key_id"] == "AKIAIOSFODNN7EXAMPLE"
        assert result["aws_secret_access_key"] == "wJalrXUtnFEMI"
        assert "aws_session_token" not in result
        assert "region_name" not in result

    def test_three_part_with_region(self) -> None:
        from app.llm.bedrock_client import _parse_bedrock_api_key

        result = _parse_bedrock_api_key("AKIA123:secret456:us-west-2")
        assert result["aws_access_key_id"] == "AKIA123"
        assert result["aws_secret_access_key"] == "secret456"
        assert result["region_name"] == "us-west-2"
        assert "aws_session_token" not in result

    def test_three_part_with_session_token(self) -> None:
        from app.llm.bedrock_client import _parse_bedrock_api_key

        # Session token doesn't look like a region (no dashes)
        result = _parse_bedrock_api_key("AKIA123:secret456:FwoGZXIvYXdz...")
        assert result["aws_access_key_id"] == "AKIA123"
        assert result["aws_secret_access_key"] == "secret456"
        assert result["aws_session_token"] == "FwoGZXIvYXdz..."
        assert "region_name" not in result

    def test_four_part_full(self) -> None:
        from app.llm.bedrock_client import _parse_bedrock_api_key

        result = _parse_bedrock_api_key("ASIA123:secret:token:eu-west-1")
        assert result["aws_access_key_id"] == "ASIA123"
        assert result["aws_secret_access_key"] == "secret"
        assert result["aws_session_token"] == "token"
        assert result["region_name"] == "eu-west-1"

    def test_single_part_raises(self) -> None:
        from app.llm.bedrock_client import _parse_bedrock_api_key

        with pytest.raises(ValueError, match="at least ACCESS_KEY:SECRET_KEY"):
            _parse_bedrock_api_key("just-a-single-string")

    def test_five_parts_raises(self) -> None:
        from app.llm.bedrock_client import _parse_bedrock_api_key

        with pytest.raises(ValueError, match="too many colon-separated parts"):
            _parse_bedrock_api_key("a:b:c:d:e")

    def test_whitespace_stripped(self) -> None:
        from app.llm.bedrock_client import _parse_bedrock_api_key

        result = _parse_bedrock_api_key("  AKIA123 : secret456 : us-east-1 ")
        assert result["aws_access_key_id"] == "AKIA123"
        assert result["aws_secret_access_key"] == "secret456"
        assert result["region_name"] == "us-east-1"

    def test_empty_string_raises(self) -> None:
        from app.llm.bedrock_client import _parse_bedrock_api_key

        with pytest.raises(ValueError):
            _parse_bedrock_api_key("")


# ── Credential resolution ────────────────────────────────────────────────────


class TestResolveCredentials:
    def test_composite_key_takes_priority(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from app.llm.bedrock_client import _resolve_credentials

        monkeypatch.setenv("AWS_BEDROCK_API_KEY", "AKIA123:secret456:us-west-2")
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "SHOULD_NOT_USE")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "SHOULD_NOT_USE")

        result = _resolve_credentials()
        assert result["aws_access_key_id"] == "AKIA123"
        assert result["aws_secret_access_key"] == "secret456"
        assert result["region_name"] == "us-west-2"

    def test_standard_env_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from app.llm.bedrock_client import _resolve_credentials

        monkeypatch.delenv("AWS_BEDROCK_API_KEY", raising=False)
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIA_STD")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "secret_std")
        monkeypatch.setenv("AWS_SESSION_TOKEN", "tok")
        monkeypatch.setenv("AWS_DEFAULT_REGION", "ap-southeast-1")

        result = _resolve_credentials()
        assert result["aws_access_key_id"] == "AKIA_STD"
        assert result["aws_secret_access_key"] == "secret_std"
        assert result["aws_session_token"] == "tok"
        assert result["region_name"] == "ap-southeast-1"

    def test_default_chain_fallback(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from app.llm.bedrock_client import _resolve_credentials

        monkeypatch.delenv("AWS_BEDROCK_API_KEY", raising=False)
        monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
        monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)
        monkeypatch.delenv("AWS_DEFAULT_REGION", raising=False)
        monkeypatch.delenv("AWS_REGION", raising=False)

        monkeypatch.delenv("BEDROCK_REGION", raising=False)

        result = _resolve_credentials()
        # Only region should be present — boto3 uses default chain for creds
        assert result["region_name"] == "eu-central-1"
        assert "aws_access_key_id" not in result

    def test_region_fallback_order(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from app.llm.bedrock_client import _resolve_region

        # BEDROCK_REGION takes priority
        monkeypatch.setenv("BEDROCK_REGION", "eu-west-1")
        monkeypatch.setenv("AWS_DEFAULT_REGION", "eu-central-1")
        monkeypatch.setenv("AWS_REGION", "ap-northeast-1")
        assert _resolve_region() == "eu-west-1"

        # AWS_DEFAULT_REGION is second
        monkeypatch.delenv("BEDROCK_REGION")
        assert _resolve_region() == "eu-central-1"

        # AWS_REGION is third
        monkeypatch.delenv("AWS_DEFAULT_REGION")
        assert _resolve_region() == "ap-northeast-1"

        # Fallback is an EU region — the default model is an ``eu.`` profile,
        # and us-east-1 cannot resolve one (ValidationException).
        monkeypatch.delenv("AWS_REGION")
        assert _resolve_region() == "eu-central-1"


# ── Provider resolution ──────────────────────────────────────────────────────


class TestProviderResolution:
    def test_bedrock_is_valid_provider(self) -> None:
        from app.llm import resolve_provider

        assert resolve_provider("bedrock") == "bedrock"

    def test_bedrock_case_insensitive(self) -> None:
        from app.llm import resolve_provider

        assert resolve_provider("BEDROCK") == "bedrock"
        assert resolve_provider("Bedrock") == "bedrock"

    def test_existing_providers_unchanged(self) -> None:
        from app.llm import resolve_provider

        for p in ("anthropic", "cli", "openai_wrapper", "groq", "gemini"):
            assert resolve_provider(p) == p


# ── Request building ─────────────────────────────────────────────────────────


class TestBuildConverseKwargs:
    def test_basic_request(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from app.llm.bedrock_client import BedrockRequest, _build_converse_kwargs

        monkeypatch.delenv("BEDROCK_DEFAULT_MODEL", raising=False)

        req = BedrockRequest(user="Hello, Claude!")
        kwargs = _build_converse_kwargs(req)

        assert kwargs["modelId"] == "eu.anthropic.claude-opus-4-8"
        assert kwargs["messages"] == [
            {"role": "user", "content": [{"text": "Hello, Claude!"}]}
        ]
        assert "system" not in kwargs

    def test_system_prompt_separate(self) -> None:
        from app.llm.bedrock_client import BedrockRequest, _build_converse_kwargs

        req = BedrockRequest(user="Hi", system="You are an EU AI Act expert.")
        kwargs = _build_converse_kwargs(req)

        assert kwargs["system"] == [{"text": "You are an EU AI Act expert."}]

    def test_explicit_model_override(self) -> None:
        from app.llm.bedrock_client import BedrockRequest, _build_converse_kwargs

        req = BedrockRequest(
            user="Hi",
            model="us.anthropic.claude-3-haiku-20240307-v1:0",
        )
        kwargs = _build_converse_kwargs(req)
        assert kwargs["modelId"] == "us.anthropic.claude-3-haiku-20240307-v1:0"

    def test_inference_config(self) -> None:
        from app.llm.bedrock_client import BedrockRequest, _build_converse_kwargs

        req = BedrockRequest(
            user="Hi",
            max_tokens=4096,
            temperature=0.7,
            top_p=0.9,
            stop_sequences=["END", "STOP"],
        )
        kwargs = _build_converse_kwargs(req)
        ic = kwargs["inferenceConfig"]

        assert ic["maxTokens"] == 4096
        assert ic["temperature"] == 0.7
        assert ic["topP"] == 0.9
        assert ic["stopSequences"] == ["END", "STOP"]

    def test_tool_config_passthrough(self) -> None:
        from app.llm.bedrock_client import BedrockRequest, _build_converse_kwargs

        tool_config = {
            "tools": [{
                "toolSpec": {
                    "name": "get_weather",
                    "description": "Get weather data",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                "city": {"type": "string"}
                            },
                        }
                    },
                }
            }]
        }
        req = BedrockRequest(user="What's the weather?", tool_config=tool_config)
        kwargs = _build_converse_kwargs(req)
        assert kwargs["toolConfig"] == tool_config

    def test_temperature_zero_is_valid(self) -> None:
        """Temperature=0.0 is a valid explicit value, not a sentinel for 'unset'."""
        from app.llm.bedrock_client import BedrockRequest, _build_converse_kwargs

        req = BedrockRequest(user="Hi", temperature=0.0)
        kwargs = _build_converse_kwargs(req)
        assert kwargs["inferenceConfig"]["temperature"] == 0.0

    def test_env_default_model(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from app.llm.bedrock_client import BedrockRequest, _build_converse_kwargs

        monkeypatch.setenv("BEDROCK_DEFAULT_MODEL", "us.amazon.nova-pro-v1:0")
        req = BedrockRequest(user="Hi")
        kwargs = _build_converse_kwargs(req)
        assert kwargs["modelId"] == "us.amazon.nova-pro-v1:0"


# ── Response parsing ─────────────────────────────────────────────────────────


class TestParseConverseResponse:
    def test_text_response(self) -> None:
        from app.llm.bedrock_client import _parse_converse_response

        raw = {
            "output": {
                "message": {
                    "role": "assistant",
                    "content": [{"text": "Hello! How can I help?"}],
                }
            },
            "usage": {"inputTokens": 10, "outputTokens": 7},
            "stopReason": "end_turn",
        }
        result = _parse_converse_response(raw, "claude-3-sonnet", 150)

        assert result.text == "Hello! How can I help?"
        assert result.model == "claude-3-sonnet"
        assert result.input_tokens == 10
        assert result.output_tokens == 7
        assert result.elapsed_ms == 150
        assert result.finish_reason == "end_turn"
        assert result.error is None
        assert result.tool_use == []

    def test_tool_use_response(self) -> None:
        from app.llm.bedrock_client import _parse_converse_response

        raw = {
            "output": {
                "message": {
                    "role": "assistant",
                    "content": [
                        {"text": "Let me check the weather."},
                        {
                            "toolUse": {
                                "toolUseId": "tool_01",
                                "name": "get_weather",
                                "input": {"city": "Helsinki"},
                            }
                        },
                    ],
                }
            },
            "usage": {"inputTokens": 20, "outputTokens": 15},
            "stopReason": "tool_use",
        }
        result = _parse_converse_response(raw, "claude-3-sonnet", 200)

        assert result.text == "Let me check the weather."
        assert result.finish_reason == "tool_use"
        assert len(result.tool_use) == 1
        assert result.tool_use[0]["name"] == "get_weather"
        assert result.tool_use[0]["input"] == {"city": "Helsinki"}

    def test_empty_content(self) -> None:
        from app.llm.bedrock_client import _parse_converse_response

        raw = {
            "output": {"message": {"role": "assistant", "content": []}},
            "usage": {},
            "stopReason": "",
        }
        result = _parse_converse_response(raw, "test-model", 0)
        assert result.text == ""
        assert result.finish_reason is None
        assert result.input_tokens == 0

    def test_missing_output_keys(self) -> None:
        from app.llm.bedrock_client import _parse_converse_response

        # Completely empty response — should not crash
        result = _parse_converse_response({}, "test-model", 0)
        assert result.text == ""
        assert result.error is None


# ── Error classification ─────────────────────────────────────────────────────


class TestClassifyClientError:
    def _make_client_error(
        self, code: str, status: int = 400, message: str = "test"
    ) -> ClientError:
        return ClientError(
            error_response={
                "Error": {"Code": code, "Message": message},
                "ResponseMetadata": {"HTTPStatusCode": status},
            },
            operation_name="Converse",
        )

    # R346.1 — a dead/expired ABSK key is a GLOBAL credential failure, not a
    # per-model entitlement gap. AWS answers with the same AccessDenied code
    # but a distinct message; it must classify separately, be non-skippable
    # (no chain burn, no wrapper hop) and never be remembered per-model.
    def test_auth_failed_classifies_as_key_invalid(self) -> None:
        from app.llm.bedrock_client import _classify_client_error

        exc = self._make_client_error(
            "AccessDeniedException", 403,
            message="Authentication failed: Please make sure your API Key is valid.",
        )
        assert _classify_client_error(exc) == "api_key_invalid_403"

    def test_key_invalid_is_not_entitlement(self) -> None:
        from app.llm.bedrock_client import is_entitlement_error

        assert not is_entitlement_error("api_key_invalid_403")

    def test_key_invalid_fails_fast_not_skippable(self) -> None:
        """A dead key must NOT advance the chain (every model fails the same
        way) and must NOT reach the wrapper hop — the tunnel is reserved."""
        from app.llm.bedrock_client import is_skippable_error

        assert not is_skippable_error("api_key_invalid_403")

    def test_plain_access_denied_still_entitlement(self) -> None:
        """The distinct marker must not change the pre-existing behaviour for
        genuine per-model entitlement errors ("not available for this account")."""
        from app.llm.bedrock_client import (
            _classify_client_error,
            is_entitlement_error,
            is_skippable_error,
        )

        exc = self._make_client_error("AccessDeniedException", 403)
        classified = _classify_client_error(exc)
        assert classified == "api_access_denied_403"
        assert is_entitlement_error(classified)
        assert is_skippable_error(classified)

    def test_throttling(self) -> None:
        from app.llm.bedrock_client import _classify_client_error

        exc = self._make_client_error("ThrottlingException", 429)
        assert _classify_client_error(exc) == "api_throttled_429"

    def test_access_denied(self) -> None:
        from app.llm.bedrock_client import _classify_client_error

        exc = self._make_client_error("AccessDeniedException", 403)
        assert _classify_client_error(exc) == "api_access_denied_403"

    def test_validation(self) -> None:
        from app.llm.bedrock_client import _classify_client_error

        exc = self._make_client_error("ValidationException", 400)
        assert _classify_client_error(exc) == "api_validation_400"

    def test_model_not_ready(self) -> None:
        from app.llm.bedrock_client import _classify_client_error

        exc = self._make_client_error("ModelNotReadyException", 424)
        assert _classify_client_error(exc) == "api_model_not_ready_424"

    def test_resource_not_found(self) -> None:
        from app.llm.bedrock_client import _classify_client_error

        exc = self._make_client_error("ResourceNotFoundException", 404)
        assert _classify_client_error(exc) == "api_resource_not_found_404"

    def test_model_timeout(self) -> None:
        from app.llm.bedrock_client import _classify_client_error

        exc = self._make_client_error("ModelTimeoutException", 408)
        assert _classify_client_error(exc) == "api_model_timeout_408"

    def test_quota_exceeded(self) -> None:
        from app.llm.bedrock_client import _classify_client_error

        exc = self._make_client_error("ServiceQuotaExceededException", 402)
        assert _classify_client_error(exc) == "api_quota_exceeded_402"

    def test_unknown_error_code(self) -> None:
        from app.llm.bedrock_client import _classify_client_error

        exc = self._make_client_error("SomeNewException", 500)
        assert _classify_client_error(exc) == "api_status_500_SomeNewException"


# ── Provider complete() with mocked boto3 ────────────────────────────────────


class TestBedrockProviderComplete:
    def test_happy_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from app.llm.bedrock_client import (
            BedrockProvider,
            BedrockRequest,
            _reset_bedrock_singletons_for_tests,
        )

        _reset_bedrock_singletons_for_tests()

        mock_client = MagicMock()
        mock_client.converse.return_value = {
            "output": {
                "message": {
                    "role": "assistant",
                    "content": [{"text": "PONG"}],
                }
            },
            "usage": {"inputTokens": 5, "outputTokens": 3},
            "stopReason": "end_turn",
        }

        with patch(
            "app.llm.bedrock_client._get_runtime_client", return_value=mock_client
        ):
            provider = BedrockProvider()
            result = provider.complete(
                BedrockRequest(user="ping", model="us.anthropic.claude-3-5-sonnet-20241022-v2:0")
            )

        assert result.error is None
        assert result.text == "PONG"
        assert result.input_tokens == 5
        assert result.output_tokens == 3
        assert result.finish_reason == "end_turn"
        assert result.elapsed_ms >= 0

    def test_client_error_surfaces_as_error_field(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from app.llm.bedrock_client import (
            BedrockProvider,
            BedrockRequest,
            _reset_bedrock_singletons_for_tests,
        )

        _reset_bedrock_singletons_for_tests()

        mock_client = MagicMock()
        mock_client.converse.side_effect = ClientError(
            error_response={
                "Error": {"Code": "ThrottlingException", "Message": "Rate exceeded"},
                "ResponseMetadata": {"HTTPStatusCode": 429},
            },
            operation_name="Converse",
        )

        with patch(
            "app.llm.bedrock_client._get_runtime_client", return_value=mock_client
        ):
            provider = BedrockProvider()
            result = provider.complete(BedrockRequest(user="hi"))

        assert result.error == "api_throttled_429"
        assert result.text == ""

    def test_botocore_error_surfaces_as_error_field(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from botocore.exceptions import EndpointConnectionError

        from app.llm.bedrock_client import (
            BedrockProvider,
            BedrockRequest,
            _reset_bedrock_singletons_for_tests,
        )

        _reset_bedrock_singletons_for_tests()

        mock_client = MagicMock()
        mock_client.converse.side_effect = EndpointConnectionError(
            endpoint_url="https://bedrock.us-east-1.amazonaws.com"
        )

        with patch(
            "app.llm.bedrock_client._get_runtime_client", return_value=mock_client
        ):
            provider = BedrockProvider()
            result = provider.complete(BedrockRequest(user="hi"))

        assert result.error is not None
        assert "EndpointConnectionError" in result.error


# ── Per-call timeout isolation (CR-02) ───────────────────────────────────────


class TestPerCallTimeoutIsolation:
    def test_default_timeout_uses_singleton(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from app.llm.bedrock_client import (
            BedrockProvider,
            _reset_bedrock_singletons_for_tests,
        )

        _reset_bedrock_singletons_for_tests()

        mock_runtime = MagicMock()

        with patch(
            "app.llm.bedrock_client._get_runtime_client",
            return_value=mock_runtime,
        ):
            provider = BedrockProvider()
            client = provider._client_for_timeout(None)
            assert client is mock_runtime

    def test_custom_timeout_creates_new_client(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from app.llm.bedrock_client import (
            BedrockProvider,
            _reset_bedrock_singletons_for_tests,
        )

        _reset_bedrock_singletons_for_tests()
        monkeypatch.delenv("AWS_BEDROCK_API_KEY", raising=False)
        monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
        monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)

        mock_runtime = MagicMock()
        mock_session = MagicMock()
        mock_custom_client = MagicMock()
        mock_session.client.return_value = mock_custom_client

        with patch(
            "app.llm.bedrock_client._get_runtime_client",
            return_value=mock_runtime,
        ), patch(
            "app.llm.bedrock_client.boto3.Session",
            return_value=mock_session,
        ):
            provider = BedrockProvider()
            # 2.5s != 60s default → must create a new client
            client = provider._client_for_timeout(2.5)
            assert client is mock_custom_client
            assert client is not mock_runtime


# ── Streaming ────────────────────────────────────────────────────────────────


class TestBedrockProviderStream:
    def test_stream_text_events(self) -> None:
        from app.llm.bedrock_client import (
            BedrockProvider,
            BedrockRequest,
            _reset_bedrock_singletons_for_tests,
        )

        _reset_bedrock_singletons_for_tests()

        mock_stream = MagicMock()
        mock_stream.__iter__ = MagicMock(
            return_value=iter([
                {"contentBlockDelta": {"delta": {"text": "Hello"}}},
                {"contentBlockDelta": {"delta": {"text": " world"}}},
                {"messageStop": {"stopReason": "end_turn"}},
                {"metadata": {"usage": {"inputTokens": 10, "outputTokens": 5}}},
            ])
        )
        mock_stream.close = MagicMock()

        mock_client = MagicMock()
        mock_client.converse_stream.return_value = {"stream": mock_stream}

        with patch(
            "app.llm.bedrock_client._get_runtime_client", return_value=mock_client
        ):
            provider = BedrockProvider()
            events = list(provider.stream(BedrockRequest(user="Hi")))

        assert events[0] == {"type": "text", "text": "Hello"}
        assert events[1] == {"type": "text", "text": " world"}
        assert events[2] == {"type": "stop", "stopReason": "end_turn"}
        assert events[3]["type"] == "metadata"
        assert events[3]["inputTokens"] == 10

        # CR-08: stream.close() must be called
        mock_stream.close.assert_called_once()

    def test_stream_cleanup_on_error(self) -> None:
        """Stream close is called even when iteration raises."""
        from app.llm.bedrock_client import (
            BedrockProvider,
            BedrockRequest,
            _reset_bedrock_singletons_for_tests,
        )

        _reset_bedrock_singletons_for_tests()

        mock_stream = MagicMock()
        mock_stream.__iter__ = MagicMock(
            return_value=iter([
                {"contentBlockDelta": {"delta": {"text": "partial"}}},
            ])
        )
        # Simulate error mid-stream
        mock_stream.__iter__.return_value = iter([])
        mock_stream.close = MagicMock()

        mock_client = MagicMock()
        mock_client.converse_stream.return_value = {"stream": mock_stream}

        with patch(
            "app.llm.bedrock_client._get_runtime_client", return_value=mock_client
        ):
            provider = BedrockProvider()
            _ = list(provider.stream(BedrockRequest(user="Hi")))

        # Even on empty/error stream, close MUST be called
        mock_stream.close.assert_called_once()

    def test_stream_client_error_yields_error_event(self) -> None:
        """ClientError during streaming yields an error event, not an exception."""
        from app.llm.bedrock_client import (
            BedrockProvider,
            BedrockRequest,
            _reset_bedrock_singletons_for_tests,
        )

        _reset_bedrock_singletons_for_tests()

        def _raise_client_error():
            yield {"contentBlockDelta": {"delta": {"text": "Hello"}}}
            raise ClientError(
                error_response={
                    "Error": {"Code": "ThrottlingException", "Message": "Rate exceeded"},
                    "ResponseMetadata": {"HTTPStatusCode": 429},
                },
                operation_name="ConverseStream",
            )

        mock_stream = MagicMock()
        mock_stream.__iter__ = MagicMock(return_value=_raise_client_error())
        mock_stream.close = MagicMock()

        mock_client = MagicMock()
        mock_client.converse_stream.return_value = {"stream": mock_stream}

        with patch(
            "app.llm.bedrock_client._get_runtime_client", return_value=mock_client
        ):
            provider = BedrockProvider()
            events = list(provider.stream(BedrockRequest(user="Hi")))

        assert events[0] == {"type": "text", "text": "Hello"}
        assert events[1]["type"] == "error"
        assert "api_throttled_429" in events[1]["error"]
        mock_stream.close.assert_called_once()


# ── Singleton lifecycle ──────────────────────────────────────────────────────


class TestSingletonLifecycle:
    def test_singleton_preserved(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from app.llm.bedrock_client import (
            _reset_bedrock_provider_for_tests,
            get_bedrock_provider,
        )

        _reset_bedrock_provider_for_tests()

        p1 = get_bedrock_provider()
        p2 = get_bedrock_provider()
        assert p1 is p2

        _reset_bedrock_provider_for_tests()

    def test_reset_clears_singleton(self) -> None:
        from app.llm.bedrock_client import (
            _reset_bedrock_provider_for_tests,
            get_bedrock_provider,
        )

        _reset_bedrock_provider_for_tests()
        p1 = get_bedrock_provider()
        _reset_bedrock_provider_for_tests()
        p2 = get_bedrock_provider()
        assert p1 is not p2

        _reset_bedrock_provider_for_tests()


# ── Provider enable detection ────────────────────────────────────────────────


class TestIsBedrockProviderEnabled:
    def test_composite_key_enables(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from app.llm.bedrock_client import is_bedrock_provider_enabled

        monkeypatch.setenv("AWS_BEDROCK_API_KEY", "AKIA:secret")
        assert is_bedrock_provider_enabled() is True

    def test_standard_keys_enable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from app.llm.bedrock_client import is_bedrock_provider_enabled

        monkeypatch.delenv("AWS_BEDROCK_API_KEY", raising=False)
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIA123")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "secret")
        assert is_bedrock_provider_enabled() is True

    def test_no_creds_disables(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from app.llm.bedrock_client import is_bedrock_provider_enabled

        monkeypatch.delenv("AWS_BEDROCK_API_KEY", raising=False)
        monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
        monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)
        assert is_bedrock_provider_enabled() is False

    def test_empty_key_disables(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from app.llm.bedrock_client import is_bedrock_provider_enabled

        monkeypatch.setenv("AWS_BEDROCK_API_KEY", "  ")
        monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
        assert is_bedrock_provider_enabled() is False


# ── Security: credential masking ─────────────────────────────────────────────


class TestCredentialMasking:
    def test_repr_does_not_contain_secrets(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from app.llm.bedrock_client import BedrockProvider

        monkeypatch.setenv("AWS_BEDROCK_API_KEY", "AKIA_VERYSECRET:supersecret:us-east-1")
        provider = BedrockProvider()
        repr_str = repr(provider)

        assert "supersecret" not in repr_str
        assert "AKIA_VERYSECRET" not in repr_str
        assert "BedrockProvider" in repr_str
        assert "us-east-1" in repr_str

    def test_str_does_not_contain_secrets(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from app.llm.bedrock_client import BedrockProvider

        monkeypatch.setenv("AWS_BEDROCK_API_KEY", "AKIA_SECRET:mysecretkey:us-west-2")
        provider = BedrockProvider()
        str_repr = str(provider)

        assert "mysecretkey" not in str_repr
        assert "AKIA_SECRET" not in str_repr


# ── Model prefixes ───────────────────────────────────────────────────────────


class TestModelPrefixes:
    def test_claude_prefixes(self) -> None:
        from app.llm.bedrock_client import CLAUDE_MODEL_PREFIXES

        assert "anthropic.claude" in CLAUDE_MODEL_PREFIXES
        assert "us.anthropic.claude" in CLAUDE_MODEL_PREFIXES

    def test_nova_prefixes(self) -> None:
        from app.llm.bedrock_client import NOVA_MODEL_PREFIXES

        assert "amazon.nova" in NOVA_MODEL_PREFIXES
        assert "us.amazon.nova" in NOVA_MODEL_PREFIXES

    def test_llama_prefixes(self) -> None:
        from app.llm.bedrock_client import LLAMA_MODEL_PREFIXES

        assert "meta.llama" in LLAMA_MODEL_PREFIXES


# ── EU cross-region inference geography (R328) ───────────────────────────────


class TestEUInferenceGeography:
    """The Region and the model's geography prefix are ONE decision.

    Measured 2026-08-11: ``eu.anthropic.claude-opus-4-8`` invoked from
    ``us-east-1`` fails with ``ValidationException: The provided model
    identifier is invalid`` — the profile does not exist in that Region's
    catalog. A ``us-east-1`` default silently breaks every EU deploy.
    """

    def test_default_region_is_in_the_eu_geography(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from app.llm.bedrock_client import (
            DEFAULT_REGION,
            EU_INFERENCE_REGIONS,
            _resolve_default_model,
            _resolve_region,
        )

        for var in ("BEDROCK_REGION", "AWS_DEFAULT_REGION", "AWS_REGION"):
            monkeypatch.delenv(var, raising=False)
        monkeypatch.delenv("BEDROCK_DEFAULT_MODEL", raising=False)

        assert DEFAULT_REGION in EU_INFERENCE_REGIONS
        # The default model and the default Region must agree.
        assert _resolve_default_model().startswith("eu.")
        assert _resolve_region() in EU_INFERENCE_REGIONS

    def test_eu_profile_outside_eu_region_warns(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        from app.llm.bedrock_client import resolve_bedrock_model

        monkeypatch.setenv("BEDROCK_REGION", "us-east-1")
        with caplog.at_level(logging.WARNING, logger="app.llm.bedrock_client"):
            out = resolve_bedrock_model("claude-opus-4-8")

        assert out == "eu.anthropic.claude-opus-4-8"
        assert "bedrock_region_geography_mismatch" in caplog.text

    def test_eu_profile_inside_eu_region_is_quiet(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        from app.llm.bedrock_client import resolve_bedrock_model

        monkeypatch.setenv("BEDROCK_REGION", "eu-central-1")
        with caplog.at_level(logging.WARNING, logger="app.llm.bedrock_client"):
            resolve_bedrock_model("claude-sonnet-5")

        assert "bedrock_region_geography_mismatch" not in caplog.text

    def test_unknown_alias_warns_instead_of_silently_swapping(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        """A typo'd alias silently running a different model makes any model
        A/B measure nothing. It must be audible."""
        from app.llm.bedrock_client import resolve_bedrock_model

        monkeypatch.setenv("BEDROCK_REGION", "eu-central-1")
        monkeypatch.delenv("BEDROCK_DEFAULT_MODEL", raising=False)
        with caplog.at_level(logging.WARNING, logger="app.llm.bedrock_client"):
            out = resolve_bedrock_model("claude-opus-4-8-typo")

        assert out == "eu.anthropic.claude-opus-4-8"
        assert "bedrock_model_alias_unknown" in caplog.text

    def test_operator_targets_resolve_to_eu_profiles(self) -> None:
        """Operator ask 2026-08-11: Opus 4.8 for the RAG, Sonnet 5 for the judge.
        Both right-hand sides verified ACTIVE in eu-central-1 on that date."""
        from app.llm.bedrock_client import resolve_bedrock_model

        assert resolve_bedrock_model("claude-opus-4-8") == "eu.anthropic.claude-opus-4-8"
        assert resolve_bedrock_model("claude-sonnet-5") == "eu.anthropic.claude-sonnet-5"

    def test_every_alias_target_is_an_eu_profile(self) -> None:
        from app.llm.bedrock_client import BEDROCK_MODEL_ALIASES

        for alias, target in BEDROCK_MODEL_ALIASES.items():
            if any(k in alias for k in ("claude", "opus", "sonnet", "haiku")):
                assert target.startswith("eu.anthropic.claude"), (alias, target)
            else:
                assert target.startswith(("eu.", "qwen.", "meta.", "mistral.", "nvidia.", "amazon.")), (alias, target)


class TestTimeoutClientCaching:
    def test_non_default_timeout_client_is_cached(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The judge passes timeout_s=45 on every axis of every row. Building a
        client per call means a fresh connection pool per call."""
        import app.llm.bedrock_client as bc

        bc._reset_bedrock_provider_for_tests()
        calls: list[float] = []

        def _fake_create(service: str, read_timeout: float, max_pool: int,
                         target_region: str | None = None) -> object:
            calls.append(read_timeout)
            return object()

        monkeypatch.setattr(bc, "_create_client_with_auth", _fake_create)
        provider = bc.BedrockProvider()

        first = provider._client_for_timeout(45.0)
        second = provider._client_for_timeout(45.0)
        third = provider._client_for_timeout(45.0)

        assert first is second is third
        assert calls == [45.0]
        bc._reset_bedrock_provider_for_tests()


# ── R328.2 entitlement fallback ──────────────────────────────────────────────


class _StubProvider:
    """Provider whose ``complete`` is driven by a model_id -> response map."""

    def __init__(self, outcomes: dict[str, str | None]) -> None:
        self.outcomes = outcomes
        self.calls: list[str] = []

    def complete(self, req):  # type: ignore[no-untyped-def]
        from app.llm.bedrock_client import BedrockResponse

        self.calls.append(req.model)
        err = self.outcomes.get(req.model, "api_access_denied_403")
        if err is None:
            return BedrockResponse(text="OK", model=req.model)
        return BedrockResponse(error=err, model=req.model)


@pytest.fixture()
def _clean_entitlement_cache():
    import app.llm.bedrock_client as bc

    bc.reset_bedrock_entitlement_cache()
    yield
    bc.reset_bedrock_entitlement_cache()


class TestEntitlementFallback:
    def test_is_entitlement_error_matches_real_classifier_output(self) -> None:
        """The markers must match what ``_classify_client_error`` actually emits.

        A fallback that greps for a string the classifier never produces is the
        inert-feature trap this whole path exists to avoid.
        """
        from app.llm.bedrock_client import is_entitlement_error, is_skippable_error

        # DURABLE per-model denials — safe to remember for the TTL.
        assert is_entitlement_error("api_access_denied_403")
        assert is_entitlement_error("api_resource_not_found_404")

        # ValidationException skips the model but is NOT durable: it also means
        # "this REQUEST is bad", which would be true of every model in the chain.
        assert is_skippable_error("api_validation_400")
        assert not is_entitlement_error("api_validation_400")

        # Transient failures must NOT burn the chain at all.
        for transient in (
            "api_throttled_429",
            "botocore_error: ReadTimeoutError",
            None,
            "",
        ):
            assert not is_entitlement_error(transient)
            assert not is_skippable_error(transient)

    def test_fallback_target_differs_from_pinned_default(self) -> None:
        """Regression: the chain head must not equal its own fallback.

        The 2026-08-13 working tree downgraded the default to the fallback
        target, making the failover a no-op on the exact tier it guarded.
        """
        from app.llm.bedrock_client import (
            BEDROCK_FALLBACK_CHAINS,
            _resolve_default_model,
        )

        opus = BEDROCK_FALLBACK_CHAINS["opus"]
        assert opus[0] == _resolve_default_model()
        assert len(set(opus)) == len(opus) >= 2
        assert opus[0] != opus[-1]

    def test_degrades_to_first_invocable_model(
        self, monkeypatch, _clean_entitlement_cache
    ) -> None:
        import app.llm.bedrock_client as bc

        stub = _StubProvider(
            {
                "eu.anthropic.claude-opus-4-8": "api_access_denied_403",
                "eu.anthropic.claude-opus-5": "api_access_denied_403",
                "eu.anthropic.claude-opus-4-6-v1": None,
            }
        )
        monkeypatch.setattr(bc, "get_bedrock_provider", lambda: stub)

        resp = bc.complete_with_fallback(
            bc.BedrockRequest(user="hi", model="eu.anthropic.claude-opus-4-8")
        )

        assert resp.error is None
        assert resp.model == "eu.anthropic.claude-opus-4-6-v1"
        assert stub.calls == [
            "eu.anthropic.claude-opus-4-8",
            "eu.anthropic.claude-opus-5",
            "eu.anthropic.claude-opus-4-6-v1",
        ]

    def test_does_not_burn_chain_on_transient_error(
        self, monkeypatch, _clean_entitlement_cache
    ) -> None:
        import app.llm.bedrock_client as bc

        stub = _StubProvider({"eu.anthropic.claude-opus-4-8": "api_throttled_429"})
        monkeypatch.setattr(bc, "get_bedrock_provider", lambda: stub)

        resp = bc.complete_with_fallback(
            bc.BedrockRequest(user="hi", model="eu.anthropic.claude-opus-4-8")
        )

        assert resp.error == "api_throttled_429"
        assert stub.calls == ["eu.anthropic.claude-opus-4-8"]

    def test_denied_model_skipped_on_subsequent_calls(
        self, monkeypatch, _clean_entitlement_cache
    ) -> None:
        """The 403 round-trip is paid once per TTL, not once per request."""
        import app.llm.bedrock_client as bc

        stub = _StubProvider(
            {
                "eu.anthropic.claude-opus-4-8": "api_access_denied_403",
                "eu.anthropic.claude-opus-5": "api_access_denied_403",
                "eu.anthropic.claude-opus-4-6-v1": None,
            }
        )
        monkeypatch.setattr(bc, "get_bedrock_provider", lambda: stub)
        req = bc.BedrockRequest(user="hi", model="eu.anthropic.claude-opus-4-8")

        bc.complete_with_fallback(req)
        stub.calls.clear()
        resp = bc.complete_with_fallback(req)

        assert resp.error is None
        assert stub.calls == ["eu.anthropic.claude-opus-4-6-v1"]

    def test_caller_request_is_not_mutated(
        self, monkeypatch, _clean_entitlement_cache
    ) -> None:
        import app.llm.bedrock_client as bc

        stub = _StubProvider(
            {
                "eu.anthropic.claude-opus-4-8": "api_access_denied_403",
                "eu.anthropic.claude-opus-5": None,
            }
        )
        monkeypatch.setattr(bc, "get_bedrock_provider", lambda: stub)
        req = bc.BedrockRequest(user="hi", model="eu.anthropic.claude-opus-4-8")

        bc.complete_with_fallback(req)

        assert req.model == "eu.anthropic.claude-opus-4-8"

    def test_all_denied_returns_last_real_error(
        self, monkeypatch, _clean_entitlement_cache
    ) -> None:
        import app.llm.bedrock_client as bc

        stub = _StubProvider({})  # everything 403s
        monkeypatch.setattr(bc, "get_bedrock_provider", lambda: stub)

        resp = bc.complete_with_fallback(
            bc.BedrockRequest(user="hi", model="eu.anthropic.claude-opus-4-8")
        )

        assert resp.error == "api_access_denied_403"
        assert len(stub.calls) == 3

    def test_unknown_family_has_no_invented_substitute(self) -> None:
        from app.llm.bedrock_client import fallback_chain_for

        assert fallback_chain_for("eu.meta.llama-3-70b") == ()
        assert fallback_chain_for("") == ()
        # A model in a known family but absent from its chain has an unknown
        # rank, so we cannot say what "degrading" means — no substitute.
        assert fallback_chain_for("eu.anthropic.claude-sonnet-9-v9:9") == ()
        # The chain head degrades to everything below it, and only below it.
        assert fallback_chain_for("eu.anthropic.claude-sonnet-5") == (
            "eu.anthropic.claude-sonnet-4-6",
            "eu.anthropic.claude-sonnet-4-5-20250929-v1:0",
        )

    def test_ttl_expiry_lets_a_reminted_key_heal(
        self, monkeypatch, _clean_entitlement_cache
    ) -> None:
        """A re-minted key must heal without a redeploy.

        Drives ``complete_with_fallback`` end-to-end rather than asserting
        ``_is_denied`` with ``_is_denied`` — the earlier version of this test
        proved nothing about healing, and monkeypatched stdlib
        ``time.monotonic`` with a lambda that raised KeyError once the TTL
        branch deleted the key it read.
        """
        import app.llm.bedrock_client as bc

        pinned = "eu.anthropic.claude-opus-4-8"
        state = {"denied": True}

        class _Healing:
            def __init__(self) -> None:
                self.calls: list[str] = []

            def complete(self, req):
                self.calls.append(req.model)
                if req.model == pinned and state["denied"]:
                    return bc.BedrockResponse(
                        error="api_access_denied_403", model=req.model
                    )
                return bc.BedrockResponse(text="OK", model=req.model)

        stub = _Healing()
        monkeypatch.setattr(bc, "get_bedrock_provider", lambda: stub)
        req = bc.BedrockRequest(user="hi", model=pinned)

        # 1) pinned tier denied -> chain degrades, denial remembered
        assert bc.complete_with_fallback(req).model != pinned

        # 2) key is re-minted, but the memo still hides the pinned tier
        state["denied"] = False
        stub.calls.clear()
        assert bc.complete_with_fallback(req).model != pinned
        assert pinned not in stub.calls, "cached denial should skip the pin"

        # 3) TTL lapses -> the pinned tier is re-probed and now serves
        clock = [bc.time.monotonic() + bc._DENIED_TTL_SECONDS + 1]
        monkeypatch.setattr(bc.time, "monotonic", lambda: clock[0])
        stub.calls.clear()

        assert bc.complete_with_fallback(req).model == pinned
        assert stub.calls[0] == pinned

    # ── R328.2 hardening (found by the outside voice) ──────────────────────

    def test_non_head_pin_never_escalates_upward(self) -> None:
        """Pinning a cheaper model must not silently promote to a dearer one."""
        from app.llm.bedrock_client import fallback_chain_for

        chain = fallback_chain_for("eu.anthropic.claude-sonnet-4-6")

        assert "eu.anthropic.claude-sonnet-5" not in chain
        assert chain == ("eu.anthropic.claude-sonnet-4-5-20250929-v1:0",)

    def test_chain_tail_has_nowhere_to_degrade(self) -> None:
        from app.llm.bedrock_client import fallback_chain_for

        assert fallback_chain_for("eu.anthropic.claude-opus-4-6-v1") == ()

    def test_code_bug_is_not_mistaken_for_an_entitlement_error(self) -> None:
        """The blanket ``except Exception`` formats free-form type names.

        ``ParamValidationError`` contains the substring "validation"; treating
        it as an entitlement failure would burn the whole chain on a code bug.
        """
        from app.llm.bedrock_client import is_entitlement_error, is_skippable_error

        for err in (
            "unexpected_error: ParamValidationError: bad param",
            "unexpected_error: ValidationError: nope",
        ):
            assert not is_entitlement_error(err)
            assert not is_skippable_error(err)

    def test_validation_advances_chain_but_is_not_remembered(
        self, monkeypatch, _clean_entitlement_cache
    ) -> None:
        """One oversized prompt must not evict the working model for 15 min.

        ``ValidationException`` covers both "profile unresolvable here" (per
        model) and "input too long" (per request), so it may skip but must
        never be cached.
        """
        import app.llm.bedrock_client as bc

        stub = _StubProvider({
            "eu.anthropic.claude-opus-4-8": "api_validation_400",
            "eu.anthropic.claude-opus-5": "api_validation_400",
            "eu.anthropic.claude-opus-4-6-v1": "api_validation_400",
        })
        monkeypatch.setattr(bc, "get_bedrock_provider", lambda: stub)
        req = bc.BedrockRequest(user="x" * 99, model="eu.anthropic.claude-opus-4-8")

        bc.complete_with_fallback(req)

        assert bc._DENIED_MODELS == {}, "a per-request error was cached per-model"

    def test_all_denied_reprobes_the_tail_not_the_dead_head(
        self, monkeypatch, _clean_entitlement_cache
    ) -> None:
        """The head is 403 by construction; re-probing it burns the round-trip."""
        import app.llm.bedrock_client as bc

        for m in (
            "eu.anthropic.claude-opus-4-8",
            "eu.anthropic.claude-opus-5",
            "eu.anthropic.claude-opus-4-6-v1",
        ):
            bc._note_denied(m)

        stub = _StubProvider({"eu.anthropic.claude-opus-4-6-v1": None})
        monkeypatch.setattr(bc, "get_bedrock_provider", lambda: stub)

        resp = bc.complete_with_fallback(
            bc.BedrockRequest(user="hi", model="eu.anthropic.claude-opus-4-8")
        )

        assert stub.calls == ["eu.anthropic.claude-opus-4-6-v1"]
        assert resp.error is None

    def test_reasoning_content_populates_thinking(self) -> None:
        from app.llm.bedrock_client import _parse_converse_response

        resp = _parse_converse_response(
            {
                "output": {
                    "message": {
                        "content": [
                            {"reasoningContent": {"reasoningText": {"text": "step 1"}}},
                            {"text": "final answer"},
                        ]
                    }
                },
                "usage": {"inputTokens": 3, "outputTokens": 4},
                "stopReason": "end_turn",
            },
            "eu.anthropic.claude-opus-4-8",
            12,
        )

        assert resp.text == "final answer"
        assert resp.thinking == "step 1"
        assert resp.prompt_tokens == 3
        assert resp.completion_tokens == 4
