"""Server-side, role-aware scoping of the Copilot AI context (privacy firewall).

Rules enforced here:

- The backend is the source of truth for authorization. The AI never sees
  context the authenticated user's role is not allowed to see; scoping the
  context server-side is the enforcement point, not frontend hiding.
- Data minimization: passwords, password hashes, JWT tokens, API keys and
  other credentials never exist in any AI context (they are not collected
  here at all).
- Personnel records: only what is needed for the current finance-control
  task. No personal identifiers, contact details or private attributes are
  added to AI context.
- Unknown roles map to the least-privileged bucket.

Final per-tier matrix:

  cfo      (Admin, CFO / Manager, Finance Controller)
           -> full context: overview incl. named exceptions and financial
              availability, reconciliation records, risk, review queue,
              statistical anomalies, previous-run history
  manager  (Finance Manager)
           -> operational context: numeric overview, reconciliation records,
              risk, review queue, statistical anomalies
           (no CFO-only current-run metadata / named exception panels)
  analyst  (Finance Analyst)
           -> investigation context: numeric overview + reconciliation
              records (transaction level) + statistical anomalies
  reviewer (Reviewer)
           -> decision context: only the review queue items with the
              evidence (amounts, variance, reason, date) a decision needs
  user     (any other role)
           -> numeric overview metrics only (matches the read-only API
              surface any authenticated user already has)
"""

from __future__ import annotations

# Canonical role -> tier. Unknown roles default to "user".
ROLE_TIERS = {
    "Admin": "cfo",
    "CFO / Manager": "cfo",
    "Finance Controller": "cfo",
    "Finance Manager": "manager",
    "Finance Analyst": "analyst",
    "Reviewer": "reviewer",
}

DEFAULT_TIER = "user"

TIER_LABELS = {
    "cfo": "CFO / controller",
    "manager": "Finance Manager",
    "analyst": "Finance Analyst",
    "reviewer": "Reviewer",
    "user": "standard user",
}

# Numeric-only metrics. Safe for every tier (matches open read-only API).
NUMERIC_OVERVIEW_KEYS = (
    "revenue", "expenses", "net_profit", "refunds", "fees", "high_risk",
    "total_transactions", "reconciliation_rate", "cash_balance", "currency",
    "largest_variance", "risk_distribution", "reconciliation",
)

# Named/record-level context: full overview extras (CFO/controller only).
NAMED_OVERVIEW_KEYS = (
    "current_run", "top_exceptions", "largest_exception", "financial",
    "previous_reconciliation",
)

# Capability buckets per tier (used by the AI providers for question gating).
TIER_CAPABILITIES = {
    "cfo": {"overview", "reconciliation", "risk", "review", "history", "anomaly"},
    "manager": {"overview", "reconciliation", "risk", "review", "anomaly"},
    "analyst": {"overview", "reconciliation", "anomaly"},
    "reviewer": {"review"},
    "user": {"overview"},
}

REVIEW_EVIDENCE_KEYS = (
    "transaction_id", "status", "variance", "reason", "amount",
    "settlement_amount", "date",
)


def role_tier(role: str | None) -> str:
    role = (role or "").strip()
    return ROLE_TIERS.get(role, DEFAULT_TIER)


def tier_label(tier: str) -> str:
    return TIER_LABELS.get(tier, TIER_LABELS[DEFAULT_TIER])


def capabilities_for(tier: str) -> set[str]:
    return set(TIER_CAPABILITIES.get(tier, set()))


def role_capabilities(role: str | None) -> set[str]:
    return capabilities_for(role_tier(role))


def authorized_scope_text(tier: str) -> str:
    """Human summary of what a tier is authorized to ask the Copilot."""
    if tier == "cfo":
        return "financial overview, risk, forecasting/scenarios, review, anomalies, audit/control context"
    if tier == "manager":
        return "reconciliation exceptions, review queue, risk prioritization and operational finance"
    if tier == "analyst":
        return "transaction investigation, reconciliation details and statistical anomaly data"
    if tier == "reviewer":
        return "authorized review items and the evidence needed to decide on them"
    return "high-level financial metrics already available on your dashboard"


def _pick(context: dict, keys) -> dict:
    return {key: context[key] for key in keys if key in context}


def _reviewer_review_records(context: dict) -> list[dict]:
    """Review items enriched only with the evidence a decision requires.

    Merchant/vendor/party identifiers are excluded: a reviewer receives the
    transaction identifier, amounts, variance, reason, date and review state
    - nothing else.
    """
    by_transaction = {
        record.get("transaction_id"): record
        for record in context.get("reconciliation_records", [])
    }
    enriched = []
    for item in context.get("review_records", []):
        record = {
            key: item.get(key)
            for key in ("id", "run_id", "transaction_id", "status", "note",
                        "created_at")
        }
        evidence = by_transaction.get(item.get("transaction_id")) or {}
        for key in ("amount", "settlement_amount", "variance", "date"):
            if evidence.get(key) is not None:
                record[key] = evidence.get(key)
        enriched.append(record)
    return enriched


def _analyst_summary(context: dict) -> dict:
    """Numeric-only reconciliation summary for investigation questions."""
    summary = {}
    reconciliation = context.get("reconciliation")
    if isinstance(reconciliation, dict):
        for key in ("total", "matched", "exceptions", "partial", "mismatch",
                    "unmatched", "duplicate", "match_rate", "variance"):
            if key in reconciliation:
                summary[key] = reconciliation[key]
    return summary


def scope_ai_context(context: dict, tier: str) -> dict:
    """Return a NEW context dict containing only what `tier` may see.

    The caller's dict is never mutated. The returned dict is fully authorized
    for the AI provider - no further filtering happens downstream.
    """
    scoped: dict[str, object] = {}

    if tier == "cfo":
        scoped.update(_pick(context, NUMERIC_OVERVIEW_KEYS))
        scoped.update(_pick(context, NAMED_OVERVIEW_KEYS))
        scoped["reconciliation_records"] = context.get("reconciliation_records", [])
        scoped["risk_records"] = context.get("risk_records", [])
        scoped["review_records"] = context.get("review_records", [])
        scoped["anomaly_records"] = context.get("anomaly_records", [])
        return scoped

    if tier == "manager":
        scoped.update(_pick(context, NUMERIC_OVERVIEW_KEYS))
        scoped["reconciliation_records"] = context.get("reconciliation_records", [])
        scoped["risk_records"] = context.get("risk_records", [])
        scoped["review_records"] = context.get("review_records", [])
        scoped["anomaly_records"] = context.get("anomaly_records", [])
        return scoped

    if tier == "analyst":
        scoped.update(_pick(context, NUMERIC_OVERVIEW_KEYS))
        scoped["reconciliation_records"] = context.get("reconciliation_records", [])
        scoped["anomaly_records"] = context.get("anomaly_records", [])
        return scoped

    if tier == "reviewer":
        scoped.update(_pick(context, ("currency",)))
        scoped["review_records"] = _reviewer_review_records(context)
        return scoped

    # user (least privilege): numeric overview only.
    scoped.update(_pick(context, NUMERIC_OVERVIEW_KEYS))
    return scoped
