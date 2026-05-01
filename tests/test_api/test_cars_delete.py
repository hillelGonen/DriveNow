"""DELETE /cars/{id} tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.models.user import User


def test_delete_car_returns_204(api_client: TestClient) -> None:
    car_id = api_client.post(
        "/api/v1/cars", json={"model": "Tesla Model Y", "year": 2024}
    ).json()["id"]
    r = api_client.delete(f"/api/v1/cars/{car_id}")
    assert r.status_code == 204
    assert api_client.get("/api/v1/cars").json() == []


def test_delete_unknown_car_returns_404(api_client: TestClient) -> None:
    r = api_client.delete("/api/v1/cars/9999")
    assert r.status_code == 404


def test_delete_car_with_active_rental_returns_409(
    api_client: TestClient, seed_user: User
) -> None:
    car_id = api_client.post(
        "/api/v1/cars", json={"model": "Tesla Model 3", "year": 2024}
    ).json()["id"]
    rental_resp = api_client.post(
        "/api/v1/rentals/", json={"user_id": seed_user.id, "car_id": car_id}
    )
    assert rental_resp.status_code == 201

    r = api_client.delete(f"/api/v1/cars/{car_id}")
    assert r.status_code == 409
    assert "active rental" in r.json()["detail"].lower()
