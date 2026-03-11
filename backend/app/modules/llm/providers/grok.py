import httpx
from openai import AsyncOpenAI

from app.core.exceptions import BadRequestException
from app.modules.llm.crud import get_provider_config
from app.modules.llm.models import BaseLLMClient


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
