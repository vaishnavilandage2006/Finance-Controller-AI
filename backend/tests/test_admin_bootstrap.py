from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.core.bootstrap import DEMO_ADMIN_EMAIL, DEMO_ADMIN_PASSWORD, demo_admin_credentials, ensure_demo_admin
from app.core.config import settings
from app.core.security import hash_password, verify_password
from app.db import Base, get_db
from app.main import app
from app.models import Transaction, User


def session_factory(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'bootstrap.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    return engine, sessionmaker(bind=engine)


def test_admin_is_created_and_existing_data_is_preserved(tmp_path):
    engine, factory = session_factory(tmp_path)
    db = factory()
    db.add(User(
        email="analyst@example.com",
        password_hash=hash_password("UnrelatedPassword123!"),
        role="Finance Analyst",
    ))
    db.add(Transaction(
        transaction_id="PRESERVED-001",
        date="2026-09-04",
        amount=10,
        type="revenue",
        status="completed",
    ))
    db.commit()

    ensure_demo_admin(db)
    ensure_demo_admin(db)

    assert db.query(User).filter(User.email == DEMO_ADMIN_EMAIL).count() == 1
    admin = db.query(User).filter(User.email == DEMO_ADMIN_EMAIL).one()
    assert admin.role == "Admin"
    assert verify_password(DEMO_ADMIN_PASSWORD, admin.password_hash)
    assert db.query(User).filter(User.email == "analyst@example.com").count() == 1
    assert db.query(Transaction).filter(Transaction.transaction_id == "PRESERVED-001").count() == 1
    db.close()
    engine.dispose()


def test_invalid_existing_admin_password_is_repaired(tmp_path):
    engine, factory = session_factory(tmp_path)
    db = factory()
    db.add(User(
        email=DEMO_ADMIN_EMAIL,
        password_hash="not-a-valid-argon2-hash",
        role="Admin",
    ))
    db.commit()

    ensure_demo_admin(db)

    admin = db.query(User).filter(User.email == DEMO_ADMIN_EMAIL).one()
    assert verify_password(DEMO_ADMIN_PASSWORD, admin.password_hash)
    assert db.query(User).filter(User.email == DEMO_ADMIN_EMAIL).count() == 1
    db.close()
    engine.dispose()


def test_bootstrap_uses_env_configured_password(tmp_path, monkeypatch):
    """A BOOTSTRAP_ADMIN_PASSWORD value must win over the dev fallback,
    including in a production environment."""
    engine, factory = session_factory(tmp_path)
    db = factory()
    monkeypatch.setattr(settings, "bootstrap_admin_email", "admin@demo.com")
    monkeypatch.setattr(settings, "bootstrap_admin_password", "EnvConfiguredPass1!")
    monkeypatch.setattr(settings, "app_env", "production")

    ensure_demo_admin(db)

    admin = db.query(User).filter(User.email == "admin@demo.com").one()
    assert admin.role == "Admin"
    assert verify_password("EnvConfiguredPass1!", admin.password_hash)
    assert not verify_password("DemoPassword123!", admin.password_hash)
    assert demo_admin_credentials() == ("admin@demo.com", "EnvConfiguredPass1!")
    db.close()
    engine.dispose()


def test_production_without_password_creates_no_admin(tmp_path, monkeypatch):
    """Production must never auto-create an admin with an unconfigured/
    fallback password."""
    engine, factory = session_factory(tmp_path)
    db = factory()
    monkeypatch.setattr(settings, "bootstrap_admin_password", "")
    monkeypatch.setattr(settings, "app_env", "production")

    assert ensure_demo_admin(db) is None
    assert (
        db.query(User).filter(User.email == "admin@demo.com").count() == 0
    )
    assert demo_admin_credentials() == ("admin@demo.com", None)
    db.close()
    engine.dispose()


def test_production_without_password_does_not_reset_existing_admin(tmp_path, monkeypatch):
    """An existing admin's password must not be silently reset when no
    bootstrap password is configured in production."""
    engine, factory = session_factory(tmp_path)
    db = factory()
    existing = User(
        email="admin@demo.com",
        password_hash=hash_password("ExistingProdPass1!"),
        role="Admin",
    )
    db.add(existing)
    db.commit()
    monkeypatch.setattr(settings, "bootstrap_admin_password", "")
    monkeypatch.setattr(settings, "app_env", "production")

    assert ensure_demo_admin(db) is None
    admin = db.query(User).filter(User.email == "admin@demo.com").one()
    assert verify_password("ExistingProdPass1!", admin.password_hash)
    assert not verify_password("DemoPassword123!", admin.password_hash)
    db.close()
    engine.dispose()


def test_login_succeeds_with_bootstrapped_admin(tmp_path):
    engine, factory = session_factory(tmp_path)
    db = factory()
    ensure_demo_admin(db)
    db.close()

    def override_get_db():
        session = factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/auth/login",
                json={"email": DEMO_ADMIN_EMAIL, "password": DEMO_ADMIN_PASSWORD},
            )
            assert response.status_code == 200
            assert response.json()["user"]["role"] == "Admin"
            assert response.json()["access_token"]
    finally:
        app.dependency_overrides.clear()
        engine.dispose()