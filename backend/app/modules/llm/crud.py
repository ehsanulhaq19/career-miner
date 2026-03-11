from app.config import get_settings


def get_provider_config(provider_name: str) -> dict:
    """
    Retrieve configuration for the given LLM provider from application settings.

    Args:
        provider_name: The provider identifier (e.g., grok).

    Returns:
        Dictionary containing provider-specific configuration such as api_key.
    """
    settings = get_settings()
    provider_key = provider_name.lower()
    if provider_key == "grok":
        return {"api_key": getattr(settings, "XAI_API_KEY", "") or ""}
    return {}
