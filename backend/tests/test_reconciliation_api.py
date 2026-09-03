from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.security import hash_password
from app.db import Base, get_db
from app.main import app
from app.models import (
    AuditLog,
    ReconciliationResult,
    ReviewItem,
    ReconciliationRun,
    Transaction,
    User,
)


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


def auth_headers(client):
    response = client.post(
        "/api/auth/login",
        json={
            "email": "admin@demo.com",
            "password": "DemoPassword123!",
        },
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_login_requires_authentication(client):
    test_client, _ = client
    assert test_client.get("/api/reconciliation").status_code == 401
    assert auth_headers(test_client)["Authorization"].startswith("Bearer ")


def test_multi_file_upload_creates_independent_runs(client):
    test_client, session_factory = client
    headers = auth_headers(test_client)
    files = {
        "bank_file": ("bank.csv", b"bank_reference,bank_amount\nR1,100\n", "text/csv"),
        "ledger_file": ("ledger.csv", b"ledger_reference,ledger_amount\nR1,98\n", "text/csv"),
    }

    first = test_client.post(
        "/api/reconciliation/multi-file",
        files=files,
        headers=headers,
    )
    second = test_client.post(
        "/api/reconciliation/multi-file",
        files=files,
        headers=headers,
    )

    assert first.status_code == 200
    assert second.status_code == 200
    db = session_factory()
    assert db.query(Transaction).filter_by(transaction_id="R1").count() == 1
    results = db.query(ReconciliationResult).filter_by(transaction_id="R1").all()
    reviews = db.query(ReviewItem).filter_by(transaction_id="R1").all()
    assert len(results) == 2
    assert len({result.run_id for result in results}) == 2
    assert len(reviews) == 2
    assert len({review.run_id for review in reviews}) == 2
    assert db.query(AuditLog).filter_by(action="MULTI_FILE_RECONCILIATION").count() == 2
    db.close()


def test_latest_reconciliation_and_review_are_run_scoped(client):
    test_client, session_factory = client
    headers = auth_headers(test_client)
    first = test_client.post(
        "/api/reconciliation/single-file",
        files={"file": ("alpha.csv", b"reference,bank_amount,ledger_amount\nA1,100,90\nA2,100,90\nA3,100,90\n", "text/csv")},
        headers=headers,
    )
    second = test_client.post(
        "/api/reconciliation/single-file",
        files={"file": ("omega.csv", b"reference,bank_amount,ledger_amount\nB1,200,190\n", "text/csv")},
        headers=headers,
    )

    assert first.status_code == 200
    assert second.status_code == 200
    first_run_id = first.json()["run_id"]
    second_run_id = second.json()["run_id"]
    assert first_run_id != second_run_id

    latest = test_client.get("/api/reconciliation", headers=headers)
    assert latest.status_code == 200
    assert latest.json()["run_id"] == second_run_id
    assert latest.json()["total"] == 1
    assert [record["transaction_id"] for record in latest.json()["records"]] == ["B1"]

    history = test_client.get(f"/api/reconciliation?run_id={first_run_id}", headers=headers)
    assert history.json()["total"] == 3
    assert {record["transaction_id"] for record in history.json()["records"]} == {"A1", "A2", "A3"}

    review = test_client.get("/api/review", headers=headers)
    assert {item["transaction_id"] for item in review.json()} == {"B1"}
    assert {item["run_id"] for item in review.json()} == {second_run_id}
    db = session_factory()
    assert db.query(ReconciliationResult).filter_by(run_id=first_run_id).count() == 3
    assert db.query(ReconciliationResult).filter_by(run_id=second_run_id).count() == 1
    db.close()


def test_single_file_upload_allows_missing_date_and_creates_audit(client):
    test_client, session_factory = client
    response = test_client.post(
        "/api/reconciliation/single-file",
        files={
            "file": (
                "single.csv",
                b"reference,bank_amount,ledger_amount\nS1,100,98\n",
                "text/csv",
            )
        },
        headers=auth_headers(test_client),
    )

    assert response.status_code == 200
    db = session_factory()
    transaction = db.query(Transaction).filter_by(transaction_id="S1").one()
    assert transaction.date is None
    assert db.query(ReconciliationResult).filter_by(transaction_id="S1").count() == 1
    assert db.query(ReviewItem).filter_by(transaction_id="S1").count() == 1
    assert db.query(AuditLog).filter_by(action="SINGLE_FILE_RECONCILIATION").count() == 1
    db.close()


def test_single_file_api_reconciles_generic_settled_value_schema(client):
    test_client, _ = client
    mismatches = [50] * 39 + [1625]
    rows = [
        f"{index},payment-{index},{1000 + index},{1000 + index},Merchant,2026-01-01"
        if index < 160
        else f"{index},payment-{index},{1000 + index},{1000 + index - mismatches[index - 160]},Merchant,2026-01-01"
        for index in range(200)
    ]
    data = (
        "id,payment_reference,gross_amount,settled_value,merchant_name,transaction_date\n"
        + "\n".join(rows)
        + "\n"
    ).encode()
    response = test_client.post(
        "/api/reconciliation/single-file",
        files={"file": ("completely-new-name.csv", data, "text/csv")},
        headers=auth_headers(test_client),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 200
    assert body["matched"] == 160
    assert body["mismatch"] == 40
    assert body["partial"] == 0
    assert body["exceptions"] == 40
    assert body["match_rate"] == 80
    assert body["variance"] == 3575


def test_review_action_updates_status_and_audit_log(client):
    test_client, session_factory = client
    headers = auth_headers(test_client)
    upload = test_client.post(
        "/api/reconciliation/single-file",
        files={
            "file": (
                "single.csv",
                b"reference,bank_amount,ledger_amount\nS1,100,98\n",
                "text/csv",
            )
        },
        headers=headers,
    )
    assert upload.status_code == 200
    review = test_client.get("/api/review", headers=headers)
    item_id = review.json()[0]["id"]
    action = test_client.post(
        f"/api/review/{item_id}/action",
        json={"action": "INVESTIGATE", "note": "Check settlement evidence"},
        headers=headers,
    )

    assert action.status_code == 200
    assert action.json()["new_status"] == "UNDER_REVIEW"
    db = session_factory()
    assert db.query(ReviewItem).filter_by(id=item_id).one().status == "UNDER_REVIEW"
    assert db.query(AuditLog).filter_by(action="REVIEW_INVESTIGATE").count() == 1
    db.close()


def test_scenario_uses_deterministic_financial_values(client):
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
                currency="INR",
            ),
            Transaction(
                transaction_id="EXP-1",
                date="2026-01-01",
                amount=400,
                type="expense",
                status="completed",
                fee=0,
                refund_amount=0,
                currency="INR",
            ),
        ]
    )
    db.commit()
    db.close()

    response = test_client.post(
        "/api/scenarios",
        json={"revenue_change": -10},
        headers=auth_headers(test_client),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["projected_revenue"] == 900
    assert body["projected_expenses"] == 400
    assert body["projected_profit"] == 350
    assert body["cash_impact"] == -100


def test_dashboard_uses_latest_reconciliation_run(client):
    test_client, session_factory = client
    db = session_factory()
    db.add(
        ReconciliationRun(
            run_id="REC-LATEST",
            mode="single_file",
            filename="user-upload.csv",
            user_email="admin@demo.com",
            bank_filename="",
            ledger_filename="",
            settlement_filename=None,
            total=4,
            matched=3,
            partial=0,
            unmatched=0,
            duplicate=0,
            exceptions=1,
            match_rate=75,
            total_variance=12.5,
        )
    )
    db.commit()
    db.close()

    body = test_client.get(
        "/api/dashboard",
        headers=auth_headers(test_client),
    ).json()

    assert body["reconciliation_rate"] == 75
    assert body["reconciliation"] == {
        "total": 4,
        "matched": 3,
        "partial": 0,
        "mismatch": 1,
        "unmatched": 0,
        "duplicate": 0,
        "exceptions": 1,
        "match_rate": 75.0,
        "variance": 12.5,
        "run_id": "REC-LATEST",
        "mode": "single_file",
        "created_at": body["reconciliation"]["created_at"],
    }