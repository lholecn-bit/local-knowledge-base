# AI Coding Agent Instructions - Local Knowledge Base System

## Architecture Overview

**Local Knowledge Base System** is a RAG (Retrieval-Augmented Generation) application combining vector search, document re-ranking, and LLM integration.

### Core Components

| Component | Purpose | Key Files |
|-----------|---------|-----------|
| **Backend (Flask)** | REST API server for knowledge base operations | `backend/app.py`, `backend/knowledge_base.py` |
| **Vector DB (FAISS)** | Stores document embeddings for semantic search | `knowledge_db/faiss_index/`, uses LangChain's FAISS wrapper |
| **Embeddings** | Converts documents/queries to vectors via OpenAI API | `backend/embeddings.py`, model: `text-embedding-3-small` |
| **Re-Ranker** | Re-ranks search results using `sentence-transformers` CrossEncoder | `backend/knowledge_base.py` (lazy-loaded) |
| **LLM Client** | Calls OpenAI API for chat/generation with streaming support | `backend/llm_client.py` |
| **Frontend** | Vanilla JS + HTML/CSS for UI, 3 query modes | `frontend/` (index.html, js/app.js, js/api.js) |

### Query Flow (Stream-Query Mode)
```
User Question
  → KB.search(question, top_k=3)
  → FAISS similarity search → relevance_threshold filter (0.3)
  → Re-ranking with CrossEncoder (optional, "light" model)
  → Build RAG prompt with sources
  → LLMClient.chat() → stream response to frontend
  → Deduplicate and display related documents
```

## Critical Configuration & Patterns

### Environment Setup (`backend/app.py`, `backend/knowledge_base.py`)
- **OPENAI_API_KEY**: Required; falls back to env var if not passed to constructors
- **OPENAI_BASE_URL**: Optional custom API endpoint (line 121 in `knowledge_base.py`)
- **Offline Mode**: `HF_HOME` and `HF_HUB_OFFLINE=1` force local model cache via `models_cache/` (line 19-23)
- **CORS Configuration**: See line 36-44; `/api/*` routes allow cross-origin from `http://localhost:3000`
- **Proxy Handling**: Both `knowledge_base.py` (line 123-129) and `llm_client.py` (line 48-54) explicitly clear proxy env vars to prevent OpenAI/HuggingFace failures

### Delayed Model Loading (Critical for Startup)
- Embeddings and re-ranker are **lazy-loaded** in `search()` method, not `__init__` (line 100, knowledge_base.py)
- Reason: Ensures environment variables (`HF_HOME`, offline mode) are set before importing models
- Pattern: Check `if self.embeddings is None` then initialize (see `search()` method, line 280+)

### Re-Ranking Pattern (`knowledge_base.py:350-395`)
- Re-ranker loads **on first search** (lazy): `sentence-transformers` CrossEncoder model `ms-marco-MiniLM-L-6-v2`
- Controlled by `use_reranking=True` parameter in `search()` and `/api/stream-query` (line 129 in app.py)
- Returns tuple: `(search_results, reranked_results)` - frontend shows reranked results but includes original sources

### Metadata & Document Tracking
- `knowledge_db/metadata.json`: Stores file hashes (MD5) and upload timestamps to prevent duplicates
- When adding documents: check `_should_skip_file()` (line 204-217) before processing
- File deletion updates both metadata and vector store

## API Endpoints & Request Patterns

### Key Endpoints

| Endpoint | Method | Purpose | Response |
|----------|--------|---------|----------|
| `/api/stream-query` | POST | **Main query**: RAG with streaming response | `type: 'start' \| 'chunk' \| 'end'`, JSON lines format |
| `/api/kb/search` | POST | Vector search only (no LLM) | `{'results': [...], 'query': '...'}` |
| `/api/documents/upload` | POST | Upload PDF/MD/TXT files | `{'added_chunks': int, 'files': [], 'errors': []}` |
| `/api/documents/list` | GET | List all documents in KB | `{'documents': [{'filename': str, ...}]}` |
| `/api/documents/<filename>` | DELETE | Remove document | `{'message': 'deleted', ...}` |
| `/api/health` | GET | System status | `{'status': 'ok', 'kb_ready': bool, ...}` |

### Stream-Query Mode Parameter (`app.py:196-210`)
- **mode**: `'auto'` (search then LLM if found), `'kb'` (always search), `'llm'` (skip KB) → affects result scoring
- **top_k**: Number of vectors to retrieve (default 3) - controls depth vs speed tradeoff

