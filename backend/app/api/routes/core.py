from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime

from ...db import get_db
from ...models import *
from ...api.dependencies.auth import current_user
from ...services.finance.engine import metrics
from ...services.risk.engine import (
    assess_exception,
    calculate,
    run_marker,
    split_run_marker,
)
from ...services.ai.providers import get_provider
from ...core.config import settings
from ...services.csv.processor import validate_csv
from ...services.reconciliation.adaptive import (
    MultiFileValidationError,
    classify_counts,
    detect_mapping_from_bytes,
    detect_source_role,
    parse_single_file,
    parse_source,
    reconcile_sources,
)
from ...services.razorpay.adapter import (
    RazorpayAPIError,
    RazorpayConfigurationError,
    fetch_test_payments,
    payments_csv,
)

import json
from io import BytesIO


router = APIRouter()


# ============================================================
# RAZORPAY TEST MODE
# ============================================================

@router.get("/razorpay/test-payments")
def razorpay_test_payments(
    limit: int = 100,
    u=Depends(current_user),
):
    if settings.razorpay_mode.lower() != "test":
        raise HTTPException(503, "Razorpay integration is restricted to test mode")
    try:
        payments = fetch_test_payments(
            settings.razorpay_key_id,
            settings.razorpay_key_secret,
            limit,
        )
    except RazorpayConfigurationError as exc:
        raise HTTPException(503, str(exc)) from exc
    except RazorpayAPIError as exc:
        raise HTTPException(502, str(exc)) from exc
    return {"source": "razorpay_test", "count": len(payments), "items": payments}


@router.post("/razorpay/test-payments/import")
async def import_razorpay_test_payments(
    limit: int = 100,
    db: Session = Depends(get_db),
    u=Depends(current_user),
):
    if settings.razorpay_mode.lower() != "test":
        raise HTTPException(503, "Razorpay integration is restricted to test mode")
    try:
        payments = fetch_test_payments(
            settings.razorpay_key_id,
            settings.razorpay_key_secret,
            limit,
        )
    except RazorpayConfigurationError as exc:
        raise HTTPException(503, str(exc)) from exc
    except RazorpayAPIError as exc:
        raise HTTPException(502, str(exc)) from exc
    if not payments:
        return {"source": "razorpay_test", "imported": 0, "duplicates": 0, "errors": [], "warnings": ["No Razorpay test payments were returned."]}
    upload = UploadFile(
        file=BytesIO(payments_csv(payments)),
        filename="razorpay-test-payments.csv",
    )
    result = await import_csv(upload, db, u)
    result["source"] = "razorpay_test"
    return result

# ============================================================
# RUNTIME EXCEPTION RISK HELPERS
# ============================================================

RISK_EXCEPTION_STATUSES = {"PARTIAL", "MISMATCH", "UNMATCHED", "DUPLICATE", "EXCEPTION"}


def _clean_risk_factors(factors_text):
    clean, _ = split_run_marker(factors_text)
    return clean


def _risk_for_transaction(db, transaction_id, run_id):
    """Prefer the assessment belonging to the same reconciliation run;
    fall back to the highest-score assessment for the transaction."""
    rows = (
        db.query(RiskAssessment)
        .filter(RiskAssessment.transaction_id == transaction_id)
        .order_by(RiskAssessment.id.desc())
        .limit(20)
        .all()
    )
    if not rows:
        return None
    if run_id:
        marker = run_marker(run_id)
        for row in rows:
            if marker in (row.risk_factors or ""):
                return row
    return max(rows, key=lambda r: r.risk_score or 0)


def _in_chunks(values, size=1000):
    values = list(values)
    for start in range(0, len(values), size):
        yield values[start:start + size]


def _transactions_by_id(db, transaction_ids):
    result = {}
    for chunk in _in_chunks(set(transaction_ids)):
        if chunk:
            result.update({
                row.transaction_id: row
                for row in db.query(Transaction).filter(
                    Transaction.transaction_id.in_(chunk)
                ).all()
            })
    return result


def _upsert_exception_risk(db, run_id, transaction_ref, amount, settlement_amount, variance, reason, seen):
    """Score one exception of a run and upsert its RiskAssessment row
    (run isolated via a 'source_run:<run_id>' marker in risk_factors).
    HIGH/CRITICAL exceptions also create/refresh one Anomaly per run."""
    if transaction_ref in seen:
        return
    seen.add(transaction_ref)
    score, level, factors = assess_exception(
        transaction_ref,
        amount=amount,
        settlement_amount=settlement_amount,
        variance=variance,
    )
    marker = run_marker(run_id)
    stored = json.dumps(factors + [marker])
    db.add(RiskAssessment(
        transaction_id=transaction_ref,
        risk_score=score,
        risk_level=level,
        risk_factors=stored,
    ))
    if level not in ("HIGH", "CRITICAL"):
        return
    settlement_text = (
        f"{float(settlement_amount):.2f}"
        if settlement_amount is not None
        else "n/a"
    )
    evidence = (
        f"Run {run_id}; amount={float(amount or 0):.2f}; "
        f"settlement={settlement_text}; variance={float(variance or 0):.2f}; "
        f"{reason or 'High-risk reconciliation exception.'}"
    )
    db.add(Anomaly(
        transaction_id=transaction_ref,
        reason="High-risk reconciliation exception.",
        severity=level,
        evidence=evidence,
        score=score,
    ))



# ============================================================
# TRANSACTIONS
# ============================================================

@router.get("/transactions")
def transactions(
    page: int = 1,
    page_size: int = 25,
    db: Session = Depends(get_db),
    u=Depends(current_user)
):
    q = db.query(Transaction).order_by(Transaction.id.desc())

    total = q.count()

    rows = (
        q.offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "items": [
            {
                c: getattr(x, c)
                for c in [
                    "transaction_id",
                    "date",
                    "amount",
                    "type",
                    "status",
                    "merchant",
                    "vendor",
                    "fee",
                    "refund_amount",
                    "category",
                    "currency",
                ]
            }
            for x in rows
        ],
        "total": total,
        "page": page,
    }


# ============================================================
# DASHBOARD
# ============================================================

@router.get("/dashboard")
def dashboard(
    db: Session = Depends(get_db),
    u=Depends(current_user)
):
    return metrics(db)


