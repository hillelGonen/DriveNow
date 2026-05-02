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
    """Emit a domain event.

    ``event`` is a dotted name (e.g. ``rental.started``, ``rental.ended``).
    ``payload`` is a JSON-serializable dict with event-specific fields.

    Always logs at INFO. Also pushes to Redis Stream if pool is available.
    Never raises.
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
