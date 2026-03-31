---
name: checkpoint
description: Walk through the verification steps for a specific implementation checkpoint in TODO.md for enggsystemfeed.
---

Read `TODO.md` and guide the user through the checkpoint specified in $ARGUMENTS.
Valid values: `1` (Infra), `2` (Database), `3` (Backend core), `4` (Auth), `5` (Blog/Tags/Search), `6` (Summary/Simplify), `7` (Prerequisites), `8` (Ingest), `9` (Frontend E2E).
If $ARGUMENTS is empty, ask which checkpoint to verify.

---

## How to run a checkpoint

1. Read the checkpoint section from `TODO.md` for the given number.
2. Present each verification item as a numbered checklist — one at a time.
3. For each item:
   - State clearly what to check and where (pgadmin, browser, terminal, RedisInsight).
   - Provide the exact command or URL to use where applicable.
   - Wait for the user to confirm pass or report a failure.
4. If an item fails:
   - Ask the user to share the error or symptom.
   - Diagnose the likely cause based on the stack (FastAPI, PostgreSQL, Redis, Docker).
   - Suggest a fix. Do not proceed to the next item until the current one passes.
5. Once all items pass: confirm the checkpoint is complete and tell the user which agent to run next.

---

## Useful commands per checkpoint

### Docker / App
```bash
docker compose ps                        # check all containers are running
docker compose logs app                  # app startup errors and runtime logs
docker compose logs app --tail=50 -f     # follow logs in real time
docker compose restart app               # restart after a code change
docker compose down && docker compose up -d  # full restart
```

### Database (pgadmin)
- URL: `http://localhost:5050`
- Query tool: right-click database → Query Tool
- Check tables: expand Schemas → public → Tables
- Check extension: `SELECT * FROM pg_extension WHERE extname = 'vector';`
- Check column type: `SELECT column_name, data_type, udt_name FROM information_schema.columns WHERE table_name = '<table>';`

### Redis (RedisInsight)
- URL: `http://localhost:5540`
- Browse keys: click the database → browse
- Check a key: click the key to see value and TTL

### Alembic
```bash
docker compose exec app alembic upgrade head     # run migrations
docker compose exec app alembic current          # check current revision
docker compose exec app alembic history          # show migration history
```

### API testing
- Swagger UI: `http://localhost:8000/docs` (requires `SWAGGER_USERNAME`/`SWAGGER_PASSWORD`)
- Or use curl: `curl -s http://localhost:8000/api/v1/blogs | python3 -m json.tool`