@router.get("/analytics")
def analytics(
    db: Session = Depends(get_db),
    u=Depends(current_user)
):
    m = metrics(db)

    return {
        **m,
        "insight": "Metrics are calculated from imported transaction data."
    }


# ============================================================
# RECONCILIATION
# ============================================================

def _upsert_reconciliation_transaction(
    db,
    transaction_id,
    amount,
    settlement_amount=None,
    date_value=None,
    vendor=None,
    description=None,
    fee=0,
    currency="INR",
    existing=None,
    lookup_if_missing=True,
):
    transaction = existing
    if transaction is None and lookup_if_missing:
        transaction = (
            db.query(Transaction)
            .filter(Transaction.transaction_id == transaction_id)
            .first()
        )

    if transaction is None:
        transaction = Transaction(
            transaction_id=transaction_id,
            date=date_value,
            amount=float(amount),
            type="reconciliation",
            status="imported",
            merchant=description or vendor,
            vendor=vendor or description,
            settlement_amount=(
                float(settlement_amount)
                if settlement_amount is not None
                else None
            ),
            fee=float(fee or 0),
            refund_amount=0,
            currency=currency or "INR",
        )
        db.add(transaction)
        return transaction

    if transaction.settlement_amount is None and settlement_amount is not None:
        transaction.settlement_amount = float(settlement_amount)
    if transaction.date is None and date_value is not None:
        transaction.date = date_value
    if transaction.vendor is None and (vendor or description):
        transaction.vendor = vendor or description
    if transaction.merchant is None and (description or vendor):
        transaction.merchant = description or vendor
    return transaction


def _upsert_reconciliation_result(db, run_id, transaction_id, status, variance, reason):
    result = (
        db.query(ReconciliationResult)
        .filter(
            ReconciliationResult.run_id == run_id,
            ReconciliationResult.transaction_id == transaction_id,
        )
        .order_by(ReconciliationResult.id.desc())
        .first()
    )
    if result is None:
        result = ReconciliationResult(run_id=run_id, transaction_id=transaction_id)
        db.add(result)

    result.status = status
    result.variance = float(variance or 0)
    result.reason = reason or ""
    return result


def _upsert_review_item(db, run_id, transaction_id, reason):
    item = (
        db.query(ReviewItem)
        .filter(
            ReviewItem.run_id == run_id,
            ReviewItem.transaction_id == transaction_id,
        )
        .first()
    )
    if item is None:
        item = ReviewItem(
            run_id=run_id,
            transaction_id=transaction_id,
            status="OPEN",
            note=reason,
        )
        db.add(item)
    return item

@router.get("/reconciliation")
def reconciliation(
    db: Session = Depends(get_db),
    run_id: str | None = None,
    u=Depends(current_user)
):
    run = (
        db.query(ReconciliationRun)
        .filter(ReconciliationRun.run_id == run_id)
        .first()
        if run_id
        else db.query(ReconciliationRun)
        .filter(ReconciliationRun.status == "COMPLETED")
        .order_by(ReconciliationRun.created_at.desc(), ReconciliationRun.id.desc())
        .first()
    )
    if run:
        reconciliation_rows = (
            db.query(ReconciliationResult)
            .filter(ReconciliationResult.run_id == run.run_id)
            .order_by(ReconciliationResult.id.desc())
            .all()
        )
        if not reconciliation_rows and not run_id:
            run = None
    else:
        reconciliation_rows = (
            db.query(ReconciliationResult)
            .filter(ReconciliationResult.run_id.is_(None))
            .order_by(ReconciliationResult.id.desc())
            .all()
        )

    counts = {
        status: sum(
            x.status == status
            for x in reconciliation_rows
        )
        for status in [
            "MATCHED",
            "PARTIAL",
            "UNMATCHED",
            "DUPLICATE",
            "MISMATCH",
            "EXCEPTION",
        ]
    }

    total_variance = sum(
        abs(float(x.variance or 0))
        for x in reconciliation_rows
    )

    transaction_map = _transactions_by_id(
        db,
        (row.transaction_id for row in reconciliation_rows),
    )
    review_map = {}
    if reconciliation_rows:
        run_ids = {row.run_id for row in reconciliation_rows}
        review_rows = db.query(ReviewItem).filter(
            ReviewItem.transaction_id.in_({row.transaction_id for row in reconciliation_rows}),
            ReviewItem.run_id.in_(run_ids),
        ).all()
        review_map = {
            (row.run_id, row.transaction_id): row
            for row in review_rows
        }
    records = []

    for x in reconciliation_rows:

        # ----------------------------------------------------
        # Transaction
        # ----------------------------------------------------

        transaction = transaction_map.get(x.transaction_id)

        # ----------------------------------------------------
        # Review item
        # ----------------------------------------------------

        review_item = review_map.get((x.run_id, x.transaction_id))

        # ----------------------------------------------------
        # Build record
        # ----------------------------------------------------

        record = {
            "id": x.id,

            "transaction_id": x.transaction_id,

            "status": x.status,

            "variance": round(
                abs(float(x.variance or 0)),
                2
            ),

            "reason": x.reason,

            # Transaction information
            "amount": (
                float(transaction.amount)
                if transaction
                and transaction.amount is not None
                else None
            ),

            "settlement_amount": (
                float(transaction.settlement_amount)
                if transaction
                and transaction.settlement_amount is not None
                else None
            ),

            "merchant": (
                transaction.merchant
                if transaction
                else None
            ),

            "vendor": (
                transaction.vendor
                if transaction
                else None
            ),

            "date": (
                transaction.date
                if transaction
                else None
            ),

            "category": (
                transaction.category
                if transaction
                else None
            ),

            "currency": (
                transaction.currency
                if transaction
                else "INR"
            ),

            "type": (
                transaction.type
                if transaction
                else None
            ),

            "transaction_status": (
                transaction.status
                if transaction
                else None
            ),

            # ------------------------------------------------
            # Review information
            # ------------------------------------------------

            "review_item_id": (
                review_item.id
                if review_item
                else None
            ),

            "review_status": (
                review_item.status
                if review_item
                else None
            ),

            "review_note": (
                review_item.note
                if review_item
                else None
            ),

            "review_created_at": (
                review_item.created_at.isoformat()
                if review_item
                and review_item.created_at
                else None
            ),
        }

        records.append(record)

    total = len(reconciliation_rows)

    matched = counts.get("MATCHED", 0)

    exceptions = total - matched

    match_rate = (
        (matched / total) * 100
        if total > 0
        else 0
    )

    return {
        "run_id": run.run_id if run else None,
        "mode": run.mode if run else None,
        "created_at": run.created_at.isoformat() if run and run.created_at else None,
        "total": total,

        "matched": matched,

        "exceptions": exceptions,
        "partial": counts.get("PARTIAL", 0),
        "mismatch": counts.get("MISMATCH", 0),
        "unmatched": counts.get("UNMATCHED", 0),
        "duplicate": counts.get("DUPLICATE", 0),

        "match_rate": round(
            match_rate,
            2
        ),

        "counts": counts,

        "variance": round(
            total_variance,
            2
        ),

        "records": records,
    }


