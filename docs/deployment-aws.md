# Deployment Steps — AWS EC2 (migrated from DigitalOcean)

## Stack
- **Server:** AWS EC2 — t3.small (2 vCPU, 2GB RAM), 25GB gp3 EBS root volume
- **Region:** eu-north-1
- **Database:** PostgreSQL in Docker Compose (migrated from DO droplet)
- **Cache:** Redis in Docker Compose
- **Domain:** `enggfeed.mridulabs.dev` (Cloudflare DNS) → Elastic IP `3.111.22.146`, reverse-proxied via Nginx with SSL (Let's Encrypt/Certbot). Google OAuth login working.

---

## Why AWS over DO this time
- $50 promotional credit (redeemed after resolving an account closure issue — 6-month free plan had expired, account required a self-upgrade to a paid plan to reopen). Credit valid until **2026-10-31**.
- Right-sized to t3.small (2 vCPU/2GB) instead of matching DO's 1 vCPU/1GB — avoids the swap-under-memory-pressure issue the DO droplet hit with 6 services running on 1GB RAM.

---

## One-Time Account Setup

- [x] Resolved AWS account closure (free plan period ended, self-upgraded to paid plan)
- [x] Redeemed $50 promotional credit
- [x] Set up billing budgets: existing "Monthly Learning Budget" ($5 alert), new budget ($25/month, recurring, all-scope, alert thresholds at 50%/80%/100%)
- [ ] Switch from root to IAM user for routine work (root reserved for account/billing-level actions)

## One-Time Server Setup

- [x] Launch EC2 instance — Ubuntu Server 24.04 LTS, t3.small, 25GB gp3 EBS
- [x] Create key pair (`enggfeed-key`, RSA, .pem) — downloaded and saved locally
- [x] Security group: inbound SSH (22) from My IP, custom TCP (8000) from Anywhere (0.0.0.0/0). HTTP (80) / HTTPS (443) left closed — no Nginx yet.
- [x] SSH into instance and install Docker + Docker Compose (via `get.docker.com` convenience script; added `ubuntu` user to `docker` group to avoid `sudo` prefix)
- [x] Swap not needed — 2GB RAM handled `docker compose up -d --build` with all 6 services without OOM issues (unlike DO's 1GB)

---

## Environment Variables (Prod)

Same as DO — recreate `.env.prod` on the new server (gitignored, must be recreated per deploy). See `docs/deployment.md` → Environment Variables table for the full variable list, or copy directly from the DO droplet's `.env.prod` while it's still running.

---

## Deploy App

```bash
# On EC2 instance
git clone <repo-url> enggsystemfeed
cd enggsystemfeed

# Create docker-compose.override.yml pointing to .env.prod (see DO droplet's copy)
docker compose up -d
```

Run Alembic migrations:
```bash
docker exec app alembic upgrade head
```

---

## Database Migration (DO → AWS)

Before dumping fresh from DO, confirmed via `SELECT count(*) FROM blog;` on DO that the row count still matched the local dump used for the DO migration (232) — the daily ingest cron never ran (GitHub Actions auto-disables after 60 days idle, never re-enabled), so no new data existed on DO beyond what the local dump already had. Used the existing local `enggsystemfeed_dump.sql` directly instead of re-dumping from DO.

**Hit the same FK-ordering issue as the local → DO migration**: `blog`, `blog_prerequisite`, `blog_tag` failed on first pass (loaded before their dependencies existed) while `blog_source` (13), `prerequisite` (380), `tag` (438), `user` (1) succeeded. Fixed the same way — extracted the 3 failed tables' `COPY` blocks via `awk '/^COPY public\.TABLE \(/,/^\\.$/'` and reloaded in dependency order: `blog` (232) → `blog_prerequisite` (482) → `blog_tag` (485).

Final row counts confirmed matching DO exactly: blog=232, blog_source=13, blog_tag=485, blog_prerequisite=482, tag=438, prerequisite=380, user=1.

**Also hit the same stale-connection bug as DO** ("relation blog does not exist" despite tables existing) — fixed identically via `docker compose up -d --force-recreate app`.

---

## Verify Deployment

- [x] `GET /` returns the feed page — verified via `curl localhost:8000` on instance, then externally at `http://3.110.41.165:8000`
- [x] All 6 containers running (`app`, `postgresql`, `redis`, `pgadmin`, `redisinsight`, `phoenix`)
- [x] Data matches DO droplet (row counts confirmed identical across all 7 tables)
- [x] `GET /api/v1/blogs` returns articles — verified via `https://enggfeed.mridulabs.dev/api/v1/blogs`, total=232 matches migrated data
- [x] Phoenix UI accessible — `http://3.111.22.146:6006` returns HTTP 200 (had to open port 6006 in security group; wasn't open by default)

## Only After Full Verification

- [x] Final DB data confirmed matching DO exactly (row counts across all 7 tables) before migration — effectively the safety net
- [x] Deleted DO droplet (`ubuntu-s-1vcpu-1gb-blr1-Redeploy-enggfeed`)

---

## Static IP + Domain

- [x] Allocated an Elastic IP and associated it with the instance — public IP is now static: `3.111.22.146` (was `3.110.41.165` before association)
- [x] Pointed `enggfeed.mridulabs.dev` (Cloudflare DNS, A record, proxy off/DNS-only since Cloudflare doesn't proxy port 8000) at the Elastic IP
- [x] Opened security group ports 80 (HTTP) and 443 (HTTPS), source Anywhere-IPv4 — port 8000 left open for now (direct access still works alongside Nginx)
- [x] Installed Nginx, configured as reverse proxy (`enggfeed.mridulabs.dev` → `127.0.0.1:8000`)
- [x] Obtained SSL cert via Certbot/Let's Encrypt (`certbot --nginx --redirect`) — auto-renews via systemd timer, expires 2026-11-17
- [x] HTTP now 301-redirects to HTTPS; `https://enggfeed.mridulabs.dev` confirmed working
- [x] Created Google OAuth 2.0 credentials (Client ID + Secret) — these never existed on DO either, which is why Google login was broken there too
- [x] Added `https://enggfeed.mridulabs.dev/auth/callback` as authorised redirect URI in Google Cloud Console
- [x] Updated `GOOGLE_REDIRECT_URI`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` in `.env.prod`, restarted app — Google OAuth login confirmed working on the live server
- [ ] Close port 8000 in security group now that Nginx is proxying (optional hardening — not done yet)
