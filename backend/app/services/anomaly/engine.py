"""Independent, explainable statistical anomaly detection.

This engine is deliberately separate from the reconciliation exception and
risk engines. A transaction may be matched AND statistically anomalous,
mismatched AND statistically normal, or both/neither - those are different
concepts and are reported independently.

Methodology (all deterministic, no fabricated confidence):
- Amount outliers: robust z-score using the median and median absolute
  deviation (MAD) of transaction amounts. MAD falls back to standard
  deviation when MAD is zero (e.g. many identical amounts).
- Repeated/burst detection: identical rounded amounts observed more than
  `REPEAT_MIN` times are flagged as repeated-transaction activity.
- Merchant/party concentration: a single merchant (or vendor/party) that
  accounts for a large share of transaction count or value.
- Refund patterns: repeated refunds that are material relative to the
  original transaction amount.
- Fee patterns: repeated processing fees that are unusually high relative
  to the transaction amount.

Every anomaly carries a human-readable reason and evidence that explains
exactly WHY it was flagged and how the threshold was derived. Nothing here
should be interpreted as a probabilistic statement about the future.
"""

from __future__ import annotations

import math
import statistics
from typing import Any, Iterable

# Minimum number of transactions before amount-based statistics are used.
# Below this the dataset is too small for meaningful baselines.
MIN_SAMPLE = 10

# Robust z-score threshold for an amount outlier.
ROBUST_Z_THRESHOLD = 3.5

# A rounded amount seen this many times is treated as repeated activity.
REPEAT_MIN = 3

# A merchant/party owning >= this share of count OR value is concentrated.
CONCENTRATION_SHARE = 0.60

# Refund flagged when refund_amount > this share of the transaction amount.
REFUND_RATIO = 0.10
REFUND_MIN_COUNT = 3

# Fee flagged when fee > this share of the transaction amount.
FEE_RATIO = 0.05
FEE_MIN_COUNT = 3


def _value(transaction: Any, attr: str):
    """Read an attribute from an ORM row or a mapping, tolerating absence."""
    if isinstance(transaction, dict):
        return transaction.get(attr)
    return getattr(transaction, attr, None)


def _amount(transaction: Any) -> float:
    value = _value(transaction, "amount")
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _text(transaction: Any, *attrs: str) -> str:
    for attr in attrs:
        value = _value(transaction, attr)
        if value:
            return str(value).strip()
    return ""


def _share_description(count: int, value: float, total_count: int, total_value: float) -> str:
    parts = []
    if total_count:
        parts.append(f"{count}/{total_count} transactions ({count / total_count * 100:.1f}%)")
    if total_value:
        parts.append(f"₹{value:,.2f} of ₹{total_value:,.2f} value ({value / total_value * 100:.1f}%)")
    return ", ".join(parts)


def _score_for_outlier(robust_z: float) -> int:
    """Deterministic 0-100 score derived from the robust z-score magnitude."""
    return min(100, int(round(30 + min(abs(robust_z), 12.0) * 6)))


def _severity_for_outlier(robust_z: float) -> str:
    if robust_z >= 6:
        return "HIGH"
    return "MEDIUM"


def _outlier_anomaly(transaction: Any, median: float, scale: float, robust_z: float) -> dict[str, Any]:
    amount = _amount(transaction)
    transaction_id = _text(transaction, "transaction_id", "reference", "id") or "unknown"
    method = (
        f"robust z-score {robust_z:.2f} exceeds the {ROBUST_Z_THRESHOLD:.1f} threshold "
        f"(median ₹{median:,.2f}, MAD ₹{scale:,.2f})"
    )
    return {
        "transaction_id": transaction_id,
        "category": "amount_outlier",
        "severity": _severity_for_outlier(robust_z),
        "score": _score_for_outlier(robust_z),
        "reason": (
            "Statistical anomaly: transaction amount deviates from the "
            "historical amount behavior of the dataset."
        ),
        "method": method,
        "evidence": (
            f"amount ₹{amount:,.2f}; dataset median ₹{median:,.2f}; "
            f"MAD ₹{scale:,.2f}; robust z-score {robust_z:.2f}"
        ),
    }


def _fallback_outlier_anomaly(transaction: Any, mean: float, std: float, z: float) -> dict[str, Any]:
    amount = _amount(transaction)
    transaction_id = _text(transaction, "transaction_id", "reference", "id") or "unknown"
    return {
        "transaction_id": transaction_id,
        "category": "amount_outlier",
        "severity": "HIGH" if z >= 6 else "MEDIUM",
        "score": min(100, int(round(30 + min(abs(z), 12.0) * 6))),
        "reason": (
            "Statistical anomaly: transaction amount deviates from the "
            "historical amount behavior of the dataset."
        ),
        "method": (
            f"amounts are highly identical (MAD=0), so standard-deviation "
            f"z-score {z:.2f} exceeds the {ROBUST_Z_THRESHOLD:.1f} threshold "
            f"(mean ₹{mean:,.2f}, σ ₹{std:,.2f})"
        ),
        "evidence": (
            f"amount ₹{amount:,.2f}; dataset mean ₹{mean:,.2f}; "
            f"σ ₹{std:,.2f}; z-score {z:.2f}"
        ),
    }


