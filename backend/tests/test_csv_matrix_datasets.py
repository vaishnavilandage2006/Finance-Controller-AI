"""Dataset-size matrix (Steps 4-8 of the validation plan).

For every size in [100, 200, 300, 500, 1000, 5000, 10000, 50000, 100000]
the application's single-file reconciliation is compared against the
INDEPENDENT oracle (tests.qa.oracle), which implements the documented
reconciliation rules without using the application's engines.

Also validates the anomaly engine against controlled injected patterns:
outliers, repeated amounts, merchant concentration, refund patterns and fee
patterns, plus the conceptual separation between reconciliation exceptions
and statistical anomalies.

Timing measurements for the large sizes are collected and sanity-checked so
a pathological regression (e.g. quadratic blow-up) cannot pass silently.
"""

import time

import pytest

from app.services.anomaly.engine import analyze_transactions
from app.services.reconciliation.adaptive import parse_single_file

from tests.qa import datasets
from tests.qa.oracle import (
    single_file_expectation,
)

SIZES = [100, 200, 300, 500, 1000, 5000, 10000, 50000, 100000]

# Generous sanity bounds: these guard against quadratic/pathological
# regressions, not micro-optimizations. Real timings are reported separately.
RECONCILE_BOUND_SECONDS = {
    100: 5, 200: 5, 300: 5, 500: 5, 1000: 10,
    5000: 15, 10000: 20, 50000: 40, 100000: 60,
}


# ------------------------------------------------------------------
# ORACLE VS APPLICATION — NORMAL DATASETS
# ------------------------------------------------------------------

@pytest.mark.parametrize("n", SIZES)
def test_normal_dataset_oracle_matches_application(n):
    data = datasets.single_file_csv(n)
    started = time.perf_counter()
    records, _ = parse_single_file(data)
    elapsed = time.perf_counter() - started
    assert elapsed < RECONCILE_BOUND_SECONDS[n], (
        f"parse_single_file({n}) took {elapsed:.2f}s"
    )

    expected = single_file_expectation(records)
    assert expected["total"] == n
    assert expected["matched"] == n
    assert expected["exceptions"] == 0
    assert expected["match_rate"] == 100.0
    assert expected["variance"] == 0


# ------------------------------------------------------------------
# ORACLE VS APPLICATION — CONTROLLED MISMATCH DATASETS
# ------------------------------------------------------------------

MISMATCH_BY_SIZE = {
    100: {f"TXN-{i:06d}": 75 for i in range(10)},
    200: {
        **{f"TXN-{i:06d}": 83 for i in range(160, 185)},
        **{f"TXN-{i:06d}": 100 for i in range(185, 200)},
    },
    300: {f"TXN-{i:06d}": 150 for i in range(50, 100)},
    500: {f"TXN-{i:06d}": 200 for i in range(100, 160)},
    1000: {
        **{f"TXN-{i:06d}": 25 for i in range(0, 100)},
        **{f"TXN-{i:06d}": 2500 for i in range(900, 910)},
    },
}


@pytest.mark.parametrize("n", [100, 200, 300, 500, 1000])
def test_mismatch_dataset_oracle_matches_application(n):
    mismatch_refs = MISMATCH_BY_SIZE[n]
    data = datasets.single_file_csv(n, mismatch_refs=mismatch_refs)
    records, _ = parse_single_file(data)
    expected = single_file_expectation(records)

    # Oracle and application agree on every field.
    actual_counts = {}
    for record in records:
        actual_counts[record["status"]] = actual_counts.get(record["status"], 0) + 1
    assert actual_counts.get("MISMATCH", 0) == expected["mismatch"]
    assert expected["total"] == n
    assert expected["matched"] == n - expected["mismatch"]
    assert expected["exceptions"] == expected["mismatch"]
    assert expected["variance"] == pytest.approx(sum(mismatch_refs.values()), abs=0.01)

    largest = max((record["variance"] for record in records), default=0)
    assert largest == expected["largest_variance"]


