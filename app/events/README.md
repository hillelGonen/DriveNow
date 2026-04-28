# `app/events/`

Reserved for asynchronous message-queue integration (RabbitMQ or Redis
Streams). Today the publisher is a no-op so service-layer code can already
emit domain events without waiting on the broker rollout.

## Planned event taxonomy

| Event | Producer | Payload |
|-------|----------|---------|
| `car.created` | `CarService.create` | `{id, model, year}` |
| `car.status_changed` | `CarService.update_status` | `{id, from, to, at}` |
| `rental.created` | `RentalService.book` | `{id, car_id, customer_name, start_date, end_date}` |
| `rental.completed` | `RentalService.return_car` | `{id, car_id, returned_at}` |

## Future structure

```
events/
├── publisher.py       # publish(event, payload) — broker-aware impl
├── consumers/
│   ├── __init__.py
│   └── rental_consumer.py
└── schemas.py         # pydantic models for event payloads
```

Consumers run as separate processes (`python -m app.events.consumers.rental_consumer`)
and ride the same `app/core/logging.py` + `app/core/metrics.py` infrastructure.
