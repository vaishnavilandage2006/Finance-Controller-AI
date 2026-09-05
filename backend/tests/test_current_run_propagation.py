"""Regression tests: current-run data propagation across control modules.

The bug being fixed: reconciliation correctly reported the latest run's
figures, but downstream modules (dashboard totals, transactions, anomalies,
risk, forecast, CFO trend/expense charts, scenarios, alerts and the Copilot
context) were still aggregating ALL historical database rows. After a
200-record upload into a database that already contains historical runs,
the dashboard reported the historical total (e.g. 1301) instead of the
current run (200).

These tests prove:
1. a new upload becomes the current run,
2. dashboard current-run totals are 200, not the historical total,
3. reconciliation keeps producing 40 exceptions and Rs.3,575 variance,
4. anomaly/risk consume the current run's exception/risk records,
5. forecast is scoped to the current run (and never leaks historical rows),
6. the CFO report is scoped to the current run,
7. alerts derive from the current run,
8. the AI Copilot receives current-run context,
9. Settings/analytics identifies the current run correctly,
10. historical data is NOT deleted,
11. RBAC still works and unauthenticated endpoints stay protected.

The uploaded file used here has the SAME production-verified outcome as the
operator's my_new_finance_data_200.csv upload (total=200, matched=160,
mismatch=40, variance=3575, match rate=80%, risk LOW 25 / MEDIUM 15 /
HIGH 0 / CRITICAL 0). Every assertion is derived from the real
reconciliation / risk engines - nothing is hardcoded in the handlers.
"""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.security import hash_password
from app.db import Base, get_db
from app.main import app
from app.models import (
    ReconciliationResult,
    ReconciliationRun,
    Transaction,
    User,
)

SAMPLE = Path(__file__).resolve().parents[2] / "database" / "sample_data"

USERS = [
    ("admin@demo.com", "DemoPassword123!", "Admin"),
    ("analyst@demo.com", "AnalystPass1!", "Finance Analyst"),
]


@pytest.fixture
def client(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'propagation.db'}",
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
    with TestClient(app) as test_client:
        yield test_client, session_factory
    app.dependency_overrides.clear()
    engine.dispose()


def auth_headers(client, email="admin@demo.com", password="DemoPassword123!"):
    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def post_single(client, filename, data):
    response = client.post(
        "/api/reconciliation/single-file",
        files={"file": (filename, data, "text/csv")},
        headers=auth_headers(client),
    )
    assert response.status_code == 200
    return response.json()


def finance_1000_bytes():
    return (SAMPLE / "finance_transactions.csv").read_bytes()


def current_run_200_bytes():
    """200-record upload with the production-verified outcome of
    my_new_finance_data_200.csv: 160 matched, 25 LOW + 15 MEDIUM
    exceptions (no HIGH/CRITICAL), Rs.3,575 total variance, 80% match.

    25 mismatches of Rs.83  -> risk score 20 + ratio bonus 5 = 25 -> LOW
    15 mismatches of Rs.100 -> risk score 32 + ratio bonus 5 = 37 -> MEDIUM
    total variance = 25*83 + 15*100 = 3575
    """
    rows = []
    for index in range(200):
        amount = 1000 + index
        if index < 160:
            settled = amount  # matched
        elif index < 185:
            settled = amount - 83  # LOW exception (25)
        else:
            settled = amount - 100  # MEDIUM exception (15)
        rows.append(f"{index},payment-{index},{amount},{settled},Merchant,2026-01-01")
    return (
        "id,payment_reference,gross_amount,settled_value,merchant_name,transaction_date\n"
        + "\n".join(rows)
        + "\n"
    ).encode()


def seed_historical_and_current_run(client):
    """Simulate the production state: a historical 1000-row run exists and a
    200-record upload then becomes the current run."""
    run1 = post_single(client, "finance_transactions.csv", finance_1000_bytes())
    assert run1["total"] == 1000
    run2 = post_single(client, "my_new_finance_data_200.csv", current_run_200_bytes())
    assert run2["total"] == 200
    return run1["run_id"], run2["run_id"]


