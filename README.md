# Whats-What — City Pulse Tracker

A real-time signal aggregator that surfaces trending venues, artists, events, and experiences across five cities. It pulls from social media, event platforms, review sites, and RSS feeds, scores everything daily, and serves a mobile-first web dashboard plus email digest.

---

## What It Does

Users pick a city and a category (Music, Food, Fitness, Networking) and see what's trending *right now* — not just popular, but **rising vs. fading** — based on a composite score of volume, sentiment, and freshness.

**Cities:** Austin · Dallas · San Antonio · New York · Los Angeles

**Categories:** Music · Food · Fitness & Wellness · Networking & Happy Hours

**Entity types tracked:** Venues, Artists, Events, Dishes

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI (Python 3.12), async SQLAlchemy 2.0 |
| Database | PostgreSQL 16 |
| Task queue | Celery 5 + Redis 7 |
| Sentiment | VADER NLP |
| Auth | Magic link email + JWT (HS256) |
| Email | Resend |
| Frontend | Next.js 16, React 19, Tailwind CSS 4 |
| Local infra | Docker Compose (Postgres + Redis) |

---

## Project Structure

```
Whats-What/
├── backend/
│   ├── app/
│   │   ├── api/            # FastAPI routers (health, auth, trending, onboarding)
│   │   ├── auth/           # JWT tokens, magic link email, Bearer dep
│   │   ├── collectors/     # 8 data source collectors
│   │   ├── models/         # SQLAlchemy ORM models
│   │   ├── scoring/        # Trending score engine
│   │   ├── tasks/          # Celery tasks (collect, score)
│   │   ├── config.py       # Pydantic settings (reads .env)
│   │   ├── database.py     # Async engine + session factory
│   │   └── main.py         # FastAPI app
│   ├── alembic/            # DB migrations
│   ├── scripts/            # One-off scripts (seed_sources.py)
│   ├── tests/              # 70 passing tests
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── app/            # Next.js App Router pages
│   │   │   ├── page.tsx        # Main feed (city + category + trend cards)
│   │   │   └── auth/           # sign-in and verify pages
│   │   ├── components/     # TrendCard, CitySelector, CategoryTabs
│   │   └── lib/            # API client, shared types
│   └── next.config.ts      # Proxies /api/* → backend :8000
├── docker-compose.yml      # Postgres (5433) + Redis (6379)
└── docs/
    └── superpowers/
        └── specs/          # Full design spec
```

---

## Data Sources

| Source | Categories | Auth Required |
|---|---|---|
| Reddit | Music, Food, Fitness, Networking | Client ID + Secret |
| Yelp Fusion | Food, Music (venues) | API key |
| Eventbrite | Music, Food, Fitness, Networking | API key |
| Bandsintown | Music | None (app_id only) |
| Spotify | Music (artist popularity) | Client ID + Secret |
| Eater RSS | Food | None |
| Luma (scraper) | Fitness, Networking | None |
| Partiful (scraper) | Fitness, Networking | None |

---

## Trending Score

```
composite = volume(0.50) + sentiment(0.25) + freshness(0.25)
```

- **Volume** — normalized mention count across all sources in the last 7 days
- **Sentiment** — average sentiment from collector ratings + VADER NLP on text snippets
- **Freshness** — exponential decay with a 3.5-day half-life (today = 1.0, week-old = 0.25)
- **Trend direction** — `new` / `rising` / `peak` / `fading` vs. the prior day's score

---

## Local Development Setup

### Prerequisites

- Python 3.12+
- Node.js 20+
- Docker Desktop

### 1. Clone and configure

```bash
git clone https://github.com/aristotle-resonate/Whats-what.git
cd Whats-what

cp backend/.env.example backend/.env
# Fill in API keys in backend/.env (see section below)
```

### 2. Start infrastructure

```bash
docker compose up -d
# Postgres on localhost:5433, Redis on localhost:6379
```

### 3. Backend

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

alembic upgrade head          # Create all tables
python scripts/seed_sources.py  # Populate sources table (run once)

