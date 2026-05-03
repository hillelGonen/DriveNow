"""DriveNow Admin Dashboard.

Streamlit-based internal tool for full CRUD across cars, users, and rentals
plus live Prometheus metrics. Talks to the FastAPI backend via Docker-internal
DNS (``http://api:8000``) or, for local dev, an override via the
``API_BASE_URL`` env var.
"""

import os
import re
from typing import Any

import pandas as pd
import requests
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://api:8000")
REQUEST_TIMEOUT = 5  # seconds

CAR_STATUSES = ["AVAILABLE", "IN_USE", "MAINTENANCE"]

st.set_page_config(
    page_title="DriveNow Admin",
    page_icon="🚗",
    layout="wide",
)


# ---------- API client helpers ----------


def _get(path: str, params: dict | None = None) -> Any:
    """GET ``path`` and return parsed JSON, or ``None`` on transport error."""
    try:
        r = requests.get(f"{API_BASE_URL}{path}", params=params, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as exc:
        st.error(f"GET {path} failed: {exc}")
        return None


def _post(path: str, body: dict) -> tuple[bool, dict]:
    """POST ``body`` to ``path``. Returns ``(ok, json_or_error_dict)``."""
    try:
        r = requests.post(f"{API_BASE_URL}{path}", json=body, timeout=REQUEST_TIMEOUT)
        if r.status_code >= 400:
            return False, (r.json() if r.content else {"detail": r.reason})
        return True, r.json()
    except requests.RequestException as exc:
        return False, {"detail": str(exc)}


def _patch(path: str, body: dict | None = None) -> tuple[bool, dict]:
    """PATCH ``path`` with optional body. Returns ``(ok, json_or_error_dict)``."""
    try:
        r = requests.patch(f"{API_BASE_URL}{path}", json=body, timeout=REQUEST_TIMEOUT)
        if r.status_code >= 400:
            return False, (r.json() if r.content else {"detail": r.reason})
        return True, (r.json() if r.content else {})
    except requests.RequestException as exc:
        return False, {"detail": str(exc)}


def _delete(path: str) -> tuple[bool, dict]:
    """DELETE ``path``. Returns ``(ok, error_dict_or_empty)``."""
    try:
        r = requests.delete(f"{API_BASE_URL}{path}", timeout=REQUEST_TIMEOUT)
        if r.status_code >= 400:
            return False, (r.json() if r.content else {"detail": r.reason})
        return True, {}
    except requests.RequestException as exc:
        return False, {"detail": str(exc)}


def _fetch_metrics_text() -> str | None:
    """Fetch raw Prometheus exposition text from the API."""
    try:
        r = requests.get(f"{API_BASE_URL}/metrics", timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        return r.text
    except requests.RequestException as exc:
        st.error(f"GET /metrics failed: {exc}")
        return None


def _parse_gauge(text: str, name: str) -> float | None:
    """Extract a single gauge value (no labels) from Prometheus text."""
    match = re.search(rf"^{re.escape(name)} ([\d.eE+-]+)$", text, re.MULTILINE)
    return float(match.group(1)) if match else None


def _sum_counter_by_status(text: str, name: str, status: str) -> float:
    """Sum a counter across all label sets that match ``status=<status>``."""
    pattern = (
        rf'^{re.escape(name)}\{{[^}}]*status="{re.escape(status)}"[^}}]*\}} '
        rf"([\d.eE+-]+)$"
    )
    return sum(float(m) for m in re.findall(pattern, text, re.MULTILINE))


def _per_operation_counts(text: str, name: str) -> pd.DataFrame:
    """Parse counter ``name`` into a DataFrame with operation/status/count columns."""
    pattern = (
        rf'^{re.escape(name)}\{{operation="([^"]+)",status="([^"]+)"\}} '
        rf"([\d.eE+-]+)$"
    )
    rows = [
        {"operation": op, "status": status, "count": float(count)}
        for op, status, count in re.findall(pattern, text, re.MULTILINE)
    ]
    return pd.DataFrame(rows) if rows else pd.DataFrame(
        columns=["operation", "status", "count"]
    )


_STATUS_BADGE = {
    "AVAILABLE": "🟢 AVAILABLE",
    "IN_USE": "🔵 IN_USE",
    "MAINTENANCE": "🟡 MAINTENANCE",
}


# ---------- Sidebar ----------


def render_sidebar() -> None:
    """Render the metrics sidebar."""
    st.sidebar.title("📊 System Health")

    if st.sidebar.button("🔄 Refresh", use_container_width=True):
        st.rerun()

    text = _fetch_metrics_text()
    if text is None:
        st.sidebar.warning("Metrics unavailable")
        return

    available = _parse_gauge(text, "drivenow_available_cars")
    active = _parse_gauge(text, "drivenow_active_rentals")
    successes = _sum_counter_by_status(
        text, "drivenow_service_operation_total", "success"
    )
    errors = _sum_counter_by_status(
        text, "drivenow_service_operation_total", "error"
    )

    st.sidebar.metric(
        "Available Cars",
        f"{int(available) if available is not None else '—'}",
    )
    st.sidebar.metric(
        "Active Rentals",
        f"{int(active) if active is not None else '—'}",
    )
    st.sidebar.metric("Successful Ops", f"{int(successes)}")
    st.sidebar.metric("Errored Ops", f"{int(errors)}")

    st.sidebar.caption(f"API: `{API_BASE_URL}`")


# ---------- Cars tab ----------


def _car_select_label(c: dict) -> str:
    return f"#{c['id']} — {c['model']} ({c['year']}) [{c['status']}]"


def render_cars_tab() -> None:
    """Full CRUD for cars."""
    st.subheader("🚗 Fleet")

    cars = _get("/api/v1/cars", params={"limit": 200}) or []
    if cars:
        df = pd.DataFrame(cars)
        df["status"] = df["status"].map(lambda s: _STATUS_BADGE.get(s, s))
        df = df[["id", "model", "year", "status", "created_at", "updated_at"]]
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No cars in the fleet yet.")

    st.divider()

    col_create, col_update, col_delete = st.columns(3)

    with col_create:
        st.markdown("### ➕ Create Car")
        with st.form("car_create", clear_on_submit=True):
            model = st.text_input("Model", max_chars=100)
            year = st.number_input(
                "Year", min_value=1900, max_value=2100, value=2024, step=1
            )
            initial_status = st.selectbox("Initial status", CAR_STATUSES, index=0)
            if st.form_submit_button("Create", type="primary"):
                if not model.strip():
                    st.error("Model is required.")
                else:
                    ok, body = _post(
                        "/api/v1/cars",
                        {"model": model, "year": int(year), "status": initial_status},
                    )
                    if ok:
                        st.success(f"Car #{body['id']} created.")
                        st.rerun()
                    else:
                        st.error(body.get("detail", "Unknown error"))

    with col_update:
        st.markdown("### ✏️ Update Car")
        if not cars:
            st.caption("No cars to update.")
        else:
            with st.form("car_update", clear_on_submit=False):
                car = st.selectbox(
                    "Car",
                    options=cars,
                    format_func=_car_select_label,
                    key="update_car_select",
                )
                new_model = st.text_input("Model (blank = keep)", "")
                new_year = st.number_input(
                    "Year (0 = keep)", min_value=0, max_value=2100, value=0, step=1
                )
                new_status = st.selectbox(
                    "Status", ["(keep)"] + CAR_STATUSES, index=0
                )
                if st.form_submit_button("Update", type="primary"):
                    payload: dict[str, Any] = {}
                    if new_model.strip():
                        payload["model"] = new_model.strip()
                    if new_year:
                        payload["year"] = int(new_year)
                    if new_status != "(keep)":
                        payload["status"] = new_status
                    if not payload:
                        st.warning("Nothing to update.")
                    else:
                        ok, body = _patch(f"/api/v1/cars/{car['id']}", payload)
                        if ok:
                            st.success(f"Car #{body['id']} updated.")
                            st.rerun()
                        else:
                            st.error(body.get("detail", "Unknown error"))

    with col_delete:
        st.markdown("### 🗑️ Delete Car")
        if not cars:
            st.caption("No cars to delete.")
        else:
            with st.form("car_delete", clear_on_submit=True):
                car = st.selectbox(
                    "Car",
                    options=cars,
                    format_func=_car_select_label,
                    key="delete_car_select",
                )
                confirm = st.checkbox("I confirm deletion")
                if st.form_submit_button("Delete", type="secondary"):
                    if not confirm:
                        st.warning("Tick the confirm box first.")
                    else:
                        ok, body = _delete(f"/api/v1/cars/{car['id']}")
                        if ok:
                            st.success(f"Car #{car['id']} deleted.")
                            st.rerun()
                        else:
                            st.error(body.get("detail", "Unknown error"))


# ---------- Users tab ----------


def _user_select_label(u: dict) -> str:
    return f"#{u['id']} — {u['name']}"


def render_users_tab() -> None:
    """Full CRUD for users (no PATCH endpoint — create/list/get/delete only)."""
    st.subheader("👥 Users")

    users = _get("/api/v1/users/", params={"limit": 200}) or []
    cars = _get("/api/v1/cars", params={"limit": 200}) or []
    active_rentals = _get("/api/v1/rentals/", params={"active": "true", "limit": 500}) or []

    if users:
        cars_by_id = {c["id"]: c for c in cars}
        cars_by_user: dict[int, list[str]] = {}
        for r in active_rentals:
            car = cars_by_id.get(r["car_id"])
            label = (
                f"#{r['car_id']} {car['model']}"
                if car
                else f"#{r['car_id']} (deleted)"
            )
            cars_by_user.setdefault(r["user_id"], []).append(label)

        rows = []
        for u in users:
            held = cars_by_user.get(u["id"], [])
            rows.append(
                {
                    "id": u["id"],
                    "name": u["name"],
                    "active_rentals": len(held),
                    "currently_renting": ", ".join(held) if held else "—",
                    "created_at": u["created_at"],
                }
            )
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("No users yet.")

    st.divider()

    col_create, col_lookup, col_delete = st.columns(3)

    with col_create:
        st.markdown("### ➕ Create User")
        with st.form("user_create", clear_on_submit=True):
            name = st.text_input("Name", max_chars=200)
            if st.form_submit_button("Create", type="primary"):
                if not name.strip():
                    st.error("Name is required.")
                else:
                    ok, body = _post("/api/v1/users/", {"name": name.strip()})
                    if ok:
                        st.success(f"User #{body['id']} created.")
                        st.rerun()
                    else:
                        st.error(body.get("detail", "Unknown error"))

    with col_lookup:
        st.markdown("### 🔍 Lookup User")
        with st.form("user_lookup"):
            user_id = st.number_input("User ID", min_value=1, step=1)
            if st.form_submit_button("Fetch"):
                body = _get(f"/api/v1/users/{int(user_id)}")
                if body:
                    st.json(body)

    with col_delete:
        st.markdown("### 🗑️ Delete User")
        if not users:
            st.caption("No users to delete.")
        else:
            with st.form("user_delete", clear_on_submit=True):
                user = st.selectbox(
                    "User",
                    options=users,
                    format_func=_user_select_label,
                    key="delete_user_select",
                )
                confirm = st.checkbox("I confirm deletion")
                if st.form_submit_button("Delete", type="secondary"):
                    if not confirm:
                        st.warning("Tick the confirm box first.")
                    else:
                        ok, body = _delete(f"/api/v1/users/{user['id']}")
                        if ok:
                            st.success(f"User #{user['id']} deleted.")
                            st.rerun()
                        else:
                            st.error(body.get("detail", "Unknown error"))


# ---------- Rentals tab ----------


def render_rentals_tab() -> None:
    """Start and return rentals.

    Note: API has no rentals-list endpoint, so the return form takes a
    rental_id number input. The active-rental count is shown via metrics.
    """
    st.subheader("🚙 Rentals")

    metrics_text = _fetch_metrics_text()
    if metrics_text:
        active = _parse_gauge(metrics_text, "drivenow_active_rentals")
        st.info(f"Currently active rentals: **{int(active) if active is not None else '—'}**")

    cars = _get("/api/v1/cars", params={"limit": 200}) or []
    users = _get("/api/v1/users/", params={"limit": 200}) or []
    active_rentals = _get(
        "/api/v1/rentals/", params={"active": "true", "limit": 500}
    ) or []

    available_cars = [c for c in cars if c["status"] == "AVAILABLE"]
    in_use_cars = [c for c in cars if c["status"] == "IN_USE"]

    users_by_id = {u["id"]: u for u in users}
    rental_by_car: dict[int, dict] = {r["car_id"]: r for r in active_rentals}

    st.markdown("### 🚗 Fleet — Cars × Active Rental")
    if cars:
        rows = []
        for c in cars:
            r = rental_by_car.get(c["id"])
            user = users_by_id.get(r["user_id"]) if r else None
            rows.append(
                {
                    "car_id": c["id"],
                    "model": c["model"],
                    "year": c["year"],
                    "status": _STATUS_BADGE.get(c["status"], c["status"]),
                    "rental_id": r["id"] if r else "—",
                    "user_id": r["user_id"] if r else "—",
                    "user_name": (user["name"] if user else ("—" if not r else "(deleted)")),
                    "started_at": r["start_time"] if r else "—",
                }
            )
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("No cars in the fleet.")

    st.divider()

    left, right = st.columns(2)

    with left:
        st.markdown("### ▶️ Start Rental")
        if not available_cars:
            st.info("No AVAILABLE cars right now.")
        elif not users:
            st.info("No users — create one in the Users tab first.")
        else:
            with st.form("start_rental", clear_on_submit=True):
                car = st.selectbox(
                    "Car",
                    options=available_cars,
                    format_func=lambda c: f"#{c['id']} — {c['model']} ({c['year']})",
                )
                user = st.selectbox(
                    "User",
                    options=users,
                    format_func=_user_select_label,
                )
                if st.form_submit_button("Start Rental", type="primary"):
                    ok, body = _post(
                        "/api/v1/rentals/",
                        {"user_id": user["id"], "car_id": car["id"]},
                    )
                    if ok:
                        st.success(
                            f"Rental #{body['id']} started — car #{body['car_id']}, "
                            f"user #{body['user_id']}."
                        )
                        st.rerun()
                    else:
                        st.error(body.get("detail", "Unknown error"))

    with right:
        st.markdown("### ⏹️ Return Car")
        if in_use_cars:
            ids = ", ".join(f"#{c['id']}" for c in in_use_cars)
            st.caption(f"Cars currently IN_USE: {ids}")
        with st.form("return_rental", clear_on_submit=True):
            rental_id = st.number_input("Rental ID", min_value=1, step=1)
            if st.form_submit_button("Return", type="primary"):
                ok, body = _patch(f"/api/v1/rentals/{int(rental_id)}/return")
                if ok:
                    st.success(
                        f"Rental #{body['id']} returned at {body['end_time']}."
                    )
                    st.rerun()
                else:
                    st.error(body.get("detail", "Unknown error"))


# ---------- Metrics tab ----------


def render_metrics_tab() -> None:
    """Detailed metrics view with per-operation breakdown."""
    st.subheader("📈 Operations Metrics")

    text = _fetch_metrics_text()
    if text is None:
        return

    df = _per_operation_counts(text, "drivenow_service_operation_total")
    if df.empty:
        st.info("No operations recorded yet.")
        return

    pivot = (
        df.pivot_table(
            index="operation", columns="status", values="count", fill_value=0
        )
        .reset_index()
    )
    for col in ("success", "error"):
        if col not in pivot.columns:
            pivot[col] = 0
    pivot["total"] = pivot["success"] + pivot["error"]
    pivot = pivot[["operation", "success", "error", "total"]].sort_values("total", ascending=False)

    st.dataframe(pivot, use_container_width=True, hide_index=True)

    st.markdown("#### Live gauges")
    cols = st.columns(2)
    with cols[0]:
        st.metric(
            "Available Cars",
            int(_parse_gauge(text, "drivenow_available_cars") or 0),
        )
    with cols[1]:
        st.metric(
            "Active Rentals",
            int(_parse_gauge(text, "drivenow_active_rentals") or 0),
        )


# ---------- Page ----------


def main() -> None:
    """Compose the dashboard page."""
    render_sidebar()

    st.title("DriveNow Admin")
    st.caption("Internal control plane — cars, users, rentals, metrics.")

    tab_cars, tab_users, tab_rentals, tab_metrics = st.tabs(
        ["🚗 Cars", "👥 Users", "🚙 Rentals", "📈 Metrics"]
    )

    with tab_cars:
        render_cars_tab()
    with tab_users:
        render_users_tab()
    with tab_rentals:
        render_rentals_tab()
    with tab_metrics:
        render_metrics_tab()


if __name__ == "__main__":
    main()
