# IntelliRAG

**Advanced RAG Knowledge Base Q&A System**

A full-stack Retrieval-Augmented Generation system that lets you upload documents, build knowledge bases, and chat with your data using LLMs — with source citations, hybrid search, and real-time streaming.

<!-- Add your demo screenshot here -->
<!-- ![IntelliRAG Demo](docs/images/demo.png) -->

---

## ✨ Features

### Core RAG Pipeline

- **Multi-Format Ingestion** — Upload PDF, DOCX, TXT, Markdown, CSV, PPTX, and HTML files
- **Hybrid Search** — Combines dense semantic vectors (MiniLM) with sparse keyword vectors (SPLADE) using Reciprocal Rank Fusion (RRF)
- **Cross-Encoder Reranking** — Optional second-stage reranking with `ms-marco-MiniLM-L-6-v2` for precision-critical queries
- **SSE Streaming Chat** — Real-time token-by-token streaming with source citations
- **Resumable Ingestion** — State machine pipeline (queued → parsing → chunking → embedding → ready) with automatic retry from last successful chunk

### Multi-Provider LLM Support

- **Groq** (Llama 3.1, Mixtral) — Ultra-fast inference, free tier available
- **OpenRouter** (Unified access to Claude, GPT-4, Llama, and more via a single API)
- **Google** (Gemini)

### Knowledge Base Management

- Create isolated knowledge bases with locked embedding dimensions
- Per-KB Qdrant collections for clean data separation
- Document lifecycle tracking with real-time status updates
- Conversation history with thumbs up/down feedback

### Robust Architecture

- **FastAPI** async backend with Pydantic validation
- **React + Vite** frontend with glassmorphism dark UI
- **Qdrant** vector database (Docker or in-memory fallback)
- **SQLite** for metadata, conversations, and query logs
- **ThreadPoolExecutor** for CPU-bound embedding without blocking the async event loop
- Comprehensive query logging for evaluation and debugging

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (React + Vite)              │
│  ┌──────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │ Sidebar  │  │  ChatWindow  │  │     SourcePanel        │ │
│  │ (KB/Doc  │  │  (SSE Stream │  │  (Citations, Scores,   │ │
│  │  Mgmt)   │  │   + History) │  │   Content Preview)     │ │
│  └──────────┘  └──────────────┘  └────────────────────────┘ │
└───────────────────────┬─────────────────────────────────────┘
                        │ HTTP / SSE
┌───────────────────────▼─────────────────────────────────────┐
│                    Backend (FastAPI)                        │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                   API Layer                         │    │
│  │  /chat/stream  /knowledge-bases  /documents  /models│    │
│  └────────┬────────────────┬───────────────┬───────────┘    │
│           │                │               │                │
│  ┌────────▼────────┐ ┌────▼─────┐  ┌──────▼──────────┐      │
│  │   Retrieval     │ │ Ingestion│  │   Generation    │      │
│  │                 │ │ Pipeline │  │                 │      │
│  │ Hybrid Search   │ │ Loader   │  │ LLM Router      │      │
│  │ (RRF/Weighted)  │ │ Chunker  │  │ (Groq/Google/   │      │
│  │ Cross-Encoder   │ │ Embedder │  │  OpenRouter)    │      │
│  │ Reranker        │ │ Store    │  │                 │      │
│  └────────┬────────┘ └────┬─────┘  └──────┬──────────┘      │
│           │               │               │                 │
│  ┌────────▼───────────────▼───────────────▼──────────┐      │
│  │              Storage Layer                        │      │
│  │  ┌──────────────┐    ┌──────────────────────┐     │      │
│  │  │   Qdrant     │    │      SQLite          │     │      │
│  │  │  (Vectors)   │    │  (Metadata, Chunks,  │     │      │
│  │  │  Dense+Sparse│    │   Conversations,     │     │      │
│  │  │              │    │   Query Logs)        │     │      │
│  │  └──────────────┘    └──────────────────────┘     │      │
│  └───────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Tech Stack

