# EnggFeed

A one-stop aggregator for engineering blogs from top tech companies — Netflix, Cloudflare, Stripe, GitHub, and more.

## Features

- Browse and filter articles by company and topic
- AI-generated summaries and ELI5 explanations (signed-in users)
- Prerequisite topics with primer and deep dive explanations (signed-in users)
- Daily RSS ingestion via GitHub Actions

## Stack

- **Backend:** FastAPI + PostgreSQL + Redis
- **Frontend:** Alpine.js
- **LLM:** Claude (Anthropic)
- **Embeddings:** text-embedding-3-small (OpenAI)
- **Observability:** Phoenix (self-hosted)

## Running Locally

1. Copy `.env.example` to `.env.local` and fill in the required values
2. Start containers:
   ```bash
   docker compose up -d
   ```
3. Run migrations:
   ```bash
   docker exec app alembic upgrade head
   ```
4. Visit `http://localhost:8000`

## Folder Structure

```
enggsystemfeed/
├── app.py              # FastAPI app, router registration, startup ingest
├── config.py           # Environment config
├── constants.py        # App-wide constants
├── database.py         # SQLAlchemy session setup
├── exceptions.py       # Custom exception classes
├── schemas.py          # Shared Pydantic schemas (APIResponse, ErrorDetail)
├── utils.py            # Shared utilities (call_llm, check_refresh_due)
├── rss_client.py       # RSS feed fetching
├── auth/               # Google OAuth, JWT issuance and validation
├── blog/               # Blog listing, filtering, pagination
├── tags/               # Tag lookup and filtering
├── summary/            # On-demand AI summary generation
├── simplify/           # On-demand ELI5 explanation generation
├── prerequisites/      # On-demand prerequisite explanation generation
├── ingest/             # Daily RSS ingestion pipeline
├── prompts/            # LLM prompt templates
├── templates/          # HTML shell (Alpine.js frontend)
├── static/             # CSS, JS, favicon
├── eval/               # Eval scripts for tags and prerequisites quality
└── docs/               # Architecture, schema, API contracts, deployment guide
```

## Docs

See the `docs/` folder for architecture, schema, API contracts, and deployment guide.
