"""User CRUD endpoint tests."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_create_user_returns_201_with_body(api_client: TestClient) -> None:
    r = api_client.post("/api/v1/users/", json={"name": "Ada Lovelace"})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["name"] == "Ada Lovelace"
    assert isinstance(body["id"], int)


def test_list_users_returns_inserted(api_client: TestClient) -> None:
    api_client.post("/api/v1/users/", json={"name": "A"})
    api_client.post("/api/v1/users/", json={"name": "B"})
    r = api_client.get("/api/v1/users/")
    assert r.status_code == 200
    assert {u["name"] for u in r.json()} == {"A", "B"}


def test_get_user_by_id(api_client: TestClient) -> None:
    created = api_client.post("/api/v1/users/", json={"name": "Grace"}).json()
    r = api_client.get(f"/api/v1/users/{created['id']}")
    assert r.status_code == 200
    assert r.json()["name"] == "Grace"


def test_get_unknown_user_returns_404(api_client: TestClient) -> None:
    r = api_client.get("/api/v1/users/9999")
    assert r.status_code == 404


def test_delete_user_then_get_returns_404(api_client: TestClient) -> None:
    user_id = api_client.post("/api/v1/users/", json={"name": "Hopper"}).json()["id"]
    delete_resp = api_client.delete(f"/api/v1/users/{user_id}")
    assert delete_resp.status_code == 204
    assert api_client.get(f"/api/v1/users/{user_id}").status_code == 404


def test_delete_user_with_active_rental_returns_409(api_client: TestClient) -> None:
    user_id = api_client.post("/api/v1/users/", json={"name": "Renting User"}).json()[
        "id"
    ]
    car_id = api_client.post(
        "/api/v1/cars", json={"model": "Tesla Model Y", "year": 2024}
    ).json()["id"]
    rental_resp = api_client.post(
        "/api/v1/rentals/", json={"user_id": user_id, "car_id": car_id}
    )
    assert rental_resp.status_code == 201

    r = api_client.delete(f"/api/v1/users/{user_id}")
    assert r.status_code == 409
    assert "active rental" in r.json()["detail"].lower()
