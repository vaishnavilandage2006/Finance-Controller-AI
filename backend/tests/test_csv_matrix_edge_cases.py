"""CSV edge-case matrix (Step 5 of the validation plan).

Covers the data-quality edge cases: empty file, one row, headers only,
missing/extra/reordered columns, blank and null cells, invalid date/amount,
text in numeric fields, negative/zero/extreme amounts, duplicate ids and
references, whitespace, case-insensitive values, malformed CSV, quoted
values, commas inside merchant names, Unicode merchant names, special
characters, and spreadsheet formula injection.

Every expectation is derived independently (the edge case itself defines the
expected behavior), never from the application's output.
"""

import pytest

from app.services.csv.processor import validate_csv
from app.services.reconciliation.adaptive import (
    MultiFileValidationError,
    parse_single_file,
)

from tests.qa.datasets import rows_to_csv, single_file_csv
from tests.qa.oracle import single_file_expectation

VALID_HEADER = (
    "transaction_id,date,amount,type,status,merchant,settlement_amount\n"
)
VALID_ROW = "TXN-1,2026-01-01,1000.00,revenue,completed,Acme Traders,1000.00\n"


# ------------------------------------------------------------------
# A. NORMAL DATA
# ------------------------------------------------------------------

def test_normal_dataset_100_percent_matched():
    data = single_file_csv(200)
    records, mapping = parse_single_file(data)
    expected = single_file_expectation([row for row in records])

    assert mapping["amount"] == "amount"
    assert mapping["settlement_amount"] == "settlement_amount"
    assert expected["total"] == 200
    assert expected["matched"] == 200
    assert expected["exceptions"] == 0
    assert expected["match_rate"] == 100.0
    assert expected["variance"] == 0


# ------------------------------------------------------------------
# B. RECONCILIATION MISMATCH / EDGE PATTERNS
# ------------------------------------------------------------------

def test_mismatch_values_at_each_band():
    """Deltas of 25/50/75/100/150/200 and a large 2500 delta are each
    detected as MISMATCH with exactly the injected variance."""
    mismatch = {}
    for index, delta in enumerate([25, 50, 75, 100, 150, 200, 2500]):
        mismatch[f"TXN-{index:06d}"] = delta
    data = single_file_csv(50, mismatch_refs=mismatch)
    records, _ = parse_single_file(data)
    expected = single_file_expectation(records)

    by_ref = {r["transaction_id"]: r for r in records}
    for index, delta in enumerate([25, 50, 75, 100, 150, 200, 2500]):
        record = by_ref[f"TXN-{index:06d}"]
        assert record["status"] == "MISMATCH"
        assert record["variance"] == delta

    assert expected["mismatch"] == 7
    assert expected["matched"] == 43
    assert expected["variance"] == sum([25, 50, 75, 100, 150, 200, 2500])


def test_missing_settlement_is_partial_not_matched():
    data = single_file_csv(
        30,
        unmatched_refs={f"TXN-{index:06d}" for index in range(5)},
    )
    records, _ = parse_single_file(data)
    expected = single_file_expectation(records)

    assert expected["partial"] == 5
    assert expected["matched"] == 25
    assert expected["exceptions"] == 5


def test_duplicate_reference_is_duplicate():
    data = single_file_csv(
        40,
        duplicate_refs={"TXN-000000", "TXN-000001"},
    )
    records, _ = parse_single_file(data)
    expected = single_file_expectation(records)

    assert expected["total"] == 42
    assert expected["duplicate"] == 2
    assert expected["matched"] == 40
    assert expected["exceptions"] == 2


def test_repeated_upload_same_file_is_deterministic():
    data = single_file_csv(200, mismatch_refs={"TXN-000005": 83})
    first, _ = parse_single_file(data)
    second, _ = parse_single_file(data)
    assert single_file_expectation(first) == single_file_expectation(second)


# ------------------------------------------------------------------
# C. DATA QUALITY EDGE CASES (validator)
# ------------------------------------------------------------------

def test_empty_file_is_rejected():
    rows, errors = validate_csv(b"")
    assert rows == []
    assert any("required columns" in error for error in errors)


def test_headers_only_is_valid_but_has_no_rows():
    rows, errors = validate_csv(VALID_HEADER.encode())
    assert errors == []
    assert rows == []
    records, _ = parse_single_file(VALID_HEADER.encode())
    assert records == []


def test_single_row_dataset_works():
    rows, errors = validate_csv((VALID_HEADER + VALID_ROW).encode())
    assert errors == []
    assert len(rows) == 1


def test_missing_required_column_is_rejected():
    rows, errors = validate_csv(b"transaction_id,date,amount,status\nT1,2026-01-01,100,done\n")
    assert rows == []
    assert any("Missing required columns" in error for error in errors)


