"""Tests for hardened CSV import validation and upload size guards.

The existing valid CSV contract must keep working while malicious or broken
files (formula injection, duplicate ids, extreme/NaN numbers, oversized
uploads) are rejected with clear errors.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.security import hash_password
from app.db import Base, get_db
from app.main import app
from app.models import User
from app.services.csv.processor import validate_csv

VALID_HEADER = b"transaction_id,date,amount,type,status"


def rows_for(extra_rows):
    return VALID_HEADER + b"\n" + extra_rows


# ------------------------------------------------------------
# Unit tests on validate_csv
# ------------------------------------------------------------
def test_valid_csv_still_parses():
    rows, errors = validate_csv(
        rows_for(b"T1,2026-01-01,10,revenue,completed\nT2,2026-01-02,-5,expense,completed\n")
    )
    assert len(rows) == 2 and not errors


def test_formula_injection_is_rejected():
    csv_bytes = rows_for(
        b"T1,2026-01-01,10,revenue,completed,=2+5\n"
    )
    rows, errors = validate_csv(
        b"transaction_id,date,amount,type,status,merchant\n"
        + b"T1,2026-01-01,10,revenue,completed,=cmd|' /C calc'!A0\n"
    )
    assert errors and any("formula" in error for error in errors)


def test_formula_injection_plus_at_and_dash_forms():
    for leader in (b"@SUM(A1)", b"-cmd|' /C powershell'!A0", b"\t=1+1"):
        csv_bytes = (
            b"transaction_id,date,amount,type,status,category\n"
            + b"T1,2026-01-01,10,revenue,completed," + leader + b"\n"
        )
        _, errors = validate_csv(csv_bytes)
        assert errors, leader


def test_negative_amounts_and_dates_are_not_formula_flags():
    rows, errors = validate_csv(
        rows_for(
            b"T1,2026-01-01,-125.5,expense,completed\n"
            b"T2,-2026-01-01,10,revenue,completed\n"
        )
    )
    # Row 2 has an invalid date, but must never be reported as formula injection.
    assert errors
    assert not any("formula" in error for error in errors)


def test_duplicate_transaction_ids_rejected():
    _, errors = validate_csv(
        rows_for(b"T1,2026-01-01,10,revenue,completed\nT1,2026-01-02,20,expense,completed\n")
    )
    assert any("duplicate transaction_id 'T1'" in error for error in errors)


def test_extreme_and_non_finite_amounts_rejected():
    _, errors = validate_csv(rows_for(b"T1,2026-01-01,1e15,revenue,completed\n"))
    assert errors and any("magnitude" in error for error in errors)

    _, errors = validate_csv(rows_for(b"T1,2026-01-01,nan,revenue,completed\n"))
    assert errors

    _, errors = validate_csv(rows_for(b"T1,2026-01-01,inf,revenue,completed\n"))
    assert errors


def test_invalid_fee_and_refund_values_rejected():
    _, errors = validate_csv(
        b"transaction_id,date,amount,type,status,fee,refund_amount\n"
        b"T1,2026-01-01,10,revenue,completed,abc,0\n"
    )
    assert errors and any("fee" in error for error in errors)

    _, errors = validate_csv(
        b"transaction_id,date,amount,type,status,fee,refund_amount\n"
        b"T1,2026-01-01,10,revenue,completed,1e15,0\n"
    )
    assert errors and any("fee" in error and "magnitude" in error for error in errors)


def test_oversized_file_rejected():
    rows, errors = validate_csv(b"x" * (10 * 1024 * 1024 + 1))
    assert not rows and errors


# ------------------------------------------------------------
# API tests
# ------------------------------------------------------------
@pytest.fixture
def client(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'csv.db'}",
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
        yield test_client
    app.dependency_overrides.clear()
    engine.dispose()


def auth_headers(client):
    response = client.post(
        "/api/auth/login",
        json={"email": "admin@demo.com", "password": "DemoPassword123!"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_import_rejects_formula_injection_without_importing(client):
    csv_bytes = (
        b"transaction_id,date,amount,type,status,merchant\n"
        b"T1,2026-01-01,100,revenue,completed,=HYPERLINK(\"http://evil\")\n"
    )
    response = client.post(
        "/api/import",
        files={"file": ("evil.csv", csv_bytes, "text/csv")},
        headers=auth_headers(client),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["imported"] == 0
    assert any("formula" in error for error in body["errors"])


def test_import_rejects_duplicate_ids_without_importing(client):
    csv_bytes = rows_for(
        b"T1,2026-01-01,100,revenue,completed\nT1,2026-01-02,200,expense,completed\n"
    )
    response = client.post(
        "/api/import",
        files={"file": ("dupes.csv", csv_bytes, "text/csv")},
        headers=auth_headers(client),
    )
    body = response.json()
    assert body["imported"] == 0
    assert any("duplicate transaction_id" in error for error in body["errors"])


def test_single_file_upload_rejects_oversized_csv(client):
    block = b"R1,100\n" * 1000  # ~7 KB
    oversized = b"reference,amount\n" + block * 3000  # ~21 MB
    response = client.post(
        "/api/reconciliation/single-file",
        files={"file": ("huge.csv", oversized, "text/csv")},
        headers=auth_headers(client),
    )
    assert response.status_code == 413


def test_reconciliation_still_accepts_valid_csv_after_hardening(client):
    csv_bytes = b"reference,amount,settlement_amount,merchant\nR1,100,90,Acme\n"
    response = client.post(
        "/api/reconciliation/single-file",
        files={"file": ("ok.csv", csv_bytes, "text/csv")},
        headers=auth_headers(client),
    )
    assert response.status_code == 200
    assert response.json()["total"] == 1