def detect_amount_outliers(transactions: list[Any]) -> list[dict[str, Any]]:
    """Flag amounts that deviate from the dataset's median/MAD baseline."""
    usable = []
    for transaction in transactions:
        amount = _amount(transaction)
        if math.isfinite(amount):
            usable.append((transaction, amount))
    if len(usable) < MIN_SAMPLE:
        return []
    amounts = [amount for _, amount in usable]
    median = statistics.median(amounts)
    deviations = [abs(amount - median) for amount in amounts]
    mad = statistics.median(deviations)
    flagged = []
    if mad > 0:
        for transaction, amount in usable:
            robust_z = 0.6745 * (amount - median) / mad
            if abs(robust_z) >= ROBUST_Z_THRESHOLD:
                flagged.append(_outlier_anomaly(transaction, median, mad, robust_z))
        return flagged
    # MAD == 0: amounts are extremely concentrated (all equal to the median).
    # Fall back to a standard-deviation z-score for genuinely distinct rows.
    mean = sum(amounts) / len(amounts)
    variance = sum((amount - mean) ** 2 for amount in amounts) / len(amounts)
    std = math.sqrt(variance)
    if std <= 0:
        return []
    for transaction, amount in usable:
        z = (amount - mean) / std
        if abs(z) >= ROBUST_Z_THRESHOLD:
            flagged.append(_fallback_outlier_anomaly(transaction, mean, std, z))
    return flagged


def detect_repeated_transactions(transactions: list[Any]) -> list[dict[str, Any]]:
    """Flag identical rounded amounts repeated more than REPEAT_MIN times."""
    if len(transactions) < REPEAT_MIN:
        return []
    buckets: dict[tuple, list[Any]] = {}
    for transaction in transactions:
        amount = _amount(transaction)
        if not math.isfinite(amount):
            continue
        # Round to whole rupees so near-identical settlement amounts group.
        bucket = (round(amount), _text(transaction, "merchant", "vendor", "party"))
        buckets.setdefault(bucket, []).append(transaction)
    flagged = []
    for (amount, party), group in buckets.items():
        if len(group) < REPEAT_MIN:
            continue
        share = len(group) / len(transactions)
        if share < 0.05 and len(group) < 5:
            # Small groups are only flagged when they dominate their party.
            if not party or len(group) < REPEAT_MIN + 2:
                continue
        first = group[0]
        flagged.append({
            "transaction_id": _text(first, "transaction_id", "reference", "id") or "unknown",
            "category": "repeated_transaction",
            "severity": "MEDIUM" if share < 0.25 else "HIGH",
            "score": min(100, 30 + len(group) * 5 + (20 if share >= 0.25 else 0)),
            "reason": (
                "Statistical anomaly: repeated transactions with an identical "
                "amount suggest duplication or burst activity."
            ),
            "method": (
                f"amount ₹{amount:,.2f} observed {len(group)} times across the dataset "
                f"({len(group)}/{len(transactions)} transactions)"
            ),
            "evidence": (
                f"identical rounded amount ₹{amount:,.2f}; occurrences={len(group)}; "
                f"share={share * 100:.1f}%"
            ),
        })
    return flagged


def detect_merchant_concentration(transactions: list[Any]) -> list[dict[str, Any]]:
    """Flag datasets where one merchant/party dominates count or value."""
    if not transactions:
        return []
    by_party: dict[str, dict[str, float]] = {}
    total_count = 0
    total_value = 0.0
    for transaction in transactions:
        party = _text(transaction, "merchant", "vendor", "party") or "(unnamed)"
        amount = _amount(transaction)
        total_count += 1
        total_value += amount
        entry = by_party.setdefault(party, {"count": 0, "value": 0.0})
        entry["count"] += 1
        entry["value"] += amount
    flagged = []
    for party, stats in by_party.items():
        if not stats["count"]:
            continue
        count_share = stats["count"] / total_count
        value_share = (stats["value"] / total_value) if total_value else 0.0
        if count_share < CONCENTRATION_SHARE and value_share < CONCENTRATION_SHARE:
            continue
        flagged.append({
            "transaction_id": party,
            "category": "merchant_concentration",
            "severity": "MEDIUM" if max(count_share, value_share) < 0.85 else "HIGH",
            "score": min(100, int(round(max(count_share, value_share) * 100))),
            "reason": (
                "Statistical anomaly: a single merchant/party accounts for an "
                "unusually large share of transactions or value."
            ),
            "method": (
                f"concentration threshold {CONCENTRATION_SHARE * 100:.0f}% of count or value "
                f"({_share_description(int(stats['count']), stats['value'], total_count, total_value)})"
            ),
            "evidence": (
                f"party '{party}'; count share={count_share * 100:.1f}%; "
                f"value share={value_share * 100:.1f}%"
            ),
        })
    return flagged