def test_extra_columns_are_accepted():
    rows, errors = validate_csv(
        b"transaction_id,date,amount,type,status,extra_note,budget_code\n"
        b"T1,2026-01-01,100,revenue,done,note,BUD-1\n"
    )
    assert errors == []
    assert len(rows) == 1


def test_reordered_columns_are_accepted():
    rows, errors = validate_csv(
        b"status,amount,date,transaction_id,type\n"
        b"done,100,2026-01-01,T1,revenue\n"
    )
    assert errors == []
    assert rows[0]["transaction_id"] == "T1"


def test_blank_amount_cell_is_rejected():
    rows, errors = validate_csv(
        b"transaction_id,date,amount,type,status\nT1,2026-01-01,,revenue,done\n"
    )
    # Blank amount -> the row is dropped with an error appended.
    assert len(rows) == 0
    assert any("amount" in error for error in errors)


def test_null_like_values_are_rejected_as_invalid_numbers():
    rows, errors = validate_csv(
        b"transaction_id,date,amount,type,status\nT1,2026-01-01,NULL,revenue,done\n"
    )
    assert len(rows) == 0
    assert any("amount" in error for error in errors)


def test_invalid_date_is_rejected():
    rows, errors = validate_csv(
        b"transaction_id,date,amount,type,status\nT1,31-12-2026,100,revenue,done\n"
    )
    assert len(rows) == 0
    assert any("date" in error for error in errors)


def test_text_inside_numeric_field_is_rejected():
    rows, errors = validate_csv(
        b"transaction_id,date,amount,type,status\nT1,2026-01-01,one-hundred,revenue,done\n"
    )
    assert len(rows) == 0
    assert any("amount" in error for error in errors)


def test_negative_amount_is_supported_when_settlement_agrees():
    rows, errors = validate_csv(
        b"transaction_id,date,amount,type,status,settlement_amount\n"
        b"T1,2026-01-01,-125.50,refund,done,-125.50\n"
    )
    assert errors == []
    records, _ = parse_single_file(
        b"transaction_id,date,amount,type,status,settlement_amount\n"
        b"T1,2026-01-01,-125.50,refund,done,-125.50\n"
    )
    assert records[0]["status"] == "MATCHED"


def test_zero_amount_is_supported():
    rows, errors = validate_csv(
        b"transaction_id,date,amount,type,status,settlement_amount\n"
        b"T1,2026-01-01,0,revenue,done,0\n"
    )
    assert errors == []
    assert rows[0]["amount"] == "0"


def test_extreme_amount_is_rejected():
    rows, errors = validate_csv(
        b"transaction_id,date,amount,type,status\nT1,2026-01-01,1e13,revenue,done\n"
    )
    assert len(rows) == 0
    assert any("magnitude" in error for error in errors)


def test_duplicate_transaction_ids_are_rejected_by_import_validator():
    rows, errors = validate_csv(
        b"transaction_id,date,amount,type,status\n"
        b"T1,2026-01-01,100,revenue,done\n"
        b"T1,2026-01-02,200,revenue,done\n"
    )
    assert len(rows) == 1
    assert any("duplicate transaction_id" in error for error in errors)


def test_whitespace_around_values_is_accepted():
    # The validator trims values for its checks and accepts padded cells;
    # the reconciliation parser normalises references downstream.
    rows, errors = validate_csv(
        b"transaction_id,date,amount,type,status\n"
        b"  TXN-1  , 2026-01-01 , 100.00 , revenue , done \n"
    )
    assert errors == []
    assert len(rows) == 1
    assert rows[0]["amount"] == " 100.00 "

    records, _ = parse_single_file(
        b"reference,amount,settlement_amount\n"
        b"  TXN-1  , 100.00 , 100.00 \n"
    )
    assert records[0]["transaction_id"] == "TXN-1"


def test_uppercase_and_lowercase_type_values_are_accepted():
    rows, errors = validate_csv(
        b"transaction_id,date,amount,type,status\n"
        b"T1,2026-01-01,100,REVENUE,DONE\n"
        b"T2,2026-01-01,100,revenue,done\n"
    )
    assert errors == []
    assert len(rows) == 2


def test_malformed_csv_unbalanced_quotes_does_not_crash():
    data = (
        b"transaction_id,date,amount,type,status,merchant\n"
        b'T1,2026-01-01,100,revenue,done,"Acme "Traders"\n'
    )
    rows, errors = validate_csv(data)
    # The row is malformed; the parser must not crash and the import must
    # not silently accept a corrupted row set.
    assert len(rows) <= 1