| Layer | Technology |
| ------- | ----------- |
| **Frontend** | React 19, Vite, Glassmorphism CSS |
| **Backend** | Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2.0 |
| **Vector DB** | Qdrant (Docker or in-memory) |
| **Embeddings** | FastEmbed (all-MiniLM-L6-v2, 384d) + SPLADE sparse |
| **LLM** | LangChain-OpenAI (Groq, OpenRouter, Google, Ollama) |
| **Search** | Hybrid RRF fusion, Cross-Encoder reranking |
| **Database** | SQLite (zero-config, embedded) |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- A Groq API key (free at [console.groq.com](https://console.groq.com)) — or any supported LLM provider key

### 1. Clone the Repository

```bash
git clone https://github.com/nehamalik12210/IntelliRAG.git
cd IntelliRAG
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate        # Linux/Mac
# venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your API keys:
# e.g: GROQ_API_KEY=gsk_your_key_here 
```

### 3. Frontend Setup

```bash
cd frontend
npm install
```

### 4. Run

```bash
# Terminal 1 — Backend
cd backend
uvicorn app.main:app --reload --port 8000

# Terminal 2 — Frontend
cd frontend
npm run dev
```

Open **<http://localhost:5173>** and you're ready to go!

> **Note:** The first document upload takes ~30 seconds while the embedding model downloads (~90MB). Subsequent uploads are fast.

---

## ⚙️ Configuration

All configuration is via environment variables in `backend/.env`:

### LLM Providers (pick one or more)

```env
# Groq (recommended — fast & free tier)
GROQ_API_KEY = enter_your_key_here
DEFAULT_LLM_PROVIDER = groq
DEFAULT_LLM_MODEL = llama-3.1-8b-instant

# Google Gemini
GEMINI_API_KEY = enter_your_key_here

# OpenRouter (access to Claude, GPT-4, Llama, etc. via one key)
OPENROUTER_API_KEY = enter_your_key_here
```

### Retrieval Tuning

```env
CHUNK_SIZE=512                    # Characters per chunk
CHUNK_OVERLAP=50                  # Overlap between chunks
TOP_K_RETRIEVAL=20                # Candidates from hybrid search
TOP_K_RERANK=5                    # Final results after reranking
RERANKER_ENABLED=false            # Enable cross-encoder reranker
HYBRID_FUSION_METHOD=rrf          # rrf | weighted_sum | dense_only
```

### Vector Database

```env
# Docker (persistent)
QDRANT_URL=http://localhost:6333

# No config needed for in-memory mode — auto-fallback when Qdrant is unreachable
```

---

## 📁 Project Structure

```
intellirag/
├── backend/
│   ├── app/
│   │   ├── api/                    # FastAPI route handlers
│   │   │   ├── chat.py             # SSE streaming chat endpoint
│   │   │   ├── documents.py        # Upload, status, retry, delete
│   │   │   ├── knowledge_base.py   # KB CRUD operations
│   │   │   ├── conversations.py    # Chat history management
│   │   │   ├── models.py           # Available LLM listing
│   │   │   └── settings.py         # Runtime settings API
│   │   ├── core/
│   │   │   ├── ingestion/          # Document processing pipeline
│   │   │   │   ├── pipeline.py     # State machine orchestrator
│   │   │   │   ├── loader.py       # 7-format document loaders
│   │   │   │   ├── chunker.py      # Recursive text splitter
│   │   │   │   ├── embedder.py     # Dense + sparse embedding
│   │   │   │   └── chunk_store.py  # SQLite chunk persistence
│   │   │   ├── retrieval/          # Search & ranking
│   │   │   │   ├── hybrid_search.py # RRF + weighted sum fusion
│   │   │   │   └── reranker.py     # Cross-encoder reranking
│   │   │   └── generation/         # LLM response generation
│   │   │       ├── llm_router.py   # Multi-provider LLM routing
│   │   │       ├── prompts.py      # RAG prompt templates
│   │   │       └── citations.py    # Source citation extraction
│   │   ├── db/                     # Database layer
│   │   │   ├── database.py         # SQLAlchemy setup
│   │   │   ├── models.py           # ORM models (6 tables)
│   │   │   └── vector_store.py     # Qdrant client wrapper
│   │   ├── schemas/                # Pydantic request/response models
│   │   └── config.py               # Pydantic Settings configuration
│   ├── requirements.txt
│   └── .env
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── chat/               # ChatWindow, MessageBubble, ChatInput
│   │   │   ├── kb/                 # KBList, DocUpload, DocStatus
│   │   │   └── settings/           # SettingsPanel
│   │   ├── hooks/
│   │   │   └── useChat.js          # SSE streaming state management
│   │   ├── services/
│   │   │   └── api.js              # API client with SSE parser
│   │   ├── App.jsx                 # Main app with routing
│   │   └── index.css               # Glassmorphism design system
│   ├── package.json
│   └── vite.config.js
└── README.md
```

---

## 🔌 API Reference

The backend exposes a RESTful API with interactive Swagger docs at **`/docs`**.

### Key Endpoints

| Method | Endpoint | Description |
| -------- | ---------- | ------------- |
| `POST` | `/api/chat/stream` | SSE streaming chat with RAG context |
| `POST` | `/api/knowledge-bases` | Create a knowledge base |
| `GET` | `/api/knowledge-bases` | List all knowledge bases |
| `POST` | `/api/documents/upload` | Upload a document (multipart) |
| `GET` | `/api/documents/{doc_id}/status` | Poll ingestion progress |
| `POST` | `/api/documents/{doc_id}/retry` | Retry failed ingestion |
| `GET` | `/api/models` | List available LLM models |
| `GET` | `/api/health` | Health check |

### SSE Event Types

```
event: sources    → Retrieved source citations
event: token      → Streaming text token
event: done       → Completion metadata (conversation_id, model, latency)
event: error      → Error message
```

---

## 🧪 How It Works

### Ingestion Pipeline

```
Upload → Parse (PyPDF2/docx/etc) → Chunk (512 chars, 50 overlap)
       → Persist to SQLite → Embed (Dense + Sparse) → Index to Qdrant
```

Each document tracks its state: `queued → parsing → chunking → persisting → embedding → ready`

If embedding fails mid-batch, the system records `last_successful_chunk` and retries from exactly where it left off — no re-parsing, no re-chunking.

### Retrieval Pipeline

```
Query → Dense Embed → Hybrid Search (RRF Fusion) → [Optional] Cross-Encoder Rerank
      → Top-K Results → Build RAG Prompt → Stream LLM Response → Extract Citations
```

**Hybrid Search** combines two signals:

- **Dense vectors** (all-MiniLM-L6-v2, 384d) capture semantic meaning
- **Sparse vectors** (SPLADE) capture exact keyword matches
- **RRF fusion** merges both ranked lists without needing score calibration

---

## 🐳 Running with Docker (Optional)

For persistent vector storage, run Qdrant via Docker:

```bash
docker run -d --name qdrant -p 6333:6333 qdrant/qdrant
```

The backend auto-detects Qdrant at `localhost:6333`. Without Docker, it falls back to in-memory mode (data lost on restart).

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

---

<p align="center">
  Built with ❤️ by <a href="https://github.com/nehamalik12210">Neha</a>
</p>
