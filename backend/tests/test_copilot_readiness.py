"""Regression tests for the evaluator-readiness Copilot pass.

Covers natural-language intent handling ("largest/biggest exception",
"highest variance", review-first), dynamic largest-exception answers,
grouped exception causes, the deterministic-data disclosure, and the
requirement that Copilot risk context never leaks stale rows from a
previous reconciliation run.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.security import hash_password
from app.db import Base, get_db
from app.main import app
from app.models import User

SAMPLE = Path(__file__).resolve().parents[2] / "database" / "sample_data"

DISCLOSURE = "generated deterministically from the reconciliation data"


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
        yield test_client
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


def ask(client, question):
    response = client.post(
        "/api/copilot",
        json={"question": question},
        headers=auth_headers(client),
    )
    assert response.status_code == 200
    return response.json()["answer"]


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


def post_multi_file(client):
    def upload(name):
        return (name, (SAMPLE / name).read_bytes(), "text/csv")

    response = client.post(
        "/api/reconciliation/multi-file",
        files={
            "bank_file": upload("bank_1000.csv"),
            "ledger_file": upload("ledger_1000.csv"),
            "settlement_file": upload("settlement_1000.csv"),
        },
        headers=auth_headers(client),
    )
    assert response.status_code == 200
    return response.json()


def finance_largest_reference(body):
    return max(body["records"], key=lambda r: r["variance"])["reference"]


# ------------------------------------------------------------
# Largest-exception phrasing variants (dynamic, never hardcoded)
# ------------------------------------------------------------
@pytest.mark.parametrize(
    "question",
    [
        "What is the largest reconciliation exception?",
        "What is the biggest exception?",
        "Which exception has the highest variance?",
    ],
)
def test_copilot_largest_exception_phrasings_return_live_transaction(client, question):
    body = post_single(client, "finance_transactions.csv", finance_csv_bytes())
    assert body["matched"] == 972 and body["mismatch"] == 28
    largest_id = finance_largest_reference(body)

    answer = ask(client, question)
    assert "Largest Reconciliation Exception" in answer
    assert largest_id in answer
    assert "Risk level: HIGH" in answer, answer
    assert "Recommended controller action" in answer
    assert DISCLOSURE in answer


def test_copilot_review_first_and_action_plan_are_grounded(client):
    body = post_single(client, "finance_transactions.csv", finance_csv_bytes())
    largest_id = finance_largest_reference(body)

    review_first = ask(client, "Which exceptions should I review first?")
    assert largest_id in review_first
    assert "Recommended first action" in review_first
    assert "Risk:" in review_first

    plan = ask(client, "Give me today's controller action plan")
    assert largest_id in plan
    assert "Risk level: HIGH" in plan
    assert DISCLOSURE in plan


# ------------------------------------------------------------
# Grouped exception causes (only categories present in the data)
# ------------------------------------------------------------
def test_copilot_grouped_causes_report_only_existing_categories(client):
    body = post_single(client, "finance_transactions.csv", finance_csv_bytes())
    assert body["mismatch"] == 28

    answer = ask(client, "Why are there reconciliation exceptions?")
    assert "Exception cause grouping:" in answer
    assert "Settlement amount mismatch: 28" in answer
    # Per-record reasons are preserved alongside the grouping.
    assert "Observed exception reasons:" in answer
    # Categories absent from this dataset must not be reported.
    assert "Missing settlement" not in answer
    assert "Missing reference" not in answer
    assert DISCLOSURE in answer


# ------------------------------------------------------------
# Disclosure on every answer; no fabrication for unknown ids
# ------------------------------------------------------------
def test_copilot_disclosure_present_on_every_answer(client):
    post_single(client, "finance_transactions.csv", finance_csv_bytes())
    for question in [
        "Show high-risk transactions",
        "What is the current reconciliation rate?",
        "What are the most urgent finance issues?",
    ]:
        assert DISCLOSURE in ask(client, question)


def test_copilot_does_not_fabricate_for_unknown_transaction(client):
    post_single(client, "finance_transactions.csv", finance_csv_bytes())
    answer = ask(client, "Why is TXN-999999 an exception?")
    assert "TXN-999999" not in answer


# ------------------------------------------------------------
# Clean-run behavior: no exceptions -> clear, consistent answers
# ------------------------------------------------------------
def test_copilot_clean_run_reports_no_exceptions_and_no_stale_risk(client):
    body = post_multi_file(client)
    assert body["summary"]["matched"] == 1000

    answer = ask(client, "What is the largest reconciliation exception?")
    assert "No reconciliation exceptions" in answer

    risk_answer = ask(client, "Show high-risk transactions")
    assert "No risk assessment records" in risk_answer


# ------------------------------------------------------------
# Copilot risk context is scoped to the current reconciliation run
# ------------------------------------------------------------
def test_copilot_risk_context_is_current_run_scoped(client):
    post_single(client, "finance_transactions.csv", finance_csv_bytes())
    second = post_single(client, "synthetic-200.csv", synthetic_200_bytes())
    assert second["matched"] == 160

    answer = ask(client, "Show high-risk transactions")
    assert "payment-199" in answer
    assert "TXN-" not in answer, answer


# ------------------------------------------------------------
# Authentication is preserved on the Copilot endpoint
# ------------------------------------------------------------
def test_copilot_requires_authentication(client):
    response = client.post("/api/copilot", json={"question": "hello"})
    assert response.status_code == 401
