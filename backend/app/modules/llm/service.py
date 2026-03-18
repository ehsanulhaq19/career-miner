from app.config import get_settings
from app.core.exceptions import BadRequestException
from app.modules.llm.models import BaseLLMClient
from app.modules.llm.providers.gemini import GeminiLLMClient
from app.modules.llm.providers.grok import GrokLLMClient

DEFAULT_WEB_SEARCH_MODEL = "gemini-2.5-flash"
DEFAULT_WEB_SEARCH_PROVIDER = "gemini"


class LLMFactory:
    """Factory for creating LLM client instances based on provider and model."""

    _PROVIDERS: dict[str, type[BaseLLMClient]] = {
        "grok": GrokLLMClient,
        "gemini": GeminiLLMClient,
    }

    @classmethod
    def get_client(cls, provider_name: str, model_name: str) -> BaseLLMClient:
        """
        Create and return an LLM client instance for the given provider and model.

        Args:
            provider_name: The AI service provider identifier (e.g., grok).
            model_name: The specific model to use within the provider.

        Returns:
            An instance of BaseLLMClient configured for the provider and model.

        Raises:
            BadRequestException: When the provider is not supported.
        """
        provider_key = provider_name.lower().strip()
        client_class = cls._PROVIDERS.get(provider_key)
        if client_class is None:
            supported = ", ".join(cls._PROVIDERS.keys())
            raise BadRequestException(
                detail=f"Unsupported LLM provider: {provider_name}. Supported: {supported}"
            )
        return client_class(model_name=model_name)

    @classmethod
    def get_supported_providers(cls) -> list[str]:
        """
        Return the list of supported LLM provider names.

        Returns:
            List of provider identifiers that can be used with get_client.
        """
        return list(cls._PROVIDERS.keys())

    @classmethod
    def get_web_search_providers(cls) -> list[str]:
        """Return providers that support web search."""
        return ["gemini", "grok"]