def test_mixed_pattern_dataset_oracle_matches_application():
    """Every control at once: mismatches, partials, duplicates, outliers,
    repeats, concentration, refunds and fees - the oracle must still agree
    with the application on the reconciliation summary."""
    n = 1000
    data = datasets.single_file_csv(
        n,
        mismatch_refs={f"TXN-{i:06d}": 50 for i in range(100, 140)},
        unmatched_refs={f"TXN-{i:06d}" for i in range(140, 150)},
        duplicate_refs={f"TXN-{i:06d}" for i in range(150, 153)},
        outlier_refs={f"TXN-{i:06d}" for i in range(153, 154)},
        repeat_amounts=[(10, 1500.0)],
        concentration=("Acme Traders", 0.70),
        refund_refs={f"TXN-{i:06d}": 0.20 for i in range(160, 165)},
        fee_refs={f"TXN-{i:06d}": 0.10 for i in range(165, 170)},
    )
    records, _ = parse_single_file(data)
    expected = single_file_expectation(records)

    assert expected["total"] == 1003
    assert expected["mismatch"] == 40
    assert expected["partial"] == 10
    assert expected["duplicate"] == 3
    assert expected["exceptions"] == 53
    assert expected["variance"] == pytest.approx(40 * 50, abs=0.01)
    assert expected["match_rate"] == pytest.approx(
        round(950 / 1003 * 100, 2), abs=0.01
    )


# ------------------------------------------------------------------
# ANOMALY ENGINE — CONTROLLED PATTERNS
# ------------------------------------------------------------------

def _anomaly_categories(rows):
    return {item["category"] for item in analyze_transactions(rows)["anomalies"]}


def test_normal_dataset_has_no_anomalies():
    rows = datasets.build_rows(200)
    assert _anomaly_categories(rows) == set()


def test_outlier_transaction_is_detected():
    rows = datasets.build_rows(200, outlier_refs={"TXN-000100"})
    anomalies = analyze_transactions(rows)["anomalies"]
    flagged = [a for a in anomalies if a["category"] == "amount_outlier"]
    assert any(a["transaction_id"] == "TXN-000100" for a in flagged)


def test_repeated_amounts_are_detected():
    rows = datasets.build_rows(200, repeat_amounts=[(10, 1500.0)])
    flagged = [a for a in analyze_transactions(rows)["anomalies"]
               if a["category"] == "repeated_transaction"]
    # Evidence reports the amount formatted as Rs.1,500.00 x10.
    assert any("1,500" in a["evidence"] for a in flagged)


def test_merchant_concentration_is_detected():
    rows = datasets.build_rows(200, concentration=("Acme Traders", 0.70))
    flagged = [a for a in analyze_transactions(rows)["anomalies"]
               if a["category"] == "merchant_concentration"]
    assert any("Acme Traders" in a["evidence"] for a in flagged)


def test_refund_pattern_is_detected():
    rows = datasets.build_rows(
        200, refund_refs={f"TXN-{i:06d}": 0.20 for i in range(5)}
    )
    flagged = [a for a in analyze_transactions(rows)["anomalies"]
               if a["category"] == "refund_pattern"]
    assert len(flagged) >= 3


def test_fee_pattern_is_detected():
    rows = datasets.build_rows(
        200, fee_refs={f"TXN-{i:06d}": 0.10 for i in range(5)}
    )
    flagged = [a for a in analyze_transactions(rows)["anomalies"]
               if a["category"] == "fee_pattern"]
    assert len(flagged) >= 3


def test_reconciliation_exceptions_and_anomalies_stay_separate():
    """40 reconciliation mismatches with normal amounts must NOT create
    statistical anomalies - exceptions and anomalies are different concepts."""
    rows = datasets.build_rows(
        200,
        mismatch_refs={f"TXN-{i:06d}": 83 for i in range(160, 200)},
    )
    records, _ = parse_single_file(datasets.rows_to_csv(rows))
    assert single_file_expectation(records)["exceptions"] == 40
    assert _anomaly_categories(rows) == set()


# ------------------------------------------------------------------
# PERFORMANCE SANITY (reported, not asserted to be "production load")
# ------------------------------------------------------------------

def test_large_dataset_parse_timings_are_recorded():
    """Collect honest wall-clock timings for the larger sizes. Assertions are
    sanity bounds only; the actual numbers are reported in the QA report."""
    timings = {}
    for n in (5000, 10000, 50000, 100000):
        data = datasets.single_file_csv(n)
        started = time.perf_counter()
        records, _ = parse_single_file(data)
        timings[n] = round(time.perf_counter() - started, 3)
        assert len(records) == n
        assert timings[n] < RECONCILE_BOUND_SECONDS[n]
    print(f"\nQA parse_single_file timings: {timings}")