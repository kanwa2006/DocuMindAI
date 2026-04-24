# DocuMind AI 🧠

**Secure Per-User RAG-Based Intelligent Document Q&A System**

SP301 Special Project | IcfaiTech Hyderabad | 2025-2026

---

## Quick Start

### Backend Setup

```bash
cd DocuMindAI

# 1. Create and activate virtual environment
python -m venv venv
source venv/bin/activate          # Linux/Mac
venv\Scripts\activate             # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Install Tesseract OCR
# Ubuntu/Debian:
sudo apt-get install tesseract-ocr poppler-utils
# Mac:
brew install tesseract poppler
# Windows: download installer from https://github.com/UB-Mannheim/tesseract/wiki

# 4. Configure environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# 5. Run backend
uvicorn backend.main:app --reload --port 8000
```

Backend API docs available at: http://localhost:8000/docs

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
# Opens at http://localhost:5173
```

---

## Architecture

```
User Request
    │
    ▼
React Frontend (Vite)
    │  JWT Bearer token
    ▼
FastAPI Backend
    ├── /auth  → Register, Login (JWT)
    ├── /documents → Upload (OCR→Embed→Index), List, Delete
    └── /qa → Ask (Retrieve→Generate), History, Clear
         │
         ├── OCR Layer: pdf2image + Tesseract
         ├── Embedding: SentenceTransformers (MiniLM-L6-v2)
         ├── Vector Store: FAISS (per-user IndexFlatL2)
         └── LLM: LangChain RetrievalQA + OpenAI GPT-3.5
```

## Per-User Isolation

```
storage/
└── {user_id}/
    ├── documents/    ← uploaded PDFs
    ├── images/       ← extracted images
    └── index/
        ├── faiss.index     ← FAISS vector index
        └── chunks.json     ← chunk metadata
```

## Key Design Decisions

- **Strict document-only answers**: System prompt explicitly forbids outside knowledge
- **OCR auto-detection**: If digital extraction < 100 chars → assume scanned → use Tesseract
- **Incremental indexing**: Each new upload appends to existing FAISS index (no full rebuild)
- **Modular**: Each module (auth, documents, qa) is independently testable
- **No hallucinations**: Empty context → immediate "not found" response without LLM call