@router.post("/reconciliation/multi-file")
async def multi_file_reconciliation(
    bank_file: UploadFile = File(...),
    ledger_file: UploadFile = File(...),
    settlement_file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    u=Depends(current_user)
):
    uploads = [
        ("bank", bank_file),
        ("ledger", ledger_file),
    ]
    if settlement_file is not None:
        uploads.append(("settlement", settlement_file))

    for source, upload in uploads:
        if not (upload.filename or "").lower().endswith(".csv"):
            raise HTTPException(
                status_code=400,
                detail={
                    "source": source,
                    "error": "Only CSV files are accepted",
                },
            )

    parsed = {}
    mappings = {}
    role_details = {}
    occupied_roles = set()
    for slot, upload in uploads:
        try:
            data = await upload.read()
            mapping = detect_mapping_from_bytes(data, slot)
            role = detect_source_role(list(mapping.values()), upload.filename or "")
            detected_role = role["role"]
            if detected_role not in {"BANK", "LEDGER", "SETTLEMENT"} or detected_role in occupied_roles:
                detected_role = slot.upper()
                role["assumption"] = role.get("assumption") or f"Role inferred from the upload slot because schema signals were ambiguous: {detected_role}."
            occupied_roles.add(detected_role)
            source_key = detected_role.lower()
            mappings[source_key] = mapping
            role_details[source_key] = {
                **role,
                "role": detected_role,
                "filename": upload.filename,
                "columns": mapping,
            }
            parsed[source_key] = parse_source(data, detected_role)
        except MultiFileValidationError as error:
            raise HTTPException(status_code=400, detail=error.as_dict())

    if "bank" not in parsed or "ledger" not in parsed:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Unable to confidently identify both BANK and LEDGER sources. Upload files with bank/UTR or ledger/invoice schema signals, or use the designated upload slots.",
                "roles": role_details,
            },
        )

    bank_records = parsed["bank"]
    ledger_records = parsed["ledger"]
    settlement_records = parsed.get("settlement", [])
    records = reconcile_sources(
        bank_records,
        ledger_records,
        settlement_records,
    )
    counts = classify_counts(records)
    total_records = len(records)
    match_rate = (
        counts["MATCHED"] / total_records * 100
        if total_records
        else 0
    )
    total_variance = round(
        sum(float(record["variance"] or 0) for record in records),
        2,
    )
    exception_count = total_records - counts["MATCHED"]
    run_id = f"REC-{datetime.utcnow():%Y%m%d%H%M%S%f}"

    run = ReconciliationRun(
        run_id=run_id,
        mode="multi_file",
        filename=None,
        user_email=u.email,
        bank_filename=bank_file.filename or "",
        ledger_filename=ledger_file.filename or "",
        settlement_filename=(
            settlement_file.filename
            if settlement_file is not None
            else None
        ),
        bank_records=len(bank_records),
        ledger_records=len(ledger_records),
        settlement_records=len(settlement_records),
        total=total_records,
        matched=counts["MATCHED"],
        partial=counts["PARTIAL"],
        unmatched=counts["UNMATCHED"],
        duplicate=counts["DUPLICATE"],
        exceptions=exception_count,
        match_rate=round(match_rate, 2),
        total_variance=total_variance,
    )
    db.add(run)

    exception_statuses = {"PARTIAL", "MISMATCH", "UNMATCHED", "DUPLICATE", "EXCEPTION"}
    transaction_map = _transactions_by_id(
        db,
        (record["reference"] for record in records),
    )
    source_maps = {
        source: {
            source_record.reference: source_record
            for source_record in parsed.get(source, [])
        }
        for source in ("bank", "ledger", "settlement")
    }
    for record in records:
        source_records = {
            source: source_maps[source].get(record["reference"])
            for source in ("bank", "ledger", "settlement")
        }
        bank_record = source_records["bank"]
        ledger_record = source_records["ledger"]
        settlement_record = source_records["settlement"]
        amount_record = bank_record or ledger_record or settlement_record
        date_record = next(
            (
                source_record
                for source_record in (
                    bank_record,
                    ledger_record,
                    settlement_record,
                )
                if source_record and source_record.date is not None
            ),
            None,
        )
        transaction = _upsert_reconciliation_transaction(
            db,
            record["reference"],
            amount_record.amount if amount_record else 0,
            settlement_record.amount if settlement_record else (
                ledger_record.amount if ledger_record else None
            ),
            date_record.date.isoformat() if date_record else None,
            description=(
                bank_record.description
                if bank_record
                else ledger_record.description
                if ledger_record
                else None
            ),
            fee=settlement_record.fee if settlement_record else 0,
            currency=(
                amount_record.currency
                if amount_record
                else "INR"
            ),
            existing=transaction_map.get(record["reference"]),
            lookup_if_missing=False,
        )
        db.add(ReconciliationResult(
            run_id=run_id,
            transaction_id=record["reference"],
            status=record["status"],
            variance=float(record["variance"] or 0),
            reason=record["reason"] or "",
        ))
        transaction_map[record["reference"]] = transaction
        if record["status"] not in exception_statuses:
            continue
        db.add(ReviewItem(
            run_id=run_id,
            transaction_id=record["reference"],
            status="OPEN",
            note=record["reason"],
        ))

    db.add(
        AuditLog(
            user_email=u.email,
            action="MULTI_FILE_RECONCILIATION",
            entity=run_id,
            detail=(
                f"Run {run_id}; files: "
                f"bank={bank_file.filename}, "
                f"ledger={ledger_file.filename}, "
                f"settlement={settlement_file.filename if settlement_file else 'none'}; "
                f"records: bank={len(parsed['bank'])}, "
                f"ledger={len(parsed['ledger'])}, "
                f"settlement={len(parsed.get('settlement', []))}; "
                f"match rate={match_rate:.2f}%; exceptions={exception_count}; "
                f"tolerance=0.01; roles={json.dumps(role_details, default=str)}"
            ),
        )
    )
    seen = set()
    for record in records:
        if record.get("status") in RISK_EXCEPTION_STATUSES:
            _upsert_exception_risk(
                db,
                run_id,
                record.get("reference") or record.get("transaction_id"),
                record.get("amount"),
                record.get("settlement_amount"),
                record.get("variance"),
                record.get("reason"),
                seen,
            )
    db.commit()

    return {
        "run_id": run_id,
        "sources": {
            "bank": {
                "filename": bank_file.filename,
                "records": len(bank_records),
                "mapping": mappings["bank"],
                "role": role_details["bank"],
            },
            "ledger": {
                "filename": ledger_file.filename,
                "records": len(ledger_records),
                "mapping": mappings["ledger"],
                "role": role_details["ledger"],
            },
            "settlement": {
                "filename": settlement_file.filename
                if settlement_file is not None
                else None,
                "records": len(settlement_records),
                "mapping": mappings.get("settlement", {}),
                "role": role_details.get("settlement"),
            },
        },
        "summary": {
            "total_records": total_records,
            "matched": counts["MATCHED"],
            "partial": counts["PARTIAL"],
            "mismatch": counts["MISMATCH"],
            "unmatched": counts["UNMATCHED"],
            "duplicate": counts["DUPLICATE"],
            "exception": total_records - counts["MATCHED"],
            "match_rate": round(match_rate, 2),
            "total_variance": total_variance,
        },
        "roles": role_details,
        "tolerance": 0.01,
        "assumptions": [detail["assumption"] for detail in role_details.values() if detail.get("assumption")],
        "records": records,
    }


