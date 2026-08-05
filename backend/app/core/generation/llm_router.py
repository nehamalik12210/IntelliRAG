"""LLM router — supports multiple providers with a unified interface.

Providers: Ollama (local), OpenAI, Anthropic, Google.
All providers are accessed through LangChain's ChatModel abstraction.
Supports both streaming and non-streaming responses.
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
    """Get a LangChain chat model for the specified provider.

    Args:
        provider: LLM provider (ollama, openai, anthropic, google)
        model: Model name/ID
        temperature: Sampling temperature
        streaming: Whether to enable streaming

    Returns:
        LangChain BaseChatModel instance
    """
    provider = provider or settings.default_llm_provider
    model = model or settings.default_llm_model

    cache_key = f"{provider}:{model}:{temperature}:{streaming}"
    if cache_key in _model_cache:
        return _model_cache[cache_key]

    if provider == "ollama":
        from langchain_community.chat_models import ChatOllama
        llm = ChatOllama(
            base_url=settings.ollama_base_url,
            model=model,
            temperature=temperature,
            streaming=streaming,
        )

    elif provider == "openrouter":
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(
            model=model,
            api_key=settings.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
            temperature=temperature,
            streaming=streaming,
        )

    elif provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI
        llm = ChatGoogleGenerativeAI(
            model=model,
            google_api_key=settings.gemini_api_key or settings.google_api_key,
            temperature=temperature,
            streaming=streaming,
        )

    elif provider == "groq":
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(
            model=model,
            api_key=settings.groq_api_key,
            base_url="https://api.groq.com/openai/v1",
            temperature=temperature,
            streaming=streaming,
        )

    else:
        raise ValueError(f"Unknown LLM provider: {provider}")

    _model_cache[cache_key] = llm
    logger.info(f"Loaded LLM: {provider}/{model}")
    return llm


async def stream_chat_response(
    messages: list[dict],
    provider: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.7,
) -> AsyncGenerator[str, None]:
    """Stream a chat response token by token.

    Args:
        messages: List of message dicts with 'role' and 'content'
        provider: LLM provider
        model: Model name
        temperature: Sampling temperature

    Yields:
        String tokens as they're generated
    """
    from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

    llm = get_chat_model(provider, model, temperature, streaming=True)

    # Convert dict messages to LangChain message objects
    lc_messages = []
    for msg in messages:
        role = msg["role"]
        content = msg["content"]
        if role == "user":
            lc_messages.append(HumanMessage(content=content))
        elif role == "assistant":
            lc_messages.append(AIMessage(content=content))
        elif role == "system":
            lc_messages.append(SystemMessage(content=content))

    async for chunk in llm.astream(lc_messages):
        if chunk.content:
            yield chunk.content


def get_available_models(provider: Optional[str] = None) -> list[dict]:
    """List available models for a provider.

    For Ollama, queries the local API. For cloud providers, returns known models.
    """
    provider = provider or settings.default_llm_provider

    if provider == "ollama":
        try:
            import httpx
            response = httpx.get(f"{settings.ollama_base_url}/api/tags", timeout=0.5)
            if response.status_code == 200:
                data = response.json()
                return [
                    {"id": m["name"], "name": m["name"], "provider": "ollama"}
                    for m in data.get("models", [])
                ]
        except Exception as e:
            logger.warning(f"Failed to list Ollama models: {e}")
        return []

    elif provider == "openrouter":
        return [
            {"id": "meta-llama/llama-3.1-8b-instruct", "name": "Llama 3.1 8B (OR)", "provider": "openrouter"},
            {"id": "google/gemini-2.5-pro", "name": "Gemini 2.5 Pro (OR)", "provider": "openrouter"},
            {"id": "anthropic/claude-3.5-sonnet", "name": "Claude 3.5 Sonnet (OR)", "provider": "openrouter"},
            {"id": "openai/gpt-4o", "name": "GPT-4o (OR)", "provider": "openrouter"},
        ]

    elif provider == "google":
        return [
            {"id": "gemini-2.0-flash", "name": "Gemini 2.0 Flash", "provider": "google"},
            {"id": "gemini-2.5-pro-preview-05-06", "name": "Gemini 2.5 Pro", "provider": "google"},
        ]

    elif provider == "groq":
        return [
            {"id": "llama-3.1-8b-instant", "name": "Llama 3.1 8B", "provider": "groq"},
            {"id": "llama-3.3-70b-versatile", "name": "Llama 3.3 70B", "provider": "groq"},
            {"id": "mixtral-8x7b-32768", "name": "Mixtral 8x7B", "provider": "groq"},
        ]

    return []
