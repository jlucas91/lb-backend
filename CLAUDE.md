# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**No local uv** — all commands run inside Docker via `docker compose`. The `app` service builds the `dev` target which includes dev tools (ruff, mypy, pytest). Source directories are bind-mounted so code reloading works automatically.

```bash
# Start services (DB + API with hot reload)
docker compose up -d --build

# Lint + format + typecheck (always auto-fix)
docker compose run --rm app sh -c "ruff check --fix app/ tests/ && ruff format app/ tests/ && mypy app/"

# Tests (requires DB running via docker compose)
docker compose run --rm \
  -e DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/locationsbook_test \
  -e SECRET_KEY=test-secret-key \
  app pytest -v

# Single test — append path to pytest command above, e.g.:
# app pytest -v tests/test_auth.py::test_register

# Lock file
docker compose run --rm app uv lock

# Alembic migration
docker compose run --rm app alembic revision --autogenerate -m "description"
docker compose run --rm app alembic upgrade head
```

## Architecture

MVC with FastAPI. Endpoints are thin route handlers; controllers hold business logic and access control.

```
Request → Endpoint (app/api/v1/endpoints/) → Controller (app/controllers/) → Model (app/models/)
                                                                              Schema (app/schemas/)
```

**Flow**: Endpoints parse HTTP, call controllers, then `await db.commit()`. Controllers call `await db.flush()` (not commit) so tests can roll back transactions.

**Auth**: JWT (HS256) via `app/core/security.py`. The `get_current_user` dependency in `app/api/deps.py` decodes the token and fetches the User. OAuth2PasswordBearer tokenUrl is `/api/v1/auth/login`.

**Access control** is enforced in controllers, not endpoints. Location read access uses a subquery union (owner OR share recipient OR production member). Write access checks owner OR edit-share.

**Database**: async SQLAlchemy 2.0 with asyncpg. `app/core/database.py` provides `Base`, `engine`, `get_db()`. Models use `Mapped[T]` typed columns with UUID PKs (`default=uuid.uuid4`) and `server_default=func.now()` timestamps.

**Enums**: `app/models/enums.py` uses `enum.StrEnum`. Stored as `String(N)` columns, validated by Pydantic schemas.

## Key Conventions

- Python 3.13 — use `enum.StrEnum`, PEP 695 type params (`class Foo[T]`), `AsyncGenerator[T]` (not `AsyncGenerator[T, None]`)
- Ruff strict mode: E, W, F, I, N, UP, B, SIM, RUF. B008 suppressed in `app/api/**` for `Depends()`. Always run ruff with `--fix` and `ruff format` (not `--check`) to auto-fix lint and formatting issues
- mypy strict mode. `bcrypt.*` and `asyncpg.*` have `ignore_missing_imports`. `jwt.encode` return needs `# type: ignore[return-value]` (stubs say bytes, actually str)
- After `db.flush()` on models with `onupdate=func.now()`, call `db.refresh(obj)` before returning to avoid lazy-load errors in Pydantic serialization
- Docker ports: db=5433 host, app=9000 host. Postgres volume at `/var/lib/postgresql` (not `/var/lib/postgresql/data`)

## Test Setup

Tests use per-test transactional rollback via `conftest.py`. The `db_session` fixture (autouse) creates a fresh engine + connection + transaction per test, overrides `get_db`, and rolls back after. `session.commit` is replaced with an async no-op since controllers already flush.

Key fixtures: `client` (unauthenticated), `test_user` (test@example.com / testpass123), `auth_headers` (JWT Bearer dict), `authenticated_client` (client with auth).
