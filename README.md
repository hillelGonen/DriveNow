# DriveNow

Vehicle Management System for a Car Rental Company.
FastAPI + PostgreSQL + SQLAlchemy, containerized with Docker Compose,
instrumented with Prometheus.

## Architecture

```mermaid
flowchart LR
    Client([Client])
    API[API Layer<br/>app/api/v1/endpoints/]
    CRUD[CRUD Layer<br/>app/crud/<br/>@track_operation]
    DB[(PostgreSQL)]
    Events[Event Publisher<br/>app/events/ — reserved]
    MQ[[Message Queue<br/>future]]
    Prom[/Prometheus<br/>/metrics/]

    Client -->|HTTP| API
    API -->|Pydantic DTO| CRUD
    CRUD -->|SQLAlchemy| DB
    API -.->|publish events| Events
    Events -.->|future| MQ
    API -. instrumentator .-> Prom
    API -. track_operation .-> Prom
```

Outer layers depend on inner ones, never the reverse.

### Layers

| Layer | Path | Responsibility |
|-------|------|----------------|
| **API** | `app/api/v1/endpoints/` | HTTP routing, request validation via `app/schemas/`, dependency injection of the DB session. No business rules. |
| **Schemas** | `app/schemas/` | Pydantic DTOs. The only types that cross the API boundary — ORM objects never leave the CRUD layer. |
| **CRUD** | `app/crud/` | SQLAlchemy data access. Cars: pure CRUD. Rentals: also owns the `start_rental` / `return_car` transactions (row lock + status flip + idempotent return), which would normally live in a service layer. |
| **Models** | `app/models/` | SQLAlchemy ORM definitions. UTC-aware timestamps via `TimestampMixin`. |
| **Core** | `app/core/` | Cross-cutting infrastructure: settings, DB engine, logging, Prometheus metrics. |
| **Events** | `app/events/` | Reserved for message-broker integration. Stub publisher today, broker-aware tomorrow. |
| **Services / Repositories** | `app/services/`, `app/repositories/` | Empty packages reserved for when business logic outgrows the CRUD layer (e.g., a third entity, multi-step workflows, or external integrations). |

## Quickstart

```bash
docker compose up --build
```

On boot, the `api` container runs `alembic upgrade head` and then starts uvicorn.

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Liveness check |
| `GET /metrics` | Prometheus exposition (API + service-layer histograms) |
| `GET /docs` | OpenAPI / Swagger UI |

## API usage

### Create a car

```bash
curl -s -X POST http://localhost:8000/api/v1/cars \
  -H 'content-type: application/json' \
  -d '{"model": "Tesla Model 3", "year": 2024}'
```

```json
{
  "id": 1,
  "model": "Tesla Model 3",
  "year": 2024,
  "status": "AVAILABLE",
  "created_at": "2026-04-29T04:41:27.797189Z",
  "updated_at": "2026-04-29T04:41:27.797189Z"
}
```

`status` defaults to `AVAILABLE`. Allowed values: `AVAILABLE`, `IN_USE`,
`MAINTENANCE`. `year` is constrained to 1900–2100; `model` to 1–100 chars.

### List cars (with optional filter + pagination)

```bash
curl -s http://localhost:8000/api/v1/cars
curl -s "http://localhost:8000/api/v1/cars?status=AVAILABLE"
curl -s "http://localhost:8000/api/v1/cars?status=MAINTENANCE&limit=20&offset=0"
```

`limit` is capped at 200, `offset` defaults to 0. Result is sorted by `id` ascending.

### Update a car (partial)

```bash
curl -s -X PATCH http://localhost:8000/api/v1/cars/1 \
  -H 'content-type: application/json' \
  -d '{"status": "MAINTENANCE"}'
```

```json
{
  "id": 1,
  "model": "Tesla Model 3",
  "year": 2024,
  "status": "MAINTENANCE",
  "created_at": "2026-04-29T04:41:27.797189Z",
  "updated_at": "2026-04-29T04:41:27.839032Z"
}
```

Only the fields you send are updated. Unknown `id` returns `404 {"detail": "Car not found"}`.

### Delete a car

```bash
curl -s -X DELETE http://localhost:8000/api/v1/cars/1
```

`204 No Content` on success. Returns `404` if the car doesn't exist, `409
{"detail": "Car 1 has an active rental"}` if a rental is in progress —
the guard prevents orphaning rental rows whose `car_id` would otherwise
cascade-delete.

### Create a user

```bash
curl -s -X POST http://localhost:8000/api/v1/users/ \
  -H 'content-type: application/json' \
  -d '{"name": "Ada Lovelace"}'
