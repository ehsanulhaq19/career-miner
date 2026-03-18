from fastapi import APIRouter, Depends

from app.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.llm.schemas import (
    GenerateContentRequest,
    GenerateContentResponse,
    SupportedProvidersResponse,
    WebSearchRequest,
    WebSearchResponse,
)
from app.modules.llm.service import DEFAULT_WEB_SEARCH_MODEL, LLMFactory

router = APIRouter()


@router.get("/providers", response_model=SupportedProvidersResponse)
async def list_providers(
    current_user: User = Depends(get_current_user),
) -> SupportedProvidersResponse:
    """Return the list of supported LLM providers."""
    return SupportedProvidersResponse(
        providers=LLMFactory.get_supported_providers()
    )


@router.get("/web-search/providers", response_model=SupportedProvidersResponse)
async def list_web_search_providers(
    current_user: User = Depends(get_current_user),
) -> SupportedProvidersResponse:
    """Return the list of providers that support web search."""
    return SupportedProvidersResponse(
        providers=LLMFactory.get_web_search_providers()
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


@router.post("/web-search", response_model=WebSearchResponse)
async def web_search_endpoint(
    request: WebSearchRequest,
    current_user: User = Depends(get_current_user),
) -> WebSearchResponse:
    """Perform a web search using the specified LLM provider (e.g., Grok)."""
    model = request.model or DEFAULT_WEB_SEARCH_MODEL
    client = LLMFactory.get_client(
        provider_name=request.provider,
        model_name=model,
    )
    content = await client.web_search(request.query)
    return WebSearchResponse(content=content)
