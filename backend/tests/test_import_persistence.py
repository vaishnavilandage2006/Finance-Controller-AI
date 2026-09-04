from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.db import Base, get_db
from app.main import app
from app.models import AuditLog, ReconciliationResult, Transaction, User
from app.core.security import hash_password


def test_new_csv_import_persists_rows_and_derived_records(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'import.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    setup = session_factory()
    setup.add(User(
        email="admin@demo.com",
        password_hash=hash_password("DemoPassword123!"),
        role="Admin",
    ))
    setup.commit()
    setup.close()

    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            login = client.post(
                "/api/auth/login",
                json={"email": "admin@demo.com", "password": "DemoPassword123!"},
            )
            headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
            csv = (
                b"transaction_id,date,amount,type,status,settlement_amount\n"
                b"NEW-CSV-001,2026-09-04,1250,revenue,completed,1250\n"
                b"NEW-CSV-002,2026-09-04,2400,expense,completed,2300\n"
            )
            response = client.post(
                "/api/import",
                files={"file": ("new-finance.csv", csv, "text/csv")},
                headers=headers,
            )
            assert response.status_code == 200
            assert response.json()["imported"] == 2
            run_id = response.json()["run_id"]

            transactions = client.get(
                "/api/transactions?page=1&page_size=10",
                headers=headers,
            ).json()
            transaction_ids = {item["transaction_id"] for item in transactions["items"]}
            assert {"NEW-CSV-001", "NEW-CSV-002"}.issubset(transaction_ids)
            assert client.get("/api/dashboard", headers=headers).json()["total_transactions"] == 2
            assert client.get("/api/analytics", headers=headers).status_code == 200
            assert client.get(f"/api/risk?run_id={run_id}", headers=headers).status_code == 200
            assert client.get(f"/api/reconciliation?run_id={run_id}", headers=headers).json()["total"] == 2
            assert any(
                row["action"] == "CSV_IMPORT"
                for row in client.get("/api/audit", headers=headers).json()
            )

        db = session_factory()
        assert db.query(Transaction).filter(Transaction.transaction_id.like("NEW-CSV-%")).count() == 2
        assert db.query(ReconciliationResult).filter(ReconciliationResult.run_id == run_id).count() == 2
        assert db.query(AuditLog).filter(AuditLog.action == "CSV_IMPORT").count() == 1
        db.close()
    finally:
        app.dependency_overrides.clear()
        engine.dispose()