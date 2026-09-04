"""Tests for the time-based forecast baseline and the scenario simulator.

The forecast must be transparent (historical period + horizon + method),
deterministic, and must not fabricate confidence intervals. The scenario
simulator must apply volume_change deterministically and label itself as a
simulation.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.security import hash_password
from app.db import Base, get_db
from app.main import app
from app.models import Transaction, User


@pytest.fixture
def client(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'forecast.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    session.add(
        User(
            email="admin@demo.com",
            password_hash=hash_password("DemoPassword123!"),
            role="Admin",
        )
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
    with TestClient(app) as test_client:
        yield test_client, session_factory
    app.dependency_overrides.clear()
    engine.dispose()


def auth_headers(test_client):
    response = test_client.post(
        "/api/auth/login",
        json={"email": "admin@demo.com", "password": "DemoPassword123!"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def seed_flat_series(session_factory, revenue_days=35, expense_days=35):
    import datetime

    db = session_factory()
    for index in range(revenue_days):
        day = datetime.date(2026, 1, 1) + datetime.timedelta(days=index)
        db.add(
            Transaction(
                transaction_id=f"REV-{index}",
                date=day.isoformat(),
                amount=1000.0,
                type="revenue",
                status="completed",
            )
        )
    for index in range(expense_days):
        day = datetime.date(2026, 1, 1) + datetime.timedelta(days=index)
        db.add(
            Transaction(
                transaction_id=f"EXP-{index}",
                date=day.isoformat(),
                amount=200.0,
                type="expense",
                status="completed",
            )
        )
    db.commit()
    db.close()


def test_forecast_uses_flat_daily_baseline_over_30_day_horizon(client):
    test_client, session_factory = client
    seed_flat_series(session_factory)

    body = test_client.get("/api/forecast", headers=auth_headers(test_client)).json()
    assert body["available"] is True
    assert body["horizon_days"] == 30

    revenue = body["series"]["revenue"]
    assert revenue["available"] is True
    assert revenue["historical_start"] == "2026-01-01"
    assert revenue["historical_end"] == "2026-02-04"
    assert revenue["historical_days_observed"] == 35
    assert revenue["daily_average"] == 1000.0
    assert revenue["daily_trend"] == 0.0
    # Flat series: horizon * average == 30 * 1000.
    assert body["revenue_forecast"] == 30000.0

    expenses = body["series"]["expenses"]
    assert expenses["available"] is True
    assert body["expense_forecast"] == 30 * 200.0

    # No refunds/fees in the data -> reported unavailable, never zero.
    assert body["series"]["refunds"]["available"] is False
    assert body["series"]["fees"]["available"] is False
    assert body["cash_flow_forecast"] == 30000.0 - 6000.0
    assert "no fabricated confidence intervals" in body["method"]


def test_forecast_reports_insufficient_data_honestly(client):
    test_client, session_factory = client
    db = session_factory()
    db.add(
        Transaction(
            transaction_id="REV-1",
            date="2026-01-01",
            amount=1000.0,
            type="revenue",
            status="completed",
        )
    )
    db.commit()
    db.close()

    body = test_client.get("/api/forecast", headers=auth_headers(test_client)).json()
    assert body["available"] is False
    assert "Insufficient historical data" in body["message"]
    assert "revenue_forecast" not in body


def test_forecast_is_deterministic(client):
    test_client, session_factory = client
    seed_flat_series(session_factory)
    headers = auth_headers(test_client)
    first = test_client.get("/api/forecast", headers=headers).json()
    second = test_client.get("/api/forecast", headers=headers).json()
    assert first["series"] == second["series"]
    assert first["revenue_forecast"] == second["revenue_forecast"]


def test_scenario_applies_volume_change_deterministically(client):
    test_client, session_factory = client
    db = session_factory()
    db.add_all(
        [
            Transaction(
                transaction_id="REV-1",
                date="2026-01-01",
                amount=1000,
                type="revenue",
                status="completed",
                fee=100,
                refund_amount=50,
            ),
            Transaction(
                transaction_id="EXP-1",
                date="2026-01-01",
                amount=400,
                type="expense",
                status="completed",
            ),
        ]
    )
    db.commit()
    db.close()

    response = test_client.post(
        "/api/scenarios",
        json={"volume_change": 10},
        headers=auth_headers(test_client),
    )
    assert response.status_code == 200
    body = response.json()
    # Baseline: revenue=1000, expenses=400, refunds=50, fees=100.
    # Volume +10% scales every money movement before per-category deltas.
    assert body["volume_change_applied"] is True
    assert body["projected_revenue"] == 1100.0
    assert body["projected_expenses"] == 440.0
    assert body["projected_profit"] == 1100 - 440 - 55 - 110
    assert "Simulation only" in body["simulation_note"]


def test_scenario_without_volume_change_keeps_existing_contract(client):
    test_client, session_factory = client
    db = session_factory()
    db.add_all(
        [
            Transaction(
                transaction_id="REV-1",
                date="2026-01-01",
                amount=1000,
                type="revenue",
                status="completed",
                fee=100,
                refund_amount=50,
            ),
            Transaction(
                transaction_id="EXP-1",
                date="2026-01-01",
                amount=400,
                type="expense",
                status="completed",
            ),
        ]
    )
    db.commit()
    db.close()

    body = test_client.post(
        "/api/scenarios",
        json={"revenue_change": -10},
        headers=auth_headers(test_client),
    ).json()
    assert body["volume_change_applied"] is False
    assert body["projected_revenue"] == 900
    assert body["projected_expenses"] == 400
    assert body["projected_profit"] == 350
    assert body["cash_impact"] == -100
