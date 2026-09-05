"""Independent validation oracle for reconciliation and risk expectations.

This module intentionally does NOT import the application's reconciliation,
risk or anomaly engines. It implements the DOCUMENTED behavior of those
specifications from first principles so the test suite can compare the
application's output against an independently computed expectation.

Documented spec implemented here (matching the product's published rules):

Single-file reconciliation (per record):
  - duplicate reference in the file          -> DUPLICATE
  - no settlement amount supplied            -> PARTIAL
  - |amount - settlement| <= 0.01            -> MATCHED
  - otherwise                                -> MISMATCH
  - per-record variance = |amount - settlement| (0 when no settlement)
  - total variance = sum of per-record variances
  - match_rate = matched / total * 100 (rounded to 2 decimals)

Multi-file reconciliation (per reference group):
  - a source with more than one record       -> DUPLICATE
  - fewer than two sources present           -> UNMATCHED
  - |max(amounts) - min(amounts)| > 0.01     -> MISMATCH
  - settlement file supplied but no
    SETTLEMENT record for the group          -> PARTIAL
  - otherwise                                -> MATCHED

Risk level for a run exception (documented assess_exception bands):
  base by variance, + ratio bonus (variance/amount), + amount bonus,
  level thresholds 80 CRITICAL / 60 HIGH / 30 MEDIUM / else LOW.
"""

from __future__ import annotations

from typing import Iterable

TOLERANCE = 0.01

STATUS_MATCHED = "MATCHED"
STATUS_MISMATCH = "MISMATCH"
STATUS_PARTIAL = "PARTIAL"
STATUS_UNMATCHED = "UNMATCHED"
STATUS_DUPLICATE = "DUPLICATE"


def _reference(row: dict) -> str:
    return (
        row.get("transaction_id")
        or row.get("payment_reference")
        or row.get("reference")
        or ""
    ).strip()


def _amount(row: dict) -> float:
    value = row.get("amount")
    if isinstance(value, str):
        return float(value.strip())
    return float(value)


def _settlement(row: dict) -> float | None:
    value = row.get("settlement_amount")
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        return float(value) if value else None
    return float(value)


def single_file_expectation(rows: Iterable[dict]) -> dict:
    """Compute the expected single-file reconciliation summary from raw CSV
    rows. `rows` may be the generator output (dicts) or the parsed records
    list returned by the API (which carries the same fields)."""
    seen: set[str] = set()
    total = 0
    counts = {
        STATUS_MATCHED: 0,
        STATUS_MISMATCH: 0,
        STATUS_PARTIAL: 0,
        STATUS_UNMATCHED: 0,
        STATUS_DUPLICATE: 0,
    }
    variance_sum = 0.0
    largest = 0.0
    for row in rows:
        ref = _reference(row)
        amount = _amount(row)
        settlement = _settlement(row)
        variance = abs(amount - settlement) if settlement is not None else 0.0
        if ref in seen:
            status = STATUS_DUPLICATE
        elif settlement is None:
            status = STATUS_PARTIAL
        elif variance <= TOLERANCE:
            status = STATUS_MATCHED
        else:
            status = STATUS_MISMATCH
        seen.add(ref)
        counts[status] += 1
        total += 1
        variance_sum += variance
        largest = max(largest, variance)

    matched = counts[STATUS_MATCHED]
    return {
        "total": total,
        "matched": matched,
        "mismatch": counts[STATUS_MISMATCH],
        "partial": counts[STATUS_PARTIAL],
        "unmatched": counts[STATUS_UNMATCHED],
        "duplicate": counts[STATUS_DUPLICATE],
        "exceptions": total - matched,
        "match_rate": round(matched / total * 100, 2) if total else 0.0,
        "variance": round(variance_sum, 2),
        "largest_variance": round(largest, 2),
    }


