from pydantic import BaseModel, Field


class GenerateContentRequest(BaseModel):
    """Schema for LLM content generation request."""

    provider: str = Field(..., description="AI service provider name (e.g., grok)")
    model: str = Field(..., description="Model name within the provider")
    system_prompt: str = Field(..., description="System instructions for the model")
    prompt: str = Field(..., description="User prompt for content generation")


class GenerateContentResponse(BaseModel):
    """Schema for LLM content generation response."""

    content: str = Field(..., description="Generated text from the LLM")


class SupportedProvidersResponse(BaseModel):
    """Schema for listing supported LLM providers."""

    providers: list[str] = Field(..., description="List of supported provider names")


class WebSearchRequest(BaseModel):
    """Schema for web search request."""

    provider: str = Field(
        default="grok",
        description="AI provider for web search (e.g., grok)",
    )
    model: str | None = Field(
        default=None,
        description="Model name. Defaults to grok-3-mini for grok.",
    )
    query: str = Field(..., description="Search query")


class WebSearchResponse(BaseModel):
    """Schema for web search response."""

    content: str = Field(..., description="Search result text from the provider")