uvicorn app.main:app --reload   # API at http://localhost:8000
```

### 4. Frontend

```bash
cd frontend
npm install
npm run dev                   # App at http://localhost:3000
```

### 5. Run a manual collection + score cycle

```bash
# In backend venv — runs one collector for Austin and scores it
python -c "
import asyncio
from app.collectors.bandsintown import BandsintownCollector
from app.scoring.engine import compute_scores_for_city
asyncio.run(BandsintownCollector().run('austin'))
asyncio.run(compute_scores_for_city('austin'))
print('Done — refresh localhost:3000')
"
```

### 6. Tests

```bash
cd backend
python -m pytest -v    # 70 tests, all should pass
```

---

## Environment Variables

Copy `backend/.env.example` to `backend/.env` and fill in:

```env
# Required for any data to appear
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5433/whatswhat
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=<random 32+ char string>

# Email (magic link auth) — get at resend.com
RESEND_API_KEY=

# Reddit — create app at reddit.com/prefs/apps (type: script)
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=

# Yelp — get at fusion.yelp.com
YELP_API_KEY=

# Eventbrite — get at eventbrite.com/platform/api-keys
EVENTBRITE_API_KEY=

# Bandsintown — no auth needed, uses app_id
BANDSINTOWN_APP_ID=whats-what

# Spotify — create app at developer.spotify.com/dashboard
SPOTIFY_CLIENT_ID=
SPOTIFY_CLIENT_SECRET=

# Frontend URL (for magic link emails)
FRONTEND_URL=http://localhost:3000
```

---

## Scheduled Jobs (Celery Beat)

| Time (UTC) | Task |
|---|---|
| 2:00 AM | Collect from all 8 sources × 5 cities |
| 3:00 AM | Compute trending scores for all cities |

Start workers locally:

```bash
# Worker
celery -A app.celery_app worker --loglevel=info

# Scheduler
celery -A app.celery_app beat --loglevel=info
```

---

## API Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/health` | — | Health check |
| POST | `/auth/request-link` | — | Send magic sign-in link |
| GET | `/auth/verify?token=` | — | Validate token, return JWT |
| GET | `/auth/me` | Bearer | Current user profile |
| PUT | `/auth/onboarding` | Bearer | Save city + category preferences |
| GET | `/trending?city=&category=&limit=` | — | Latest trending entities |

Interactive docs at `http://localhost:8000/docs` when backend is running.

---

## What's Built (Plans 1–5)

- [x] **Plan 1 — Foundation**: PostgreSQL models, Alembic migrations, FastAPI skeleton, health endpoint, Next.js scaffold
- [x] **Plan 2 — Collection Layer**: 8 data collectors, BaseCollector, Celery beat schedule, source seeding
- [x] **Plan 3 — Scoring Engine**: 7-day mention aggregation, VADER sentiment, freshness decay, composite scoring, trend direction
- [x] **Plan 4 — Auth & Onboarding**: Magic link login, JWT sessions, user preferences, digest subscription setup
- [x] **Plan 5 — Dashboard**: `GET /trending` API, Next.js mobile-first feed (city selector, category tabs, trend cards, sign-in flow)

---

## What Still Needs Building

See [`docs/GOING_LIVE.md`](docs/GOING_LIVE.md) for the full production checklist.

Short version:

- [ ] **Plan 6 — Email Digest**: Daily Resend email at 8am local time per city
- [ ] **Production infra**: Dockerfiles for backend + Celery, hosting (Railway / Render / Fly.io recommended), domain + SSL
- [ ] **Real API keys**: All keys in `.env.example` need to be filled for full data coverage
- [ ] **Database migration**: Run `alembic upgrade head` against the production database on first deploy
- [ ] **Secret key**: Generate a strong `SECRET_KEY` for production JWT signing (`openssl rand -hex 32`)
- [ ] **Frontend env**: Set `NEXT_PUBLIC_API_URL` or update rewrite target to point at production backend
