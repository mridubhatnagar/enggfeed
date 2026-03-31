---
name: backend-prerequisites
description: Implements the prerequisites/ module — schemas, DAOs, services, handler, and controller.
---

# Backend Prerequisites Sub-agent

## Scope
Create exactly these files:
- `prerequisites/schemas.py`, `prerequisites/dao.py`, `prerequisites/service.py`, `prerequisites/handler.py`, `prerequisites/controller.py`

Also add the prerequisites router registration to `app.py` — scoped addition only (see below).

## Context from previous sub-agents
The following files already exist — import from them, do not recreate or modify them:
- `database.py` — `get_db`
- `config.py`
- `constants.py` — `REFRESH_INTERVAL_DAYS`
- `exceptions.py` — `DatabaseError`, `UnauthorizedError`, `LLMUnreachableError`
- `schemas.py` — `APIResponse`, `ErrorDetail`
- `utils.py` — `check_refresh_due`, `call_llm`
- `auth/utils.py` — `decode_jwt_token`
- ORM models — location confirmed by orchestrator
- `prompts/prerequisites.py` — exists as a stub (`PREREQUISITES_PROMPT = None`)

## Mandatory reads before starting
- `docs/dao_and_service_class_design.md` — exact signatures for `PrerequisiteDAO`, `PrerequisiteService`, `BlogPrerequisiteDAO`, `BlogPrerequisiteService`
- `docs/handler_design_guide.md` — `PrerequisiteHandler` design, constructor dependencies, `get_prerequisite` flow, NULL definition trigger, primer assembly
- `docs/api_contracts.md` — `/api/v1/prerequisites/{topic_name}` contract, `Primer`, `PrerequisiteDetail`
- `docs/tech_decisions.md` — prerequisites caching, refresh logic, error handling and status code mapping

## Hard rules
- Do not add methods to DAO or Service classes beyond `docs/dao_and_service_class_design.md`.
- `PrerequisiteDAO.find_similar` uses pgvector `<=>` cosine distance operator.
- `definition is None` on the DB row means "never generated" — triggers LLM call unconditionally, regardless of `updated_at`.
- `primer` is assembled by the handler from flat DB columns (`definition`, `why_it_matters`, `example`) into a nested `Primer` object — it is not stored nested in the DB.
- The `prerequisite` row always exists when this handler is called — created at ingest with `topic_name` and `embedding`. Handler never creates a new row.
- `app.py` modification: add the prerequisites router registration only. Do not touch any other part of `app.py`.
- If anything is unclear, stop and ask.

---

## Files

### `prerequisites/schemas.py`
Implement exactly from `docs/api_contracts.md` (prerequisites endpoint section):
`Primer`, `PrerequisiteDetail`

### `prerequisites/dao.py`
Implement `IPrerequisiteDAO`, `PrerequisiteDAO`, `IBlogPrerequisiteDAO`, `BlogPrerequisiteDAO`.
Signatures exactly from `docs/dao_and_service_class_design.md`.

### `prerequisites/service.py`
Implement `PrerequisiteService`, `BlogPrerequisiteService`.
Signatures exactly from `docs/dao_and_service_class_design.md`.

### `prerequisites/handler.py`
Implement `PrerequisiteHandler`. Constructor dependencies and `get_prerequisite` exactly as specified in `docs/handler_design_guide.md`.
Prompt imported from `prompts/prerequisites.py`.

### `prerequisites/controller.py`
FastAPI router. Route: `GET /api/v1/prerequisites/{topic_name}` → `APIResponse[PrerequisiteDetail]`

### `app.py` — scoped addition
Add the prerequisites router import and registration to `app.py` in the router registration section. Do not modify anything else in `app.py`.

---

## Checkpoint — pause here
Stop. Manually insert a row in `prerequisite` with a `topic_name` and `embedding` (zero vector is fine), leaving `definition` NULL.
Notify the user to verify:
- `GET /api/v1/prerequisites/{topic_name}` as signed-in returns all fields on first call (LLM invoked)
- Second call returns same result instantly (from cache — verify no second LLM call in logs)
- `prerequisite` row in DB updated with `definition`, `why_it_matters`, `example`, `deep_dive`
- Cache entry visible in RedisInsight
- Guest request → 401
- Response shape matches `docs/api_contracts.md` exactly: `topic_name`, `primer` as nested object, `deep_dive`, `updated_at`
