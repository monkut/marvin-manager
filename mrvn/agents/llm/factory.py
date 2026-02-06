"""Factory for creating LLM clients based on provider."""

import logging
from typing import Any

from agents.llm.base import BaseLLMClient
from agents.models import LLMProvider

logger = logging.getLogger(__name__)


def create_llm_client(
    provider: str | LLMProvider,
    *,
    api_key: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
    **kwargs: Any,
) -> BaseLLMClient:
    """Create an LLM client for the specified provider.

    Args:
        provider: The LLM provider (anthropic, gemini, ollama, vllm).
        api_key: API key for authentication.
        base_url: Base URL for the API.
        model: Model name to use.
        **kwargs: Additional provider-specific options.

    Returns:
        BaseLLMClient instance for the provider.

    Raises:
        ValueError: If the provider is not supported.
    """
    # Normalize provider string
    if isinstance(provider, LLMProvider):
        provider_str = provider.value
    else:
        provider_str = provider.lower()

    if provider_str == LLMProvider.ANTHROPIC.value:
        from agents.llm.anthropic_client import AnthropicClient  # noqa: PLC0415

        return AnthropicClient(
            api_key=api_key,
            base_url=base_url,
            model=model,
            **kwargs,
        )

    if provider_str == LLMProvider.GEMINI.value:
        from agents.llm.gemini_client import GeminiClient  # noqa: PLC0415

        return GeminiClient(
            api_key=api_key,
            base_url=base_url,
            model=model,
            **kwargs,
        )

    if provider_str == LLMProvider.OLLAMA.value:
        from agents.llm.ollama_client import OllamaClient  # noqa: PLC0415

        return OllamaClient(
            api_key=api_key,
            base_url=base_url,
            model=model,
            **kwargs,
        )

    if provider_str == LLMProvider.VLLM.value:
        # vLLM uses OpenAI-compatible API
        from agents.llm.openai_client import OpenAIClient  # noqa: PLC0415

        return OpenAIClient(
            api_key=api_key or "dummy",  # vLLM may not require auth
            base_url=base_url,
            model=model,
            **kwargs,
        )

    raise ValueError(f"Unsupported LLM provider: {provider}")


async def create_client_from_agent(agent: Any) -> BaseLLMClient:
    """Create an LLM client from an Agent model instance.

    Args:
        agent: Agent model instance.

    Returns:
        Configured BaseLLMClient.
    """
    # Get API key from credentials if available
    api_key = None
    try:
        if hasattr(agent, "credential") and agent.credential:
            api_key = agent.credential.encrypted_api_key
    except AttributeError:
        logger.debug("No credentials found for agent %s", agent.name)

    return create_llm_client(
        provider=agent.provider,
        api_key=api_key,
        base_url=agent.base_url or None,
        model=agent.model_name,
        temperature=agent.temperature,
        max_tokens=agent.max_tokens,
    )
