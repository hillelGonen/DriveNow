import logging

logger = logging.getLogger(__name__)


def publish(event: str, payload: dict) -> None:
    """Reserved interface for the message broker. No-op until wired.

    Service-layer code may call ``publish("rental.created", {...})`` today;
    when a broker (RabbitMQ / Redis Streams) is added, only this module
    changes. Keeping the call site stable lets domain events be authored
    alongside business logic without waiting on infrastructure.
    """
    logger.debug("event.publish.noop event=%s payload=%s", event, payload)