```

```json
{
  "id": 1,
  "name": "Ada Lovelace",
  "created_at": "2026-04-30T08:00:00.000000Z",
  "updated_at": "2026-04-30T08:00:00.000000Z"
}
```

`GET /api/v1/users/`, `GET /api/v1/users/{id}`, and `DELETE /api/v1/users/{id}`
mirror the car endpoints. Delete refuses (`409`) if the user has an active
rental — same guard pattern as car delete, preserves rental history.

### Start a rental

```bash
curl -s -X POST http://localhost:8000/api/v1/rentals/ \
  -H 'content-type: application/json' \
  -d '{"user_id": 1, "car_id": 1}'
```

```json
{
  "id": 1,
  "user_id": 1,
  "car_id": 1,
  "start_time": "2026-04-30T04:03:20.802051Z",
  "end_time": null
}
```

The car's status flips to `IN_USE` atomically. Renting a car that is not
`AVAILABLE` returns `400 {"detail": "Car 1 is not available (status=IN_USE)"}`.
The CRUD layer takes a `SELECT … FOR UPDATE` row lock on the car so concurrent
booking attempts of the same car serialize at the DB.

### Return a rental

```bash
curl -s -X PATCH http://localhost:8000/api/v1/rentals/1/return
```

```json
{
  "id": 1,
  "user_id": 1,
  "car_id": 1,
  "start_time": "2026-04-30T04:03:20.802051Z",
  "end_time": "2026-04-30T04:03:20.901813Z"
}
```

`end_time` is set to `datetime.now(timezone.utc)`, the car flips back to
`AVAILABLE`. The endpoint is **idempotent in the sense that double returns
are rejected**: a second call returns `400 {"detail": "Rental 1 was already
returned at …"}` instead of silently mutating `end_time` twice. Unknown `id`
returns `404`.

## Metrics

Two complementary instrumentation paths feed `/metrics`:

- **`http_request_duration_seconds_*`**, **`http_requests_total`** — produced
  automatically by `prometheus-fastapi-instrumentator`; covers every API
  request.
- **`drivenow_service_operation_duration_seconds_*`**,
  **`drivenow_service_operation_total`** — produced by `app/core/metrics.py`;
  one labelled time series per business operation (`operation`, `status`).

To track a new operation:

```python
from app.core.metrics import track_operation

@track_operation("rental.book")
def book(car_id: int, ...) -> Rental: ...
```

Recorded labels: `operation` (the name you pass), `status` (`success` /
`error`). The decorator works on both sync and async callables and
preserves the wrapped signature, so it's safe on FastAPI route handlers.

Confirmed live after exercising both CRUD APIs:

```
drivenow_service_operation_total{operation="car.create",   status="success"} 1.0
drivenow_service_operation_total{operation="car.list",     status="success"} 2.0
drivenow_service_operation_total{operation="car.update",   status="success"} 1.0
drivenow_service_operation_total{operation="rental.start", status="success"} 1.0
drivenow_service_operation_total{operation="rental.start", status="error"}   1.0
drivenow_service_operation_total{operation="rental.return",status="success"} 1.0
drivenow_service_operation_total{operation="rental.return",status="error"}   1.0
```

The `error` rows correspond to the rejected double-rental and double-return —
proof the decorator captures failure paths, not just happy ones.

## Migrations

Alembic is wired up. The `api` container runs `alembic upgrade head` on every
boot — migrations are part of the deployment, not a manual step.

```bash
# Create a new revision after editing models
docker compose run --rm api alembic revision --autogenerate -m "describe change"

# Apply / roll back manually
docker compose exec api alembic upgrade head
docker compose exec api alembic downgrade -1
```

- [alembic/versions/0001_initial_schema.py](alembic/versions/0001_initial_schema.py) — `cars`, `rentals`, `carstatus` enum.
- [alembic/versions/0002_rental_engine.py](alembic/versions/0002_rental_engine.py) — adds `users`, restructures `rentals` (`user_id` FK, renames `start_date`/`end_date` → `start_time`/`end_time`, makes `end_time` nullable, drops `customer_name`). Downgrade backfills before tightening NOT-NULL constraints so it round-trips on populated tables.

## Tests

```bash
docker compose exec api pytest tests/ -v
```

Three tests today:

| File | Test | What it proves |
|---|---|---|
| [tests/test_api/test_cars.py](tests/test_api/test_cars.py) | `test_create_and_list_car` | POST creates a car (default `AVAILABLE`), GET lists it, status filter works. |
| [tests/test_api/test_rentals.py](tests/test_api/test_rentals.py) | `test_double_rental_returns_400` | First booking succeeds and flips the car to `IN_USE`; the second returns 400. |
| [tests/test_api/test_rentals.py](tests/test_api/test_rentals.py) | `test_return_rental_sets_end_time_and_frees_car` | Return sets `end_time`, flips the car back to `AVAILABLE`; second return is rejected. |

Shared fixtures live in [tests/test_api/conftest.py](tests/test_api/conftest.py): a per-test in-memory SQLite engine with `StaticPool`, a `db_session`, an `api_client` that overrides FastAPI's `get_db`, and a `seed_user` fixture so the rental tests run zero-touch (no manual psql).

> Gotcha worth knowing: `sqlite:///:memory:` without `StaticPool` gives
> each new SQLAlchemy session its own empty in-memory database. Sharing
> a single connection via `StaticPool` is what makes the tests see the
> tables created in the fixture.

## Development conventions

- **UTC everywhere.** All timestamp columns are `timestamptz`. Application
  code constructs datetimes with `datetime.now(timezone.utc)`. Naive
  datetimes never enter the DB. `TZ=UTC` is set in both the API and
  Postgres containers; Postgres reports `SHOW timezone;` → `UTC`.
- **No ORM objects across the API boundary.** Endpoints accept and return
  Pydantic models from [app/schemas/](app/schemas/); CRUD returns ORM
  objects to the API which maps them through `CarRead.model_validate(...)`.
  This keeps the wire format decoupled from storage and prevents
  accidentally leaking internal columns.
- **Logs go to stdout *and* `logs/app.log`** (rotating, 10 MB × 5 backups,
  UTC ISO timestamps). The host `./logs` directory is bind-mounted; it
  must exist with UID 1000 ownership before the first `docker compose up`
  (the tracked `logs/.gitkeep` ensures this).
- **The `api` container runs as non-root** (`appuser`, UID 1000) so the
  bind-mounted `./logs` is writable from inside.

## Database choice

PostgreSQL.

- Rentals and cars are a natural relational pair: `rentals.car_id` is a
  hard FK with `ON DELETE CASCADE`. Joining and filtering on relations
  is the dominant access pattern, which is what relational engines are
  optimized for.
- `timestamptz` correctly stores datetimes as UTC regardless of client
  timezone — important for a rental product where bookings cross
  timezones and a "server local time" assumption silently corrupts data
  at booking boundaries.
- Today's concurrency guarantee for "no double-booking the same car" is a
  `SELECT … FOR UPDATE` row lock on the car inside `start_rental`. A future
  iteration can harden this with a Postgres `tstzrange` + `EXCLUDE USING
  gist (... WITH &&)` constraint (requires the `btree_gist` extension
  shipped in `postgres-contrib`) so overlapping rental windows are
  rejected at the DB level, not just at the application level.

## Layout

```
app/
├── api/
│   └── v1/endpoints/   # FastAPI routers: cars.py, rentals.py, users.py
├── crud/               # SQLAlchemy data access: crud_car.py, crud_rental.py, crud_user.py
├── models/             # SQLAlchemy ORM (User, Car, Rental, TimestampMixin)
├── schemas/            # Pydantic DTOs (car.py, rental.py, user.py)
├── services/           # reserved — see Layers table
├── repositories/       # reserved — see services/
├── events/             # reserved publisher stub for future broker
├── core/               # config, database, logging, metrics
└── main.py             # FastAPI app entrypoint
alembic/                # schema migrations
  ├── 0001              # cars + rentals + carstatus enum
  └── 0002              # rental engine (users, user_id FK, time columns)
tests/
├── conftest.py         # shared fixtures (engine, db_session, api_client, seed_user)
├── test_api/           # endpoint smoke tests
└── test_crud/          # direct CRUD layer unit tests
docs/                   # additional architecture docs (placeholder)
logs/                   # host-mounted log dir (.gitkeep tracked)
```

## Development & Quality Assurance

To ensure code quality, security, and consistent formatting, an audit script is provided:

```bash
./scripts/audit.sh
```

## Out of scope (next iterations)

- DB-level overlap prevention via `tstzrange` + `EXCLUDE USING gist`.
- Real message broker — `app/events/publisher.py` is still a no-op.
- Promote the `app/services/` layer; align the `app/crud/` vs
  `app/repositories/` naming.
- Real message broker — `app/events/publisher.py` is a no-op today.
- Auth, rate limiting.
