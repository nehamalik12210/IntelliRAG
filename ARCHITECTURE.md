# IntelliRAG Architecture

## Overview
IntelliRAG is a production-grade Retrieval-Augmented Generation (RAG) system built with FastAPI (Backend) and React (Frontend). It features hybrid search (dense + sparse), cross-encoder reranking, asynchronous background ingestion, and automated LLM-as-a-judge evaluation.

## System Components

### 1. Frontend (React + Vite)
- **`src/App.jsx`**: Main application shell, routing, and sidebar layout.
- **`src/components/chat/`**: 
  - `ChatWindow.jsx`: Core chat interface.
  - `MessageBubble.jsx`: Renders Markdown and citations.
  - `InputBar.jsx`: Chat input with multi-document selection.
  - `SourcePanel.jsx`: Displays retrieved chunk metadata and content.
- **`src/components/kb/`**: Knowledge base creation and management.
- **`src/components/eval/`**: Dashboard for RAGAS evaluation metrics and human feedback.
- **`src/hooks/useChat.js`**: Manages chat state and SSE streaming connection.

### 2. Backend (FastAPI)
- **`app/main.py`**: Application entry point, CORS, Rate Limiting (SlowAPI).
- **`app/api/`**: 
  - `chat.py`: SSE streaming chat endpoint with hybrid retrieval integration.
  - `knowledge_base.py`, `documents.py`, `conversations.py`: CRUD endpoints.
  - `eval.py`: Aggregates metrics for the dashboard.
- **`app/core/`**:
  - `ingestion/`: Handles document parsing, chunking (recursive character), and embedding. Runs in a ThreadPoolExecutor.
  - `retrieval/`: `hybrid_search.py` routes queries. `reranker.py` applies cross-encoder scoring.
  - `generation/`: Manages LLM connections via LangChain (Ollama, Groq, OpenRouter).
  - `eval/`: `ragas_eval.py` computes Faithfulness and Answer Relevancy asynchronously.
- **`app/db/`**:
  - `database.py`: SQLite connection with WAL mode enabled for high concurrency.
  - `models.py`: SQLAlchemy schemas (KnowledgeBase, Document, Conversation, Message, QueryLog, etc.).
  - `vector_store.py`: Abstraction over Qdrant client for hybrid vector search.

## Data Flow: Chat Request
1. User sends message via `InputBar.jsx`.
2. `useChat.js` initiates `POST /api/chat/stream`.
3. `chat.py` receives request, creates a new `Conversation` and user `Message` in SQLite.
4. **Retrieval**: `hybrid_search.py` calls Qdrant for dense (MiniLM) + sparse (SPLADE) search using Reciprocal Rank Fusion (RRF).
5. **Reranking**: (Optional) `reranker.py` re-scores the top chunks using a cross-encoder model.
6. **Generation**: Top chunks are injected into `QA_PROMPT_TEMPLATE`. LangChain streams LLM response chunks.
7. **Streaming**: `chat.py` yields `event: sources` then `event: token` to the frontend via SSE.
8. **Evaluation**: After generation, `chat.py` triggers an async background task (`ragas_eval.py`) to grade the response without blocking the user.

## Storage Layer
- **SQLite (`data/intellirag.db`)**: Stores relational metadata (conversations, chat history, document statuses, evaluation metrics). WAL mode ensures reads aren't blocked by writes.
- **Qdrant (`data/qdrant_db`)**: Vector database storing dense vectors, sparse vectors, and chunk payloads.
- **File System (`data/uploads`)**: Original uploaded documents.

## Deployment
The system can be deployed using the provided `docker-compose.yml`, which spins up:
- `frontend` (Nginx + React)
- `backend` (Uvicorn + FastAPI)
- `qdrant` (Vector database)
