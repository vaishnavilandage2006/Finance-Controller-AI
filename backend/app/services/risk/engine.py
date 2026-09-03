from ...models import Transaction


def calculate(t, variance=0, duplicate=False, frequency=False):
    """Legacy scoring used by seed/import flows. Kept unchanged so seeded
    data and existing tests keep their original semantics."""
    score = 0; factors = []
    if t.amount > 100000:
        score += 30; factors.append("amount anomaly")
    if variance > 1:
        score += 25; factors.append("settlement variance")
    if duplicate:
        score += 25; factors.append("duplicate-like activity")
    if frequency:
        score += 20; factors.append("frequency anomaly")
    score = min(100, score)
    level = "LOW" if score <= 30 else "MEDIUM" if score <= 60 else "HIGH" if score <= 80 else "CRITICAL"
    return score, level, factors


# ============================================================
# RUNTIME EXCEPTION RISK ENGINE
# ------------------------------------------------------------
# Used after every reconciliation run to score the exceptions of
# that run. Materiality-aware and additive: it never replaces the
# legacy calculate() above, which remains for seeded/import data.
# ============================================================

RISK_RUN_PREFIX = "source_run:"


def assess_exception(
    transaction_ref: str,
    amount: float | None = None,
    settlement_amount: float | None = None,
    variance: float | None = None,
    category: str | None = None,
) -> tuple[int, str, list[str]]:
    """Score a single reconciliation exception by financial impact.

    Score = base(variance band) + ratio bonus + amount bonus, capped at 100.
    Levels: >=80 CRITICAL, >=60 HIGH, >=30 MEDIUM, <30 LOW.

    Base bands (absolute variance, INR):
       >= 50,000 -> 80 | >= 10,000 -> 70 | >= 5,000 -> 65 | >= 1,000 -> 60
       >= 500 -> 45   | >= 100 -> 32    | >= 10 -> 20    | 0 < v < 10 -> 12
       v == 0 (PARTIAL/DUPLICATE without variance evidence) -> 10
    Ratio bonus (variance / transaction amount):
       >= 20% -> +15 | >= 10% -> +10 | >= 5% -> +5
    Amount bonus: >= 1,000,000 -> +20 | >= 100,000 -> +10

    A genuine ~1,400 INR exception therefore scores 65 (HIGH), and matched
    rows (variance ~0) never enter this path.
    """
    variance = abs(float(variance or 0))
    amount = abs(float(amount or 0))
    if variance >= 50000:
        base = 80
    elif variance >= 10000:
        base = 70
    elif variance >= 5000:
        base = 65
    elif variance >= 1000:
        base = 60
    elif variance >= 500:
        base = 45
    elif variance >= 100:
        base = 32
    elif variance >= 10:
        base = 20
    elif variance > 0:
        base = 12
    else:
        base = 10
    ratio = (variance / amount) if amount > 0 else 0.0
    if ratio >= 0.20:
        ratio_bonus = 15
    elif ratio >= 0.10:
        ratio_bonus = 10
    elif ratio >= 0.05:
        ratio_bonus = 5
    else:
        ratio_bonus = 0
    if amount >= 1000000:
        amount_bonus = 20
    elif amount >= 100000:
        amount_bonus = 10
    else:
        amount_bonus = 0
    score = min(100, base + ratio_bonus + amount_bonus)
    if score >= 80:
        level = "CRITICAL"
    elif score >= 60:
        level = "HIGH"
    elif score >= 30:
        level = "MEDIUM"
    else:
        level = "LOW"
    factors = []
    if variance >= 1000:
        factors.append(f"material settlement variance (₹{variance:,.2f})")
    elif variance >= 100:
        factors.append(f"settlement variance (₹{variance:,.2f})")
    elif variance > 0:
        factors.append(f"small settlement variance (₹{variance:,.2f})")
    else:
        factors.append("exception without settlement variance")
    if ratio >= 0.05:
        factors.append(f"variance is {ratio * 100:.1f}% of transaction amount")
    if amount >= 100000:
        factors.append("high transaction amount")
    if category:
        factors.append(f"category: {category}")
    return score, level, factors


def run_marker(run_id: str) -> str:
    """Marker embedded in the risk_factors JSON list for run isolation."""
    return f"{RISK_RUN_PREFIX}{run_id}"


def split_run_marker(factors_text: str | None) -> tuple[list[str], str | None]:
    """Return (clean factor list, run_id). Stored risk_factors is a JSON list
    that may embed one 'source_run:<run_id>' entry for run isolation; that
    entry is stripped from every consumer-facing factor list."""
    import json

    try:
        factors = json.loads(factors_text or "[]")
    except (TypeError, ValueError):
        return [], None
    if not isinstance(factors, list):
        return [], None
    run_id = None
    clean = []
    for factor in factors:
        text = str(factor)
        if text.startswith(RISK_RUN_PREFIX):
            run_id = text[len(RISK_RUN_PREFIX):] or None
        else:
            clean.append(factor)
    return clean, run_id