## Frontend Architecture

### API Wrapper Pattern (`js/api.js`)
- `API` class provides methods: `search()`, `query()`, `streamQuery()`, `upload()`, `deleteDoc()`
- All methods use centralized `request()` method → standardized error handling
- `streamQuery()` reads response as **text stream** (line ~100), parses JSON lines

### Stream Response Handling (`js/app.js`)
- Frontend reads streaming response line-by-line, parses JSON chunks
- Types: `'start'` (metadata), `'chunk'` (LLM token), `'end'` (sources array)
- **Deduplication logic**: Remove repeated documents in sources (see `deduplicateSources()` in `js/ui.js`)

### Markdown Rendering
- Uses `marked.js` library (line 8 in index.html)
- Code highlighting via `highlight.js` (line 7)
- Pattern: `marked.parse(markdown)` → add to DOM with proper escaping

## Important Conventions & Gotchas

### 1. **Python Module as Both Script and Module**
- `app.py` uses pattern: `if __name__ == '__main__':` at end (line 463+)
- Global initialization (`load_dotenv()`, `kb = LocalKnowledgeBase()`) happens **before** the check
- This allows importing `app` module without auto-starting Flask server

### 2. **Error Handling Strategy**
- Backend returns JSON errors with descriptive messages: `{'error': 'specific reason'}`
- Frontend wraps API calls in `try-catch`, displays errors to user
- **Console logging**: Extensive debugging logs (print statements with emoji markers) in `app.py` and `knowledge_base.py` for troubleshooting

### 3. **Knowledge Base Initialization**
- `kb = LocalKnowledgeBase()` at line 59 in `app.py` requires OPENAI_API_KEY set in `.env`
- If initialization fails: `/api/health` returns `kb_ready: false`, endpoints return 500
- Test with: `curl http://localhost:5000/api/health`

### 4. **Document Processing**
- Supports: `.pdf`, `.md`, `.txt` files
- Uses `langchain_community` loaders (`PDFPlumberLoader`, `TextLoader`)
- Chunks via `RecursiveCharacterTextSplitter` (chunk_size=1000, overlap=200)
- File upload returns both `added_chunks` count and `errors` array for partial failures

### 5. **Relevance Threshold**
- Set at `self.relevance_threshold = 0.3` (line 80 in knowledge_base.py)
- Filters embeddings-based search results below this score
- If search returns 0 results after filtering: modes differ:
  - `auto`/`kb`: Returns "no relevant documents found"
  - `llm`: Skips KB entirely, uses pure LLM

## Development Workflow

### Running Locally
```bash
# Backend (Flask)
cd backend
pip install -r requirements.txt
export OPENAI_API_KEY="sk-..."
python app.py  # Runs on http://localhost:5000

# Frontend (requires backend running)
# Open frontend/index.html in browser (or use Python's `python -m http.server 3000`)
```

### Testing Additions
- Test script template: `test/testScript/run_rag_tests.py`
- Document test cases: `test/testDoc/TEST_QUESTIONS.md`

### Model Caching
- First `search()` or `add_documents()` downloads embeddings & re-ranker models → stored in `models_cache/`
- Subsequent runs use cached versions (check `HF_HOME` env var)
- To reset: Delete `models_cache/` directory

## Key Files by Purpose

| Goal | Primary Files | Secondary |
|------|---------------|-----------|
| Add feature to KB operations | `backend/knowledge_base.py` | `backend/app.py` (routing) |
| Add REST API endpoint | `backend/app.py` | `frontend/js/api.js` (client) |
| Improve search quality | `backend/knowledge_base.py:search()`, re-ranking logic | `backend/llm_client.py` (prompt) |
| Fix streaming response | `backend/app.py:stream_query() generator`, `frontend/js/app.js` | `frontend/index.html` (UI) |
| Document management | `backend/knowledge_base.py:add_documents()`, metadata handling | Vector store persistence |

## Unsolved Design Issues (From TODOLIST.txt)
- **Issue #16**: KB mode vs Auto mode appear identical to users → may need mode differentiation in future
- **Issue #14**: Irrelevant documents shown even when LLM says they're not used → source selection logic needs review
- **Re-ranking effectiveness** (#11): CrossEncoder improves ranking but marginal gains documented
- **Duplicate handling**: Frontend deduplicates related docs, but backend could optimize earlier

---
*Last Updated: 2025-12-19 | RAG System with LangChain + FAISS + StreamingLLM*
