# FinPulse Backend

**Stock Market Monitoring Platform — FastAPI Backend**

---

## Tech Stack

| Layer | Technology |
|---|---|
| Web Framework | FastAPI + Uvicorn |
| Database | PostgreSQL (via asyncpg) |
| ORM | SQLAlchemy 2.x (async) |
| Migrations | Alembic |
| Scheduler | APScheduler |
| Config | pydantic-settings |
| Logging | Python logging + JSON formatter |

---

## Project Structure

```
finpulse-backend/
├── app/
│   ├── main.py              ← FastAPI app factory, lifespan hooks
│   ├── config.py            ← Environment-based settings (pydantic-settings)
│   ├── api/                 ← HTTP layer: route handlers only
│   │   ├── deps.py          ← Shared FastAPI Depends() callables
│   │   ├── router.py        ← Master router aggregation
│   │   └── v1/              ← Versioned API endpoints
│   ├── core/                ← Cross-cutting concerns
│   │   ├── logging.py       ← Logging setup
│   │   ├── exceptions.py    ← Custom exception classes
│   │   └── exception_handlers.py
│   ├── database/            ← DB connection infrastructure
│   │   ├── engine.py        ← Async SQLAlchemy engine
│   │   ├── session.py       ← Session factory + dependency
│   │   └── base.py          ← DeclarativeBase + mixins
│   ├── models/              ← SQLAlchemy ORM table definitions
│   ├── schemas/             ← Pydantic request/response DTOs
│   ├── repositories/        ← Data access layer (DB queries)
│   ├── services/            ← Business logic layer
│   ├── scheduler/           ← APScheduler configuration
│   ├── middleware/          ← Custom ASGI middleware
│   └── utils/               ← Pure utility helpers
├── migrations/              ← Alembic migration files
├── tests/                   ← pytest test suite (conftest.py ready)
├── .env                     ← Local environment variables (not committed)
├── .env.example             ← Environment variable template
├── alembic.ini              ← Alembic config
├── docker-compose.yml       ← PostgreSQL + app container setup
└── requirements.txt         ← Python dependencies
```

---

## Quickstart

### 1. Clone & Setup Environment
```bash
cd finpulse-backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/Mac
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
copy .env.example .env        # Windows
# cp .env.example .env        # Linux/Mac
# Edit .env with your values
```

### 3. Run Database Migrations
```bash
alembic upgrade head
```

### 4. Start the Server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. View API Docs
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health: http://localhost:8000/health

---

## Architecture Principles

- **Clean Architecture** — each layer has one responsibility
- **Dependency Injection** — services/repos injected via FastAPI `Depends()`
- **Async First** — all DB operations are async (asyncpg driver)
- **No business logic in routes** — controllers are thin; logic lives in services
- **Idempotent migrations** — Alembic manages all schema changes

---

## Layer Responsibilities

| Layer | Folder | Responsibility |
|---|---|---|
| HTTP | `api/` | Accept requests, validate input, return responses |
| Business Logic | `services/` | Orchestrate operations, enforce rules |
| Data Access | `repositories/` | Database queries only — no business logic |
| ORM Models | `models/` | Table definitions |
| DTOs | `schemas/` | Pydantic input/output shapes |
| Infrastructure | `database/`, `core/` | Sessions, logging, exceptions |
| Background | `scheduler/` | Periodic jobs (data refresh) |
