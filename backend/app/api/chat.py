"""Chat API — SSE streaming chat with knowledge base context."""

import asyncio
import json
import logging
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.db.database import get_db
from app.db.models import KnowledgeBase, Conversation, Message, QueryLog
from app.db.vector_store import vector_store
from app.core.retrieval.hybrid_search import retrieve as hybrid_retrieve
from app.core.retrieval.reranker import rerank
from app.core.generation.llm_router import stream_chat_response
from app.core.generation.prompts import build_rag_messages, NO_CONTEXT_RESPONSE
from app.core.generation.citations import extract_citations
from app.schemas.chat import ChatRequest, FeedbackRequest
from app.config import settings
from app.main import limiter

router = APIRouter(prefix="/api/chat", tags=["chat"])
logger = logging.getLogger(__name__)


@router.post("/stream")
@limiter.limit("20/minute")
async def chat_stream(
    request: Request,
    chat_request: ChatRequest,
    db: Session = Depends(get_db)
):
    """Stream a RAG-powered chat response via Server-Sent Events.

    Events:
    - token: A streaming text token
    - sources: Source citations (sent once after retrieval)
    - done: Stream complete with metadata
    - error: Error occurred
    """
    # Get or create conversation
    conversation = None
    if chat_request.conversation_id:
        conversation = db.query(Conversation).filter(
            Conversation.id == chat_request.conversation_id
        ).first()
        if not conversation:
            raise HTTPException(404, "Conversation not found")
    else:
        conversation = Conversation(
            kb_id=chat_request.kb_id,
            title=chat_request.message[:50] + ("..." if len(chat_request.message) > 50 else ""),
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    # Save user message
    user_msg = Message(
        conversation_id=conversation.id,
        role="user",
        content=chat_request.message,
    )
    db.add(user_msg)
    
    # Touch the conversation to bump its updated_at timestamp
    if chat_request.conversation_id:
        conversation.updated_at = func.now()
        
    db.commit()

    # Get conversation history
    history = db.query(Message).filter(
        Message.conversation_id == conversation.id,
        Message.message_type == "text",
    ).order_by(Message.created_at).all()

    conversation_history = [
        {"role": m.role, "content": m.content}
        for m in history[:-1]  # Exclude the message we just added
    ]

    async def event_stream():
        retrieved_chunks = []
        retrieval_method = "none"
        retrieval_latency_ms = 0
        full_response = ""
        sources = []

        try:
            # ── Retrieval (hybrid search + reranker) ──
            if chat_request.kb_id:
                kb = db.query(KnowledgeBase).filter(
                    KnowledgeBase.id == chat_request.kb_id
                ).first()

                if kb:
                    collection_name = f"kb_{kb.id}"
                    if vector_store.collection_exists(collection_name):
                        start = time.time()

                        # Phase 2: Hybrid retrieval (rrf/weighted_sum/dense_only)
                        retrieved_chunks = hybrid_retrieve(
                            collection_name=collection_name,
                            query=chat_request.message,
                            document_ids=chat_request.document_ids,
                        )
                        retrieval_method = (
                            retrieved_chunks[0].get("retrieval_method", "unknown")
                            if retrieved_chunks else "none"
                        )

                        # Phase 2: Rerank with cross-encoder
                        if retrieved_chunks and settings.reranker_enabled:
                            retrieved_chunks = await rerank(
                                query=chat_request.message,
                                results=retrieved_chunks,
                            )
                            retrieval_method += "+reranked"

                        retrieval_latency_ms = int((time.time() - start) * 1000)

            # ── Generation ──
            messages = build_rag_messages(
                question=chat_request.message,
                context_chunks=retrieved_chunks,
                conversation_history=conversation_history,
            )

            if not retrieved_chunks and chat_request.kb_id:
                # No relevant context found
                full_response = NO_CONTEXT_RESPONSE
                yield f"event: token\ndata: {json.dumps({'token': full_response})}\n\n"
            else:
                # Stream LLM response
                async for token in stream_chat_response(
                    messages=messages,
                    provider=chat_request.provider,
                    model=chat_request.model,
                    temperature=chat_request.temperature,
                ):
                    full_response += token
                    yield f"event: token\ndata: {json.dumps({'token': token})}\n\n"

            # Send sources event AFTER generation so extract_citations has the full response
            if retrieved_chunks:
                sources = extract_citations(full_response, retrieved_chunks)
                yield f"event: sources\ndata: {json.dumps(sources)}\n\n"

            # Save assistant message
            assistant_msg = Message(
                conversation_id=conversation.id,
                role="assistant",
                content=full_response,
                sources=sources if sources else None,
            )
            db.add(assistant_msg)
            db.commit()
            db.refresh(assistant_msg)

            # Save query log for evaluation
            query_log = QueryLog(
                conversation_id=conversation.id,
                message_id=assistant_msg.id,
                query=chat_request.message,
                kb_id=chat_request.kb_id,
                retrieved_chunks=[
                    {
                        "id": c.get("id"), 
                        "score": c.get("score"), 
                        "source": c.get("payload", {}).get("source_filename"),
                        "content": c.get("payload", {}).get("content")
                    }
                    for c in retrieved_chunks
                ] if retrieved_chunks else None,
                retrieval_method=retrieval_method,
                retrieval_latency_ms=retrieval_latency_ms,
                response=full_response,
                model_used=f"{chat_request.provider or settings.default_llm_provider}/{chat_request.model or settings.default_llm_model}",
            )
            db.add(query_log)
            db.commit()

            # Trigger async RAGAS evaluation in the background
            from app.core.eval.ragas_eval import run_evaluation_async
            import asyncio
            asyncio.create_task(run_evaluation_async(query_log.id))

            # Send done event
            done_data = {
                "conversation_id": conversation.id,
                "message_id": assistant_msg.id,
                "model_used": query_log.model_used,
                "retrieval_method": retrieval_method,
                "retrieval_latency_ms": retrieval_latency_ms,
                "chunks_retrieved": len(retrieved_chunks),
            }
            yield f"event: done\ndata: {json.dumps(done_data)}\n\n"

        except Exception as e:
            logger.exception(f"Chat stream error: {e}")
            error_data = {"error": str(e)}
            yield f"event: error\ndata: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/feedback")
async def submit_feedback(request: FeedbackRequest, db: Session = Depends(get_db)):
    """Submit thumbs up/down feedback on a message."""
    message = db.query(Message).filter(Message.id == request.message_id).first()
    if not message:
        raise HTTPException(404, "Message not found")

    message.feedback = request.feedback
    message.feedback_comment = request.comment
    db.commit()

    return {"status": "ok"}