def test_new_upload_becomes_the_current_run(client):
    test_client, _ = client
    run1_id, run2_id = seed_historical_and_current_run(test_client)

    dashboard = test_client.get(
        "/api/dashboard", headers=auth_headers(test_client)
    ).json()
    assert dashboard["reconciliation"]["run_id"] == run2_id
    assert dashboard["current_run"]["run_id"] == run2_id
    assert dashboard["current_run"]["filename"] == "my_new_finance_data_200.csv"
    assert dashboard["current_run"]["mode"] == "single_file"


def test_dashboard_current_run_totals_are_200_not_historical(client):
    test_client, session_factory = client
    run1_id, run2_id = seed_historical_and_current_run(test_client)

    db = session_factory()
    historical_count = db.query(Transaction).count()
    db.close()
    # Historical rows still exist and are untouched (requirement: never
    # delete historical data).
    assert historical_count == 1200

    dashboard = test_client.get(
        "/api/dashboard", headers=auth_headers(test_client)
    ).json()
    # The dashboard total must be the CURRENT run's 200 records - not the
    # historical database total (1200 here, 1301 in production).
    assert dashboard["total_transactions"] == 200
    assert dashboard["reconciliation"]["total"] == 200
    # Financial dimensions are honestly unavailable for this run's schema
    # (no revenue/expense column) - never leaked from historical rows.
    assert dashboard["financial"]["revenue"]["available"] is False
    assert dashboard["financial"]["expenses"]["available"] is False
    assert dashboard["revenue"] == 0
    assert dashboard["expenses"] == 0


def test_reconciliation_keeps_40_exceptions_and_3575_variance(client):
    test_client, _ = client
    run1_id, run2_id = seed_historical_and_current_run(test_client)

    reconciliation = test_client.get(
        "/api/reconciliation", headers=auth_headers(test_client)
    ).json()
    assert reconciliation["run_id"] == run2_id
    assert reconciliation["total"] == 200
    assert reconciliation["matched"] == 160
    assert reconciliation["mismatch"] == 40
    assert reconciliation["partial"] == 0
    assert reconciliation["unmatched"] == 0
    assert reconciliation["duplicate"] == 0
    assert reconciliation["exceptions"] == 40
    assert reconciliation["match_rate"] == 80
    assert reconciliation["variance"] == 3575


def test_risk_and_anomaly_consume_current_run_records(client):
    test_client, _ = client
    run1_id, run2_id = seed_historical_and_current_run(test_client)

    # /api/risk without a run_id defaults to the CURRENT run: exactly the
    # run's 40 exceptions, never the historical run's 28.
    risk = test_client.get("/api/risk", headers=auth_headers(test_client)).json()
    assert len(risk) == 40
    assert {item["run_id"] for item in risk} == {run2_id}
    assert all(item["transaction_id"].startswith("payment-") for item in risk)

    # Explicit run_id still reaches the historical run.
    risk1 = test_client.get(
        f"/api/risk?run_id={run1_id}", headers=auth_headers(test_client)
    ).json()
    assert len(risk1) == 28

    # The documented current-run risk distribution: LOW 25 / MEDIUM 15 /
    # HIGH 0 / CRITICAL 0.
    distribution = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
    for item in risk:
        distribution[str(item["risk_level"]).upper()] += 1
    assert distribution == {"LOW": 25, "MEDIUM": 15, "HIGH": 0, "CRITICAL": 0}

    dashboard = test_client.get(
        "/api/dashboard", headers=auth_headers(test_client)
    ).json()
    assert dashboard["risk_distribution"] == {
        "LOW": 25, "MEDIUM": 15, "HIGH": 0, "CRITICAL": 0,
    }
    assert dashboard["high_risk"] == 0

    # /api/anomalies without a run_id defaults to the CURRENT run. The
    # single-file path now runs independent statistical detection, so this
    # synthetic dataset's merchant concentration is visible for run 2 while
    # remaining separate from exception-driven risk.
    anomalies = test_client.get("/api/anomalies", headers=auth_headers(test_client)).json()
    assert anomalies
    assert {item["transaction_id"] for item in anomalies} == {"Merchant"}
    assert {item["variance"] for item in anomalies} == {None}
    anomalies1 = test_client.get(
        f"/api/anomalies?run_id={run1_id}", headers=auth_headers(test_client)
    ).json()
    assert len(anomalies1) >= 1


