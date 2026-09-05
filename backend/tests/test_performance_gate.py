"""CI performance regression gate.

Lightweight, deliberately loose bounds: the gate exists to catch MAJOR
performance regressions (e.g. accidental O(n^2) blow-ups or a broken import
path), NOT to police micro-optimizations or to claim production load
testing. It runs the deterministic QA datasets through the real engines and
sanity-checks wall-clock time. Normal CI variance will not trip it; a 10x
slowdown of the pipeline will.

Measured stages (all on deterministic synthetic datasets, fixed seed):
- validate_csv  (CSV ingestion validation)
- parse_single_file  (reconciliation)
- analyze_transactions  (anomaly detection)
- assess_exception over the run's exceptions  (risk processing)

Run directly with:
    DATABASE_URL=sqlite:///./qa_perf.db python -m pytest tests/test_performance_gate.py -q
"""

import time

import pytest

from app.services.csv.processor import validate_csv
from app.services.reconciliation.adaptive import parse_single_file
from app.services.anomaly.engine import analyze_transactions
from app.services.risk.engine import assess_exception

from tests.qa import datasets

SIZES = [100, 200, 300, 500, 1000, 5000, 10000, 50000, 100000]

# Generous per-size bounds (seconds). Measured on this machine: 100k rows
# validate ~1.0s, reconcile ~3.6s, anomaly ~0.7s, risk ~0.07s. The bounds
# allow ~10-15x headroom so CI variance never false-fails, while a major
# regression (minutes instead of seconds) still fails.
BOUNDS = {
    100: 10, 200: 10, 300: 10, 500: 10, 1000: 15,
    5000: 20, 10000: 30, 50000: 60, 100000: 90,
}


def _run_stage(n: int) -> dict:
    rows = datasets.build_rows(
        n,
        mismatch_refs={f"TXN-{i:06d}": 83 for i in range(max(1, n // 5))},
    )
    data = datasets.rows_to_csv(rows)

    started = time.perf_counter()
    parsed_rows, errors = validate_csv(data)
    t_validate = time.perf_counter() - started
    assert errors == []

    started = time.perf_counter()
    records, _ = parse_single_file(data)
    t_reconcile = time.perf_counter() - started

    started = time.perf_counter()
    analysis = analyze_transactions(rows)
    t_anomaly = time.perf_counter() - started

    exceptions = [r for r in records if r["status"] != "MATCHED"]
    started = time.perf_counter()
    for record in exceptions:
        assess_exception(
            record["transaction_id"],
            amount=record.get("amount"),
            variance=record.get("variance"),
        )
    t_risk = time.perf_counter() - started

    assert len(parsed_rows) == n
    assert len(records) == n
    assert analysis["sample_size"] == n
    return {
        "validate": t_validate,
        "reconcile": t_reconcile,
        "anomaly": t_anomaly,
        "risk": t_risk,
    }


@pytest.mark.parametrize("n", SIZES)
def test_performance_gate_all_sizes(n):
    timings = _run_stage(n)
    for stage, seconds in timings.items():
        assert seconds < BOUNDS[n], (
            f"size={n} stage={stage} took {seconds:.2f}s "
            f"(bound {BOUNDS[n]}s)"
        )


def test_performance_gate_full_matrix_is_measured():
    """Run the whole matrix once and surface the numbers for the report."""
    results = {}
    for n in SIZES:
        results[n] = _run_stage(n)
    summary = ", ".join(
        f"{n}: v={results[n]['validate']:.2f}s r={results[n]['reconcile']:.2f}s "
        f"a={results[n]['anomaly']:.2f}s k={results[n]['risk']:.3f}s"
        for n in SIZES
    )
    print(f"\nPERF GATE: {summary}")