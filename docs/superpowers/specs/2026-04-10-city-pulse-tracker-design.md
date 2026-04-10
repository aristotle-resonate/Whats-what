# City Pulse Tracker — Design Spec
**Date:** 2026-04-10
**Status:** Approved

---

## Overview

A city pulse tracker that aggregates signals from social media, event platforms, review sites, and local newsletters to surface trending venues, artists, events, and experiences across five cities. Determines what's hip, what's peaking, and what's fading — with emphasis on music and food.

**Cities:** Austin, Dallas, San Antonio, New York, Los Angeles
**Categories:** Music (heavy), Food (heavy), Fitness & Wellness, Networking & Happy Hours
**Audience:** Personal use → community → public product

---

## Architecture

### Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js (mobile-first, SSR) |
| Backend API | FastAPI (Python) |
| Task Queue | Celery + Redis |
| Database | PostgreSQL |
| Email delivery | Resend (or SendGrid) |
| Frontend hosting | Vercel |
| Backend + DB hosting | Railway |

### System Diagram

```
┌─────────────────────────────────────────────────────┐
│                  COLLECTION LAYER                   │
│  Celery workers (one per source, run daily @ 2am)   │
│  Reddit · Yelp · Eventbrite · Bandsintown           │
│  Spotify · Google Places · Eater RSS                │
│  Luma · Partiful · Local venue sites                │
└──────────────────────┬──────────────────────────────┘
                       │ raw mentions/events → Postgres
┌──────────────────────▼──────────────────────────────┐
│                  SCORING ENGINE                     │
│  volume score + sentiment score + freshness score   │
│  → composite_score (0–100), trend_direction label   │
│  Runs after collection, results stored in Postgres  │
└──────────────────────┬──────────────────────────────┘
                       │ scored data
        ┌──────────────┴──────────────┐
        ▼                             ▼
┌───────────────┐            ┌─────────────────────┐
│   DASHBOARD   │            │  DIGEST DELIVERY    │
│  Next.js SSR  │            │  Email (Resend)      │
│  Mobile-first │            │  SMS (Twilio)        │
│  Per-city     │            │  Daily 8am local time│
│  Per-category │            └─────────────────────┘
└───────────────┘
```

### Key Principles

- Everything is tagged with `city` + `category`
- Raw data is preserved so scores can be recalculated with improved algorithms
- All sources feed one unified `mentions` table — the scoring engine is source-agnostic
- City/source combos are config-driven — adding a new source requires no code changes

---

## Data Model

### `users`
```
id, email, phone, city, created_at, onboarding_completed_at
```

### `user_preferences`
Captured during optional onboarding (3–4 questions, each skippable).
```
id, user_id, categories (array, weighted),
favorite_venues (array), favorite_artists (array),
neighborhood (optional),
vibe_tags (e.g. "live music", "craft cocktails", "rooftop")
```

### `mentions`
Raw ingested data — one row per scraped/fetched item.
```
id, city, category, source, entity_name, entity_type
(venue | artist | event | dish), content_snippet,
url, mention_count, sentiment_score, published_at, collected_at
```

### `trending_scores`
Computed daily per entity per city.
```
id, entity_name, entity_type, city, category,
volume_score, sentiment_score, freshness_score,
composite_score (0–100),
trend_direction (rising | peak | fading | new),
scored_at
```

### `digest_subscriptions`
```
id, user_id, city, categories (array), frequency, format (email)
```

### `sources`
Config table — which source/city combos are active, credentials, rate limits.
```
id, name, city, categories (array), active, rate_limit_daily, last_run_at
```

### `collection_errors`
```
id, source, city, error_message, occurred_at, retry_count
```

---

## Data Sources

| Source | Category | What we pull | Method |
|---|---|---|---|
| Reddit | All | Post/comment volume, upvotes, sentiment on city subreddits | Official API |
| Yelp Fusion | Food, Fitness | New businesses, review velocity, rating trends | Official API |
| Eventbrite | Networking, Fitness, Music, Wellness | Events, RSVP counts, sell-out speed | Official API |
| Luma (lu.ma) | Wellness, Fitness, Networking | Run clubs, wellness gatherings, social events | HTML scrape |
| Partiful | Networking, Social | Public event listings, RSVP momentum | HTML scrape |
| Bandsintown | Music | Shows, artist popularity, venue activity | Official API |
| Spotify | Music | Artist popularity scores, trending tracks | Official API |
| Google Places | Food, Music, Fitness | Review counts over time, rating momentum | Official API (pay-per-use) |
| Eater RSS | Food | Editorial mention = buzz signal | RSS scrape |
| Local venue sites | Music | Calendars, newsletter content | HTML scrape |

**Tier 1 (MVP launch):** Reddit, Yelp, Eventbrite, Luma, Partiful, Bandsintown, Spotify, Eater RSS
**Tier 2 (add after MVP):** Google Places, local venue sites

