# City Pulse Tracker — Plan 1: Foundation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scaffold the full project structure, define all database models, run the initial migration, and verify everything works with a passing health check test.

**Architecture:** FastAPI backend with async SQLAlchemy + Alembic for migrations; Next.js frontend scaffolded but not yet connected; PostgreSQL + Redis run locally via Docker Compose. All six database tables are defined and migrated in this plan — later plans add logic on top without changing the schema.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0 (async), Alembic, asyncpg, pydantic-settings, Celery, Redis, pytest, Next.js 14, TypeScript, Tailwind CSS, Docker Compose

---

## File Map

```
Whats-what/
├── backend/
│   ├── pyproject.toml
│   ├── .env.example
│   ├── .env                        # git-ignored
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   │       └── 0001_initial_schema.py
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app + router registration
│   │   ├── config.py               # Pydantic settings (reads .env)
│   │   ├── database.py             # Async engine, session factory, Base
│   │   ├── models/
│   │   │   ├── __init__.py         # Re-exports all models (required by Alembic)
│   │   │   ├── user.py             # User, UserPreferences
│   │   │   ├── mention.py          # Mention
│   │   │   ├── trending.py         # TrendingScore
│   │   │   ├── source.py           # Source, CollectionError
│   │   │   └── digest.py           # DigestSubscription
│   │   └── api/
│   │       ├── __init__.py
│   │       └── health.py           # GET /health
│   └── tests/
│       ├── conftest.py             # Async test DB session fixture
│       └── test_health.py
├── frontend/
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   ├── next.config.ts
│   └── src/
│       └── app/
│           ├── layout.tsx
│           └── page.tsx
└── docker-compose.yml
```

---

## Task 1: Docker Compose (local Postgres + Redis)

**Files:**
- Create: `docker-compose.yml`

- [ ] **Step 1: Write `docker-compose.yml`**

```yaml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: whatswhat
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

- [ ] **Step 2: Start services**

```bash
docker compose up -d
```

Expected: containers `whats-what-postgres-1` and `whats-what-redis-1` running.

```bash
docker compose ps
```

Expected: both show `running`.

- [ ] **Step 3: Commit**

```bash
git add docker-compose.yml
git commit -m "feat: add docker-compose for local postgres and redis"
```

---

## Task 2: Backend Project Scaffold

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/.env.example`
- Create: `backend/.env`
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/app/main.py`

- [ ] **Step 1: Create `backend/pyproject.toml`**

```toml
[project]
name = "whats-what-backend"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.32",
    "sqlalchemy[asyncio]>=2.0",
    "asyncpg>=0.30",
    "alembic>=1.14",
    "pydantic-settings>=2.7",
    "celery[redis]>=5.4",
    "redis>=5.2",
    "httpx>=0.28",
    "pydantic>=2.10",
    "vaderSentiment>=3.3",
    "feedparser>=6.0",
    "beautifulsoup4>=4.12",
    "resend>=2.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3",
    "pytest-asyncio>=0.25",
    "pytest-cov>=6.0",
    "httpx>=0.28",
    "anyio>=4.7",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 2: Install dependencies**

```bash
cd backend
pip install -e ".[dev]"
```

Expected: all packages install without errors.

- [ ] **Step 3: Create `backend/.env.example`**

```
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/whatswhat
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=change-me-in-production
RESEND_API_KEY=
```

- [ ] **Step 4: Create `backend/.env`** (copy from example)

```bash
cp backend/.env.example backend/.env
```

- [ ] **Step 5: Create `backend/app/__init__.py`**

Empty file:
```python
```

- [ ] **Step 6: Create `backend/app/config.py`**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/whatswhat"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "dev-secret-key-change-in-production"
    resend_api_key: str = ""

    model_config = {"env_file": ".env"}


settings = Settings()
```

- [ ] **Step 7: Create `backend/app/main.py`**

```python
from fastapi import FastAPI
from app.api.health import router as health_router

app = FastAPI(title="Whats-What API", version="0.1.0")

app.include_router(health_router)
```

- [ ] **Step 8: Commit**

```bash
git add backend/
git commit -m "feat: scaffold backend project with fastapi and config"
```

---

## Task 3: Database Setup

**Files:**
- Create: `backend/app/database.py`

- [ ] **Step 1: Create `backend/app/database.py`**

```python
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(settings.database_url, echo=False)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_session() -> AsyncSession:
    async with async_session_factory() as session:
        yield session
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/database.py
git commit -m "feat: add async sqlalchemy engine and session factory"
```

---

## Task 4: Database Models

**Files:**
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/user.py`
- Create: `backend/app/models/mention.py`
- Create: `backend/app/models/trending.py`
- Create: `backend/app/models/source.py`
- Create: `backend/app/models/digest.py`

