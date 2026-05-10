from __future__ import annotations

import os
from typing import Any, Dict

import httpx


class CodexAIRegenoldClient:
    def __init__(self, *, base_url: str, api_key: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def ask_eu_ai_act(
        self,
        *,
        messages: list[dict],
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/api/v1/regenold/eu-ai-act/ask"
        headers = {"X-Regenold-Api-Key": self.api_key}

        payload: Dict[str, Any] = {"messages": messages}
        with httpx.Client(timeout=30.0) as client:
            r = client.post(url, headers=headers, json=payload)
            r.raise_for_status()
            return r.json()


def codexai_regenold_eu_ai_act_ask(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    MCP tool handler stub.

    Expected args:
      - messages: OpenAI/LiteLLM-style conversation history:
          [{ "role": "system"|"user"|"assistant", "content": "..." }, ...]
    """
    base_url = os.environ["CODEXAI_BASE_URL"]
    api_key = os.environ["CODEXAI_REGENOLD_API_KEY"]

    client = CodexAIRegenoldClient(base_url=base_url, api_key=api_key)
    return client.ask_eu_ai_act(messages=list(args["messages"]))

