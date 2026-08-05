"""Models API — list available LLMs and embedding models."""

from fastapi import APIRouter
from app.core.generation.llm_router import get_available_models
from app.config import settings

router = APIRouter(prefix="/api/models", tags=["models"])


@router.get("")
async def list_models():
    """List available LLM models from all configured providers."""
    all_models = []
    providers = ["ollama", "openrouter", "google", "groq"]

    for provider in providers:
        # Only list if API key is configured (or if it's ollama)
        if provider == "ollama":
            all_models.extend(get_available_models(provider))
        elif provider == "openrouter" and settings.openrouter_api_key:
            all_models.extend(get_available_models(provider))
        elif provider == "google" and (settings.gemini_api_key or settings.google_api_key):
            all_models.extend(get_available_models(provider))
        elif provider == "groq" and settings.groq_api_key:
            all_models.extend(get_available_models(provider))

    return {
        "models": all_models,
        "default_provider": settings.default_llm_provider,
        "default_model": settings.default_llm_model,
    }


@router.get("/embeddings")
async def list_embedding_models():
    """List current embedding model configuration."""
    return {
        "current": {
            "provider": settings.embedding_provider,
            "model": settings.embedding_model,
            "dimension": settings.embedding_dimension,
        },
        "available_local": [
            {"model": "sentence-transformers/all-MiniLM-L6-v2", "dimension": 384, "provider": "local"},
            {"model": "BAAI/bge-small-en-v1.5", "dimension": 384, "provider": "local"},
            {"model": "BAAI/bge-base-en-v1.5", "dimension": 768, "provider": "local"},
        ],
        "available_openai": [
            {"model": "text-embedding-3-small", "dimension": 1536, "provider": "openai"},
            {"model": "text-embedding-3-large", "dimension": 3072, "provider": "openai"},
        ],
    }
