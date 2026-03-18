import json
from typing import Any

import httpx
from openai import AsyncOpenAI

from app.core.exceptions import BadRequestException
from app.modules.llm.crud import get_provider_config
from app.modules.llm.models import BaseLLMClient

WEB_SEARCH_TIMEOUT = 30.0


class GrokLLMClient(BaseLLMClient):
    """LLM client implementation for xAI Grok API using OpenAI-compatible interface."""

    BASE_URL = "https://api.x.ai/v1"

    def __init__(self, model_name: str) -> None:
        """
        Initialize the Grok client with the specified model.

        Args:
            model_name: The Grok model identifier (e.g., grok-4-1-fast-reasoning).
        """
        self.model_name = model_name
        config = get_provider_config("grok")
        api_key = config.get("api_key", "") or ""
        if not api_key:
            raise BadRequestException(
                detail="XAI_API_KEY is not configured. Set it in environment or .env."
            )
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=self.BASE_URL,
            timeout=httpx.Timeout(60.0),
        )

    async def web_search(self, query: str) -> str:
        """
        Perform a web search using xAI Grok's web_search tool (Responses API).
        Uses the same _client as generate_content.
        """
        payload = {
            "model": self.model_name,
            "input": [{"role": "user", "content": query}],
            "tools": [{"type": "web_search"}],
        }
        data = await self._client.post(
            "/responses",
            body=payload,
            cast_to=dict[str, Any],
            options={"timeout": httpx.Timeout(WEB_SEARCH_TIMEOUT)},
        )

        text_parts: list[str] = []
        output = data.get("output") or []
        for item in output:
            if isinstance(item, dict):
                content = item.get("content")
                if isinstance(content, list):
                    for c in content:
                        if isinstance(c, dict) and c.get("type") == "output_text":
                            text_parts.append(c.get("text", ""))
                elif isinstance(content, str):
                    text_parts.append(content)
        text = " ".join(text_parts).strip()
        if not text:
            text = json.dumps(data)
        return text

    async def generate_content(self, system_prompt: str, prompt: str) -> str:
        """
        Generate content using Grok chat completion with system and user prompts.

        Args:
            system_prompt: Instructions that define the model's behavior and context.
            prompt: The user's input prompt for content generation.

        Returns:
            The generated text response from Grok.
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]
        completion = await self._client.chat.completions.create(
            model=self.model_name,
            messages=messages,
        )
        message = completion.choices[0].message
        return message.content or ""
