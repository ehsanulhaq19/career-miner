from fastapi import APIRouter, Depends

from app.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.llm.schemas import (
    GenerateContentRequest,
    GenerateContentResponse,
    SupportedProvidersResponse,
)
from app.modules.llm.service import LLMFactory

router = APIRouter()


@router.get("/providers", response_model=SupportedProvidersResponse)
async def list_providers(
    current_user: User = Depends(get_current_user),
) -> SupportedProvidersResponse:
    """Return the list of supported LLM providers."""
    return SupportedProvidersResponse(
        providers=LLMFactory.get_supported_providers()
    )


@router.post("/generate", response_model=GenerateContentResponse)
async def generate_content(
    request: GenerateContentRequest,
    current_user: User = Depends(get_current_user),
) -> GenerateContentResponse:
    """Generate content using the specified LLM provider and model."""
    client = LLMFactory.get_client(
        provider_name=request.provider,
        model_name=request.model,
    )
    content = await client.generate_content(
        system_prompt=request.system_prompt,
        prompt=request.prompt,
    )
    return GenerateContentResponse(content=content)
