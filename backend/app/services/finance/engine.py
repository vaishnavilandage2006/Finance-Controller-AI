from sqlalchemy import func


REVENUE_TYPES = ("revenue", "income", "sale", "payment")
EXPENSE_TYPES = ("expense", "purchase", "payout")
EXCEPTION_STATUSES = {"PARTIAL", "MISMATCH", "UNMATCHED", "DUPLICATE", "EXCEPTION"}


def current_run(db):
    """Single authoritative current-run resolver: the latest COMPLETED
    reconciliation run. Every downstream module defaults to this run so the
    UI always operates on the most recent upload rather than on a mix of
    the current run and historical database rows."""
    from ...models import ReconciliationRun

    return (
        db.query(ReconciliationRun)
        .filter(ReconciliationRun.status == "COMPLETED")
        .order_by(ReconciliationRun.created_at.desc(), ReconciliationRun.id.desc())
        .first()
    )


def resolve_run(db, run_id):
    """Resolve an explicit run_id when provided, otherwise fall back to the
    current run. Historical runs stay reachable via their run_id; the
    default is always the latest completed run."""
    if run_id:
        from ...models import ReconciliationRun

        return (
            db.query(ReconciliationRun)
            .filter(ReconciliationRun.run_id == run_id)
            .first()
        )
    return current_run(db)


def current_run_transaction_ids(db, run):
    """Set of transaction_ids belonging to a reconciliation run. Returns
    None when there is no run so callers can keep the legacy unscoped
    behaviour (fresh databases / direct transaction seeding)."""
    if run is None:
        return None
    from ...models import ReconciliationResult

    rows = (
        db.query(ReconciliationResult.transaction_id)
        .filter(ReconciliationResult.run_id == run.run_id)
        .all()
    )
    return {row.transaction_id for row in rows}


def _level_counts(rows):
    counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
    for row in rows:
        level = str(row.risk_level or "").upper()
        counts[level] = counts.get(level, 0) + 1
    return counts


def _financial_from_transactions(txns):
    """Run-scoped financial metrics with honest availability flags.

    Revenue/expenses are only considered available when the run's own
    transactions carry an explicit financial classification; refunds/fees
    only when the run carries non-zero refund/fee values. This prevents
    stale seeded P&L values from leaking into a run whose uploaded file
    does not provide those fields.
    """
    revenue = sum(t.amount for t in txns if (t.type or "").lower() in REVENUE_TYPES)
    expenses = sum(t.amount for t in txns if (t.type or "").lower() in EXPENSE_TYPES)
    refunds = sum(float(t.refund_amount or 0) for t in txns)
    fees = sum(float(t.fee or 0) for t in txns)
    has_revenue = any((t.type or "").lower() in REVENUE_TYPES for t in txns)
    has_expenses = any((t.type or "").lower() in EXPENSE_TYPES for t in txns)
    has_refunds = any(abs(float(t.refund_amount or 0)) > 0 for t in txns)
    has_fees = any(abs(float(t.fee or 0)) > 0 for t in txns)
    net = revenue - expenses - refunds - fees
    pnl = has_revenue and has_expenses
    return {
        "revenue": {"available": has_revenue, "value": round(revenue, 2)},
        "expenses": {"available": has_expenses, "value": round(expenses, 2)},
        "refunds": {"available": has_refunds, "value": round(refunds, 2)},
        "fees": {"available": has_fees, "value": round(fees, 2)},
        "net_profit": {"available": pnl, "value": round(net, 2)},
        "cash_balance": {"available": pnl, "value": round(net, 2)},
    }


