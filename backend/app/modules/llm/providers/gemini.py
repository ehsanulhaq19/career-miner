"""Gemini LLM provider implementation with Google Search grounding for web search."""

import asyncio

from google import genai
from google.genai.types import GenerateContentConfig, GoogleSearch, Tool

from app.core.exceptions import BadRequestException
from app.modules.llm.crud import get_provider_config
from app.modules.llm.models import BaseLLMClient

WEB_SEARCH_TIMEOUT = 30.0


def _gemini_web_search_sync(query: str, model_name: str, api_key: str) -> str:
    """Synchronous web search using Gemini with Google Search grounding."""
    client = genai.Client(api_key=api_key)
    grounding_tool = Tool(google_search=GoogleSearch())
    config = GenerateContentConfig(tools=[grounding_tool])
    response = client.models.generate_content(
        model=model_name,
        contents=query,
        config=config,
    )
    if response and hasattr(response, "text") and response.text:
        return response.text
    return ""


def _gemini_generate_content_sync(
    system_prompt: str, prompt: str, model_name: str, api_key: str
) -> str:
    """Synchronous content generation using Gemini."""
    client = genai.Client(api_key=api_key)
    full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
    response = client.models.generate_content(
        model=model_name,
        contents=full_prompt,
    )
    if response and hasattr(response, "text") and response.text:
        return response.text
    return ""


class GeminiLLMClient(BaseLLMClient):
    """LLM client implementation for Google Gemini API with Google Search grounding."""

    def __init__(self, model_name: str) -> None:
        """
        Initialize the Gemini client with the specified model.

        Args:
            model_name: The Gemini model identifier (e.g., gemini-2.5-flash, gemini-3.1-flash-lite).
        """
        self.model_name = model_name
        config = get_provider_config("gemini")
        api_key = config.get("api_key", "") or ""
        if not api_key:
            raise BadRequestException(
                detail="GEMINI_API_KEY is not configured. Set it in environment or .env."
            )
        self._api_key = api_key

    async def web_search(self, query: str) -> str:
        """
        Perform a web search using Gemini with Google Search grounding.
        Uses the grounding tool to fetch real-time web results.
        """
        return await asyncio.to_thread(
            _gemini_web_search_sync,
            query,
            self.model_name,
            self._api_key,
        )

    async def generate_content(self, system_prompt: str, prompt: str) -> str:
        """
        Generate content using Gemini with system and user prompts.

        Args:
            system_prompt: Instructions that define the model's behavior and context.
            prompt: The user's input prompt for content generation.

        Returns:
            The generated text response from Gemini.
        """
        return await asyncio.to_thread(
            _gemini_generate_content_sync,
            system_prompt,
            prompt,
            self.model_name,
            self._api_key,
        )
