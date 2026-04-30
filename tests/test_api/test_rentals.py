"""Rental endpoint tests.

Asserts the core invariant: a car can be rented at most once concurrently.
The second POST against the same car returns 400 Bad Request because the
car's status is now IN_USE.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.models.user import User


def test_double_rental_returns_400(api_client: TestClient, seed_user: User) -> None:
    car_resp = api_client.post(
        "/api/v1/cars",
        json={"model": "Tesla Model 3", "year": 2024},
    )
    assert car_resp.status_code == 201, car_resp.text
    car_id = car_resp.json()["id"]

    first = api_client.post(
        "/api/v1/rentals/",
        json={"user_id": seed_user.id, "car_id": car_id},
    )
    assert first.status_code == 201, first.text
    body = first.json()
    assert body["car_id"] == car_id
    assert body["user_id"] == seed_user.id
    assert body["end_time"] is None

    car_after = api_client.get(f"/api/v1/cars").json()[0]
    assert car_after["status"] == "IN_USE"

    second = api_client.post(
        "/api/v1/rentals/",
        json={"user_id": seed_user.id, "car_id": car_id},
    )
    assert second.status_code == 400, second.text
    assert "not available" in second.json()["detail"].lower()


def test_return_rental_sets_end_time_and_frees_car(
    api_client: TestClient, seed_user: User
) -> None:
    car_id = api_client.post(
        "/api/v1/cars", json={"model": "Tesla Model Y", "year": 2025}
    ).json()["id"]
    rental_id = api_client.post(
        "/api/v1/rentals/", json={"user_id": seed_user.id, "car_id": car_id}
    ).json()["id"]

    ret = api_client.patch(f"/api/v1/rentals/{rental_id}/return")
    assert ret.status_code == 200, ret.text
    assert ret.json()["end_time"] is not None

    car_after = api_client.get(f"/api/v1/cars").json()[0]
    assert car_after["status"] == "AVAILABLE"

    # Returning twice is rejected (idempotency-friendly: 400 not 500).
    again = api_client.patch(f"/api/v1/rentals/{rental_id}/return")
    assert again.status_code == 400
