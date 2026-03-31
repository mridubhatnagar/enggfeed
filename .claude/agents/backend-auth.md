---
name: backend-auth
description: Implements the auth/ module — schemas, DAO, service, utils, client, handler, and controller.
---

# Backend Auth Sub-agent

## Scope
Create exactly these files:
- `auth/schemas.py`, `auth/dao.py`, `auth/service.py`, `auth/utils.py`, `auth/client.py`, `auth/handler.py`, `auth/controller.py`

Also add the auth router registration to `app.py` — scoped addition only (see below).

## Context from previous sub-agents
The following files already exist — import from them, do not recreate or modify them:
- `database.py` — `Base`, `SessionLocal`, `get_db`
- `config.py` — `JWT_SECRET`, `JWT_ALGORITHM`, `JWT_EXPIRY_HOURS`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`
- `exceptions.py` — `UnauthorizedError`, `AuthError`, `DatabaseError`
- `schemas.py` — `APIResponse`, `ErrorDetail`
- ORM models — location confirmed by orchestrator

## Mandatory reads before starting
- `docs/dao_and_service_class_design.md` — exact signatures for `UserDAO`, `UserService`, `AllowedUserDAO`, `AllowedUserService`
- `docs/handler_design_guide.md` — `AuthHandler`, `AuthClient`, `auth/utils.py` specs
- `docs/api_contracts.md` — auth endpoint routes, request/response schemas, HTTP status codes
- `docs/tech_decisions.md` — auth flow, JWT, state token, error handling and status code mapping

## Hard rules
- Do not add methods to DAO or Service classes beyond `docs/dao_and_service_class_design.md`.
- Handlers call services only — never DAOs directly.
- Controllers catch all exceptions and return `APIResponse(success=False, ...)` with correct HTTP status per `docs/tech_decisions.md`.
- `app.py` modification: add the auth router registration only. Do not touch any other part of `app.py`.
- If anything is unclear, stop and ask.

---

## Files

### `auth/schemas.py`
Implement exactly from `docs/api_contracts.md` (auth endpoints section).

### `auth/dao.py`
Implement `IUserDAO`, `UserDAO`, `IAllowedUserDAO`, `AllowedUserDAO`.
Signatures exactly from `docs/dao_and_service_class_design.md`. No extra methods.
DAOs catch SQLAlchemy exceptions and re-raise as `DatabaseError`.

### `auth/service.py`
Implement `UserService`, `AllowedUserService`.
Signatures exactly from `docs/dao_and_service_class_design.md`. Thin wrappers over DAOs.

### `auth/utils.py`
Two functions only — specs in `docs/handler_design_guide.md` (auth section):
- `generate_jwt_token(user_id: uuid.UUID) -> str`
- `decode_jwt_token(token: str) -> dict` — raises `UnauthorizedError` if invalid or expired

### `auth/client.py`
`AuthClient` class — three methods exactly as specified in `docs/handler_design_guide.md` (auth section):
- `get_auth_url(state: str) -> str`
- `exchange_code(code: str) -> str`
- `verify_id_token(id_token: str) -> dict` — raises `AuthError` if audience check or `email_verified` fails

### `auth/handler.py`
`AuthHandler` — constructor dependencies and all methods exactly as specified in `docs/handler_design_guide.md`.
Methods: `initiate`, `callback`, `me`.

### `auth/controller.py`
FastAPI router — routes exactly from `docs/api_contracts.md`:
- `GET /auth/initiate`
- `GET /auth/callback`
- `GET /auth/me` → `APIResponse[UserDetail]`
- `POST /auth/logout`

### `app.py` — scoped addition
Add the auth router import and registration to `app.py` in the router registration section marked by the placeholder comment. Do not modify anything else in `app.py`.

---

## Checkpoint — pause here
Stop. Notify the user to verify:
- `GET /auth/initiate` redirects to Google OAuth consent screen
- Full sign-in flow completes, JWT cookie is set
- `GET /auth/me` with JWT cookie returns user data
- `GET /auth/me` without JWT cookie returns 401
- `POST /auth/logout` clears the JWT cookie
- User row appears in `user` table in pgadmin
- Sign-in with an email not in `allowed_users` is rejected with 401
