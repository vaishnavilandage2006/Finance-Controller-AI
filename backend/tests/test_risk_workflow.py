"""Regression tests for the runtime exception-risk engine.

Every reconciliation run scores its own exceptions (materiality-aware),
writes run-scoped RiskAssessment rows via the 'source_run:<run_id>' marker,
creates Anomaly rows only for HIGH/CRITICAL exceptions, and exposes
GET /api/risk?run_id= and GET /api/anomalies?run_id=.
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
    Anomaly,
    AuditLog,
    ReconciliationResult,
    ReconciliationRun,
    ReviewItem,
    RiskAssessment,
    Transaction,
    User,
)
from app.services.risk.engine import assess_exception, run_marker

SAMPLE = Path(__file__).resolve().parents[2] / "database" / "sample_data"


@pytest.fixture
def client(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
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


def auth_headers(client, email="admin@demo.com", password="DemoPassword123!"):
    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def run_risk_rows(db, run_id):
    marker = run_marker(run_id)
    return (
        db.query(RiskAssessment)
        .filter(RiskAssessment.risk_factors.like(f"%{marker}%"))
        .all()
    )


def run_anomaly_rows(db, run_id):
    return (
        db.query(Anomaly)
        .filter(Anomaly.evidence.like(f"%Run {run_id}%"))
        .all()
    )


def finance_csv_bytes():
    return (SAMPLE / "finance_transactions.csv").read_bytes()


def synthetic_200_bytes():
    mismatches = [50] * 39 + [1625]
    rows = [
        f"{i},payment-{i},{1000 + i},{1000 + i},Merchant,2026-01-01"
        if i < 160
        else f"{i},payment-{i},{1000 + i},{1000 + i - mismatches[i - 160]},Merchant,2026-01-01"
        for i in range(200)
    ]
    return (
        "id,payment_reference,gross_amount,settled_value,merchant_name,transaction_date\n"
        + "\n".join(rows)
        + "\n"
    ).encode()


def post_single(client, filename, data):
    response = client.post(
        "/api/reconciliation/single-file",
        files={"file": (filename, data, "text/csv")},
        headers=auth_headers(client),
    )
    assert response.status_code == 200
    return response.json()


# ------------------------------------------------------------
# A. Real 1000-row finance_transactions.csv
# ------------------------------------------------------------
def test_1000_row_dataset_creates_28_run_scoped_risk_assessments(client):
    test_client, session_factory = client
    body = post_single(test_client, "finance_transactions.csv", finance_csv_bytes())
    run_id = body["run_id"]
    assert body["total"] == 1000
    assert body["matched"] == 972
    assert body["mismatch"] == 28

    db = session_factory()
    risk_rows = run_risk_rows(db, run_id)
    assert len(risk_rows) == 28

    exception_ids = {
        record["reference"] for record in body["records"] if record["status"] != "MATCHED"
    }
    matched_ids = {
        record["reference"] for record in body["records"] if record["status"] == "MATCHED"
    }
    assert len(exception_ids) == 28
    assert {row.transaction_id for row in risk_rows} == exception_ids

    # Matched rows are never scored as exceptions of this run.
    for marker_row in db.query(RiskAssessment).all():
        assert marker_row.transaction_id not in matched_ids or run_marker(run_id) not in (marker_row.risk_factors or "")

    # Largest financial exception must not be LOW (materiality alignment).
    largest = max(body["records"], key=lambda r: r["variance"])
    largest_row = next(row for row in risk_rows if row.transaction_id == largest["reference"])
    assert largest_row.risk_level in ("HIGH", "CRITICAL"), (largest["reference"], largest_row.risk_level)
    # Marker stored inside risk_factors for run isolation.
    factors = json.loads(largest_row.risk_factors)
    assert any(str(f).startswith("source_run:") for f in factors)

    # HIGH/CRITICAL exception anomalies remain present, and statistical
    # anomalies detected from the uploaded dataset may be additional rows.
    anomaly_rows = run_anomaly_rows(db, run_id)
    high_count = sum(1 for row in risk_rows if row.risk_level in ("HIGH", "CRITICAL"))
    anomaly_ids = {a.transaction_id for a in anomaly_rows}
    high_ids = {row.transaction_id for row in risk_rows if row.risk_level in ("HIGH", "CRITICAL")}
    assert len(anomaly_rows) >= high_count >= 1
    assert high_ids <= anomaly_ids
    db.close()

    # GET /api/risk?run_id= returns the run's rows, enriched and marker-free.
    risk_payload = test_client.get(f"/api/risk?run_id={run_id}", headers=auth_headers(test_client)).json()
    assert len(risk_payload) == 28
    assert {item["run_id"] for item in risk_payload} == {run_id}
    assert all(item["variance"] is not None for item in risk_payload)
    assert all("source_run" not in json.dumps(item["risk_factors"]) for item in risk_payload)
    largest_payload = next(item for item in risk_payload if item["transaction_id"] == largest["reference"])
    assert largest_payload["risk_level"] in ("HIGH", "CRITICAL")

    anomalies_payload = test_client.get(f"/api/anomalies?run_id={run_id}", headers=auth_headers(test_client)).json()
    assert len(anomalies_payload) == len(anomaly_rows)


# ------------------------------------------------------------
# B. 200-row synthetic dataset
# ------------------------------------------------------------
def test_200_row_dataset_creates_40_run_scoped_risk_assessments(client):
    test_client, session_factory = client
    body = post_single(test_client, "completely-new-name.csv", synthetic_200_bytes())
    run_id = body["run_id"]
    assert body["matched"] == 160
    assert body["mismatch"] == 40

    db = session_factory()
    risk_rows = run_risk_rows(db, run_id)
    assert len(risk_rows) == 40
    exception_ids = {r["reference"] for r in body["records"] if r["status"] != "MATCHED"}
    assert {row.transaction_id for row in risk_rows} == exception_ids

    # The one ~1,625 INR exception (payment-199) is HIGH and becomes an anomaly.
    high_row = next(row for row in risk_rows if row.transaction_id == "payment-199")
    assert high_row.risk_level == "HIGH"
    anomaly_rows = run_anomaly_rows(db, run_id)
    assert {a.transaction_id for a in anomaly_rows} == {"Merchant", "payment-199"}
    assert next(a for a in anomaly_rows if a.transaction_id == "payment-199").severity == "HIGH"
    db.close()


# ------------------------------------------------------------
# C. Multi-file 1000-row dataset (0 exceptions -> 0 risk/anomaly)
# ------------------------------------------------------------
def test_multi_file_1000_row_fixtures_create_no_risk_or_anomalies(client):
    test_client, session_factory = client

    def upload(name):
        return (name, (SAMPLE / name).read_bytes(), "text/csv")

    response = test_client.post(
        "/api/reconciliation/multi-file",
        files={
            "bank_file": upload("bank_1000.csv"),
            "ledger_file": upload("ledger_1000.csv"),
            "settlement_file": upload("settlement_1000.csv"),
        },
        headers=auth_headers(test_client),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["matched"] == 1000
    run_id = body["run_id"]

    db = session_factory()
    assert len(run_risk_rows(db, run_id)) == 0
    assert len(run_anomaly_rows(db, run_id)) == 0
    db.close()
    assert test_client.get(f"/api/risk?run_id={run_id}", headers=auth_headers(test_client)).json() == []
    assert test_client.get(f"/api/anomalies?run_id={run_id}", headers=auth_headers(test_client)).json() == []


# ------------------------------------------------------------
# D. Materiality bands
# ------------------------------------------------------------
def test_assess_exception_materiality_bands():
    score, level, factors = assess_exception("T1", amount=20000, settlement_amount=19999.5, variance=0.5)
    assert level == "LOW"

    score, level, factors = assess_exception("T2", amount=5000, settlement_amount=4900, variance=100)
    assert level == "MEDIUM"

    # A genuine ~1,436 INR exception must never remain LOW (the old seed rules
    # rated it LOW 25).
    score, level, factors = assess_exception("T3", amount=23940.83, settlement_amount=22504.38, variance=1436.45)
    assert level in ("HIGH", "CRITICAL")
    assert score >= 60

    score, level, factors = assess_exception("T4", amount=1500000, settlement_amount=1400000, variance=100000)
    assert level == "CRITICAL"
    assert score == 100


# ------------------------------------------------------------
# E. Run isolation
# ------------------------------------------------------------
def test_risk_is_isolated_per_reconciliation_run(client):
    test_client, session_factory = client
    first = post_single(test_client, "finance_transactions.csv", finance_csv_bytes())
    second = post_single(test_client, "finance_transactions.csv", finance_csv_bytes())
    assert first["run_id"] != second["run_id"]

    db = session_factory()
    assert len(run_risk_rows(db, first["run_id"])) == 28
    assert len(run_risk_rows(db, second["run_id"])) == 28
    assert len(run_anomaly_rows(db, first["run_id"])) >= 1
    assert len(run_anomaly_rows(db, second["run_id"])) >= 1
    db.close()

    first_payload = test_client.get(f"/api/risk?run_id={first['run_id']}", headers=auth_headers(test_client)).json()
    second_payload = test_client.get(f"/api/risk?run_id={second['run_id']}", headers=auth_headers(test_client)).json()
    assert {item["run_id"] for item in first_payload} == {first["run_id"]}
    assert {item["run_id"] for item in second_payload} == {second["run_id"]}


# ------------------------------------------------------------
# F. Review Center association + authorization
# ------------------------------------------------------------
def test_review_items_show_run_matched_risk_and_actions_stay_authorized(client):
    test_client, session_factory = client
    body = post_single(test_client, "finance_transactions.csv", finance_csv_bytes())
    run_id = body["run_id"]

    db = session_factory()
    risk_rows = run_risk_rows(db, run_id)
    risk_by_tx = {row.transaction_id: row for row in risk_rows}
    db.close()

    review = test_client.get(f"/api/review?run_id={run_id}", headers=auth_headers(test_client)).json()
    assert len(review) == 28
    for item in review:
        expected = risk_by_tx[item["transaction_id"]]
        assert item["risk_score"] == expected.risk_score
        assert item["risk_level"] == expected.risk_level
        assert all(not str(f).startswith("source_run:") for f in item["risk_factors"])

    # Controller action still works for Admin and still audits.
    item_id = review[0]["id"]
    action = test_client.post(
        f"/api/review/{item_id}/action",
        json={"action": "APPROVE", "note": "risk workflow test"},
        headers=auth_headers(test_client),
    )
    assert action.status_code == 200
    assert action.json()["new_status"] == "APPROVED"
    db = session_factory()
    assert db.query(AuditLog).filter_by(action="REVIEW_APPROVE").count() == 1
    db.close()

    # A non-approver role is denied (403) and an unauthenticated call is 401.
    db = session_factory()
    db.add(
        User(
            email="analyst@demo.com",
            password_hash=hash_password("DemoPassword123!"),
            role="Finance Analyst",
        )
    )
    db.commit()
    db.close()
    analyst = auth_headers(test_client, email="analyst@demo.com")
    denied = test_client.post(
        f"/api/review/{item_id}/action",
        json={"action": "APPROVE"},
        headers=analyst,
    )
    assert denied.status_code == 403
    assert test_client.get("/api/risk").status_code == 401
    # Read endpoints stay available to any authenticated user.
    assert test_client.get("/api/risk", headers=analyst).status_code == 200
    assert test_client.get(f"/api/review?run_id={run_id}", headers=analyst).status_code == 200


# ------------------------------------------------------------
# G. Latest-run scoping (run-scoping UI pass)
# ------------------------------------------------------------
def test_dashboard_high_risk_count_is_scoped_to_latest_run(client):
    test_client, session_factory = client
    run1 = post_single(test_client, "finance_transactions.csv", finance_csv_bytes())
    dash_after_run1 = test_client.get("/api/dashboard", headers=auth_headers(test_client)).json()
    assert dash_after_run1["reconciliation"]["run_id"] == run1["run_id"]
    assert dash_after_run1["high_risk"] == 9  # finance run: 9 rows >= 61

    run2 = post_single(test_client, "completely-new-name.csv", synthetic_200_bytes())
    dash = test_client.get("/api/dashboard", headers=auth_headers(test_client)).json()
    assert dash["reconciliation"]["run_id"] == run2["run_id"]
    # The count CHANGES with the latest run: only run2's HIGH row counts.
    # (A DB-wide count of 9 + 1 = 10 would fail here.)
    db = session_factory()
    run2_high = sum(
        1 for r in run_risk_rows(db, run2["run_id"]) if r.risk_score >= 61
    )
    db.close()
    assert run2_high == 1
    assert dash["high_risk"] == run2_high == 1

    # /api/risk?run_id and /api/anomalies?run_id stay cross-run clean.
    risk1 = test_client.get(
        f"/api/risk?run_id={run1['run_id']}", headers=auth_headers(test_client)
    ).json()
    risk2 = test_client.get(
        f"/api/risk?run_id={run2['run_id']}", headers=auth_headers(test_client)
    ).json()
    assert len(risk1) == 28 and {r["run_id"] for r in risk1} == {run1["run_id"]}
    assert len(risk2) == 40 and {r["run_id"] for r in risk2} == {run2["run_id"]}
    assert not ({r["transaction_id"] for r in risk1} & {r["transaction_id"] for r in risk2})
    assert {r["run_id"] for r in risk1} & {r["run_id"] for r in risk2} == set()

    anom1 = test_client.get(
        f"/api/anomalies?run_id={run1['run_id']}", headers=auth_headers(test_client)
    ).json()
    anom2 = test_client.get(
        f"/api/anomalies?run_id={run2['run_id']}", headers=auth_headers(test_client)
    ).json()
    assert len(anom1) >= 9
    assert {a["transaction_id"] for a in anom2} == {"Merchant", "payment-199"}


def test_default_review_follows_latest_run_with_its_own_risk(client):
    test_client, session_factory = client
    run1 = post_single(test_client, "finance_transactions.csv", finance_csv_bytes())
    run2 = post_single(test_client, "completely-new-name.csv", synthetic_200_bytes())

    # Default /api/review (no run_id) must follow the LATEST run, not fall back
    # to stale items/risk from the earlier run.
    default_review = test_client.get("/api/review", headers=auth_headers(test_client)).json()
    assert len(default_review) == 40
    assert {item["run_id"] for item in default_review} == {run2["run_id"]}
    assert {item["transaction_id"] for item in default_review} >= {"payment-199"}

    explicit = test_client.get(
        f"/api/review?run_id={run2['run_id']}", headers=auth_headers(test_client)
    ).json()
    assert default_review == explicit

    # The run2-scoped risk values (not run1's) are what the Review Center shows.
    risk2 = {
        r["transaction_id"]: r
        for r in test_client.get(
            f"/api/risk?run_id={run2['run_id']}", headers=auth_headers(test_client)
        ).json()
    }
    payment199 = next(item for item in default_review if item["transaction_id"] == "payment-199")
    assert payment199["risk_level"] == risk2["payment-199"]["risk_level"] == "HIGH"
    assert payment199["risk_score"] == risk2["payment-199"]["risk_score"]

    # Sanity: run1 risk is NOT the run2 dataset's risk (different exception ids).
    risk1_ids = {
        r["transaction_id"]
        for r in test_client.get(
            f"/api/risk?run_id={run1['run_id']}", headers=auth_headers(test_client)
        ).json()
    }
    assert "payment-199" not in risk1_ids
