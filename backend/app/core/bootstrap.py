from sqlalchemy.orm import Session

from ..models import User
from .security import hash_password, verify_password


DEMO_ADMIN_EMAIL = "admin@demo.com"
DEMO_ADMIN_PASSWORD = "DemoPassword123!"


def ensure_demo_admin(db: Session) -> User:
    admin = db.query(User).filter(User.email == DEMO_ADMIN_EMAIL).first()
    if admin is None:
        admin = User(
            email=DEMO_ADMIN_EMAIL,
            password_hash=hash_password(DEMO_ADMIN_PASSWORD),
            role="Admin",
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        return admin

    try:
        password_valid = bool(admin.password_hash) and verify_password(
            DEMO_ADMIN_PASSWORD,
            admin.password_hash,
        )
    except (TypeError, ValueError):
        password_valid = False

    if not password_valid:
        admin.password_hash = hash_password(DEMO_ADMIN_PASSWORD)
        db.commit()

    return admin