**Note:** Eater RSS covers Austin, Dallas, New York, and Los Angeles — not San Antonio. San Antonio city coverage relies on Reddit, Yelp, Eventbrite, Luma, and Bandsintown at MVP.
**Note:** Partiful scraping depends on public event availability — monitor stability post-launch and disable per-city if scraping breaks.

---

## Scoring Engine

Runs daily after collection. Produces one `trending_scores` row per entity per city.

### Formula

```
composite_score = (volume × 0.50) + (sentiment × 0.25) + (freshness × 0.25)
```

All components normalized to 0–100 before weighting.

### Components

**Volume score:** Mention count over last 7 days vs. 30-day rolling baseline. Normalized so baseline = 50.

**Sentiment score:** VADER NLP runs on `content_snippet`. Output mapped 0–100 (0 = very negative, 100 = very positive).

**Freshness score:** Entities opened/launched recently get a boost. Decays on a curve — 2-week-old venue scores higher than a 3-year-old one, all else equal.

### Trend Direction

| Label | Condition | Display |
|---|---|---|
| `rising` | Composite up >20% vs. 7-day avg | "Trending Up ↑" |
| `peak` | High score, <20% change | "Popular" |
| `fading` | Composite down >20% vs. 7-day avg | "Cooling Off ↓" |
| `new` | <14 days of data | "New & Buzzing" |

**Hip vs. fading signal:** `rising` + high composite = hip. `fading` + was previously high = losing its moment.

### Personalization

Entities matching a user's `user_preferences` (favorite venues, vibe tags, categories) receive a 1.2× display multiplier for ordering on their personal feed. Raw scores in the DB are unchanged.

---

## Dashboard

**Tech:** Next.js, mobile-first, SSR for fast initial load.

**Navigation:** City selector → Category tabs (All / Music / Food / Fitness & Wellness / Networking)

**Trend card:**
```
[Venue/Artist/Event Name]        [Trending Up ↑]
Category · Neighborhood
"Brief snippet or reason for buzz"
⬤⬤⬤⬤○  Score: 82              [See More]
```

**Views:**
- **Home feed** — personalized if logged in, city-wide trends if anonymous
- **Category view** — filtered by category
- **Entity detail** — mention sources, score history chart, upcoming events
- **Trending map** — future phase

**Auth:** Email/password + magic link. No OAuth at MVP.

---

## Digest Delivery

**Schedule:** Daily at 8am local time per city.
**Trigger:** Celery beat task fires after scoring engine completes.

### Email Format (Resend)
Clean, skimmable. Top 5–7 items per subscribed category, ranked by composite score.

```
What's Hot in Austin Today · Thursday April 10

🎵 MUSIC
↑ The Scoot Inn — packed shows 3 nights running
↑ Khruangbin buzz spiking ahead of ACL warm-up

🍽 FOOD
↑ Comedor — new tasting menu getting serious attention
↓ [Fading spot] — reviews cooling after ownership change
```

---

## Onboarding

Optional, ~3–4 questions shown after account creation. Each step is skippable.

1. Which city are you in?
2. Which categories interest you most? (multi-select)
3. Any venues or artists you already follow? (free text, optional)
4. Pick vibe tags that fit you (e.g. "live music", "craft cocktails", "rooftop", "run clubs")

Results stored in `user_preferences`. Dashboard and digest personalize immediately.

---

## Error Handling

- Failed collection tasks log to `collection_errors` and auto-retry next cycle
- 3+ consecutive daily failures for a source → admin alert email
- Scoring engine skips entities with <3 mentions (insufficient signal)
- API rate limit hits back off and reschedule within the same daily window

---

## Testing Strategy

- **Unit:** Scoring algorithm (known inputs → expected outputs), sentiment normalization, trend direction logic
- **Integration:** Each collector tested against API using recorded fixtures — no live API calls in CI
- **End-to-end:** Full daily pipeline run against seeded test city, verifying digest output format
- **Frontend:** Basic smoke tests on dashboard render at MVP

---

## Deployment & Cost

| Service | Provider | Est. Monthly Cost |
|---|---|---|
| Frontend | Vercel (free tier) | $0 |
| Backend API + Celery | Railway | ~$10–15 |
| PostgreSQL | Railway | ~$5–10 |
| Redis | Railway | ~$5 |
| Email (Resend) | Resend free tier (3k/mo) | $0 |
| **Total** | | **~$20–30/month** |

---

## Path to Real-Time

The only component that changes when moving to real-time is the scheduler trigger:

```
MVP:    Celery beat cron → daily at 2am
Future: Webhooks/streaming → tasks fire on new data events
```

Reddit, Spotify, and Eventbrite support webhooks. The pipeline, scoring engine, delivery layer, and database schema remain unchanged.
