# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Start full stack (migrations auto-applied before uvicorn)
docker compose up --build

# Run all tests (in-container)
docker compose exec api pytest tests/ -v

# Run a single test file
docker compose exec api pytest tests/test_api/test_cars.py -v

# Run a single test by name
docker compose exec api pytest tests/ -k "test_create_and_list_car" -v

# Security audit + format check
./scripts/audit.sh

# Auto-fix formatting
black --line-length 88 app/ tests/ alembic/

# Generate migration after model changes
docker compose run --rm api alembic revision --autogenerate -m "describe change"
```

## Architecture

Strict unidirectional layers — outer depends on inner, never reverse:

```
Endpoint → Service → Repository → ORM Model → DB
               ↓
           publisher.py (domain events, post-commit)
```

| Layer | Path | Rule |
|-------|------|------|
| API | `app/api/v1/endpoints/` | Routes only. Catch domain exceptions → HTTPException. Call `model_validate()` before returning. Decorate with `@track_operation`. |
| Service | `app/services/` | Transaction boundary. Owns `db.commit()`. Publishes events post-commit. Only `RentalService` exists (start/return). |
| Repository | `app/repositories/` | Data access only. `db.add()` + `db.flush()` — never `db.commit()`. Domain exceptions defined here (`CarNotAvailableError`, `RentalNotFoundError`, `RentalAlreadyReturnedError`). |
| Events | `app/events/publisher.py` | `publish(event, payload)` — INFO log on `drivenow.events` logger + XADD to Redis Stream `drivenow_events`. Fire-and-forget: Redis failures are caught and logged; call sites never see exceptions. |
| Core | `app/core/` | Config (pydantic_settings), DB session, logging (stdout + rotating file), Prometheus metrics. |

## Key Invariants

**UTC only.** All timestamps are `DateTime(timezone=True)`. Always use `datetime.now(timezone.utc)`. Never naive datetimes.

**ORM objects never cross the API boundary.** Endpoints always call `ResponseSchema.model_validate(orm_obj)` before returning.

**Repos flush, services commit.** `db.flush()` in repos populates PKs without committing. `db.commit()` lives only in services (or endpoints that call repos directly for simple CRUD).

**SELECT FOR UPDATE serializes bookings.** `rental_repo.lock_car()` acquires a row lock before status checks. Concurrent bookings of the same car are race-free.

## Testing

Tests use in-memory SQLite with `StaticPool` — no Docker/Postgres needed. The `StaticPool` is required so all sessions share the same in-memory DB (without it, each session gets a fresh empty DB).

`conftest.py` fixtures: `engine`, `db_session`, `api_client` (overrides `get_db`), `seed_user`.

Two test categories:
- `tests/test_api/` — HTTP-level via `TestClient`
- `tests/test_crud/` — direct repo/service calls via `db_session`

## Migrations

Migration files live in `alembic/versions/`. The container entrypoint runs `alembic upgrade head` before uvicorn starts — deployment is declarative. `alembic.ini` leaves `sqlalchemy.url` empty; it's set programmatically in `alembic/env.py` from `Settings.DATABASE_URL`.

## Metrics

Two instrumentation paths:
1. `@track_operation("name")` decorator on endpoints → `drivenow_service_operation_*` counters/histograms.
2. `FleetCollector` → live DB queries at scrape time → `drivenow_available_cars`, `drivenow_active_rentals` gauges.

HTTP-level metrics (`http_request_duration_seconds_*`) come automatically from `prometheus-fastapi-instrumentator`.