- [ ] **Step 1: Create `backend/app/models/user.py`**

```python
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20))
    city: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    onboarding_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    preferences: Mapped["UserPreferences | None"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    subscriptions: Mapped[list["DigestSubscription"]] = relationship(  # noqa: F821
        back_populates="user", cascade="all, delete-orphan"
    )


class UserPreferences(Base):
    __tablename__ = "user_preferences"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    categories: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    favorite_venues: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    favorite_artists: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    neighborhood: Mapped[str | None] = mapped_column(String(100))
    vibe_tags: Mapped[list[str] | None] = mapped_column(ARRAY(String))

    user: Mapped["User"] = relationship(back_populates="preferences")
```

- [ ] **Step 2: Create `backend/app/models/mention.py`**

```python
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

ENTITY_TYPES = ("venue", "artist", "event", "dish")
CATEGORIES = ("music", "food", "fitness", "networking")


class Mention(Base):
    __tablename__ = "mentions"

    id: Mapped[int] = mapped_column(primary_key=True)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_name: Mapped[str] = mapped_column(String(255), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    content_snippet: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(Text)
    mention_count: Mapped[int] = mapped_column(Integer, default=1)
    sentiment_score: Mapped[float | None] = mapped_column()
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
```

- [ ] **Step 3: Create `backend/app/models/trending.py`**

```python
from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

TREND_DIRECTIONS = ("rising", "peak", "fading", "new")


class TrendingScore(Base):
    __tablename__ = "trending_scores"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_name: Mapped[str] = mapped_column(String(255), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    volume_score: Mapped[float] = mapped_column(Float, nullable=False)
    sentiment_score: Mapped[float] = mapped_column(Float, nullable=False)
    freshness_score: Mapped[float] = mapped_column(Float, nullable=False)
    composite_score: Mapped[float] = mapped_column(Float, nullable=False)
    trend_direction: Mapped[str] = mapped_column(String(20), nullable=False)
    scored_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
```

- [ ] **Step 4: Create `backend/app/models/source.py`**

```python
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    categories: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    rate_limit_daily: Mapped[int | None] = mapped_column(Integer)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CollectionError(Base):
    __tablename__ = "collection_errors"

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
```

- [ ] **Step 5: Create `backend/app/models/digest.py`**

```python
from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DigestSubscription(Base):
    __tablename__ = "digest_subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    categories: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    frequency: Mapped[str] = mapped_column(String(20), default="daily")
    format: Mapped[str] = mapped_column(String(20), default="email")

    user: Mapped["User"] = relationship(back_populates="subscriptions")  # noqa: F821
```

- [ ] **Step 6: Create `backend/app/models/__init__.py`**

This file must import all models so Alembic can detect them:

```python
from app.models.digest import DigestSubscription
from app.models.mention import Mention
from app.models.source import CollectionError, Source
from app.models.trending import TrendingScore
from app.models.user import User, UserPreferences

__all__ = [
    "User",
    "UserPreferences",
    "Mention",
    "TrendingScore",
    "Source",
    "CollectionError",
    "DigestSubscription",
]
```

- [ ] **Step 7: Commit**

```bash
git add backend/app/models/
git commit -m "feat: define all database models (user, mention, trending, source, digest)"
```

---

## Task 5: Alembic Setup and Initial Migration

**Files:**
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/versions/0001_initial_schema.py`

- [ ] **Step 1: Initialize Alembic**

```bash
cd backend
alembic init alembic
```

Expected: `alembic/` directory and `alembic.ini` created.

- [ ] **Step 2: Update `backend/alembic.ini`** — set the sqlalchemy.url line

Find this line:
```
sqlalchemy.url = driver://user:pass@localhost/dbname
```

Replace with:
```
sqlalchemy.url = postgresql+asyncpg://postgres:postgres@localhost:5432/whatswhat
```

- [ ] **Step 3: Replace `backend/alembic/env.py`** with async-compatible version

```python
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings
from app.database import Base
import app.models  # noqa: F401 — registers all models with Base.metadata

config = context.config
fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = create_async_engine(settings.database_url)
    async with connectable.connect() as connection:
        await connection.run_sync(
            lambda conn: context.configure(
                connection=conn, target_metadata=target_metadata
            )
        )
        async with connection.begin():
            await connection.run_sync(lambda _: context.run_migrations())


def run() -> None:
    if context.is_offline_mode():
        run_migrations_offline()
    else:
        asyncio.run(run_migrations_online())


