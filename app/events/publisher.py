"""Domain event publisher.

Today: structured INFO log on the `drivenow.events` logger so consumers
(log aggregator, audit trail, ops dashboard) can subscribe by logger
name. Tomorrow: swap this body for an AMQP/Redis publisher; the call
sites in the service layer stay identical.

Service-layer code calls publish() AFTER the transaction commits, so
event consumers never see uncommitted state.
"""

import logging
from typing import Any

logger = logging.getLogger("drivenow.events")


def publish(event: str, payload: dict[str, Any]) -> None:
    """Emit a domain event.

    `event` is a dotted name (e.g. `rental.started`, `rental.ended`).
    `payload` is a JSON-serializable dict with event-specific fields.
    """
    logger.info("event=%s payload=%s", event, payload)
