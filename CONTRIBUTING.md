# Contributing to DocuMindAI

Thank you for your interest in contributing to DocuMindAI! As an enterprise-grade document intelligence platform, we value high-quality, maintainable, and clean contributions.

This document provides guidelines and instructions for setting up the project locally, running tests, and submitting contributions.

---

## 🛠️ Development Setup

DocuMindAI is a monorepo consisting of:
- **FastAPI backend** (Python 3.11+)
- **Next.js frontend** (Node.js 18+)
- **Infrastructure** (Docker Compose with PostgreSQL + pgvector, Redis, and PgBouncer)

### Prerequisites
Before you start, make sure you have the following installed:
- Python 3.11 or higher
- Node.js 18 or higher (with npm)
- Docker and Docker Compose
- A Google Gemini API key ([get one here](https://aistudio.google.com/))

---

## 📥 Getting Started

1. **Clone the repository:**
   ```bash
   git clone https://github.com/kanwa2006/DocuMindAI.git
   cd DocuMindAI
   ```

2. **Configure environment variables:**
   Copy the example environment file at the root:
   ```bash
   cp .env.example .env
   ```
   Open `.env` and fill in your Gemini API keys and secrets. **Note:** `.env` is ignored by Git to protect your local credentials.

3. **Start local infrastructure services:**
   We use Docker Compose to run PostgreSQL (with `pgvector`), Redis, and PgBouncer.
   ```bash
   cd infrastructure
   docker-compose up -d db pgbouncer redis
   cd ..
   ```

---

## 🐍 Backend Development (FastAPI)

1. **Create and activate a virtual environment:**
   ```bash
   cd backend
   python -m venv venv
   
   # Windows:
   venv\Scripts\activate
   # macOS / Linux:
   source venv/bin/activate
   ```

2. **Install dependencies:**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. **Run database migrations:**
   Ensure the Docker services are running, then apply the migrations:
   ```bash
   alembic upgrade head
   ```

4. **Start the FastAPI server:**
   ```bash
   uvicorn app.main:app --reload
   ```
   The Swagger API docs will be available at `http://localhost:8000/docs`.

5. **Start the Celery worker (in a separate terminal):**
   ```bash
   # Make sure the virtualenv is active in the new terminal
   celery -A app.workers.celery_app worker -Q main-queue,celery --loglevel=info
   ```

### Running Backend Tests
We use `pytest` for validation and API contract tests. Run them using:
```bash
pytest tests/ -v
```

---

## ⚛️ Frontend Development (Next.js)

1. **Install dependencies:**
   ```bash
   cd frontend
   npm install
   ```

2. **Start the development server:**
   ```bash
   npm run dev
   ```
   The app will run at `http://localhost:3000`.

### Validating Frontend Code
Before opening a pull request, ensure the codebase is clean:
```bash
# Run ESLint validation
npm run lint

# Validate that the Next.js production build succeeds
npm run build
```

---

## 🤝 Code Style & Commit Guidelines

To maintain a clean repository history, we follow standard conventional commits:
- `feat:` for new features (e.g., `feat: add support for Supabase storage`)
- `fix:` for bug fixes (e.g., `fix: resolve rate limiter CORS issue`)
- `docs:` for documentation updates (e.g., `docs: add contributing guidelines`)
- `chore:` for repository maintenance (e.g., `chore: update dependencies`)

Please make sure all tests pass and that your local `.env` changes are never staged or committed.