run()
```

- [ ] **Step 4: Generate initial migration**

```bash
cd backend
alembic revision --autogenerate -m "initial schema"
```

Expected: a new file created in `alembic/versions/` named something like `xxxx_initial_schema.py`.

- [ ] **Step 5: Run the migration**

```bash
alembic upgrade head
```

Expected output ends with: `Running upgrade  -> xxxx, initial schema`

- [ ] **Step 6: Verify tables exist**

```bash
docker compose exec postgres psql -U postgres -d whatswhat -c "\dt"
```

Expected: table list showing `users`, `user_preferences`, `mentions`, `trending_scores`, `sources`, `collection_errors`, `digest_subscriptions`.

- [ ] **Step 7: Commit**

```bash
git add backend/alembic.ini backend/alembic/
git commit -m "feat: add alembic and run initial schema migration"
```

---

## Task 6: Health Endpoint

**Files:**
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/health.py`

- [ ] **Step 1: Write the failing test first**

Create `backend/tests/conftest.py`:

```python
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
```

Create `backend/tests/__init__.py` (empty):
```python
```

Create `backend/tests/test_health.py`:

```python
async def test_health_returns_ok(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend
pytest tests/test_health.py -v
```

Expected: FAIL — `404 Not Found` or import error (route not defined yet).

- [ ] **Step 3: Create `backend/app/api/__init__.py`**

```python
```

- [ ] **Step 4: Create `backend/app/api/health.py`**

```python
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}
```

- [ ] **Step 5: Run test to verify it passes**

```bash
pytest tests/test_health.py -v
```

Expected:
```
tests/test_health.py::test_health_returns_ok PASSED
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/ backend/tests/
git commit -m "feat: add health endpoint with passing test"
```

---

## Task 7: Frontend Scaffold

**Files:**
- Create: `frontend/` (Next.js project)

- [ ] **Step 1: Scaffold Next.js app**

```bash
cd "$(git rev-parse --show-toplevel)"
npx create-next-app@latest frontend \
  --typescript \
  --tailwind \
  --eslint \
  --app \
  --src-dir \
  --no-import-alias
```

When prompted, accept all defaults.

- [ ] **Step 2: Replace `frontend/src/app/page.tsx`** with placeholder

```tsx
export default function Home() {
  return (
    <main className="min-h-screen flex items-center justify-center bg-black text-white">
      <div className="text-center">
        <h1 className="text-4xl font-bold tracking-tight">Whats-What</h1>
        <p className="mt-2 text-zinc-400">City pulse tracker — coming soon</p>
      </div>
    </main>
  );
}
```

- [ ] **Step 3: Verify frontend runs**

```bash
cd frontend
npm run dev
```

Expected: server starts at `http://localhost:3000`. Open in browser — should show "Whats-What / City pulse tracker — coming soon" on a black background.

Stop the server (`Ctrl+C`).

- [ ] **Step 4: Add `.gitignore` entries at repo root**

Create `backend/.gitignore`:
```
.env
__pycache__/
*.pyc
.pytest_cache/
dist/
*.egg-info/
```

- [ ] **Step 5: Commit**

```bash
git add frontend/ backend/.gitignore
git commit -m "feat: scaffold next.js frontend with tailwind"
```

---

## Task 8: Verify Full Stack Locally

- [ ] **Step 1: Start all services**

In one terminal:
```bash
docker compose up -d
```

In a second terminal:
```bash
cd backend
uvicorn app.main:app --reload
```

In a third terminal:
```bash
cd frontend
npm run dev
```

- [ ] **Step 2: Verify backend health**

```bash
curl http://localhost:8000/health
```

Expected: `{"status":"ok"}`

- [ ] **Step 3: Verify frontend**

Open `http://localhost:3000` in browser. Expected: placeholder page renders.

- [ ] **Step 4: Run full backend test suite**

```bash
cd backend
pytest --cov=app tests/ -v
```

Expected: all tests pass, coverage report shown.

- [ ] **Step 5: Final commit and push**

```bash
git add -A
git commit -m "feat: foundation complete — backend, frontend, db schema all verified"
git push origin whats-what
```

---

## What Comes Next

| Plan | Builds |
|---|---|
| Plan 2: Collection Layer | Celery workers for Reddit, Yelp, Eventbrite, Luma, Partiful, Bandsintown, Spotify, Eater RSS |
| Plan 3: Scoring Engine | Daily trending score computation + trend direction labels |
| Plan 4: Auth & Onboarding | Magic link auth, user accounts, preference capture |
| Plan 5: Dashboard | Next.js city/category feed, trend cards, entity detail |
| Plan 6: Digest Delivery | Daily email digest via Resend |