def detect_refund_patterns(transactions: list[Any]) -> list[dict[str, Any]]:
    """Flag repeated refunds material relative to their transaction amount."""
    candidates = []
    for transaction in transactions:
        refund = 0.0
        try:
            refund = abs(float(_value(transaction, "refund_amount") or 0))
        except (TypeError, ValueError):
            refund = 0.0
        amount = _amount(transaction)
        if refund <= 0 or amount <= 0:
            continue
        if refund / amount >= REFUND_RATIO:
            candidates.append((transaction, refund, amount))
    if len(candidates) < REFUND_MIN_COUNT:
        return []
    flagged = []
    for transaction, refund, amount in candidates:
        flagged.append({
            "transaction_id": _text(transaction, "transaction_id", "reference", "id") or "unknown",
            "category": "refund_pattern",
            "severity": "MEDIUM",
            "score": min(100, 40 + int(round(refund / amount * 100))),
            "reason": (
                "Statistical anomaly: repeated refunds that are material "
                "relative to their transaction amounts."
            ),
            "method": (
                f"{len(candidates)} transactions carry refunds >= {REFUND_RATIO * 100:.0f}% of "
                f"their amount (minimum {REFUND_MIN_COUNT} required)"
            ),
            "evidence": (
                f"refund ₹{refund:,.2f} vs amount ₹{amount:,.2f} "
                f"({refund / amount * 100:.1f}%)"
            ),
        })
    return flagged


def detect_fee_patterns(transactions: list[Any]) -> list[dict[str, Any]]:
    """Flag repeated fees unusually high relative to their transaction amount."""
    candidates = []
    for transaction in transactions:
        fee = 0.0
        try:
            fee = abs(float(_value(transaction, "fee") or 0))
        except (TypeError, ValueError):
            fee = 0.0
        amount = _amount(transaction)
        if fee <= 0 or amount <= 0:
            continue
        if fee / amount >= FEE_RATIO:
            candidates.append((transaction, fee, amount))
    if len(candidates) < FEE_MIN_COUNT:
        return []
    flagged = []
    for transaction, fee, amount in candidates:
        flagged.append({
            "transaction_id": _text(transaction, "transaction_id", "reference", "id") or "unknown",
            "category": "fee_pattern",
            "severity": "MEDIUM",
            "score": min(100, 35 + int(round(fee / amount * 100))),
            "reason": (
                "Statistical anomaly: repeated processing fees unusually high "
                "relative to their transaction amounts."
            ),
            "method": (
                f"{len(candidates)} transactions carry fees >= {FEE_RATIO * 100:.0f}% of "
                f"their amount (minimum {FEE_MIN_COUNT} required)"
            ),
            "evidence": (
                f"fee ₹{fee:,.2f} vs amount ₹{amount:,.2f} "
                f"({fee / amount * 100:.1f}%)"
            ),
        })
    return flagged


def analyze_transactions(transactions: Iterable[Any]) -> dict[str, Any]:
    """Run every detector and return deduplicated anomalies plus a summary.

    Returns:
        {
          "anomalies": [ ... deterministic anomaly dicts ... ],
          "detectors_run": [ ... detector names actually executed ... ],
          "sample_size": int,
          "note": str | None,   # e.g. sample too small for amount statistics
        }
    """
    transactions = list(transactions)
    results: dict[tuple, dict[str, Any]] = {}
    note = None
    if len(transactions) < MIN_SAMPLE:
        note = (
            f"Dataset has {len(transactions)} transactions; at least {MIN_SAMPLE} "
            "are required for reliable amount statistics. Smaller datasets are "
            "only checked for repeated-transaction and concentration patterns."
        )
    detectors = [
        ("amount_outliers", detect_amount_outliers(transactions)),
        ("repeated_transactions", detect_repeated_transactions(transactions)),
        ("merchant_concentration", detect_merchant_concentration(transactions)),
        ("refund_patterns", detect_refund_patterns(transactions)),
        ("fee_patterns", detect_fee_patterns(transactions)),
    ]
    for detector_name, anomalies in detectors:
        for anomaly in anomalies:
            key = (anomaly["category"], anomaly.get("transaction_id"))
            results[key] = anomaly
    anomalies = sorted(
        results.values(),
        key=lambda item: (item.get("score", 0), item.get("category", "")),
        reverse=True,
    )
    return {
        "anomalies": anomalies,
        "sample_size": len(transactions),
        "note": note,
        "detectors_run": [name for name, _ in detectors],
    }