@router.post("/reconciliation/single-file")
async def single_file_reconciliation(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    u=Depends(current_user)
):
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Only CSV files are accepted",
        )
    try:
        records, mapping = parse_single_file(await file.read())
    except MultiFileValidationError as error:
        raise HTTPException(status_code=400, detail=error.as_dict())

    counts = classify_counts(records)
    references = {}
    for record in records:
        references.setdefault(record["reference"], []).append(record)
    for reference, duplicate_records in references.items():
        if len(duplicate_records) > 1:
            for record in duplicate_records:
                record["status"] = "DUPLICATE"
                record["reason"] = "Duplicate reference detected."
            counts["DUPLICATE"] += len(duplicate_records)
            counts["MATCHED"] -= sum(duplicate_record["status"] == "MATCHED" for duplicate_record in duplicate_records)
            counts["PARTIAL"] -= sum(duplicate_record["status"] == "PARTIAL" for duplicate_record in duplicate_records)
            counts["MISMATCH"] -= sum(duplicate_record["status"] == "MISMATCH" for duplicate_record in duplicate_records)
            counts["UNMATCHED"] -= sum(duplicate_record["status"] == "UNMATCHED" for duplicate_record in duplicate_records)

    total = len(records)
    matched = counts["MATCHED"]
    exceptions = total - matched
    variance = round(sum(record["variance"] for record in records), 2)
    match_rate = round(matched / total * 100, 2) if total else 0
    run_id = f"REC-{datetime.utcnow():%Y%m%d%H%M%S%f}"
    transaction_map = _transactions_by_id(
        db,
        (record["reference"] for record in records),
    )

    for record in records:
        amount = next(
            (
                record.get(field)
                for field in (
                    "bank_amount",
                    "ledger_amount",
                    "settlement_amount",
                )
                if record.get(field) is not None
            ),
            0,
        )
        transaction = _upsert_reconciliation_transaction(
            db,
            record["reference"],
            amount,
            record.get("settlement_amount"),
            record["date"].isoformat() if record.get("date") else None,
            record.get("vendor"),
            record.get("vendor"),
            existing=transaction_map.get(record["reference"]),
            lookup_if_missing=False,
        )
        transaction_map[record["reference"]] = transaction
        db.add(ReconciliationResult(
            run_id=run_id,
            transaction_id=record["reference"],
            status=record["status"],
            variance=float(record["variance"] or 0),
            reason=record["reason"] or "",
        ))

    db.add(ReconciliationRun(
        run_id=run_id,
        mode="single_file",
        filename=file.filename or "reconciliation.csv",
        user_email=u.email,
        bank_filename="",
        ledger_filename="",
        settlement_filename=None,
        total=total,
        matched=matched,
        partial=counts["PARTIAL"],
        unmatched=counts["UNMATCHED"],
        duplicate=counts["DUPLICATE"],
        exceptions=exceptions,
        match_rate=match_rate,
        total_variance=variance,
    ))
    for record in records:
        if record["status"] in {"PARTIAL", "MISMATCH", "UNMATCHED", "DUPLICATE", "EXCEPTION"}:
            db.add(ReviewItem(
                run_id=run_id,
                transaction_id=record["reference"],
                status="OPEN",
                note=record["reason"],
            ))
    db.add(AuditLog(
        user_email=u.email,
        action="SINGLE_FILE_RECONCILIATION",
        entity=run_id,
        detail=(
            f"Run {run_id}; filename={file.filename}; total={total}; "
            f"matched={matched}; exceptions={exceptions}; "
            f"match rate={match_rate:.2f}%; tolerance=0.01; "
            f"mapping={json.dumps(mapping, default=str)}"
        ),
    ))
    seen = set()
    for record in records:
        if record.get("status") in RISK_EXCEPTION_STATUSES:
            _upsert_exception_risk(
                db,
                run_id,
                record.get("reference") or record.get("transaction_id"),
                record.get("amount"),
                record.get("settlement_amount"),
                record.get("variance"),
                record.get("reason"),
                seen,
            )
    db.commit()

    return {
        "run_id": run_id,
        "mode": "single_file",
        "filename": file.filename,
        "mapping": mapping,
        "total": total,
        "matched": matched,
        "partial": counts["PARTIAL"],
        "mismatch": counts["MISMATCH"],
        "unmatched": counts["UNMATCHED"],
        "duplicates": counts["DUPLICATE"],
        "exceptions": exceptions,
        "match_rate": match_rate,
        "variance": variance,
        "records": records,
    }


