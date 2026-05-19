# Whats-What — Going Live Checklist

This document is a handoff guide covering everything needed to take Whats-What from the current local development state to a production deployment.

---

## Current State

The MVP codebase is complete through Plan 5 of 6:

| # | Plan | Status |
|---|---|---|
| 1 | Foundation (models, DB, API skeleton) | ✅ Done |
| 2 | Collection Layer (8 data sources, Celery) | ✅ Done |
| 3 | Scoring Engine (composite trending score) | ✅ Done |
| 4 | Auth & Onboarding (magic link, JWT, preferences) | ✅ Done |
| 5 | Dashboard (API + Next.js mobile frontend) | ✅ Done |
| 6 | Email Digest (daily Resend delivery) | ⬜ Not started |

70 backend tests passing. Frontend builds clean.

---

## Remaining Development Work

### Plan 6 — Email Digest

The data model and Resend integration are already wired. What needs building:

- A Celery task that runs at 8am local time for each city (convert from UTC per city timezone)
- Queries the latest `TrendingScore` rows for users' subscribed city + categories
- Groups by `trend_direction` (rising / peak / new / fading)
- Renders an HTML email template (top 5 per category)
- Sends via Resend to all `DigestSubscription` users for that city

Estimated scope: ~1 day of development.

---

## API Keys to Obtain

All of these are free tiers and sufficient for MVP launch:

| Service | Where to Get | Notes |
|---|---|---|
| **Resend** | resend.com | Required for magic link auth AND email digest. Free tier: 3,000 emails/month. Verify your sending domain. |
| **Reddit** | reddit.com/prefs/apps | Create a "script" type app. Free. No rate limit issues at MVP scale. |
| **Yelp Fusion** | fusion.yelp.com | Free tier: 500 calls/day. Sufficient for 5 cities daily. |
| **Eventbrite** | eventbrite.com/platform/api-keys | Free. |
| **Spotify** | developer.spotify.com/dashboard | Free. Client credentials flow (no user login needed). |
| **Bandsintown** | No key needed | Uses `app_id` string only — already set to `whats-what`. |

**Eater RSS, Luma, Partiful**: No keys — public scraping.

---

## Infrastructure Recommendations

### Recommended Stack (cost-effective, low ops overhead)

| Component | Service | Est. Monthly Cost |
|---|---|---|
| Backend API | Railway or Render (web service) | ~$5–10 |
| Celery Worker | Railway or Render (background worker) | ~$5–10 |
| PostgreSQL | Railway Postgres or Supabase (free tier) | $0–5 |
| Redis | Railway Redis or Upstash | $0–3 |
| Frontend | Vercel (Next.js native) | Free tier |
| Domain + SSL | Cloudflare + registrar | ~$10–15/year |
| Email sending | Resend | Free up to 3k/month |

**Total estimate at launch: ~$15–30/month**

### Alternative: Fly.io
Good if you want more control and want to containerize everything. Requires writing Dockerfiles for the backend, worker, and potentially the frontend.

---

## Production Setup Steps

### 1. Environment Variables

Generate a strong secret key:
```bash
openssl rand -hex 32
```

Required production `.env` values:
```env
DATABASE_URL=postgresql+asyncpg://<user>:<pass>@<host>:<port>/<db>
REDIS_URL=redis://<host>:6379/0
SECRET_KEY=<generated above>
RESEND_API_KEY=<from resend.com>
FRONTEND_URL=https://yourdomain.com

REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=
YELP_API_KEY=
EVENTBRITE_API_KEY=
SPOTIFY_CLIENT_ID=
SPOTIFY_CLIENT_SECRET=
```

### 2. Database

On first deploy, run the migration against the production database:
```bash
alembic upgrade head
python scripts/seed_sources.py
```

### 3. Frontend — Point at Production Backend

In `frontend/next.config.ts`, the `/api/*` rewrite currently points to `localhost:8000`. For production, change to:
```ts
destination: "https://api.yourdomain.com/:path*",
```

Or set a `BACKEND_URL` environment variable and read it from `next.config.ts`.

### 4. Resend Domain Verification

Magic link emails come from `noreply@whats-what.app` (or whatever domain you configure). Resend requires DNS verification of the sending domain before emails will deliver. Set up SPF + DKIM records via Resend's dashboard.

### 5. Celery Worker

The Celery beat scheduler and worker need to run as persistent background processes. On Railway/Render, create a second service (same Docker image, different start command):

```
# API service
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Worker service (combine beat + worker for MVP simplicity)
celery -A app.celery_app worker --beat --loglevel=info
```

> Note: Running beat + worker in one process is fine for single-instance MVP. For production scale, separate them.

---

## Pre-Launch Checklist

### Security
- [ ] `SECRET_KEY` is a random 32+ byte value (not the dev default)
- [ ] Postgres is not publicly exposed (internal network only)
- [ ] CORS `allow_origins` in `app/main.py` is updated to your production domain
- [ ] Magic link tokens expire in 15 minutes (already implemented)
- [ ] JWT tokens expire in 30 days (already implemented)

### Data
- [ ] `alembic upgrade head` run against production DB
- [ ] `python scripts/seed_sources.py` run once
- [ ] At least one manual collection run verified (data appears in dashboard)
- [ ] Celery beat schedule confirmed running (check logs for 2am + 3am UTC tasks)

### Frontend
- [ ] API rewrite target updated to production backend URL
- [ ] `https://yourdomain.com` set as `FRONTEND_URL` in backend env
- [ ] `/auth/verify` page redirects work correctly in production
- [ ] Mobile tested on actual device (iOS Safari + Android Chrome)

### Email
- [ ] Resend API key active
- [ ] Sending domain verified in Resend dashboard
- [ ] Test magic link email received end-to-end
- [ ] (Plan 6) Daily digest Celery task scheduled and tested

### Monitoring (Nice to Have)
- [ ] Error logging (Sentry or similar) added to FastAPI + Celery
- [ ] Uptime monitoring (Better Uptime, UptimeRobot — free tier)
- [ ] `/health` endpoint polled by uptime monitor

---

## Questions for the Developer

1. **Hosting preference**: Railway, Render, Fly.io, or self-managed VPS?
2. **Domain**: Do you have a domain purchased, or does that need to be acquired?
3. **Email sending domain**: Will emails come from `@whats-what.app` or a different domain?
4. **Plan 6 (digest)**: Should this be built before launch or post-launch?
5. **Auth UX**: Should the onboarding flow be enforced before viewing the feed, or is browse-first / sign-up-later preferred?
6. **Rate limits**: Yelp allows 500 calls/day free. At 5 cities × ~50 calls each, we're at 250/day — fine. Confirm if you want more coverage.

---

## Codebase Notes for the Developer

- All async — the backend uses `asyncpg` and `async/await` throughout. Don't add synchronous DB calls.
- Collectors are isolated and independently testable. To add a new source, extend `BaseCollector` in `app/collectors/base.py`.
- Scoring weights (`volume: 0.50`, `sentiment: 0.25`, `freshness: 0.25`) are constants at the top of `app/scoring/engine.py` — easy to tune.
- Magic links are single-use and expire in 15 minutes. JWTs last 30 days. Both values are constants in `app/auth/tokens.py`.
- The test suite uses `unittest.mock` throughout — no live DB or network calls needed to run tests.
- `docker-compose.yml` maps Postgres to port **5433** (not 5432) to avoid conflicts with any locally installed Postgres.
