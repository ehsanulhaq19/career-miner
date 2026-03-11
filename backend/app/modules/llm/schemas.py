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
