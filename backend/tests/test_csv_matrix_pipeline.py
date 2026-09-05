"""End-to-end pipeline validation (Steps 7-13 of the validation plan).

Drives the REAL API (TestClient against the actual app) with the
deterministic generated datasets and compares the results against the
independent oracle, including:
- generated 200-row dataset reproduces the production-verified outcome
  (160 matched / 40 exceptions / Rs.3,575 / 80% / LOW 25 / MEDIUM 15),
- current-run switching A -> B -> C across generated datasets,
- historical runs stay reachable and historical data is never deleted,
- anomaly patterns injected into /api/import datasets are detected,
- reconciliation exceptions and anomalies remain separate concepts,
- RBAC and unauthenticated protection remain enforced.
"""

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

from tests.qa import datasets
from tests.qa.oracle import risk_distribution_expectation, single_file_expectation

USERS = [
    ("admin@demo.com", "DemoPassword123!", "Admin"),
    ("analyst@demo.com", "AnalystPass1!", "Finance Analyst"),
]


@pytest.fixture
def client(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'matrix.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    for email, password, role in USERS:
        session.add(User(email=email, password_hash=hash_password(password), role=role))
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
        "/api/auth/login", json={"email": email, "password": password}
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def upload_single(client, filename, data):
    response = client.post(
        "/api/reconciliation/single-file",
        files={"file": (filename, data, "text/csv")},
        headers=auth_headers(client),
    )
    assert response.status_code == 200
    return response.json()


def import_csv(client, filename, data):
    response = client.post(
        "/api/import",
        files={"file": (filename, data, "text/csv")},
        headers=auth_headers(client),
    )
    assert response.status_code == 200
    return response.json()


def test_generated_200_row_dataset_reproduces_production_verified_numbers(client):
    """A GENERATED 200-row dataset (25 x Rs.83 + 15 x Rs.100 mismatches)
    must produce exactly the production-verified outcome through the real
    pipeline: 160 matched / 40 exceptions / Rs.3,575 / 80% / LOW 25 /
    MEDIUM 15 / HIGH 0 / CRITICAL 0."""
    test_client, _ = client
    rows = datasets.build_rows(
        200,
        mismatch_refs={
            **{f"TXN-{i:06d}": 83 for i in range(160, 185)},
            **{f"TXN-{i:06d}": 100 for i in range(185, 200)},
        },
    )
    data = datasets.rows_to_csv(rows)

    body = upload_single(test_client, "generated_200.csv", data)
    assert body["total"] == 200
    assert body["matched"] == 160
    assert body["mismatch"] == 40
    assert body["exceptions"] == 40
    assert body["match_rate"] == 80
    assert body["variance"] == 3575

    # The independent oracle agrees with the application.
    expected = single_file_expectation(rows)
    assert body["total"] == expected["total"]
    assert body["matched"] == expected["matched"]
    assert body["mismatch"] == expected["mismatch"]
    assert body["variance"] == expected["variance"]

    # Risk distribution matches the oracle exactly.
    dashboard = test_client.get("/api/dashboard", headers=auth_headers(test_client)).json()
    assert dashboard["total_transactions"] == 200
    assert dashboard["risk_distribution"] == {
        "LOW": 25, "MEDIUM": 15, "HIGH": 0, "CRITICAL": 0,
    }
    assert dashboard["risk_distribution"] == risk_distribution_expectation(rows)

    # Exceptions are not anomalies: no HIGH/CRITICAL rows -> no anomaly rows.
    anomalies = test_client.get("/api/anomalies", headers=auth_headers(test_client)).json()
    assert anomalies == []


def test_current_run_switches_across_generated_datasets(client):
    """Upload A (100) -> B (200) -> C (300): the current run must be C while
    A and B stay fully reachable."""
    test_client, session_factory = client
    headers = auth_headers(test_client)

    run_a = upload_single(test_client, "dataset_a.csv", datasets.single_file_csv(100))
    run_b = upload_single(test_client, "dataset_b.csv", datasets.single_file_csv(200))
    run_c = upload_single(test_client, "dataset_c.csv", datasets.single_file_csv(300))

    dashboard = test_client.get("/api/dashboard", headers=headers).json()
    assert dashboard["reconciliation"]["run_id"] == run_c["run_id"]
    assert dashboard["current_run"]["filename"] == "dataset_c.csv"
    assert dashboard["total_transactions"] == 300

    for run_id, size in ((run_a["run_id"], 100), (run_b["run_id"], 200)):
        history = test_client.get(
            f"/api/reconciliation?run_id={run_id}", headers=headers
        ).json()
        assert history["total"] == size, run_id
        txns = test_client.get(
            f"/api/transactions?run_id={run_id}&page=1&page_size=500",
            headers=headers,
        ).json()
        assert txns["total"] == size

    # Historical data is preserved: every run keeps its own reconciliation
    # results. The Transaction table holds one row per reference (upsert
    # semantics - a repeated upload refreshes the latest amount/settlement,
    # it never deletes the earlier runs' results).
    db = session_factory()
    assert db.query(ReconciliationRun).count() == 3
    assert db.query(Transaction).count() == 300  # unique refs across runs
    assert db.query(ReconciliationResult).filter_by(run_id=run_a["run_id"]).count() == 100
    assert db.query(ReconciliationResult).filter_by(run_id=run_b["run_id"]).count() == 200
    assert db.query(ReconciliationResult).filter_by(run_id=run_c["run_id"]).count() == 300
    db.close()


def test_generated_1000_row_dataset_through_api(client):
    test_client, _ = client
    body = upload_single(
        test_client, "dataset_1000.csv", datasets.single_file_csv(1000)
    )
    assert body["total"] == 1000
    assert body["matched"] == 1000
    assert body["match_rate"] == 100

    dashboard = test_client.get("/api/dashboard", headers=auth_headers(test_client)).json()
    assert dashboard["total_transactions"] == 1000


def test_import_anomaly_patterns_are_detected_through_api(client):
    test_client, _ = client
    headers = auth_headers(test_client)

    # Outlier dataset: the injected outlier must surface in /api/anomalies.
    outlier = datasets.build_rows(200, outlier_refs={"TXN-000100"})
    import_csv(test_client, "outliers.csv", datasets.rows_to_csv(outlier))
    anomalies = test_client.get("/api/anomalies", headers=headers).json()
    assert any(
        item["transaction_id"] == "TXN-000100"
        and "z-score" in item["evidence"]
        for item in anomalies
    ), anomalies[:3]

    # Normal dataset imported afterwards becomes the current run and has no
    # anomalies (amounts are normal, merchants spread, no repeats).
    normal = datasets.build_rows(200)
    import_csv(test_client, "normal.csv", datasets.rows_to_csv(normal))
    anomalies = test_client.get("/api/anomalies", headers=headers).json()
    assert anomalies == []


def test_reconciliation_exceptions_and_anomalies_remain_separate(client):
    """40 mismatches (normal amounts) -> 40 reconciliation exceptions but
    zero statistical anomalies through the full pipeline."""
    test_client, _ = client
    rows = datasets.build_rows(
        200,
        mismatch_refs={f"TXN-{i:06d}": 83 for i in range(160, 200)},
    )
    body = upload_single(test_client, "mismatches.csv", datasets.rows_to_csv(rows))
    assert body["exceptions"] == 40

    reconciliation = test_client.get(
        "/api/reconciliation", headers=auth_headers(test_client)
    ).json()
    assert reconciliation["exceptions"] == 40
    anomalies = test_client.get("/api/anomalies", headers=auth_headers(test_client)).json()
    assert anomalies == []


def test_rbac_and_unauthenticated_protection_hold(client):
    test_client, _ = client
    upload_single(test_client, "dataset_a.csv", datasets.single_file_csv(100))

    for path in ("/api/dashboard", "/api/transactions", "/api/reconciliation",
                 "/api/risk", "/api/anomalies", "/api/forecast", "/api/alerts",
                 "/api/reports/cfo", "/api/analytics"):
        assert test_client.get(path).status_code == 401, path

    analyst = auth_headers(test_client, "analyst@demo.com", "AnalystPass1!")
    assert test_client.get("/api/reports/cfo", headers=analyst).status_code == 403
    assert test_client.get("/api/risk", headers=analyst).status_code == 200
    assert test_client.get("/api/dashboard", headers=analyst).status_code == 200