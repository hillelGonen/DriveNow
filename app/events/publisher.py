"""Domain event publisher.

Emits domain events in two ways:
1. Structured INFO log on the ``drivenow.events`` logger (retained —
   log aggregators and audit trails continue to work).
2. XADD to the Redis Stream ``drivenow_events`` so downstream consumers
   can read events without polling the log file.

Fire-and-forget: if Redis is unreachable or XADD fails, the exception is
caught, logged at ERROR level, and the function returns normally. The
service-layer transaction is never affected.

Service-layer code calls publish() AFTER the transaction commits, so
event consumers never see uncommitted state.
"""

import json
import logging
from typing import Any

import redis

from app.core.config import get_settings

logger = logging.getLogger("drivenow.events")

_STREAM = "drivenow_events"

# ConnectionPool.from_url() parses the URL but does NOT open a socket —
# connections are lazily opened on first use. Pool is shared across all
# publish() calls in the process lifetime.
_pool: redis.ConnectionPool | None = None

try:
    _pool = redis.ConnectionPool.from_url(
        get_settings().REDIS_URL,
        decode_responses=True,
    )
except Exception as _exc:
    logger.error("redis pool init failed, events will be log-only: %s", _exc)


def publish(event: str, payload: dict[str, Any]) -> None:
    """Emit a domain event to the log and Redis Stream.

    Always emits a structured INFO log entry on the ``drivenow.events``
    logger so that log aggregators and audit trails capture every event.
    Additionally pushes the event to the Redis Stream ``drivenow_events``
    via ``XADD`` when the connection pool is available.

    This function is fire-and-forget with respect to Redis: any transport
    failure is caught, logged at ERROR level on the same logger, and
    suppressed so the caller's control flow is never interrupted. It is
    safe to call from within or after a database transaction.

    Args:
        event: A dotted string identifying the event type, e.g.
            ``"rental.started"`` or ``"rental.ended"``. Used as both the
            log label and the ``event`` field in the Redis Stream entry.
        payload: A JSON-serializable dictionary containing event-specific
            data. Serialized as a single ``payload`` JSON field in the
            Redis Stream entry to avoid field-name collisions across
            different event types.

    Note:
        This function never raises. All Redis errors are caught internally
        and logged at ERROR level on the ``drivenow.events`` logger.
    """
    logger.info("event=%s payload=%s", event, payload)

    if _pool is None:
        return

    try:
        client = redis.Redis(connection_pool=_pool)
        client.xadd(
            _STREAM,
            {
                "event": event,
                "payload": json.dumps(payload),
            },
        )
    except Exception as exc:
        logger.error("redis xadd failed event=%s: %s", event, exc)
