from sqlalchemy.orm import Session

from ..core.config import settings
from ..models import User
from .security import hash_password, verify_password

# DEVELOPMENT-ONLY fallback for the demo admin, used only when
# BOOTSTRAP_ADMIN_PASSWORD is not configured and APP_ENV is not
# "production". It is NOT a production credential: deployments must set
# BOOTSTRAP_ADMIN_PASSWORD (and APP_ENV=production) via the environment.
_DEV_ONLY_DEMO_PASSWORD = "DemoPassword123!"


def demo_admin_credentials() -> tuple[str, str | None]:
    """Resolve the bootstrap admin (email, password) from configuration.

    Returns ``(email, None)`` when no password is configured in a production
    environment, which disables demo-admin auto-creation and password resets.
    """
    email = settings.bootstrap_admin_email or "admin@demo.com"
    password = settings.bootstrap_admin_password or ""
    if not password:
        if (settings.app_env or "development").lower() == "production":
            return email, None
        password = _DEV_ONLY_DEMO_PASSWORD
    return email, password


# Backward-compatible exports (same import contract as before). Values are
# resolved from configuration at import time; ``DEMO_ADMIN_PASSWORD`` is
# ``None`` when a production environment is configured without an explicit
# bootstrap password. Prefer ``demo_admin_credentials()`` at call time.
DEMO_ADMIN_EMAIL = settings.bootstrap_admin_email or "admin@demo.com"
DEMO_ADMIN_PASSWORD = demo_admin_credentials()[1]


def ensure_demo_admin(db: Session) -> User | None:
    """Create (or repair) the demo admin using the configured credentials.

    Returns the admin user, or ``None`` when no bootstrap password is
    configured (production safety: never create or reset an admin account
    with an unconfigured password).
    """
    email, password = demo_admin_credentials()
    if not password:
        return None

    admin = db.query(User).filter(User.email == email).first()
    if admin is None:
        admin = User(
            email=email,
            password_hash=hash_password(password),
            role="Admin",
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        return admin

    try:
        password_valid = bool(admin.password_hash) and verify_password(
            password,
            admin.password_hash,
        )
    except (TypeError, ValueError):
        password_valid = False

    if not password_valid:
        admin.password_hash = hash_password(password)
        db.commit()

    return admin