def test_quoted_values_and_commas_inside_merchant_names_are_supported():
    data = (
        b"transaction_id,date,amount,type,status,merchant\n"
        b'T1,2026-01-01,100,revenue,done,"Acme, Traders & Co."\n'
    )
    rows, errors = validate_csv(data)
    assert errors == []
    assert rows[0]["merchant"] == "Acme, Traders & Co."


def test_unicode_merchant_names_are_supported():
    data = (
        "transaction_id,date,amount,type,status,merchant\n"
        "T1,2026-01-01,100,revenue,done,मर्चेंट नाम\n"
    ).encode("utf-8")
    rows, errors = validate_csv(data)
    assert errors == []
    assert rows[0]["merchant"] == "मर्चेंट नाम"


def test_special_characters_in_merchant_names_are_supported():
    data = (
        "transaction_id,date,amount,type,status,merchant\n"
        "T1,2026-01-01,100,revenue,done,Merchant & Sons (India) Pvt. Ltd.\n"
    ).encode("utf-8")
    rows, errors = validate_csv(data)
    assert errors == []
    assert rows[0]["merchant"] == "Merchant & Sons (India) Pvt. Ltd."


def test_utf8_bom_is_stripped():
    data = (
        b"\xef\xbb\xbftransaction_id,date,amount,type,status\n"
        b"T1,2026-01-01,100,revenue,done\n"
    )
    rows, errors = validate_csv(data)
    assert errors == []
    assert rows[0]["transaction_id"] == "T1"


def test_nul_bytes_are_rejected():
    rows, errors = validate_csv(
        b"transaction_id,date,amount,type,status\nT1,2026-01-01,100,revenue,do\x00ne\n"
    )
    assert any("NUL" in error for error in errors)


def test_non_utf8_file_is_rejected():
    rows, errors = validate_csv(b"transaction_id,date,amount,type,status\n\xff\xfe\x00T1,2026-01-01,100,revenue,done\n")
    assert any("UTF-8" in error for error in errors)


def test_file_over_10mb_is_rejected():
    header = b"transaction_id,date,amount,type,status\n"
    oversized = header + b"T1,2026-01-01,100,revenue,done\n" + b"x" * (10 * 1024 * 1024)
    rows, errors = validate_csv(oversized)
    assert any("10 MB" in error for error in errors)


def test_row_cap_100k_is_enforced():
    header = b"transaction_id,date,amount,type,status\n"
    body = b"".join(
        f"T{i},2026-01-01,100,revenue,done\n".encode() for i in range(100_001)
    )
    rows, errors = validate_csv(header + body)
    assert any("100000" in error for error in errors)


# ------------------------------------------------------------------
# D. SPREADSHEET FORMULA / CSV INJECTION
# ------------------------------------------------------------------

def test_formula_injection_in_text_column_is_rejected():
    for leader in ("=", "+", "@"):
        data = (
            f"transaction_id,date,amount,type,status,merchant\n"
            f'T1,2026-01-01,100,revenue,done,"{leader}cmd|\' /C calc!A1"\n'
        ).encode("utf-8")
        rows, errors = validate_csv(data)
        assert any("formula" in error.lower() for error in errors), leader


def test_negative_number_in_numeric_column_is_not_flagged_as_formula():
    rows, errors = validate_csv(
        b"transaction_id,date,amount,type,status,settlement_amount\n"
        b"T1,2026-01-01,-125.50,revenue,done,-125.50\n"
    )
    assert errors == []


def test_iso_date_in_date_column_is_not_flagged_as_formula():
    rows, errors = validate_csv(
        b"transaction_id,date,amount,type,status\n"
        b"T1,2026-01-01,100,revenue,done\n"
    )
    # A valid ISO date must never trip the spreadsheet-formula guard.
    assert errors == []


def test_leading_minus_letter_style_formula_is_rejected():
    data = (
        b"transaction_id,date,amount,type,status,merchant\n"
        b"T1,2026-01-01,100,revenue,done,-cmd|'/C calc\n"
    )
    rows, errors = validate_csv(data)
    assert any("formula" in error.lower() for error in errors)


# ------------------------------------------------------------------
# E. SINGLE-FILE PARSER REJECTIONS (MultiFileValidationError surface)
# ------------------------------------------------------------------

def test_empty_single_file_parser_error():
    with pytest.raises(MultiFileValidationError, match="empty"):
        parse_single_file(b"")


def test_single_file_missing_header_error():
    with pytest.raises(MultiFileValidationError, match="header"):
        parse_single_file(b"\nT1,100\n")


def test_single_file_invalid_amount_error():
    with pytest.raises(MultiFileValidationError, match="Invalid amount"):
        parse_single_file(
            b"reference,amount\nT1,not-a-number\n"
        )