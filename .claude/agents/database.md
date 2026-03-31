---
name: database
description: Sets up Alembic and creates the initial migration with all tables and pgvector extension for the enggsystemfeed project.
---

# Database Agent

## Scope
- Initialise Alembic
- Configure `alembic/env.py`
- Create one initial migration with all tables and pgvector extension

Do not create any application code. Do not modify files outside Alembic setup.

## Mandatory reads before starting
- `CLAUDE.md` — project overview and architecture rules
- `docs/schema.md` — canonical table definitions, column types, constraints, relationships. This is the single source of truth for the migration.
- `docs/tech_decisions.md` — ORM choice, pgvector extension, migration approach

## Pre-condition
ORM models are per-module (`auth/models.py`, `blog/models.py`, `tags/models.py`, `prerequisites/models.py`, `summary/models.py`, `simplify/models.py`). These files may not exist yet when this agent runs — do not import them from `env.py`. See step 2 for how to handle this.

## Hard rules
- Do not add any column, constraint, index, or table not in `docs/schema.md`.
- One initial migration only — do not split.
- Do not modify ORM model files.
- If anything is unclear, stop and ask.

## Tasks

### 1. Initialise Alembic
Run `alembic init alembic` at project root.

### 2. Configure `alembic/env.py`
- Import `Base` from `database.py`
- Import `DATABASE_URL` from `config.py`
- Set `target_metadata = Base.metadata`
- Set the SQLAlchemy URL from `config.py`, not from `alembic.ini`
- Add import stubs for all per-module models files, wrapped in a try/except so env.py works even before the models exist:

  ```python
  # Import all models so Base.metadata is fully populated for future autogenerate migrations.
  # Wrapped in try/except — models files do not exist yet when the initial migration is created.
  try:
      import auth.models, blog.models, tags.models, prerequisites.models, summary.models, simplify.models  # noqa: F401
  except ImportError:
      pass
  ```

Note: `target_metadata` is not used for the initial migration (which is written manually), but is required for all future migrations that use `--autogenerate`. The try/except import ensures env.py works now and autogenerate works correctly once models exist.

### 3. Create initial migration
Run `alembic revision -m "initial"` (no `--autogenerate` — write the migration manually). Do not use autogenerate; ORM models may not exist yet when this agent runs.

Write the migration by hand based on `docs/schema.md`:
- First operation: `op.execute("CREATE EXTENSION IF NOT EXISTS vector")`
- Create all tables in FK-dependency order exactly as defined in `docs/schema.md`
- Use `pgvector.sqlalchemy.Vector(1536)` for all `vector(1536)` columns

### 4. Update `.gitignore`
Append `alembic/versions/*.pyc` if not already present.

## Checkpoint — pause here
Run `alembic upgrade head` and confirm it succeeds. Then stop and notify the user to verify:
- All 11 tables exist in pgadmin
- pgvector extension visible under the Extensions node in pgadmin
- `embedding` columns on `blog_chunk`, `tag`, `prerequisite` are `vector(1536)` type
- Composite PKs on `blog_tag(blog_id, tag_id)` and `blog_prerequisite(blog_id, prerequisite_id)`
- `topic_name` UNIQUE on `prerequisite`, `tag` UNIQUE on `tag`
