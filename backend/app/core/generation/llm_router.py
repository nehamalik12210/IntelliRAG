"""
LLM router — supports multiple providers with a unified interface.

Providers:
- Ollama (local)
- OpenAI
- OpenRouter
- Anthropic
- Google
- Groq

All providers are accessed through LangChain's ChatModel abstraction.

Supports:
- Streaming responses
- Non-streaming responses
- Configurable default provider/model
- Frontend model selection
"""

import logging
from typing import AsyncGenerator, Optional

from app.config import settings

logger = logging.getLogger(__name__)

# Cache loaded models
_model_cache: dict[str, object] = {}


def get_chat_model(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.7,
    streaming: bool = True,
):
    """
    Get a LangChain chat model for the specified provider.

    Args:
        provider: LLM provider
        model: Model name/ID
        temperature: Sampling temperature
        streaming: Whether streaming is enabled

    Returns:
        LangChain chat model instance
    """

    # Use configured defaults when frontend doesn't provide overrides
    provider = provider or settings.default_llm_provider
    model = model or settings.default_llm_model

    cache_key = f"{provider}:{model}:{temperature}:{streaming}"

    if cache_key in _model_cache:
        return _model_cache[cache_key]

    # ─────────────────────────────────────────────
    # Ollama
    # ─────────────────────────────────────────────
    if provider == "ollama":
        from langchain_community.chat_models import ChatOllama

        llm = ChatOllama(
            base_url=settings.ollama_base_url,
            model=model,
            temperature=temperature,
            streaming=streaming,
        )

    # ─────────────────────────────────────────────
    # OpenRouter
    # ─────────────────────────────────────────────
    elif provider == "openrouter":
        from langchain_openai import ChatOpenAI

        if not settings.openrouter_api_key:
            raise ValueError(
                "OPENROUTER_API_KEY is not configured."
            )

        llm = ChatOpenAI(
            model=model,
            api_key=settings.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
            temperature=temperature,
            streaming=streaming,
        )

    # ─────────────────────────────────────────────
    # Google Gemini
    # ─────────────────────────────────────────────
    elif provider == "google":
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError as e:
            raise ImportError(
                "Google Gemini support requires the "
                "'langchain-google-genai' package. "
                "Install it with: pip install langchain-google-genai"
            ) from e

        google_key = (
            settings.gemini_api_key
            or settings.google_api_key
        )

        if not google_key:
            raise ValueError(
                "GEMINI_API_KEY or GOOGLE_API_KEY is not configured."
            )

        llm = ChatGoogleGenerativeAI(
            model=model,
            google_api_key=google_key,
            temperature=temperature,
            streaming=streaming,
        )

    # ─────────────────────────────────────────────
    # Groq
    # ─────────────────────────────────────────────
    elif provider == "groq":
        from langchain_openai import ChatOpenAI

        if not settings.groq_api_key:
            raise ValueError(
                "GROQ_API_KEY is not configured."
            )

        llm = ChatOpenAI(
            model=model,
            api_key=settings.groq_api_key,
            base_url="https://api.groq.com/openai/v1",
            temperature=temperature,
            streaming=streaming,
        )

    # ─────────────────────────────────────────────
    # Unknown provider
    # ─────────────────────────────────────────────
    else:
        raise ValueError(
            f"Unknown LLM provider: {provider}"
        )

    _model_cache[cache_key] = llm

    logger.info(
        f"Loaded LLM: {provider}/{model}"
    )

    return llm


async def stream_chat_response(
    messages: list[dict],
    provider: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.7,
) -> AsyncGenerator[str, None]:
    """
    Stream a chat response token by token.

    Args:
        messages: List of message dictionaries
        provider: LLM provider
        model: Model name
        temperature: Sampling temperature

    Yields:
        String tokens as they are generated
    """

    from langchain_core.messages import (
        HumanMessage,
        AIMessage,
        SystemMessage,
    )

    llm = get_chat_model(
        provider=provider,
        model=model,
        temperature=temperature,
        streaming=True,
    )

    # Convert dictionaries into LangChain message objects
    lc_messages = []

    for msg in messages:
        role = msg["role"]
        content = msg["content"]

        if role == "user":
            lc_messages.append(
                HumanMessage(content=content)
            )

        elif role == "assistant":
            lc_messages.append(
                AIMessage(content=content)
            )

        elif role == "system":
            lc_messages.append(
                SystemMessage(content=content)
            )

    async for chunk in llm.astream(lc_messages):
        if chunk.content:
            yield chunk.content


def get_available_models(
    provider: Optional[str] = None
) -> list[dict]:
    """
    List available models for a provider.

    Ollama:
        Queries the local Ollama API.

    Cloud providers:
        Returns the models configured for IntelliRAG.

    Returns:
        List of model dictionaries.
    """

    provider = (
        provider
        or settings.default_llm_provider
    )

    # ─────────────────────────────────────────────
    # Ollama
    # ─────────────────────────────────────────────
    if provider == "ollama":
        try:
            import httpx

            response = httpx.get(
                f"{settings.ollama_base_url}/api/tags",
                timeout=0.5,
            )

            if response.status_code == 200:
                data = response.json()

                return [
                    {
                        "id": m["name"],
                        "name": m["name"],
                        "provider": "ollama",
                    }
                    for m in data.get("models", [])
                ]

        except Exception as e:
            logger.warning(
                f"Failed to list Ollama models: {e}"
            )

        return []

    # ─────────────────────────────────────────────
    # OpenRouter
    # ─────────────────────────────────────────────
    elif provider == "openrouter":
        return [
            {
                "id": "meta-llama/llama-3.1-8b-instruct",
                "name": "Llama 3.1 8B (OpenRouter)",
                "provider": "openrouter",
            },
            {
                "id": "google/gemini-2.5-pro",
                "name": "Gemini 2.5 Pro (OpenRouter)",
                "provider": "openrouter",
            },
            {
                "id": "anthropic/claude-3.5-sonnet",
                "name": "Claude 3.5 Sonnet (OpenRouter)",
                "provider": "openrouter",
            },
            {
                "id": "openai/gpt-4o",
                "name": "GPT-4o (OpenRouter)",
                "provider": "openrouter",
            },
        ]

    # ─────────────────────────────────────────────
    # Google
    # ─────────────────────────────────────────────
    elif provider == "google":
        return [
            {
                "id": "gemini-2.0-flash",
                "name": "Gemini 2.0 Flash",
                "provider": "google",
            },
            {
                "id": "gemini-2.5-pro-preview-05-06",
                "name": "Gemini 2.5 Pro",
                "provider": "google",
            },
        ]

    # ─────────────────────────────────────────────
    # Groq
    # ─────────────────────────────────────────────
    elif provider == "groq":
        return [
            {
                "id": "openai/gpt-oss-120b",
                "name": "GPT-OSS 120B",
                "provider": "groq",
            },
            {
                "id": "openai/gpt-oss-20b",
                "name": "GPT-OSS 20B",
                "provider": "groq",
            },
        ]

    return []