def test_transactions_page_is_scoped_to_current_run(client):
    test_client, _ = client
    run1_id, run2_id = seed_historical_and_current_run(test_client)

    current = test_client.get(
        "/api/transactions?page=1&page_size=500",
        headers=auth_headers(test_client),
    ).json()
    assert current["run_id"] == run2_id
    assert current["total"] == 200
    assert {item["transaction_id"] for item in current["items"]} == {
        f"payment-{index}" for index in range(200)
    }

    historical = test_client.get(
        f"/api/transactions?run_id={run1_id}&page=1&page_size=1500",
        headers=auth_headers(test_client),
    ).json()
    assert historical["total"] == 1000
    assert "payment-199" not in {item["transaction_id"] for item in historical["items"]}


def test_forecast_uses_current_run_and_never_leaks_historical_rows(client):
    test_client, _ = client
    run1_id, run2_id = seed_historical_and_current_run(test_client)

    forecast = test_client.get("/api/forecast", headers=auth_headers(test_client)).json()
    # The forecast is scoped to the current run.
    assert forecast.get("run_id") == run2_id
    assert forecast["available"] is True
    # The current run's schema has no revenue/expense/refund/fee dimension,
    # so every series is honestly unavailable. If the historical 1000-row
    # revenue/expense data had leaked in, revenue would be "available".
    assert forecast["series"]["revenue"]["available"] is False
    assert forecast["series"]["expenses"]["available"] is False
    assert forecast["series"]["refunds"]["available"] is False
    assert forecast["series"]["fees"]["available"] is False


def test_cfo_report_uses_current_run(client):
    test_client, _ = client
    run1_id, run2_id = seed_historical_and_current_run(test_client)

    report = test_client.get("/api/reports/cfo", headers=auth_headers(test_client)).json()
    metrics = report["metrics"]
    assert metrics["total_transactions"] == 200
    assert metrics["reconciliation"]["run_id"] == run2_id
    assert report["control_context"]["run_id"] == run2_id
    # Cash-flow trend contains only the current run's dates (2026-01-01),
    # not the historical run's dates.
    trend_dates = {row["date"] for row in report["cash_flow_trend"]}
    assert trend_dates == {"2026-01-01"}
    # No expense categories exist in the current run's schema.
    assert report["expense_breakdown"] == []
    # Review workload is scoped to the current run's 40 exceptions.
    assert report["review_workload"]["total"] == 40


def test_alerts_derive_from_current_run(client):
    test_client, _ = client
    run1_id, run2_id = seed_historical_and_current_run(test_client)

    alerts = test_client.get("/api/alerts", headers=auth_headers(test_client)).json()
    messages = [alert["message"] for alert in alerts]
    # Reconciliation rate 80% < 95% -> WARNING; the current run has no
    # HIGH risk, so no high-risk alert for the current run.
    assert any("below 95%" in message for message in messages)
    assert not any("high-risk" in message for message in messages)


class CapturingProvider:
    def __init__(self, captured):
        self.captured = captured

    def answer(self, question, context):
        self.captured.append((question, context))
        return "captured-answer"


def test_copilot_receives_current_run_context(monkeypatch, client):
    test_client, _ = client
    run1_id, run2_id = seed_historical_and_current_run(test_client)

    captured = []
    monkeypatch.setattr(
        "app.api.routes.core.get_provider",
        lambda *args, **kwargs: CapturingProvider(captured),
    )
    response = test_client.post(
        "/api/copilot",
        json={"question": "Summarize the current reconciliation run"},
        headers=auth_headers(test_client),
    )
    assert response.status_code == 200
    assert captured

    context = captured[-1][1]
    # Grounded in the current run, not the whole historical database.
    assert context["reconciliation"]["run_id"] == run2_id
    assert context["total_transactions"] == 200
    records = context.get("reconciliation_records") or []
    assert len(records) == 200
    assert {record["run_id"] for record in records} == {run2_id}
    assert all(record["transaction_id"].startswith("payment-") for record in records)
    # No historical TXN-* rows leak into the AI context.
    assert not any("TXN-" in record["transaction_id"] for record in records)


