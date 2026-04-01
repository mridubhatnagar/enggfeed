# Deployment Checklist

## Stack
- **Server:** Digital Ocean Droplet — $6/month (1 vCPU, 1GB RAM)
- **Database:** PostgreSQL in Docker Compose (copied from local, not re-ingested)
- **Cache:** Redis in Docker Compose
- **Ingest scheduling:** GitHub Actions cron (daily) — re-enable manually from Actions tab if disabled after 60 days of repo inactivity
- **Observability:** Phoenix self-hosted in Docker Compose (collects prod traces from first ingest run)

---

## One-Time Server Setup

- [ ] Create DO droplet — Ubuntu 24.04 LTS, $6/month (1 vCPU, 1GB RAM)
- [ ] SSH into droplet and install Docker + Docker Compose
- [ ] Open ports: 80 (HTTP), 443 (HTTPS), 22 (SSH)
- [ ] Point domain to droplet IP (or use droplet IP directly)

---

## Environment Variables (Prod)

Create `.env.prod` on the server (never commit this):

| Variable | Note |
|---|---|
| `DATABASE_URL` | `postgresql://user:password@postgresql:5432/enggsystemfeed` |
| `REDIS_URL` | `redis://redis:6379` |
| `JWT_SECRET` | strong random string |
| `GOOGLE_CLIENT_ID` | from Google Cloud Console |
| `GOOGLE_CLIENT_SECRET` | from Google Cloud Console |
| `GOOGLE_REDIRECT_URI` | `https://<your-domain>/auth/callback` |
| `POSTGRES_USER` | for postgresql container |
| `POSTGRES_PASSWORD` | for postgresql container |
| `POSTGRES_DB` | for postgresql container |
| `SWAGGER_USERNAME` | for `/docs` Basic Auth |
| `SWAGGER_PASSWORD` | for `/docs` Basic Auth |
| `ANTHROPIC_API_KEY` | for Claude (LLM calls) |
| `OPENAI_API_KEY` | for text-embedding-3-small (embeddings) |
| `PHOENIX_ENDPOINT` | `http://phoenix:4318/v1/traces` |
| `INGEST_SECRET` | random secret — must match GitHub Actions secret `INGEST_SECRET` |

---

## Google OAuth

- [ ] Add `https://<your-domain>/auth/callback` as an authorised redirect URI in Google Cloud Console

---

## Database Migration (Local → Prod)

No re-ingest needed on prod — copy the seeded and ingested data from local.

```bash
# On local machine — dump application tables
pg_dump \
  --no-owner --no-acl \
  -t blog_source -t blog -t tag -t blog_tag -t prerequisite -t blog_prerequisite -t allowed_users \
  -h localhost -p 5432 -U <local_user> enggsystemfeed \
  > enggsystemfeed_dump.sql

# Copy dump to server
scp enggsystemfeed_dump.sql root@<droplet-ip>:~/

# On server — restore into prod DB (after containers are up)
docker exec -i postgresql psql -U <prod_user> enggsystemfeed < ~/enggsystemfeed_dump.sql
```

---

## Deploy App

```bash
# On server
git clone <repo-url> enggsystemfeed
cd enggsystemfeed

# Create docker-compose.override.yml pointing to .env.prod
docker compose up -d
```

Run Alembic migrations:
```bash
docker exec app alembic upgrade head
```

---

## GitHub Actions — Daily Ingest

- [ ] Add `INGEST_SECRET` to GitHub repo → Settings → Secrets → Actions
- [ ] Add `INGEST_URL` to GitHub repo → Settings → Secrets → Actions (value: `https://<your-domain>/api/v1/ingest`)
- [ ] Verify workflow file exists at `.github/workflows/daily_ingest.yml`
- [ ] Trigger manually once from Actions tab to verify it works

> **Note:** GitHub disables scheduled workflows after 60 days of repo inactivity. Re-enable from Actions tab → select workflow → Enable workflow.

---

## Sentry (Error Tracking + Log Monitoring)

To be set up after initial deployment is verified.

- [ ] Create project on sentry.io (free tier)
- [ ] Add `SENTRY_DSN` to `.env.prod` and GitHub Actions secrets
- [ ] Add Sentry SDK to `requirements.txt` and initialise in `app.py`

---

## Auto-Deployment (GitHub Actions → DO)

To be set up after getting acquainted with Digital Ocean.

- [ ] Configure GitHub Actions workflow to SSH into droplet and run `git pull + docker compose up -d` on push to `production`

---

## Verify Deployment

- [ ] `GET /` returns the feed page
- [ ] Google OAuth login works end-to-end
- [ ] `GET /api/v1/blogs` returns articles
- [ ] Summary / Simplify / Prerequisites work for a signed-in user
- [ ] Trigger ingest manually via GitHub Actions — verify new rows appear in DB
- [ ] Phoenix UI accessible and showing traces