def metrics(db):
    from ...models import Transaction, RiskAssessment, ReconciliationResult

    # ------------------------------------------------------------------
    # Single authoritative current run: every value below derives from it
    # when one exists; a fresh database (no runs yet) keeps the legacy
    # global aggregation so direct transaction seeding still works.
    # ------------------------------------------------------------------
    latest_run = current_run(db)
    if latest_run:
        rec = db.query(ReconciliationResult).filter(
            ReconciliationResult.run_id == latest_run.run_id
        ).all()
        from ..risk.engine import run_marker
        risk_rows = db.query(RiskAssessment).filter(
            RiskAssessment.risk_factors.like("%" + run_marker(latest_run.run_id) + "%")
        ).all()
    else:
        rec = db.query(ReconciliationResult).all()
        risk_rows = db.query(RiskAssessment).all()
    risks = sum(1 for r in risk_rows if (r.risk_score or 0) >= 61)
    if latest_run:
        reconciliation = {
            "total": latest_run.total,
            "matched": latest_run.matched,
            "partial": latest_run.partial,
            "mismatch": max(latest_run.exceptions - latest_run.partial - latest_run.unmatched - latest_run.duplicate, 0),
            "unmatched": latest_run.unmatched,
            "duplicate": latest_run.duplicate,
            "exceptions": latest_run.exceptions,
            "match_rate": latest_run.match_rate,
            "variance": latest_run.total_variance,
            "run_id": latest_run.run_id,
            "mode": latest_run.mode,
            "created_at": latest_run.created_at.isoformat() if latest_run.created_at else None,
        }
    else:
        matched = sum(1 for r in rec if r.status == "MATCHED")
        reconciliation = {
            "total": len(rec),
            "matched": matched,
            "partial": sum(r.status == "PARTIAL" for r in rec),
            "mismatch": sum(r.status == "MISMATCH" for r in rec),
            "unmatched": sum(r.status == "UNMATCHED" for r in rec),
            "duplicate": sum(r.status == "DUPLICATE" for r in rec),
            "exceptions": len(rec) - matched,
            "match_rate": matched / len(rec) * 100 if rec else 0,
            "variance": sum(abs(float(r.variance or 0)) for r in rec),
            "run_id": None,
            "mode": None,
            "created_at": None,
        }
    scoped_results = [r for r in rec if latest_run and r.run_id == latest_run.run_id]

    # ----------------------------------------------------------
    # Current-run display metadata (files, mode, status)
    # ----------------------------------------------------------
    run_metadata = None
    if latest_run:
        run_metadata = {
            "run_id": latest_run.run_id,
            "mode": latest_run.mode,
            "status": latest_run.status,
            "created_at": latest_run.created_at.isoformat() if latest_run.created_at else None,
            "filename": latest_run.filename,
            "bank_filename": latest_run.bank_filename,
            "ledger_filename": latest_run.ledger_filename,
            "settlement_filename": latest_run.settlement_filename,
            "files": [
                name for name in (
                    latest_run.filename,
                    latest_run.bank_filename,
                    latest_run.ledger_filename,
                    latest_run.settlement_filename,
                )
                if name
            ],
        }

    # ----------------------------------------------------------
    # Run-scoped risk distribution (current run only)
    # ----------------------------------------------------------
    risk_distribution = _level_counts(risk_rows)

    # ----------------------------------------------------------
    # Run-scoped financial metrics (availability-aware)
    # ----------------------------------------------------------
    scope_ids = {r.transaction_id for r in scoped_results}
    scope_txns = (
        db.query(Transaction)
        .filter(Transaction.transaction_id.in_(scope_ids))
        .all()
        if scope_ids
        else []
    )
    financial = _financial_from_transactions(scope_txns)

    # ----------------------------------------------------------
    # Largest exception + top exceptions for the Overview chart
    # ----------------------------------------------------------
    tx_by_id = {t.transaction_id: t for t in scope_txns}
    exception_rows = [
        r for r in scoped_results
        if (r.status or "").upper() in EXCEPTION_STATUSES
    ]
    exception_rows.sort(key=lambda r: abs(float(r.variance or 0)), reverse=True)
    top_exceptions = []
    for r in exception_rows[:10]:
        t = tx_by_id.get(r.transaction_id)
        top_exceptions.append({
            "transaction_id": r.transaction_id,
            "status": r.status,
            "variance": round(abs(float(r.variance or 0)), 2),
            "reason": r.reason,
            "amount": round(float(t.amount), 2) if t and t.amount is not None else None,
            "settlement_amount": (
                round(float(t.settlement_amount), 2)
                if t and t.settlement_amount is not None
                else None
            ),
            "merchant": t.merchant if t else None,
            "vendor": t.vendor if t else None,
        })
    largest_exception = top_exceptions[0] if top_exceptions else None

    # ------------------------------------------------------------------
    # Top-level convenience metrics: scoped to the current run when one
    # exists (so the dashboard/settings/Copilot never mix the current run
    # with historical database rows). Values mirror the availability-aware
    # ``financial`` block: a run whose source CSV carries no revenue/
    # expense/refund/fee dimension reports those as unavailable, never as
    # invented non-zero totals.
    # ------------------------------------------------------------------
    if latest_run:
        total_transactions = latest_run.total
        revenue = financial["revenue"]["value"]
        expenses = financial["expenses"]["value"]
        refunds = financial["refunds"]["value"]
        fees = financial["fees"]["value"]
        net_profit = financial["net_profit"]["value"]
        cash_balance = financial["cash_balance"]["value"]
    else:
        # Legacy global aggregation for databases without any run yet.
        total_transactions = db.query(func.count(Transaction.id)).scalar() or 0
        revenue = db.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
            func.lower(Transaction.type).in_(REVENUE_TYPES)
        ).scalar() or 0
        expenses = db.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
            func.lower(Transaction.type).in_(EXPENSE_TYPES)
        ).scalar() or 0
        refunds = db.query(func.coalesce(func.sum(Transaction.refund_amount), 0)).scalar() or 0
        fees = db.query(func.coalesce(func.sum(Transaction.fee), 0)).scalar() or 0
        net_profit = revenue - expenses - refunds - fees
        cash_balance = net_profit

    return {
        "revenue": revenue,
        "expenses": expenses,
        "net_profit": net_profit,
        "refunds": refunds,
        "fees": fees,
        "high_risk": risks,
        "total_transactions": total_transactions,
        "reconciliation_rate": reconciliation["match_rate"],
        "cash_balance": cash_balance,
        "currency": "INR",
        "largest_variance": max([abs(r.variance) for r in scoped_results], default=0),
        "reconciliation": reconciliation,
        # ---- current-run additions (Overview / charts) ----
        "current_run": run_metadata,
        "risk_distribution": risk_distribution,
        "top_exceptions": top_exceptions,
        "largest_exception": largest_exception,
        "financial": financial,
    }


def risk_score(t, variance=0, duplicate=False, frequency=False):
    score = 0
    factors = []
    if t.amount > 100000:
        score += 30
        factors.append("amount anomaly")
    if variance > 1:
        score += 25
        factors.append("settlement variance")
    if duplicate:
        score += 25
        factors.append("duplicate-like activity")
    if frequency:
        score += 20
        factors.append("frequency anomaly")
    score = min(100, score)
    level = "LOW" if score <= 30 else "MEDIUM" if score <= 60 else "HIGH" if score <= 80 else "CRITICAL"
    return score, level, factors