# ============================================================
# RISK
# ============================================================

@router.get("/risk")
def risk(
    db: Session = Depends(get_db),
    run_id: str | None = None,
    u=Depends(current_user)
):
    query = db.query(RiskAssessment)
    if run_id:
        query = query.filter(
            RiskAssessment.risk_factors.like(
                f"%{run_marker(run_id)}%"
            )
        )
    rows = query.order_by(
        RiskAssessment.risk_score.desc(),
        RiskAssessment.id.desc(),
    ).limit(50).all()
    result = []
    for x in rows:
        clean_factors, stored_run = split_run_marker(x.risk_factors)
        active_run = run_id or stored_run
        transaction = (
            db.query(Transaction)
            .filter(Transaction.transaction_id == x.transaction_id)
            .first()
        )
        reconciliation = None
        if active_run:
            reconciliation = (
                db.query(ReconciliationResult)
                .filter(
                    ReconciliationResult.run_id == active_run,
                    ReconciliationResult.transaction_id == x.transaction_id,
                )
                .order_by(ReconciliationResult.id.desc())
                .first()
            )
        if reconciliation is None:
            reconciliation = (
                db.query(ReconciliationResult)
                .filter(ReconciliationResult.transaction_id == x.transaction_id)
                .order_by(ReconciliationResult.id.desc())
                .first()
            )
        result.append({
            "transaction_id": x.transaction_id,
            "risk_score": x.risk_score,
            "risk_level": x.risk_level,
            "risk_factors": clean_factors,
            "run_id": active_run,
            "variance": (
                round(abs(float(reconciliation.variance or 0)), 2)
                if reconciliation
                else None
            ),
            "amount": (
                float(transaction.amount)
                if transaction and transaction.amount is not None
                else None
            ),
            "settlement_amount": (
                float(transaction.settlement_amount)
                if transaction and transaction.settlement_amount is not None
                else None
            ),
            "reason": reconciliation.reason if reconciliation else None,
        })
    return result


# ============================================================
# ANOMALIES
# ============================================================

@router.get("/anomalies")
def anomalies(
    db: Session = Depends(get_db),
    run_id: str | None = None,
    u=Depends(current_user)
):
    query = db.query(Anomaly)
    if run_id:
        query = query.filter(
            Anomaly.evidence.like(f"%Run {run_id}%")
        )
    return [
        {
            "transaction_id": x.transaction_id,
            "reason": x.reason,
            "severity": x.severity,
            "evidence": x.evidence,
            "score": x.score,
        }
        for x in (
            query.order_by(Anomaly.score.desc())
            .limit(100)
        )
    ]
# ============================================================
# REVIEW CENTER
# ============================================================

@router.get("/review")
def review(
    db: Session = Depends(get_db),
    run_id: str | None = None,
    u=Depends(current_user)
):
    run = (
        db.query(ReconciliationRun)
        .filter(ReconciliationRun.run_id == run_id)
        .first()
        if run_id
        else db.query(ReconciliationRun)
        .filter(ReconciliationRun.status == "COMPLETED")
        .order_by(ReconciliationRun.created_at.desc(), ReconciliationRun.id.desc())
        .first()
    )
    items = (
        db.query(ReviewItem)
        .filter(ReviewItem.run_id == (run.run_id if run else None))
        .order_by(ReviewItem.id.desc())
        .all()
    )
    if not items and run and not run_id:
        run = None
        items = (
            db.query(ReviewItem)
            .filter(ReviewItem.run_id.is_(None))
            .order_by(ReviewItem.id.desc())
            .all()
        )

    result = []

    for x in items:

        transaction = (
            db.query(Transaction)
            .filter(
                Transaction.transaction_id
                == x.transaction_id
            )
            .first()
        )

        reconciliation = (
            db.query(ReconciliationResult)
            .filter(
                ReconciliationResult.run_id == x.run_id,
                ReconciliationResult.transaction_id
                == x.transaction_id
            )
            .first()
        )

        risk = _risk_for_transaction(
            db,
            x.transaction_id,
            x.run_id,
        )

        result.append(
            {
                "id": x.id,

                "run_id": x.run_id,

                "transaction_id": x.transaction_id,

                "status": x.status,

                "note": x.note,

                "created_at": (
                    x.created_at.isoformat()
                    if x.created_at
                    else None
                ),

                "amount": (
                    float(transaction.amount)
                    if transaction
                    else None
                ),

                "settlement_amount": (
                    float(transaction.settlement_amount)
                    if transaction
                    and transaction.settlement_amount is not None
                    else None
                ),

                "merchant": (
                    transaction.merchant
                    if transaction
                    else None
                ),

                "vendor": (
                    transaction.vendor
                    if transaction
                    else None
                ),

                "date": (
                    transaction.date
                    if transaction
                    else None
                ),

                "category": (
                    transaction.category
                    if transaction
                    else None
                ),

                "reconciliation_status": (
                    reconciliation.status
                    if reconciliation
                    else None
                ),

                "variance": (
                    round(
                        abs(
                            float(
                                reconciliation.variance or 0
                            )
                        ),
                        2
                    )
                    if reconciliation
                    else 0
                ),

                "reason": (
                    reconciliation.reason
                    if reconciliation
                    else None
                ),

                "risk_score": (
                    risk.risk_score
                    if risk
                    else None
                ),

                "risk_level": (
                    risk.risk_level
                    if risk
                    else None
                ),

                "risk_factors": (
                    _clean_risk_factors(risk.risk_factors)
                    if risk
                    else []
                ),
            }
        )

    return result


class ReviewUpdate(BaseModel):
    status: str
    note: str | None = None


class ReviewAction(BaseModel):
    action: str
    note: str | None = None


