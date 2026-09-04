"""Regression tests for the unified CFO Command Center report.

The /reports/cfo payload stays backward compatible while now also carrying
independent anomalies, review workload, alerts, forecast, reference scenario
simulations and the audit/control trail - all backend-calculated, additive
fields. Access is role-gated to controller/manager tiers server-side.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.security import hash_password
from app.db import Base, get_db
from app.main import app
from app.models import User

USERS = [
    ("admin@demo.com", "DemoPassword123!", "Admin"),
    ("manager@demo.com", "ManagerPass1!", "Finance Manager"),
    ("analyst@demo.com", "AnalystPass1!", "Finance Analyst"),
    ("reviewer@demo.com", "ReviewerPass1!", "Reviewer"),
]


@pytest.fixture
def env(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'cfo.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    for email, password, role in USERS:
        session.add(
            User(email=email, password_hash=hash_password(password), role=role)
        )
    session.commit()
    session.close()

    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield {"client": client}
    app.dependency_overrides.clear()
    engine.dispose()


def auth_headers(client, email="admin@demo.com", password="DemoPassword123!"):
    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def seed_real_flow(client):
    """Drive the real API: /import with an outlier + mismatch creates
    statistical anomalies, review items, risk rows and audit events."""
    rows = ["transaction_id,date,amount,type,status,settlement_amount"]
    for index in range(14):
        rows.append(
            f"CFO-{index},2026-01-0{index % 9 + 1},1000,revenue,completed,1000"
        )
    rows.append("CFO-BIG,2026-02-01,900000,revenue,completed,900000")
    rows.append("CFO-MIS,2026-02-02,500,expense,completed,300")

    response = client.post(
        "/api/import",
        files={"file": ("cfo-flow.csv", ("\n".join(rows) + "\n").encode(), "text/csv")},
        headers=auth_headers(client),
    )
    assert response.status_code == 200
    assert response.json()["imported"] == 16
    assert any(
        item["transaction_id"] == "CFO-BIG"
        for item in response.json()["statistical_anomalies"]
    )
    return response.json()


def test_cfo_report_carries_unified_control_context(env):
    client = env["client"]
    seed_real_flow(client)

    body = client.get("/api/reports/cfo", headers=auth_headers(client)).json()

    # Legacy contract is untouched.
    assert body["title"] == "CFO Executive Report"
    assert "metrics" in body
    assert body["metrics"]["total_transactions"] == 16
    assert "cash_flow_trend" in body
    assert "expense_breakdown" in body
    assert "priority_actions" in body
    assert "data_note" in body

    # Independent anomalies (statistical) are present and run-scoped.
    anomalies = body["anomalies"]
    assert isinstance(anomalies["total"], int)
    assert isinstance(anomalies["by_severity"], dict)
    assert anomalies["total"] >= 1
    assert any(
        item["transaction_id"] == "CFO-BIG"
        and item["reason"].startswith("Statistical anomaly")
        for item in anomalies["recent"]
    )

    # Review workload from the real upload (CFO-MIS created a review item).
    review = body["review_workload"]
    assert review["total"] >= 1
    assert review["open"] >= 1
    assert review["attention"] >= 1
    assert review["by_status"].get("OPEN", 0) >= 1

    # Alerts list is always a list.
    assert isinstance(body["alerts"], list)

    # Forecast block is present (available or honestly unavailable).
    assert "forecast" in body
    assert "available" in body["forecast"]
    assert "series" in body["forecast"] or "message" in body["forecast"]

    # Reference scenario simulations, deterministic and clearly labeled.
    scenarios = body["scenario_insights"]
    assert len(scenarios["reference_scenarios"]) == 3
    for scenario in scenarios["reference_scenarios"]:
        assert "projected_revenue" in scenario
        assert "projected_profit" in scenario
        assert "simulation_note" in scenario
        assert "volume_change_applied" in scenario
    assert "not forecasts or guaranteed outcomes" in scenarios["note"]

    # Audit/control trail with recent control events.
    audit = body["audit_trail"]
    assert isinstance(audit, list)
    assert len(audit) >= 1
    actions = {entry["action"] for entry in audit}
    assert "CSV_IMPORT" in actions

    assert body["control_context"]["run_id"] is not None
    assert "trace_note" in body["control_context"]


def test_cfo_report_requires_controller_role(env):
    client = env["client"]
    seed_real_flow(client)

    # Controller/manager tiers may read the executive view.
    manager = client.get(
        "/api/reports/cfo",
        headers=auth_headers(client, "manager@demo.com", "ManagerPass1!"),
    )
    assert manager.status_code == 200
    assert "anomalies" in manager.json()

    # Analyst and Reviewer roles are rejected server-side (403).
    for email, password in (
        ("analyst@demo.com", "AnalystPass1!"),
        ("reviewer@demo.com", "ReviewerPass1!"),
    ):
        response = client.get(
            "/api/reports/cfo",
            headers=auth_headers(client, email, password),
        )
        assert response.status_code == 403

    # Unauthenticated access is rejected (401).
    assert client.get("/api/reports/cfo").status_code == 401


def test_cfo_shared_helpers_keep_endpoints_backward_compatible(env):
    client = env["client"]
    seed_real_flow(client)
    headers = auth_headers(client)

    # /forecast still returns the same deterministic shape.
    forecast = client.get("/api/forecast", headers=headers)
    assert forecast.status_code == 200
    assert "available" in forecast.json()

    # /scenarios still applies deterministic math (revenue -10% on 1000*14 + ...).
    scenario = client.post(
        "/api/scenarios",
        json={"revenue_change": -10},
        headers=headers,
    )
    assert scenario.status_code == 200
    body = scenario.json()
    assert "projected_revenue" in body
    assert "projected_profit" in body
    assert "simulation_note" in body

    # /alerts still returns a list.
    alerts = client.get("/api/alerts", headers=headers)
    assert alerts.status_code == 200
    assert isinstance(alerts.json(), list)