def multi_file_expectation(
    groups: dict[str, dict[str, list[float]]],
    settlement_supplied: bool,
) -> dict:
    """Compute the expected multi-file summary from a dict of
    normalized reference -> {SOURCE: [amounts]}."""
    totals = {
        STATUS_MATCHED: 0,
        STATUS_MISMATCH: 0,
        STATUS_PARTIAL: 0,
        STATUS_UNMATCHED: 0,
        STATUS_DUPLICATE: 0,
    }
    variance_sum = 0.0
    for ref, sources in groups.items():
        roles = list(sources)
        amounts = [amount for values in sources.values() for amount in values]
        duplicate_roles = [
            role for role, values in sources.items() if len(values) > 1
        ]
        if duplicate_roles:
            status = STATUS_DUPLICATE
        elif len(roles) < 2:
            status = STATUS_UNMATCHED
        elif max(amounts) - min(amounts) > TOLERANCE:
            status = STATUS_MISMATCH
        elif settlement_supplied and "SETTLEMENT" not in roles:
            status = STATUS_PARTIAL
        else:
            status = STATUS_MATCHED
        totals[status] += 1
        variance = max(amounts) - min(amounts) if len(amounts) > 1 else 0.0
        variance_sum += abs(variance)
    matched = totals[STATUS_MATCHED]
    total = sum(totals.values())
    return {
        "total": total,
        "matched": matched,
        "mismatch": totals[STATUS_MISMATCH],
        "partial": totals[STATUS_PARTIAL],
        "unmatched": totals[STATUS_UNMATCHED],
        "duplicate": totals[STATUS_DUPLICATE],
        "exceptions": total - matched,
        "match_rate": round(matched / total * 100, 2) if total else 0.0,
        "variance": round(variance_sum, 2),
    }


def expected_risk_level(amount: float, variance: float) -> str:
    """Documented assess_exception scoring: base variance band + ratio bonus
    + amount bonus, with the published level thresholds."""
    v = abs(float(variance or 0))
    a = abs(float(amount or 0))
    if v >= 50000:
        base = 80
    elif v >= 10000:
        base = 70
    elif v >= 5000:
        base = 65
    elif v >= 1000:
        base = 60
    elif v >= 500:
        base = 45
    elif v >= 100:
        base = 32
    elif v >= 10:
        base = 20
    elif v > 0:
        base = 12
    else:
        base = 10
    ratio = v / a if a > 0 else 0.0
    if ratio >= 0.20:
        ratio_bonus = 15
    elif ratio >= 0.10:
        ratio_bonus = 10
    elif ratio >= 0.05:
        ratio_bonus = 5
    else:
        ratio_bonus = 0
    if a >= 1000000:
        amount_bonus = 20
    elif a >= 100000:
        amount_bonus = 10
    else:
        amount_bonus = 0
    score = min(100, base + ratio_bonus + amount_bonus)
    if score >= 80:
        return "CRITICAL"
    if score >= 60:
        return "HIGH"
    if score >= 30:
        return "MEDIUM"
    return "LOW"


def risk_distribution_expectation(rows: Iterable[dict]) -> dict[str, int]:
    """Expected risk distribution of a single-file run: every non-matched
    record (per the documented single-file rules) is scored and bucketed."""
    distribution = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
    seen: set[str] = set()
    for row in rows:
        ref = _reference(row)
        if ref in seen:
            status = STATUS_DUPLICATE
        else:
            seen.add(ref)
            amount = _amount(row)
            settlement = _settlement(row)
            variance = abs(amount - settlement) if settlement is not None else 0.0
            status = (
                STATUS_MATCHED
                if variance <= TOLERANCE and settlement is not None
                else STATUS_PARTIAL
                if settlement is None
                else STATUS_MISMATCH
            )
        if status == STATUS_MATCHED:
            continue
        amount = _amount(row)
        settlement = _settlement(row)
        variance = abs(amount - settlement) if settlement is not None else 0.0
        level = expected_risk_level(amount, variance)
        distribution[level] = distribution.get(level, 0) + 1
    return distribution