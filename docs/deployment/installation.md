# DocuMindAI — Installation & Deployment Guide

This guide provides step-by-step instructions for running DocuMindAI in your local development environment or deploying it to production.

---

## 📋 Prerequisites

Before setting up the project, make sure you have:
- **Python 3.11+**
- **Node.js 18+** (with npm)
- **Docker & Docker Compose**
- A **Google Gemini API Key** ([get one here](https://aistudio.google.com/))

---

## 🐳 Quick Start: Run Everything with Docker Compose

The fastest way to spin up the entire stack (Database, Redis, FastAPI, Celery, and Next.js) is via Docker Compose:

1. **Configure Environment Variables:**
   ```bash
   cp .env.example .env
   ```
   *Edit the `.env` file and insert your `GEMINI_API_KEY_1`.*

2. **Build and Start Container Services:**
   ```bash
   cd infrastructure
   docker-compose up --build
   ```
   This command starts 6 containers:
   - `db` (PostgreSQL 16 + pgvector) on port `5433`
   - `pgbouncer` (Connection pooling) on port `6432`
   - `redis` (Cache/Celery broker) on port `6380`
   - `backend` (FastAPI API server) on port `8000`
   - `worker` (Celery task executor)
   - `frontend` (Next.js client) on port `3000`

---

## 🛠️ Step-by-Step Manual Local Setup

If you prefer to run services manually for debugging or active development, follow these steps:

### 1. Start Infrastructure Dependencies
Spin up PostgreSQL, PgBouncer, and Redis using Docker:
```bash
cd infrastructure
docker-compose up -d db pgbouncer redis
cd ..
```

### 2. Configure Local Environment File
Copy the example template to `.env`:
```bash
cp .env.example .env
```
Fill in the configuration variables. The default ports are configured to match the local Docker container mappings (`5433` for database, `6380` for Redis).

### 3. Backend Setup (FastAPI)
Navigate to the backend directory, initialize a Python virtual environment, install dependencies, and run database migrations:

```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate        # On Windows
# source venv/bin/activate   # On macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start development API server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
The FastAPI swagger docs are available at `http://localhost:8000/docs`.

### 4. Celery Task Queue Setup
In a new terminal with the backend virtual environment active, start the Celery worker queue:
```bash
cd backend
venv\Scripts\activate
celery -A app.workers.celery_app worker -Q main-queue,celery,export_queue,ocr_gpu_queue --loglevel=info
```

### 5. Frontend Setup (Next.js)
Install Node packages and run the client-side server:
```bash
cd frontend
npm install
npm run dev
```
The application will be accessible at `http://localhost:3000`.

---

## 🚀 Production Deployment (Railway)

This repository includes a `railway.json` file for quick deployments to Railway.

1. **Link your GitHub Repository** on the Railway dashboard.
2. **Add Environment Variables** in the Railway dashboard matching the keys inside `.env.example`.
3. Railway will automatically detect the settings and deploy both the FastAPI backend and Next.js frontend according to the multi-service deployment setup.
