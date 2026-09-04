
from app.db import Base, engine, SessionLocal
from app.models import *
from app.core.security import hash_password
from app.core.bootstrap import demo_admin_credentials
from app.services.risk.engine import calculate
import csv
import pathlib
import json


# Create database tables
Base.metadata.create_all(engine)

# Open database session
db = SessionLocal()


# ============================================================
# ADMIN USER
# ============================================================

# Admin credentials come from configuration (BOOTSTRAP_ADMIN_EMAIL /
# BOOTSTRAP_ADMIN_PASSWORD env vars, see app/core/config.py). The password
# is never printed; a development-only fallback applies outside production.
admin_email, admin_password = demo_admin_credentials()

if not admin_password:
    print("Admin bootstrap skipped: BOOTSTRAP_ADMIN_PASSWORD is not configured.")
else:
    admin = db.query(User).filter_by(email=admin_email).first()

    if admin:
        # Update existing admin credentials
        admin.password_hash = hash_password(admin_password)
        admin.role = "Admin"
    else:
        # Check whether an old admin/demo user exists
        old_admin = db.query(User).filter(
            User.email == "admin@demo.local"
        ).first()

        if old_admin:
            old_admin.email = admin_email
            old_admin.password_hash = hash_password(admin_password)
            old_admin.role = "Admin"
        else:
            # Create new admin
            db.add(
                User(
                    email=admin_email,
                    password_hash=hash_password(admin_password),
                    role="Admin"
                )
            )

    db.commit()


# ============================================================
# FINANCE TRANSACTIONS
# ============================================================

csvpath = (
    pathlib.Path(__file__).parents[1]
    / "database/sample_data/finance_transactions.csv"
)

with csvpath.open() as f:
    for r in csv.DictReader(f):

        # Skip transaction if it already exists
        if db.query(Transaction).filter_by(
            transaction_id=r["transaction_id"]
        ).first():
            continue

        # Create transaction
        t = Transaction(
            transaction_id=r["transaction_id"],
            date=r["date"],
            amount=float(r["amount"]),
            type=r["type"],
            status=r["status"],
            merchant=r["merchant"],
            vendor=r["vendor"],
            settlement_id=r["settlement_id"],
            settlement_amount=float(r["settlement_amount"]),
            fee=float(r["fee"]),
            refund_amount=float(r["refund_amount"]),
            invoice_id=r["invoice_id"],
            customer=r["customer"],
            due_date=r["due_date"],
            payment_status=r["payment_status"],
            category=r["category"],
            department=r["department"],
            currency=r["currency"]
        )

        db.add(t)
        db.flush()

        # ====================================================
        # RISK ASSESSMENT
        # ====================================================

        variance = abs(
            t.amount - t.settlement_amount
        )

        score, level, factors = calculate(
            t,
            variance,
            t.amount in [250000, 275000],
            False
        )

        db.add(
            RiskAssessment(
                transaction_id=t.transaction_id,
                risk_score=score,
                risk_level=level,
                risk_factors=json.dumps(factors)
            )
        )

        # ====================================================
        # RECONCILIATION
        # ====================================================

        status = (
            "MATCHED"
            if variance < 1
            else "MISMATCH"
        )

        db.add(
            ReconciliationResult(
                transaction_id=t.transaction_id,
                status=status,
                variance=variance,
                reason=(
                    "Exact settlement match"
                    if status == "MATCHED"
                    else "Settlement variance detected"
                )
            )
        )

        # ====================================================
        # ANOMALY + REVIEW ITEM
        # ====================================================

        if score >= 61:

            db.add(
                Anomaly(
                    transaction_id=t.transaction_id,
                    reason="Potentially unusual transaction characteristics",
                    severity=level,
                    evidence="Amount/settlement/duplicate-like signal",
                    score=score
                )
            )

            db.add(
                ReviewItem(
                    transaction_id=t.transaction_id
                )
            )


# ============================================================
# COMMIT EVERYTHING
# ============================================================

db.commit()

print("Seed complete")
print()
print(f"Admin email: {admin_email}")
if admin_password:
    print("Admin password: configured via BOOTSTRAP_ADMIN_PASSWORD (not printed)")
else:
    print("Admin account not created (BOOTSTRAP_ADMIN_PASSWORD unset)")