@router.patch("/review/{item_id}")
def update_review(
    item_id: int,
    b: ReviewUpdate,
    db: Session = Depends(get_db),
    u=Depends(current_user)
):

    # --------------------------------------------------------
    # Permission
    # --------------------------------------------------------

    if u.role not in [
        "Finance Controller",
        "CFO / Manager",
        "Admin",
    ]:
        raise HTTPException(
            status_code=403,
            detail="Approval permission required"
        )

    # --------------------------------------------------------
    # Validate status
    # --------------------------------------------------------

    allowed_statuses = [
        "OPEN",
        "UNDER_REVIEW",
        "APPROVED",
        "REJECTED",
        "ESCALATED",
        "RESOLVED",
    ]

    if b.status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail="Invalid review status"
        )

    # --------------------------------------------------------
    # Find review item
    # --------------------------------------------------------

    item = db.get(
        ReviewItem,
        item_id
    )

    if not item:
        raise HTTPException(
            status_code=404,
            detail="Review item not found"
        )

    old_status = item.status

    # --------------------------------------------------------
    # Update review
    # --------------------------------------------------------

    item.status = b.status

    if b.note is not None:
        item.note = b.note

    db.add(item)

    # --------------------------------------------------------
    # Audit log
    # --------------------------------------------------------

    audit = AuditLog(
        user_email=u.email,
        action=f"REVIEW_{b.status}",
        entity=item.run_id or item.transaction_id,
        detail=(
            f"Run {item.run_id or 'legacy'}; "
            f"Review status changed from "
            f"{old_status} to {b.status}. "
            f"Note: {b.note or 'No note provided'}"
        )
    )

    db.add(audit)

    db.commit()

    db.refresh(item)

    return {
        "ok": True,
        "id": item.id,
        "transaction_id": item.transaction_id,
        "old_status": old_status,
        "status": item.status,
        "note": item.note,
    }


@router.post("/review/{item_id}/action")
def execute_review_action(
    item_id: int,
    b: ReviewAction,
    db: Session = Depends(get_db),
    u=Depends(current_user)
):
    if u.role not in [
        "Finance Controller",
        "CFO / Manager",
        "Admin",
    ]:
        raise HTTPException(
            status_code=403,
            detail="Approval permission required"
        )

    action_statuses = {
        "INVESTIGATE": "UNDER_REVIEW",
        "APPROVE": "APPROVED",
        "REJECT": "REJECTED",
        "ESCALATE": "ESCALATED",
        "RESOLVE": "RESOLVED",
        "REOPEN": "OPEN",
    }
    action = b.action.strip().upper()
    new_status = action_statuses.get(action)

    if new_status is None:
        raise HTTPException(
            status_code=400,
            detail="Invalid review action"
        )

    item = db.get(ReviewItem, item_id)

    if not item:
        raise HTTPException(
            status_code=404,
            detail="Review item not found"
        )

    previous_status = item.status
    item.status = new_status

    if b.note is not None:
        item.note = b.note

    audit = AuditLog(
        user_email=u.email,
        action=f"REVIEW_{action}",
        entity=item.run_id or item.transaction_id,
        detail=(
            f"Run {item.run_id or 'legacy'}; "
            f"Controller action {action} changed review status "
            f"from {previous_status} to {new_status}. "
            f"Note: {b.note or 'No note provided'}"
        )
    )

    db.add(item)
    db.add(audit)
    db.commit()
    db.refresh(item)

    return {
        "ok": True,
        "action": action,
        "transaction_id": item.transaction_id,
        "previous_status": previous_status,
        "new_status": item.status,
        "note": item.note,
        "audit_logged": True,
    }


# ============================================================
# IMPORT
# ============================================================

@router.post("/import")
async def import_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    u=Depends(current_user)
):

    if not (
        file.filename or ""
    ).lower().endswith(".csv"):

        raise HTTPException(
            status_code=400,
            detail="Only CSV files are accepted"
        )

    rows, errors = validate_csv(
        await file.read()
    )

    if errors:
        return {
            "imported": 0,
            "errors": errors,
            "warnings": [],
        }

    imported = 0
    duplicates = 0
    imported_records = []
    existing_transactions = _transactions_by_id(
        db,
        (row["transaction_id"] for row in rows),
    )

    run_id = f"IMP-{datetime.utcnow():%Y%m%d%H%M%S%f}"

    for r in rows:

        if r["transaction_id"] in existing_transactions:
            duplicates += 1
            continue

        t = Transaction(
            transaction_id=r["transaction_id"],
            date=r["date"],
            amount=float(r["amount"]),
            type=r["type"],
            status=r["status"],
            merchant=r.get("merchant") or None,
            vendor=r.get("vendor") or None,
            settlement_id=r.get("settlement_id") or None,
            settlement_amount=(
                float(r["settlement_amount"])
                if r.get("settlement_amount")
                else None
            ),
            fee=float(r.get("fee") or 0),
            refund_amount=float(
                r.get("refund_amount") or 0
            ),
            invoice_id=r.get("invoice_id") or None,
            customer=r.get("customer") or None,
            due_date=r.get("due_date") or None,
            payment_status=(
                r.get("payment_status") or None
            ),
            category=r.get("category") or None,
            department=r.get("department") or None,
            currency=r.get("currency") or "INR",
        )

        db.add(t)
        existing_transactions[t.transaction_id] = t

        settlement_amount = t.settlement_amount
        variance = (
            abs(float(t.amount) - float(settlement_amount))
            if settlement_amount is not None
            else 0
        )
        status = (
            "MATCHED"
            if settlement_amount is not None and variance <= 1
            else "MISMATCH"
            if settlement_amount is not None
            else "UNMATCHED"
        )
        reason = (
            "Exact settlement match"
            if status == "MATCHED"
            else "Settlement variance detected"
            if status == "MISMATCH"
            else "No settlement amount supplied"
        )
        score, level, factors = calculate(t, variance, False, False)
        db.add(RiskAssessment(
            transaction_id=t.transaction_id,
            risk_score=score,
            risk_level=level,
            risk_factors=json.dumps(factors + [run_marker(run_id)]),
        ))
        db.add(ReconciliationResult(
            run_id=run_id,
            transaction_id=t.transaction_id,
            status=status,
            variance=variance,
            reason=reason,
        ))
        if status != "MATCHED":
            db.add(ReviewItem(
                run_id=run_id,
                transaction_id=t.transaction_id,
                note=reason,
            ))
        imported_records.append((status, variance))

        imported += 1

    counts = classify_counts([{"status": status} for status, _ in imported_records])
    db.add(ReconciliationRun(
        run_id=run_id,
        mode="import",
        filename=file.filename or "finance.csv",
        user_email=u.email,
        bank_filename="",
        ledger_filename="",
        settlement_filename=None,
        total=imported,
        matched=counts["MATCHED"],
        partial=counts["PARTIAL"],
        unmatched=counts["UNMATCHED"],
        duplicate=counts["DUPLICATE"],
        exceptions=imported - counts["MATCHED"],
        match_rate=(counts["MATCHED"] / imported * 100) if imported else 0,
        total_variance=sum(variance for _, variance in imported_records),
    ))
    db.add(AuditLog(
        user_email=u.email,
        action="CSV_IMPORT",
        entity=run_id,
        detail=(
            f"Run {run_id}; filename={file.filename}; imported={imported}; "
            f"duplicates={duplicates}; total rows={len(rows)}"
        ),
    ))
    db.commit()

    return {
        "imported": imported,
        "duplicates": duplicates,
        "errors": [],
        "warnings": [],
        "run_id": run_id,
    }


