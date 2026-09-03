"""Regression tests that run the shipped sample datasets through the active
reconciliation engine.

Expected figures are derived row-by-row from the CSV files
(variance = amount - settlement_amount for explicit amounts; fees and refunds
are evidence only and never auto-deducted). The literal dataset outcomes are
asserted as a second guard so fixture drift is caught explicitly.
"""

import csv
import io
from collections import Counter
from pathlib import Path

from app.services.reconciliation.adaptive import (
    parse_single_file,
    parse_source,
    reconcile_sources,
)

SAMPLE_DATA = Path(__file__).resolve().parents[2] / "database" / "sample_data"
FINANCE_TRANSACTIONS = SAMPLE_DATA / "finance_transactions.csv"
BANK_1000 = SAMPLE_DATA / "bank_1000.csv"
LEDGER_1000 = SAMPLE_DATA / "ledger_1000.csv"
SETTLEMENT_1000 = SAMPLE_DATA / "settlement_1000.csv"


def _csv_rows(path: Path):
    raw = path.read_bytes()
    rows = [
        row
        for row in csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
        if any((value or "").strip() for value in row.values())
    ]
    return raw, rows


def test_single_file_finance_transactions_uses_direct_settlement_comparison():
    raw, rows = _csv_rows(FINANCE_TRANSACTIONS)
    assert len(rows) == 1000
    # Fees are present on every row, so they cannot be silently deducted:
    # matching must come from amount vs settlement_amount alone.
    assert all(float(row["fee"]) > 0 for row in rows)

    records, mapping = parse_single_file(raw)
    assert mapping["amount"] == "amount"
    assert mapping["settlement_amount"] == "settlement_amount"
    assert len(records) == 1000

    differences = {
        row["transaction_id"]: float(row["amount"]) - float(row["settlement_amount"])
        for row in rows
    }

    # Per-record invariant: explicit amount vs explicit settlement_amount.
    for record in records:
        difference = differences[record["reference"]]
        if abs(difference) <= 0.01:
            assert record["status"] == "MATCHED", record
            assert record["variance"] == 0
        else:
            assert record["status"] == "MISMATCH", record
            assert record["variance_signed"] == round(difference, 2)
            assert record["variance"] == round(abs(difference), 2)
            assert record["expected_amount"] is not None
            assert record["actual_amount"] is not None

    derived_matched = sum(1 for d in differences.values() if abs(d) <= 0.01)
    derived_variance = round(
        sum(abs(d) for d in differences.values() if abs(d) > 0.01),
        2,
    )

    counts = Counter(record["status"] for record in records)
    assert counts["MATCHED"] == derived_matched
    assert counts["MISMATCH"] == len(records) - derived_matched
    assert counts["PARTIAL"] == 0
    assert counts["DUPLICATE"] == 0
    assert round(sum(record["variance"] for record in records), 2) == derived_variance

    # Documented dataset outcome (derived above, asserted here to catch drift).
    assert derived_matched == 972
    assert len(records) - derived_matched == 28
    assert round(derived_matched / len(records) * 100, 2) == 97.2
    assert derived_variance == 19414.37


def test_multi_file_thousand_row_fixtures_match_with_fee_evidence_only():
    bank = parse_source(BANK_1000.read_bytes(), "BANK")
    ledger = parse_source(LEDGER_1000.read_bytes(), "LEDGER")
    settlement = parse_source(SETTLEMENT_1000.read_bytes(), "SETTLEMENT")
    assert len(bank) == len(ledger) == len(settlement) == 1000
    # Every settlement row carries a fee in its own column, yet the explicit
    # settlement_amount equals the bank/ledger amount: fees must stay evidence.
    assert all(record.fee > 0 for record in settlement)

    records = reconcile_sources(bank, ledger, settlement)
    assert len(records) == 1000
    assert all(record["status"] == "MATCHED" for record in records)
    assert round(sum(record["variance"] for record in records), 2) == 0.0
