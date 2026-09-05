"""Deterministic, reproducible CSV dataset generators for the validation matrix.

These generators produce realistic finance records with CONTROLLED
reconciliation / anomaly / risk patterns. A fixed random seed makes every
dataset byte-for-byte reproducible across runs. The datasets contain no real
financial data: they are synthetic test vectors.

Supported controls (optional and independently combinable):

- mismatch_refs   {reference: settlement_delta}  settlement = amount - delta
- unmatched_refs  set of references with NO settlement_amount (PARTIAL)
- duplicate_refs  set of references emitted twice in the same file (DUPLICATE)
- outlier_refs    set of references whose amount is multiplied by a factor
- repeat_amounts  [(count, amount)] identical amounts emitted consecutively
- concentration   (merchant, share) one merchant owning `share` of the rows
- refund_refs     {reference: fraction} refund_amount = fraction * amount
- fee_refs        {reference: fraction} fee = fraction * amount

The base schema uses the columns the application's CSV validator requires
plus the settlement/merchant/currency fields the reconciliation engine
understands: transaction_id, date, amount, type, status, merchant,
settlement_amount, fee, refund_amount, currency.
"""

from __future__ import annotations

import csv
import io
import random
from datetime import date, timedelta

SEED = 20260905

BASE_COLUMNS = [
    "transaction_id",
    "date",
    "amount",
    "type",
    "status",
    "merchant",
    "settlement_amount",
    "fee",
    "refund_amount",
    "currency",
]

MERCHANTS = [
    "Acme Traders",
    "Vertex Supplies",
    "Orion Logistics",
    "Bluepeak Retail",
    "Nova Digital",
    "Zenith Foods",
    "Crest Pharma",
    "Harbor Exports",
    "Summit Motors",
    "Delta Textiles",
]

TYPES = ["revenue", "expense", "payment", "purchase"]


def _base_row(rng: random.Random, index: int, merchant: str) -> dict:
    """A normal, matched record: unique reference, varied amount, settlement
    equal to the amount (exact match within tolerance)."""
    amount = 1000.0 + float((index * 37) % 997) + rng.randrange(0, 40)
    day = date(2026, 1, 1) + timedelta(days=index % 90)
    return {
        "transaction_id": f"TXN-{index:06d}",
        "date": day.isoformat(),
        "amount": f"{amount:.2f}",
        "type": TYPES[index % len(TYPES)],
        "status": "completed",
        "merchant": merchant,
        "settlement_amount": f"{amount:.2f}",
        "fee": "0",
        "refund_amount": "0",
        "currency": "INR",
    }


def build_rows(
    n: int,
    *,
    seed: int = SEED,
    mismatch_refs: dict[str, float] | None = None,
    unmatched_refs: set[str] | None = None,
    duplicate_refs: set[str] | None = None,
    outlier_refs: set[str] | None = None,
    outlier_factor: float = 50.0,
    repeat_amounts: list[tuple[int, float]] | None = None,
    concentration: tuple[str, float] | None = None,
    refund_refs: dict[str, float] | None = None,
    fee_refs: dict[str, float] | None = None,
) -> list[dict]:
    """Generate `n` base rows plus any duplicate-ref rows with the requested
    controlled patterns. Returns a list of raw CSV row dicts (strings)."""
    rng = random.Random(seed)
    mismatch_refs = mismatch_refs or {}
    unmatched_refs = set(unmatched_refs or ())
    duplicate_refs = set(duplicate_refs or ())
    outlier_refs = set(outlier_refs or ())
    refund_refs = refund_refs or {}
    fee_refs = fee_refs or {}

    concentration_merchant, concentration_share = (concentration or (None, 0.0))

    rows: list[dict] = []
    for index in range(n):
        ref = f"TXN-{index:06d}"
        if concentration_merchant and index < int(n * concentration_share):
            merchant = concentration_merchant
        else:
            merchant = MERCHANTS[(index * 3) % len(MERCHANTS)]
        row = _base_row(rng, index, merchant)

        if ref in mismatch_refs:
            delta = float(mismatch_refs[ref])
            row["settlement_amount"] = f"{float(row['amount']) - delta:.2f}"
        elif ref in unmatched_refs:
            row["settlement_amount"] = ""

        if ref in outlier_refs:
            row["amount"] = f"{float(row['amount']) * outlier_factor:.2f}"
            row["settlement_amount"] = row["amount"]

        if ref in refund_refs:
            row["refund_amount"] = (
                f"{float(row['amount']) * float(refund_refs[ref]):.2f}"
            )

        if ref in fee_refs:
            row["fee"] = f"{float(row['amount']) * float(fee_refs[ref]):.2f}"

        rows.append(row)

    # Repeat-amount pattern: overwrite the amounts (and settlements) of the
    # first `count` rows with the requested identical amount. When
    # repeat_merchant is set, those rows also share that merchant so the
    # repeated-transaction detector keys them together.
    repeat_merchant = None
    for count, amount in repeat_amounts or []:
        for index in range(min(count, len(rows))):
            rows[index]["amount"] = f"{amount:.2f}"
            rows[index]["settlement_amount"] = f"{amount:.2f}"
            if repeat_merchant is None:
                repeat_merchant = rows[index]["merchant"]
            else:
                rows[index]["merchant"] = repeat_merchant

    # Duplicate references: append an exact copy of each duplicated row.
    # Only refs that exist among the base rows can be duplicated.
    for ref in sorted(duplicate_refs):
        original = next(
            (row for row in rows if row["transaction_id"] == ref),
            None,
        )
        if original is not None:
            rows.append(dict(original))

    return rows


