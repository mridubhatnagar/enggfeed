---
name: backend-models
description: Creates SQLAlchemy ORM model classes for all tables in the enggsystemfeed project.
---

# Backend Models Sub-agent

## Scope
Create per-module `models.py` files — one file per module, containing only the models owned by that module.
Do not create any other files. Do not modify any existing files.

## Context from previous sub-agents
The following files already exist — do not recreate or modify them:
- `database.py` — contains `Base = declarative_base()`. Import `Base` from here.
- `config.py`, `constants.py`, `exceptions.py`, `schemas.py`, `utils.py`, `rss_client.py`, `app.py`
- All `__init__.py` files

## Mandatory reads before starting
- `docs/schema.md` — single source of truth for all table definitions, column types, constraints, nullability, and relationships. Implement exactly what is defined there — nothing more, nothing less.
- `CLAUDE.md` — folder structure and architecture rules
- `docs/tech_decisions.md` — ORM conventions (SQLAlchemy, pgvector-sqlalchemy)

## Models location (fixed — no pre-condition needed)

| File | Models |
|------|--------|
| `auth/models.py` | `User` |
| `blog/models.py` | `BlogSource`, `Blog`, `BlogChunk` |
| `tags/models.py` | `Tag`, `BlogTag` |
| `prerequisites/models.py` | `Prerequisite`, `BlogPrerequisite` |
| `summary/models.py` | `Summary` |
| `simplify/models.py` | `Simplify` |

If `docs/schema.md` defines any table not listed above, assign it to the closest owning module.

## Hard rules
- Do not add any column, relationship, or constraint not in `docs/schema.md`.
- One `models.py` per module — do not merge models across files.
- Once created, these files are **read-only** for all subsequent sub-agents. No sub-agent may modify them.
- If anything is unclear, stop and ask.

---

## Implementation notes

These notes supplement `docs/schema.md` — they do not override it:

- Import `Base` from `database.py`
- All UUID PKs: `default=uuid.uuid4`
- All `created_at` and `updated_at` columns: `default=datetime.utcnow`
- `thumbnail` on `blog`: `nullable=True`
- `definition`, `why_it_matters`, `example`, `deep_dive` on `prerequisite`: `nullable=True`
- `embedding` columns on `blog_chunk`, `tag`, `prerequisite`: use `pgvector.sqlalchemy.Vector(1536)`
- `blog_tag` and `blog_prerequisite`: composite PKs — no surrogate key
- `blog.id` is `Text` type (RSS guid), not UUID
- Define SQLAlchemy `relationship()` where needed for ORM queries across modules

---

## Checkpoint — pause here
Stop. Notify the user to confirm:
- All 6 `models.py` files exist in their respective module directories
- All 11+ model classes are present (count from `docs/schema.md`)
- No import errors when the app starts (`docker compose logs app`)
