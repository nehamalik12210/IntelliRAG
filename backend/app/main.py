"""IntelliRAG — FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.db.database import init_db
from app.db.vector_store import vector_store

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    # Startup
    logger.info("Starting IntelliRAG backend...")
    init_db()
    logger.info("Database initialized")
    vector_store.connect()
    logger.info("Vector store connected")
    logger.info(f"LLM: {settings.default_llm_provider}/{settings.default_llm_model}")
    logger.info(f"Embeddings: {settings.embedding_provider}/{settings.embedding_model} (dim={settings.embedding_dimension})")
    yield
    # Shutdown
    logger.info("Shutting down IntelliRAG backend...")


app = FastAPI(
    title="IntelliRAG",
    description="Production-grade RAG Knowledge Base Q&A System",
    version="0.1.0",
    lifespan=lifespan,
)

# Add rate limiter state and exception handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
from app.api.chat import router as chat_router
from app.api.knowledge_base import router as kb_router
from app.api.documents import router as documents_router
from app.api.conversations import router as conversations_router
from app.api.models import router as models_router
from app.api.settings import router as settings_router
from app.api.eval import router as eval_router

app.include_router(chat_router)
app.include_router(kb_router)
app.include_router(documents_router)
app.include_router(conversations_router)
app.include_router(models_router)
app.include_router(settings_router)
app.include_router(eval_router, prefix="/api/eval", tags=["Evaluation"])

@app.get("/api/debug")
def debug_qdrant():
    from app.db.vector_store import vector_store
    cols = vector_store.client.get_collections().collections
    return [{"name": c.name} for c in cols]


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "version": "0.1.0",
        "llm_provider": settings.default_llm_provider,
        "embedding_model": settings.embedding_model,
    }
