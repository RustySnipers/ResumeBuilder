# AI-Powered ATS-Friendly Resume Builder

A secure FastAPI backend for generating ATS-friendly resumes with mandatory PII redaction, LLM-powered optimization, export tooling, analytics, and webhook integrations.

## Feature Highlights
- **Security first**: Every request passes through a non-bypassable PII redaction gate before any downstream processing or LLM usage.
- **Resume analysis**: NLP-driven gap analysis (semantic similarity, TF-IDF keywords, section parsing, keyword stuffing detection) to pinpoint missing skills.
- **LLM optimization**: Claude-based resume generation with caching, retry logic, validation/sanitization, and streaming (SSE) support.
- **Access control**: Authentication, role management, and API key routing with optional rate limiting middleware.
- **Export system**: Generate PDF/DOCX/HTML resumes using reusable templates and cacheable export metrics.
- **Analytics & metrics**: Health/readiness probes plus models for usage, export, webhook, and daily metrics collection.
- **Webhooks & resumes**: REST routers for managing webhooks and persisted resumes to support downstream integrations.

## Project Layout
- `main.py`: FastAPI entrypoint wiring routers, middleware, NLP/LLM clients, and cache.
- `backend/`
  - `auth/`, `api/`, `middleware/`: Authentication, API key routing, rate limiting hooks.
  - `llm/`: Claude client, prompt templates, caching, retry logic, validation.
  - `nlp/`: PII detection, section parsing, keyword extraction, semantic analysis.
  - `export/`: PDF/DOCX generators, template engine, cache helpers, router.
  - `analytics/`, `webhooks/`, `resumes/`: Domain routers and services for metrics, webhooks, and resume persistence.
  - `models/`, `repositories/`: SQLAlchemy models and data access helpers.
- `tests/`: Unit and integration coverage for NLP, LLM retry logic, repositories, and export flows.
- Deployment docs: `DEPLOYMENT.md`, `DEPLOYMENT_GUIDE.md`, `LOCAL_DEPLOYMENT.md`, `docker-compose.yml`.

## Getting Started
1. **Install prerequisites**
   - Python 3.10+
   - Optional services: PostgreSQL + Redis (used for persistence and caching)
2. **Create a virtual environment and install dependencies**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
   pip install -r requirements.txt
   ```
3. **Configure environment**
   - `DATABASE_URL` (e.g., `postgresql+asyncpg://user:pass@localhost:5432/resumebuilder`)
   - `REDIS_URL` (e.g., `redis://localhost:6379/0`)
   - `ANTHROPIC_API_KEY` for LLM-powered generation
4. **Run the API**
   - Quick start (uses sensible defaults):
     ```bash
     python main.py
     ```
   - Optional flags via environment variables:
     ```bash
     APP_HOST=127.0.0.1 APP_PORT=8080 APP_RELOAD=true python main.py
     ```
   - Equivalent Uvicorn invocation:
     ```bash
     uvicorn main:app --reload --host 0.0.0.0 --port 8000
     ```
   - Docs: http://localhost:8000/docs
   - Health checks: `/`, `/health`, `/health/ready`, `/health/live`

## Lite Mode (offline/desktop)
- Enable with `LITE_MODE=true` in your environment before starting the app.
- What changes:
  - In-memory caches replace Redis for both general caching and LLM responses.
  - A SQLite database file in a temporary directory replaces PostgreSQL (override with `DATABASE_URL` if you prefer a fixed SQLite file).
  - A stub Claude client returns a canned local response when `ANTHROPIC_API_KEY` is absent, keeping generation endpoints usable offline.
  - Analytics, export, webhook routing, and Redis-backed rate limiting are skipped to avoid missing dependency/import errors.
- Intended use cases: air-gapped development, quick desktop demos, and CI smoke tests without external services.

## Development & Quality Gates
- Linting/unused code: `ruff check`
- Syntax smoke test: `python -m compileall backend main.py`
- Tests: `pytest` (requires optional services for database/redis-dependent cases)
- Formatting: the codebase is Ruff-formatted; avoid wrapping imports in try/except blocks.

## API Highlights
- `GET /` and `GET /health*`: Service readiness and dependency checks (DB, Redis, LLM, NLP).
- `POST /api/v1/analyze`: PII-redacts inputs, runs NLP gap analysis, and returns missing keywords plus suggestions.
- `POST /api/v1/generate` & `/generate/stream`: Generate optimized resumes (sync or SSE stream) with caching/validation.
- `GET/DELETE /api/v1/cache*`: Inspect or clear cached LLM responses.
- Auth, export, analytics, resume, and webhook routers are included for broader platform workflows; enable middleware (rate limiting, analytics) as needed in `main.py`.

## Security & Compliance
- PII redaction is mandatory before any prompt construction.
- API keys should be supplied via headers; environment variables keep secrets out of code.
- Redis-backed rate limiting and analytics middleware are available but disabled by default for local development.

## Deployment Notes
- `docker-compose.yml` provides a local stack (API + optional services). Review `DEPLOYMENT*.md` for production hardening, migrations, and TLS guidance.