# ============================================================
# FORECAST
# ============================================================

@router.get("/forecast")
def forecast(
    db: Session = Depends(get_db),
    u=Depends(current_user)
):

    m = metrics(db)

    if m["total_transactions"] < 30:
        return {
            "message":
            "Insufficient historical data for reliable forecasting."
        }

    return {
        "revenue_forecast":
            round(m["revenue"] * 1.05, 2),

        "expense_forecast":
            round(m["expenses"] * 1.03, 2),

        "cash_flow_forecast":
            round(
                (m["revenue"] - m["expenses"]) * 1.05,
                2
            ),

        "method":
            "baseline historical trend",
    }


# ============================================================
# SCENARIOS
# ============================================================

class Scenario(BaseModel):
    revenue_change: float = 0
    expense_change: float = 0
    refund_change: float = 0
    volume_change: float = 0
    fee_change: float = 0


@router.post("/scenarios")
def scenario(
    b: Scenario,
    db: Session = Depends(get_db),
    u=Depends(current_user)
):

    m = metrics(db)

    rev = (
        m["revenue"]
        * (1 + b.revenue_change / 100)
    )

    exp = (
        m["expenses"]
        * (1 + b.expense_change / 100)
    )

    refunds = (
        m["refunds"]
        * (1 + b.refund_change / 100)
    )

    fees = (
        m["fees"]
        * (1 + b.fee_change / 100)
    )

    profit = (
        rev
        - exp
        - refunds
        - fees
    )

    return {
        "projected_revenue":
            round(rev, 2),

        "projected_expenses":
            round(exp, 2),

        "projected_profit":
            round(profit, 2),

        "projected_margin":
            round(
                profit / rev * 100,
                2
            )
            if rev
            else 0,

        "cash_impact":
            round(
                profit - m["net_profit"],
                2
            ),

        "risk_impact":
            "HIGH"
            if profit < 0
            else "NORMAL",
    }


# ============================================================
# CFO REPORT
# ============================================================

@router.get("/reports/cfo")
def cfo_report(
    db: Session = Depends(get_db),
    u=Depends(current_user)
):
    from sqlalchemy import case

    revenue_types = ("revenue", "income", "sale", "payment")
    expense_types = ("expense", "purchase", "payout")
    type_name = func.lower(Transaction.type)
    daily_rows = db.query(
        Transaction.date,
        func.coalesce(func.sum(case((type_name.in_(revenue_types), Transaction.amount), else_=0)), 0).label("revenue"),
        func.coalesce(func.sum(case((type_name.in_(expense_types), Transaction.amount), else_=0)), 0).label("expenses"),
    ).filter(Transaction.date.isnot(None)).group_by(Transaction.date).order_by(Transaction.date).all()
    expense_rows = db.query(
        Transaction.type,
        func.coalesce(func.sum(Transaction.amount), 0).label("amount"),
        func.count(Transaction.id).label("count"),
    ).filter(type_name.in_(expense_types)).group_by(Transaction.type).order_by(func.sum(Transaction.amount).desc()).all()
    report_metrics = metrics(db)

    return {
        "title": "CFO Executive Report",

        "metrics": report_metrics,
        "cash_flow_trend": [
            {
                "date": row.date,
                "revenue": round(float(row.revenue or 0), 2),
                "expenses": round(float(row.expenses or 0), 2),
                "net_cash_flow": round(float(row.revenue or 0) - float(row.expenses or 0), 2),
            }
            for row in daily_rows
        ],
        "expense_breakdown": [
            {
                "type": str(row.type or "Unclassified").title(),
                "amount": round(float(row.amount or 0), 2),
                "count": int(row.count or 0),
            }
            for row in expense_rows
        ],

        "priority_actions": [
            "Review high-risk transactions",
            "Investigate reconciliation variances",
            "Monitor liquidity and budget variance",
        ],

        "data_note":
            "Accounting measures not supported by the source CSV are marked Insufficient source data.",
    }


# ============================================================
# ALERTS
# ============================================================

@router.get("/alerts")
def alerts(
    db: Session = Depends(get_db),
    u=Depends(current_user)
):

    m = metrics(db)

    out = []

    if m["high_risk"]:
        out.append(
            {
                "severity": "HIGH",
                "message":
                    f"{m['high_risk']} high-risk transactions require review.",
            }
        )

    if m["reconciliation_rate"] < 95:
        out.append(
            {
                "severity": "WARNING",
                "message":
                    "Reconciliation rate is below 95%.",
            }
        )

    return out


# ============================================================
# AI COPILOT
# ============================================================

class Question(BaseModel):
    question: str


