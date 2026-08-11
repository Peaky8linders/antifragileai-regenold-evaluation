"""CLI Deep-Dive Testing Script for AWS Bedrock Client.

Allows testing real-world Bedrock API calls, foundation model catalog discovery,
inference profiles, text completion, streaming, and tool execution using
either AWS_BEARER_TOKEN_BEDROCK, AWS_BEDROCK_API_KEY, or standard AWS credentials.

Usage examples:
    # Diagnostic connectivity & permission probe
    python scripts/test_bedrock_client.py --probe

    # List catalog models
    python scripts/test_bedrock_client.py --list-models
    python scripts/test_bedrock_client.py --list-models --provider Anthropic

    # Run completion against specific model
    python scripts/test_bedrock_client.py --model eu.anthropic.claude-opus-4-8 --prompt "Explain Article 5 of EU AI Act in 2 sentences."

    # Test streaming
    python scripts/test_bedrock_client.py --model eu.anthropic.claude-opus-4-8 --stream --prompt "List top 3 high-risk AI system categories under Annex III."

    # Test function / tool calling
    python scripts/test_bedrock_client.py --test-tools
"""
from __future__ import annotations

import argparse
import json
import sys
import time

from dotenv import load_dotenv

from app.llm.bedrock_client import (
    BedrockProvider,
    BedrockRequest,
    check_connectivity_and_permissions,
    is_bedrock_provider_enabled,
    list_foundation_models,
)

# Reconfigure stdout for UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()


def main() -> int:
    parser = argparse.ArgumentParser(description="AWS Bedrock LLM Client Deep-Dive Tester")
    parser.add_argument("--probe", action="store_true", help="Run connectivity & permission probe")
    parser.add_argument("--list-models", action="store_true", help="List foundation models in Bedrock catalog")
    parser.add_argument("--provider", type=str, default=None, help="Filter list-models by provider (e.g. Anthropic, Amazon, Meta)")
    parser.add_argument("--model", type=str, default="eu.anthropic.claude-opus-4-8", help="Target model ID or inference profile")
    parser.add_argument("--prompt", type=str, default="Hello from AWS Bedrock client! Give a 1-sentence summary of your capabilities.", help="User prompt to send")
    parser.add_argument("--system", type=str, default="", help="System prompt")
    parser.add_argument("--max-tokens", type=int, default=300, help="Max completion tokens")
    parser.add_argument("--temperature", type=float, default=0.0, help="Temperature")
    parser.add_argument("--stream", action="store_true", help="Stream response tokens")
    parser.add_argument("--test-tools", action="store_true", help="Test tool/function calling with Converse API")
    args = parser.parse_args()

    print("=" * 70)
    print(" AWS Bedrock Client Deep-Dive Test Harness")
    print("=" * 70)
    print(f"Provider Enabled: {is_bedrock_provider_enabled()}")
    print("-" * 70)

    # 1. Probe mode
    if args.probe:
        print(f"\n[1/1] Running probe check for model: {args.model}")
        res = check_connectivity_and_permissions(model_id=args.model)
        print(json.dumps(res, indent=2))
        return 0 if res.get("status") == "ok" else 1

    # 2. List catalog models mode
    if args.list_models:
        print(f"\nListing Foundation Models (Provider filter: {args.provider or 'ALL'})...")
        try:
            models = list_foundation_models(provider=args.provider)
            print(f"Found {len(models)} model(s):\n")
            for m in models:
                provider_name = m.get("providerName", "Unknown")
                model_name = m.get("modelName", "Unknown")
                model_id = m.get("modelId", "")
                modalities = ",".join(m.get("outputModalities", []))
                print(f"  * [{provider_name}] {model_name}")
                print(f"    ID: {model_id} | Modalities: {modalities}")
            return 0
        except Exception as exc:
            print(f"ERROR listing models: {exc}")
            return 1

    # 3. Tool testing mode
    if args.test_tools:
        print(f"\nTesting Tool / Function Calling with Converse API on {args.model}...")
        provider = BedrockProvider()
        tool_config = {
            "tools": [
                {
                    "toolSpec": {
                        "name": "lookup_eu_ai_act_article",
                        "description": "Look up official text for a specific article of the EU AI Act.",
                        "inputSchema": {
                            "json": {
                                "type": "object",
                                "properties": {
                                    "article_number": {"type": "integer", "description": "Article number (e.g. 5, 9, 50)"}
                                },
                                "required": ["article_number"]
                            }
                        }
                    }
                }
            ]
        }
        req = BedrockRequest(
            user="Can you look up Article 5 of the EU AI Act for me?",
            model=args.model,
            max_tokens=300,
            tool_config=tool_config,
        )
        t0 = time.monotonic()
        res = provider.complete(req)
        elapsed_ms = int((time.monotonic() - t0) * 1000)

        print(f"Status: {'SUCCESS' if not res.error else 'ERROR (' + str(res.error) + ')'}")
        print(f"Elapsed: {elapsed_ms} ms | Finish Reason: {res.finish_reason}")
        print(f"Text Response: {res.text or '(No prose text)'}")
        print(f"Tool Call Blocks: {json.dumps(res.tool_use, indent=2)}")
        return 0 if not res.error else 1

    # 4. Streaming mode
    if args.stream:
        print(f"\nStreaming completion from {args.model}...")
        print(f"Prompt: {args.prompt!r}\n")
        provider = BedrockProvider()
        req = BedrockRequest(
            user=args.prompt,
            system=args.system,
            model=args.model,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
        )

        t0 = time.monotonic()
        tokens_received = 0
        print("STREAM OUTPUT: ", end="", flush=True)
        for event in provider.stream(req):
            if event.get("type") == "text":
                print(event["text"], end="", flush=True)
                tokens_received += 1
            elif event.get("type") == "error":
                print(f"\n[STREAM ERROR: {event['error']}]")
            elif event.get("type") == "metadata":
                print(f"\n[USAGE: in={event['inputTokens']}, out={event['outputTokens']}]")
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        print(f"\nStream complete in {elapsed_ms} ms.")
        return 0

    # 5. Standard completion mode
    print(f"\nInvoking completion on model: {args.model}")
    print(f"Prompt: {args.prompt!r}")
    if args.system:
        print(f"System: {args.system!r}")
    print("-" * 70)

    provider = BedrockProvider()
    req = BedrockRequest(
        user=args.prompt,
        system=args.system,
        model=args.model,
        max_tokens=args.max_tokens,
        temperature=args.temperature,
    )

    res = provider.complete(req)
    if res.error:
        print(f"ERROR: {res.error}")
        return 1

    print("\nRESPONSE TEXT:")
    print(res.text)
    print("\nMETRICS:")
    print(f"  Model: {res.model}")
    print(f"  Input Tokens:  {res.input_tokens}")
    print(f"  Output Tokens: {res.output_tokens}")
    print(f"  Elapsed Time:  {res.elapsed_ms} ms")
    print(f"  Finish Reason: {res.finish_reason}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