def rows_to_csv(rows: list[dict], columns: list[str] | None = None) -> bytes:
    columns = columns or (list(rows[0].keys()) if rows else BASE_COLUMNS)
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns)
    writer.writeheader()
    for row in rows:
        writer.writerow({key: row.get(key, "") for key in columns})
    return buffer.getvalue().encode("utf-8")


def single_file_csv(
    n: int,
    *,
    seed: int = SEED,
    columns: list[str] | None = None,
    **controls,
) -> bytes:
    """Bytes of a single-file finance CSV with the requested pattern."""
    return rows_to_csv(build_rows(n, seed=seed, **controls), columns=columns)


def build_multi_file(
    n: int,
    *,
    seed: int = SEED,
    mismatch_refs: dict[str, float] | None = None,
    missing_settlement_refs: set[str] | None = None,
    bank_only_refs: set[str] | None = None,
    duplicate_bank_refs: set[str] | None = None,
    omit_settlement_file: bool = False,
) -> tuple[dict[str, bytes], dict[str, dict[str, list[float]]]]:
    """Generate bank / ledger / settlement CSVs that reconcile by reference,
    plus the deterministic reference -> {SOURCE: [amounts]} group map the
    oracle consumes (so expected results stay independent of the app).

    - mismatch_refs: {ref: delta} settlement = amount - delta (MISMATCH)
    - missing_settlement_refs: refs absent from settlement (PARTIAL when the
      settlement file IS supplied)
    - bank_only_refs: refs present only in the bank file (UNMATCHED)
    - duplicate_bank_refs: refs emitted twice in the bank file (DUPLICATE)
    - omit_settlement_file: no settlement file at all (bank+ledger matches)
    """
    rng = random.Random(seed)
    mismatch_refs = mismatch_refs or {}
    missing_settlement_refs = set(missing_settlement_refs or ())
    bank_only_refs = set(bank_only_refs or ())
    duplicate_bank_refs = set(duplicate_bank_refs or ())

    bank_rows: list[list[str]] = []
    ledger_rows: list[list[str]] = []
    settlement_rows: list[list[str]] = []
    groups: dict[str, dict[str, list[float]]] = {}

    for index in range(n):
        ref = f"TXN-{index:06d}"
        amount = 1000.0 + float((index * 37) % 997) + rng.randrange(0, 40)
        day = (date(2026, 1, 1) + timedelta(days=index % 90)).isoformat()
        merchant = MERCHANTS[(index * 3) % len(MERCHANTS)]

        groups.setdefault(ref, {})
        groups[ref].setdefault("BANK", []).append(amount)
        bank_rows.append([ref, day, f"{amount:.2f}", merchant])

        # Bank-only references have NO counterpart in ledger or settlement
        # (they are the UNMATCHED records of the run).
        if ref in bank_only_refs:
            continue
        groups[ref].setdefault("LEDGER", []).append(amount)
        ledger_rows.append([ref, day, f"{amount:.2f}", merchant])

        if ref in duplicate_bank_refs:
            groups[ref]["BANK"].append(amount)
            bank_rows.append([ref, day, f"{amount:.2f}", merchant])

        if ref in missing_settlement_refs:
            continue
        settled = amount - float(mismatch_refs.get(ref, 0))
        groups[ref].setdefault("SETTLEMENT", []).append(settled)
        settlement_rows.append([ref, day, f"{settled:.2f}", merchant])

    files: dict[str, bytes] = {
        "bank": _write_csv(
            ["reference", "transaction_date", "amount", "merchant"], bank_rows
        ),
        "ledger": _write_csv(
            ["reference", "transaction_date", "amount", "merchant"], ledger_rows
        ),
    }
    if not omit_settlement_file:
        files["settlement"] = _write_csv(
            ["reference", "settlement_date", "settlement_amount", "merchant"],
            settlement_rows,
        )
    return files, groups


def multi_file_csvs(
    n: int,
    *,
    seed: int = SEED,
    **controls,
) -> dict[str, bytes]:
    """Bytes of bank / ledger / settlement CSVs with the requested pattern."""
    files, _ = build_multi_file(n, seed=seed, **controls)
    return files


def _write_csv(columns: list[str], rows: list[list[str]]) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(columns)
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def reference_of(row: dict) -> str:
    return (row.get("transaction_id") or "").strip()


def amount_of(row: dict) -> float:
    return float(row["amount"])


def settlement_of(row: dict) -> float | None:
    raw = (row.get("settlement_amount") or "").strip()
    return float(raw) if raw else None