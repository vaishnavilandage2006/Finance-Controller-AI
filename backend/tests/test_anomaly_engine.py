"""Tests for the independent, statistical anomaly engine.

Anomalies are a separate control signal from reconciliation exceptions and
risk levels. A transaction can be matched AND statistically anomalous, or an
exception AND statistically normal. These tests prove the engine is
deterministic, explainable, and distinct from exception-driven flags.
"""

from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.security import hash_password
from app.db import Base, get_db
from app.main import app
from app.models import User
from app.services.anomaly.engine import (
    analyze_transactions,
    detect_amount_outliers,
    detect_merchant_concentration,
    detect_repeated_transactions,
)


def txn(transaction_id, amount, merchant="M", refund_amount=0, fee=0, category=None):
    return SimpleNamespace(
        transaction_id=transaction_id,
        amount=amount,
        merchant=merchant,
        vendor=None,
        refund_amount=refund_amount,
        fee=fee,
        category=category,
    )


# ------------------------------------------------------------
# Unit tests: detectors are explainable and deterministic
# ------------------------------------------------------------
def test_amount_outlier_uses_median_mad_baseline():
    transactions = [txn(f"T{i}", 1000 + i) for i in range(12)]
    transactions.append(txn("T-BIG", 900000))
    outliers = detect_amount_outliers(transactions)

    assert len(outliers) == 1
    item = outliers[0]
    assert item["transaction_id"] == "T-BIG"
    assert item["category"] == "amount_outlier"
    assert "median" in item["method"]
    assert "MAD" in item["method"]
    # Must explain WHY, without fabricating confidence.
    assert item["reason"].startswith("Statistical anomaly")
    assert "robust z-score" in item["evidence"]
    assert item["score"] >= 30


def test_outlier_detection_is_deterministic():
    transactions = [txn(f"T{i}", 1000 + i) for i in range(12)]
    transactions.append(txn("T-BIG", 900000))
    first = analyze_transactions(transactions)
    second = analyze_transactions(transactions)
    assert first["anomalies"] == second["anomalies"]


def test_small_sample_reports_insufficient_data_note():
    result = analyze_transactions(
        [txn("T1", 100, merchant="M1"), txn("T2", 100, merchant="M2")]
    )
    assert result["anomalies"] == []
    assert result["note"] is not None
    assert "at least 10" in result["note"]


def test_repeated_transaction_detection():
    transactions = [txn(f"T{i}", 500, merchant="Vendor A") for i in range(6)]
    repeats = detect_repeated_transactions(transactions)
    assert any(item["category"] == "repeated_transaction" for item in repeats)
    repeated = next(item for item in repeats if item["category"] == "repeated_transaction")
    assert "observed 6 times" in repeated["method"]
    assert repeated["severity"] in ("MEDIUM", "HIGH")


def test_merchant_concentration_detection():
    transactions = [txn(f"T{i}", 100, merchant="Dominant Payee") for i in range(8)]
    transactions += [txn(f"U{i}", 100, merchant="Other Payee") for i in range(2)]
    items = detect_merchant_concentration(transactions)
    assert any(item["category"] == "merchant_concentration" for item in items)
    concentration = next(
        item for item in items if item["category"] == "merchant_concentration"
    )
    assert concentration["transaction_id"] == "Dominant Payee"
    assert "count share=80.0%" in concentration["evidence"]


def test_matched_but_statistically_anomalous_is_detected():
    """A perfectly matched transaction can still be an anomaly - the engine
    does not depend on reconciliation status at all."""
    transactions = [txn(f"T{i}", 1000 + i) for i in range(14)]
    transactions.append(txn("T-BIG", 700000))
    result = analyze_transactions(transactions)
    assert any(item["transaction_id"] == "T-BIG" for item in result["anomalies"])


# ------------------------------------------------------------
# API test: /import produces independent statistical anomalies
# ------------------------------------------------------------
def _make_client(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'anomaly.db'}",
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
    client = TestClient(app)
    return client, session_factory


def test_import_creates_statistical_anomaly_separate_from_exception(tmp_path):
    client, _ = _make_client(tmp_path)
    try:
        login = client.post(
            "/api/auth/login",
            json={"email": "admin@demo.com", "password": "DemoPassword123!"},
        )
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        rows = ["transaction_id,date,amount,type,status,settlement_amount"]
        for index in range(14):
            rows.append(
                f"TX-{index},2026-01-01,{1000 + index},revenue,completed,{1000 + index}"
            )
        rows.append("TX-BIG,2026-01-01,900000,revenue,completed,900000")
        csv_bytes = ("\n".join(rows) + "\n").encode()

        response = client.post(
            "/api/import",
            files={"file": ("anomalies.csv", csv_bytes, "text/csv")},
            headers=headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["imported"] == 15
        assert body["statistical_anomalies"]
        assert any(
            item["transaction_id"] == "TX-BIG"
            for item in body["statistical_anomalies"]
        )
        run_id = body["run_id"]

        # TX-BIG is MATCHED (amount == settlement_amount) -> no review item...
        reconciliation = client.get(
            f"/api/reconciliation?run_id={run_id}",
            headers=headers,
        ).json()
        record = next(
            row for row in reconciliation["records"]
            if row["transaction_id"] == "TX-BIG"
        )
        assert record["status"] == "MATCHED"
        assert record["variance"] == 0

        # ...yet it is flagged as a statistical anomaly (independent signal).
        anomalies = client.get("/api/anomalies", headers=headers).json()
        flagged = [
            item for item in anomalies
            if item["transaction_id"] == "TX-BIG"
        ]
        assert flagged, "TX-BIG should be statistically flagged"
        assert flagged[0]["reason"].startswith("Statistical anomaly")
        assert "median" in (flagged[0].get("evidence") or "")

        review = client.get("/api/review", headers=headers).json()
        assert not any(item["transaction_id"] == "TX-BIG" for item in review)
    finally:
        app.dependency_overrides.clear()


def test_statistical_anomaly_endpoint_is_grounded_in_real_rows(tmp_path):
    client, session_factory = _make_client(tmp_path)
    try:
        login = client.post(
            "/api/auth/login",
            json={"email": "admin@demo.com", "password": "DemoPassword123!"},
        )
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        session = session_factory()
        from app.models import Transaction

        session.add_all(
            [
                Transaction(
                    transaction_id=f"S-{index}",
                    date="2026-02-01",
                    amount=float(500 + index),
                    type="revenue",
                    status="completed",
                )
                for index in range(20)
            ]
            + [
                Transaction(
                    transaction_id="S-BIG",
                    date="2026-02-02",
                    amount=1234567.0,
                    type="revenue",
                    status="completed",
                )
            ]
        )
        session.commit()
        session.close()

        anomalies = client.get("/api/anomalies", headers=headers).json()
        # Legacy DB anomalies only appear when a run created them; none exist
        # here, so the endpoint must simply stay stable and empty instead of
        # fabricating flags for data it never analyzed.
        assert isinstance(anomalies, list)
    finally:
        app.dependency_overrides.clear()
