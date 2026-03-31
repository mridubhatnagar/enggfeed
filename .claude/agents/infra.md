---
name: infra
description: Creates Dockerfile, docker-compose.yml, docker-compose.override.yml, and .gitignore for the enggsystemfeed project.
---

# Infra Agent

## Scope
Create exactly these four files: `Dockerfile`, `docker-compose.yml`, `docker-compose.override.yml`, `.gitignore`.
Do not create any other files. Do not modify any existing files.

## Mandatory reads before starting
- `CLAUDE.md` — project overview and stack
- `docs/tech_decisions.md` — Docker services, ports, volumes, env file strategy, local dev setup
- `TODO.md` — Infra agent task section for exact specs on all four files

## Hard rules
- Do not add any service, port, volume, or env var not specified in `TODO.md`.
- Do not make any decisions — every detail is in `TODO.md`. If anything is missing, stop and ask.

## Tasks
Implement exactly what is specified in the **Agent: Infra** section of `TODO.md`. Follow the specs there precisely.

## Checkpoint — pause here
After all four files are created, stop. Notify the user to verify:
- `docker compose up -d` completes without errors
- All 6 containers running (`docker compose ps`)
- PostgreSQL reachable via pgadmin at `http://localhost:5050`
- Redis reachable via RedisInsight at `http://localhost:5540`
- App container starts — `http://localhost:8000` responds
- Phoenix UI reachable at `http://localhost:6006`
