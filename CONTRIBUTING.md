# Contributing to DocuMindAI

Thank you for your interest in contributing to DocuMindAI! As an enterprise-grade document intelligence platform, we value high-quality, maintainable, and well-tested contributions.

This guide covers everything you need to get started: development environment setup, coding standards, branch naming, commit conventions, and the pull request process.

---

## 📋 Table of Contents

- [Code of Conduct](#-code-of-conduct)
- [Development Setup](#️-development-setup)
- [Backend Development (FastAPI)](#-backend-development-fastapi)
- [Frontend Development (Next.js)](#️-frontend-development-nextjs)
- [Branch Naming](#-branch-naming)
- [Commit Conventions](#-commit-conventions)
- [Pull Request Guidelines](#-pull-request-guidelines)
- [Issue Reporting](#-issue-reporting)
- [Code Style](#-code-style)

---

## 🤝 Code of Conduct

Be respectful, constructive, and collaborative. We expect all contributors to maintain a welcoming and inclusive environment.

---

## 🛠️ Development Setup

DocuMindAI is a monorepo containing:

- **FastAPI backend** (Python 3.11+)
- **Next.js frontend** (Node.js 18+)
- **Infrastructure** (Docker Compose with PostgreSQL + pgvector, Redis, and PgBouncer)

### Prerequisites

Before you start, ensure the following tools are installed:

| Tool | Minimum Version | Notes |
|------|-----------------|-------|
| Python | 3.11 | Use `pyenv` or `conda` to manage versions |
| Node.js | 18.x | Use `nvm` for version management |
| npm | 9.x | Comes bundled with Node.js |
| Docker Desktop | latest | Required for local infrastructure |
| Docker Compose | v2 | Bundled with Docker Desktop |
| Google Gemini API Key | — | [Get one free at Google AI Studio](https://aistudio.google.com/) |

---

## 📥 Getting Started

### 1. Fork and clone the repository

```bash
git clone https://github.com/<your-username>/DocuMindAI.git
cd DocuMindAI
```

### 2. Add the upstream remote

```bash
git remote add upstream https://github.com/kanwa2006/DocuMindAI.git
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in your Gemini API keys and secrets. **Note:** `.env` is in `.gitignore` and will never be committed.

### 4. Start local infrastructure services

```bash
cd infrastructure
docker-compose up -d db pgbouncer redis
cd ..
```

This starts PostgreSQL (with `pgvector`), PgBouncer, and Redis as background services.

---

## 🐍 Backend Development (FastAPI)

### Setup

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux

# Install all dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Apply database migrations
alembic upgrade head

# Start the development server
uvicorn app.main:app --reload
```

The Swagger API docs are available at `http://localhost:8000/docs`.

### Start the Celery Worker

In a separate terminal with the virtual environment active:

```bash
cd backend
venv\Scripts\activate
celery -A app.workers.celery_app worker -Q main-queue,celery --loglevel=info
```

### Running Backend Tests

```bash
cd backend
pytest tests/ -v
```

All tests must pass before submitting a pull request.

---

## ⚛️ Frontend Development (Next.js)

### Setup

```bash
cd frontend
npm install
npm run dev
```

The application is accessible at `http://localhost:3000`.

### Validation

Run these checks before opening a pull request:

```bash
# ESLint — must produce 0 errors
npm run lint

# Verify the Next.js production build succeeds
npm run build
```

Zero ESLint **errors** are required. Warnings are acceptable but should be minimized.

---

## 🌿 Branch Naming

All branches must follow this naming convention:

| Type | Pattern | Example |
|------|---------|---------|
| New feature | `feat/<short-description>` | `feat/supabase-storage-support` |
| Bug fix | `fix/<short-description>` | `fix/rate-limiter-cors-issue` |
| Documentation | `docs/<short-description>` | `docs/update-installation-guide` |
| Chore / maintenance | `chore/<short-description>` | `chore/upgrade-sqlalchemy-2.1` |
| Refactor | `refactor/<short-description>` | `refactor/retrieval-service-cleanup` |
| Tests | `test/<short-description>` | `test/add-hr-api-contract-tests` |

Branch names should use **lowercase letters and hyphens only** — no underscores, no uppercase.

---

## 📝 Commit Conventions

DocuMindAI follows the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>(<scope>): <short summary>
```

### Allowed Types

| Type | When to use |
|------|-------------|
| `feat` | A new feature visible to the user |
| `fix` | A bug fix |
| `docs` | Documentation changes only |
| `chore` | Build process, dependencies, or repository maintenance |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `test` | Adding or updating tests |
| `perf` | A change that improves performance |
| `ci` | Changes to CI configuration or scripts |

### Scopes (optional but recommended)

Use the relevant component as scope: `auth`, `retrieval`, `ocr`, `worker`, `billing`, `frontend`, `export`, `veritas`, `hr`, `legal`, `finance`, `study`, `research`, `exam`.

### Examples

```
feat(retrieval): add BM25 tsvector fallback for short queries
fix(auth): resolve CSRF token validation on cross-origin preflight
docs(deployment): add Railway environment variable reference
chore(deps): upgrade SQLAlchemy to 2.1
test(hr): add API contract test for candidate ranking endpoint
perf(embedding): batch encode chunks to reduce round-trips
ci: pin actions/checkout to v4
```

### Rules

- Use the **imperative mood** in the summary: *"add support"* not *"added support"*
- Keep the summary line under **72 characters**
- Do not end the summary with a period
- Reference issues with `Closes #<issue-number>` in the commit body when applicable

---

## 🔀 Pull Request Guidelines

### Before Opening a PR

- [ ] Your branch is up to date with `upstream/main` (`git fetch upstream && git rebase upstream/main`)
- [ ] All backend tests pass (`pytest tests/ -v`)
- [ ] Frontend ESLint shows 0 errors (`npm run lint`)
- [ ] Frontend production build succeeds (`npm run build`)
- [ ] `.env` and any local secrets are **not** staged or committed
- [ ] New features include at least basic test coverage

### PR Description Template

When opening a pull request, please include:

```markdown
## Summary
<!-- What does this PR do? Why is this change needed? -->

## Changes
<!-- List the key files and what changed in each -->

## Testing
<!-- How did you test this? What should reviewers verify? -->

## Screenshots (if UI change)
<!-- Paste before/after screenshots for frontend changes -->

## Checklist
- [ ] Tests pass
- [ ] Lint passes
- [ ] No secrets committed
- [ ] Docs updated (if needed)
```

### Review Process

- PRs require at least **one approval** before merging.
- Address all review comments before requesting a re-review.
- Squash-merge is preferred to keep the main branch history clean.

---

## 🐛 Issue Reporting

### Bug Reports

When reporting a bug, please include:

- **DocuMindAI version** (or commit SHA)
- **Environment** (local Docker / Railway / other)
- **Steps to reproduce** (numbered, minimal)
- **Expected behavior**
- **Actual behavior** (with error messages, stack traces, or screenshots)
- **Relevant logs** from FastAPI, Celery worker, or browser console

### Feature Requests

Before opening a feature request, search existing issues to avoid duplicates. A good feature request includes:

- **Use case**: who benefits and why
- **Proposed behavior**: what should happen
- **Alternatives considered**: other approaches you evaluated

---

## 💅 Code Style

### Python (Backend)

| Tool | Purpose | Config |
|------|---------|--------|
| **Black** | Code formatting | `pyproject.toml` (if present) |
| **isort** | Import sorting | `isort` defaults |
| **Ruff** | Linting | `ruff.toml` (if present) |

Key conventions:
- Use **type hints** on all function signatures
- Prefer `async def` for all database and I/O operations
- Use **Pydantic v2 `model_config = ConfigDict(...)`** instead of deprecated `class Config`
- Keep functions focused; extract complex logic into service methods

### TypeScript / React (Frontend)

| Tool | Purpose |
|------|---------|
| **ESLint** | Linting (config: `eslint.config.mjs`) |
| **TypeScript** | Strict type checking (`tsconfig.json`) |

Key conventions:
- Use `'use client'` directive only when client-side interactivity is truly required
- Prefer `const` over `let`; avoid `var`
- Name React components in **PascalCase**; name hooks with the `use` prefix
- All `useEffect` dependency arrays must be complete (ESLint will warn on violations)

---

## 🔒 Security Notes for Contributors

- **Never commit** `.env`, API keys, secrets, or credentials — even in test files
- **Never disable** CSRF or authentication middleware in application code
- If you discover a security vulnerability, follow the [Security Policy](SECURITY.md) instead of opening a public issue

---

Thank you for helping make DocuMindAI better. Every contribution matters! 🙌