def test_settings_analytics_identifies_current_run(client):
    test_client, _ = client
    run1_id, run2_id = seed_historical_and_current_run(test_client)

    analytics = test_client.get("/api/analytics", headers=auth_headers(test_client)).json()
    assert analytics["current_run"]["run_id"] == run2_id
    assert analytics["current_run"]["filename"] == "my_new_finance_data_200.csv"
    assert analytics["current_run"]["mode"] == "single_file"
    assert analytics["total_transactions"] == 200
    assert analytics["reconciliation"]["total"] == 200


def test_historical_data_and_runs_are_preserved(client):
    test_client, session_factory = client
    run1_id, run2_id = seed_historical_and_current_run(test_client)

    db = session_factory()
    assert db.query(ReconciliationRun).count() == 2
    assert db.query(ReconciliationResult).filter_by(run_id=run1_id).count() == 1000
    assert db.query(ReconciliationResult).filter_by(run_id=run2_id).count() == 200
    assert db.query(Transaction).count() == 1200
    db.close()

    # The historical run is still reachable through its run_id.
    history = test_client.get(
        f"/api/reconciliation?run_id={run1_id}", headers=auth_headers(test_client)
    ).json()
    assert history["total"] == 1000


def test_rbac_still_works_and_unauthenticated_endpoints_stay_protected(client):
    test_client, _ = client
    run1_id, run2_id = seed_historical_and_current_run(test_client)

    # Unauthenticated protected endpoints are rejected.
    for path in ("/api/dashboard", "/api/transactions", "/api/reconciliation",
                 "/api/risk", "/api/anomalies", "/api/forecast", "/api/alerts",
                 "/api/reports/cfo", "/api/analytics"):
        assert test_client.get(path).status_code == 401, path

    # RBAC: a Finance Analyst is still denied the CFO report (403).
    analyst = auth_headers(test_client, "analyst@demo.com", "AnalystPass1!")
    assert test_client.get("/api/reports/cfo", headers=analyst).status_code == 403
    # Read endpoints remain available to any authenticated user.
    assert test_client.get("/api/risk", headers=analyst).status_code == 200
    assert test_client.get("/api/dashboard", headers=analyst).status_code == 200


def test_run_scoped_financials_are_available_for_import_runs(client):
    """A run whose uploaded schema DOES carry financial dimensions reports
    them available and scoped to that run only."""
    test_client, _ = client
    seed_historical_and_current_run(test_client)

    # A new import with revenue/expense classification becomes the current
    # run and its financials are scoped to it.
    csv = (
        b"transaction_id,date,amount,type,status,settlement_amount\n"
        b"NEW-REV,2026-09-04,1250,revenue,completed,1250\n"
        b"NEW-EXP,2026-09-04,2400,expense,completed,2300\n"
    )
    imported = test_client.post(
        "/api/import",
        files={"file": ("fresh-import.csv", csv, "text/csv")},
        headers=auth_headers(test_client),
    )
    assert imported.status_code == 200
    run_id = imported.json()["run_id"]

    dashboard = test_client.get(
        "/api/dashboard", headers=auth_headers(test_client)
    ).json()
    assert dashboard["reconciliation"]["run_id"] == run_id
    assert dashboard["total_transactions"] == 2
    assert dashboard["financial"]["revenue"]["available"] is True
    assert dashboard["financial"]["revenue"]["value"] == 1250
    assert dashboard["financial"]["expenses"]["available"] is True
    assert dashboard["financial"]["expenses"]["value"] == 2400
    assert dashboard["revenue"] == 1250
    assert dashboard["expenses"] == 2400