@router.post("/copilot")
def copilot(
    b: Question,
    db: Session = Depends(get_db),
    u=Depends(current_user)
):
    m = metrics(db)
    current_run_id = m["reconciliation"].get("run_id")

    # -------------------------------------------------
    # Previous run context (for "what changed" questions)
    # -------------------------------------------------

    if current_run_id:
        previous_run = (
            db.query(ReconciliationRun)
            .filter(
                ReconciliationRun.status == "COMPLETED",
                ReconciliationRun.run_id != current_run_id,
            )
            .order_by(
                ReconciliationRun.created_at.desc(),
                ReconciliationRun.id.desc(),
            )
            .first()
        )
        m["previous_reconciliation"] = (
            {
                "run_id": previous_run.run_id,
                "mode": previous_run.mode,
                "filename": previous_run.filename,
                "bank_filename": previous_run.bank_filename,
                "ledger_filename": previous_run.ledger_filename,
                "settlement_filename": previous_run.settlement_filename,
                "files": [
                    name
                    for name in (
                        previous_run.filename,
                        previous_run.bank_filename,
                        previous_run.ledger_filename,
                        previous_run.settlement_filename,
                    )
                    if name
                ],
                "total": previous_run.total,
                "matched": previous_run.matched,
                "exceptions": previous_run.exceptions,
                "match_rate": previous_run.match_rate,
                "variance": previous_run.total_variance,
                "created_at": previous_run.created_at.isoformat()
                if previous_run.created_at
                else None,
            }
            if previous_run
            else None
        )
    else:
        m["previous_reconciliation"] = None

    # -------------------------------------------------
    # Reconciliation context
    # -------------------------------------------------

    reconciliation_rows = (
        db.query(ReconciliationResult)
        .filter(ReconciliationResult.run_id == current_run_id)
        .order_by(
            ReconciliationResult.variance.desc()
        )
        .all()
    )

    reconciliation_context = []

    for r in reconciliation_rows:
        t = (
            db.query(Transaction)
            .filter(
                Transaction.transaction_id
                == r.transaction_id
            )
            .first()
        )

        review = (
            db.query(ReviewItem)
            .filter(
                ReviewItem.run_id == r.run_id,
                ReviewItem.transaction_id
                == r.transaction_id
            )
            .first()
        )

        reconciliation_context.append({
            "run_id": r.run_id,
            "transaction_id":
                r.transaction_id,

            "reconciliation_status":
                r.status,

            "variance":
                round(abs(r.variance or 0), 2),

            "reason":
                r.reason,

            "review_status":
                review.status
                if review
                else "NOT_QUEUED",

            "review_note":
                review.note
                if review
                else None,

            "amount":
                round(t.amount, 2)
                if t
                else None,

            "settlement_amount":
                round(t.settlement_amount, 2)
                if t and t.settlement_amount is not None
                else None,

            "merchant":
                t.merchant
                if t
                else None,

            "vendor":
                t.vendor
                if t
                else None,

            "date":
                t.date
                if t
                else None,

            "category":
                t.category
                if t
                else None,

            "currency":
                t.currency
                if t
                else "INR",
        })

    # -------------------------------------------------
    # Risk context
    # -------------------------------------------------

    risk_query = db.query(RiskAssessment)
    if current_run_id:
        risk_query = risk_query.filter(
            RiskAssessment.risk_factors.like(
                f"%{run_marker(current_run_id)}%"
            )
        )
    risk_rows = (
        risk_query
        .order_by(
            RiskAssessment.risk_score.desc()
        )
        .limit(50)
        .all()
    )

    risk_context = []

    for r in risk_rows:
        risk_context.append({
            "transaction_id":
                r.transaction_id,

            "risk_score":
                round(r.risk_score, 2),

            "risk_level":
                r.risk_level,

            "risk_factors":
                _clean_risk_factors(r.risk_factors),
        })

    # -------------------------------------------------
    # Review queue context
    # -------------------------------------------------

    review_rows = (
        db.query(ReviewItem)
        .filter(ReviewItem.run_id == current_run_id)
        .order_by(
            ReviewItem.id.desc()
        )
        .all()
    )

    review_context = []

    for r in review_rows:
        review_context.append({
            "id":
                r.id,

            "run_id":
                r.run_id,

            "transaction_id":
                r.transaction_id,

            "status":
                r.status,

            "note":
                r.note,
        })

    # -------------------------------------------------
    # Merge run-scoped risk into reconciliation records
    # -------------------------------------------------

    risk_by_tx = {
        r["transaction_id"]: r
        for r in risk_context
    }

    for record in reconciliation_context:
        risk = risk_by_tx.get(record["transaction_id"])
        if risk:
            record["risk_level"] = risk.get("risk_level")
            record["risk_score"] = risk.get("risk_score")
            record["risk_factors"] = risk.get("risk_factors")

    # -------------------------------------------------
    # Combined AI context
    # -------------------------------------------------

    m["reconciliation_records"] = (
        reconciliation_context
    )

    m["risk_records"] = risk_context

    m["review_records"] = review_context

    provider_key = settings.ai_api_key
    provider_model = None
    if settings.ai_provider.lower() == "openai":
        provider_key = settings.openai_api_key
        provider_model = settings.openai_model
    elif settings.ai_provider.lower() == "gemini":
        provider_key = settings.gemini_api_key
        provider_model = settings.gemini_model

    answer = get_provider(
        settings.ai_provider,
        provider_key,
        provider_model,
    ).answer(
        b.question,
        m
    )

    disclosure = (
        "Financial calculations and risk metrics are generated "
        "deterministically from the reconciliation data. AI is used "
        "for explanation, prioritization, and controller guidance."
    )

    return {
        "answer":
            answer
            + (chr(10) * 2)
            + disclosure
    }


# ============================================================
# AUDIT
# ============================================================

@router.get("/audit")
def audit(
    db: Session = Depends(get_db),
    u=Depends(current_user)
):

    return [
        {
            "action": x.action,

            "user": x.user_email,

            "entity": x.entity,

            "detail": x.detail,

            "created_at":
                x.created_at.isoformat(),
        }
        for x in (
            db.query(AuditLog)
            .order_by(AuditLog.id.desc())
            .limit(100)
        )
    ]


# ============================================================
# HEALTH
# ============================================================

@router.get("/health")
def health():

    return {
        "status": "ok",
        "ai_provider": settings.ai_provider,
    }