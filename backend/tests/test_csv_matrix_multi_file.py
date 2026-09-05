"""Generated multi-file reconciliation matrix (bank / ledger / settlement).

Every case generates deterministic source files with controlled patterns and
compares the application's reconciliation result against the independent
oracle (tests.qa.oracle.multi_file_expectation) - including duplicates,
missing settlement records, bank-only (unmatched) records, changed
settlement values, missing settlement files and shuffled ordering.
"""

import pytest

from app.services.reconciliation.adaptive import (
    MultiFileValidationError,
    parse_source,
    reconcile_sources,
)

from tests.qa import datasets
from tests.qa.oracle import multi_file_expectation


def reconcile_files(files: dict[str, bytes], source_names: tuple[str, ...]) -> dict:
    """Run the application's multi-file reconciliation over generated files
    and return the summary computed exactly like the API route does."""
    parsed = {}
    for source in source_names:
        role = "SETTLEMENT" if source == "settlement" else source.upper()
        parsed[source] = parse_source(files[source], role)
    records = reconcile_sources(
        parsed.get("bank", []),
        parsed.get("ledger", []),
        parsed.get("settlement", []),
    )
    counts = {"MATCHED": 0, "PARTIAL": 0, "MISMATCH": 0, "UNMATCHED": 0, "DUPLICATE": 0}
    for record in records:
        counts[record["status"]] = counts.get(record["status"], 0) + 1
    total = len(records)
    matched = counts["MATCHED"]
    return {
        "total": total,
        "matched": matched,
        "mismatch": counts["MISMATCH"],
        "partial": counts["PARTIAL"],
        "unmatched": counts["UNMATCHED"],
        "duplicate": counts["DUPLICATE"],
        "exceptions": total - matched,
        "match_rate": round(matched / total * 100, 2) if total else 0,
        "variance": round(
            sum(float(record["variance"] or 0) for record in records), 2
        ),
    }


def assert_oracle(files, groups, source_names, settlement_supplied=True):
    actual = reconcile_files(files, source_names)
    expected = multi_file_expectation(groups, settlement_supplied=settlement_supplied)
    for key in ("total", "matched", "mismatch", "partial", "unmatched",
                "duplicate", "exceptions", "match_rate", "variance"):
        assert actual[key] == pytest.approx(expected[key], abs=0.01), (
            f"field {key}: app={actual[key]} oracle={expected[key]}"
        )
    return actual, expected


def test_all_matched_200_rows():
    files, groups = datasets.build_multi_file(200)
    actual, expected = assert_oracle(files, groups, ("bank", "ledger", "settlement"))
    assert expected["total"] == 200
    assert expected["matched"] == 200
    assert expected["exceptions"] == 0
    assert actual["variance"] == 0


def test_settlement_mismatches_are_detected():
    mismatch_refs = {f"TXN-{i:06d}": 100 for i in range(10)}
    files, groups = datasets.build_multi_file(
        200, mismatch_refs=mismatch_refs
    )
    actual, expected = assert_oracle(files, groups, ("bank", "ledger", "settlement"))
    assert expected["mismatch"] == 10
    assert expected["matched"] == 190
    assert expected["variance"] == pytest.approx(1000, abs=0.01)


def test_missing_settlement_record_is_partial():
    missing = {f"TXN-{i:06d}" for i in range(5)}
    files, groups = datasets.build_multi_file(
        200, missing_settlement_refs=missing
    )
    actual, expected = assert_oracle(files, groups, ("bank", "ledger", "settlement"))
    assert expected["partial"] == 5
    assert expected["matched"] == 195


def test_bank_only_records_are_unmatched():
    bank_only = {f"TXN-{i:06d}" for i in range(3)}
    files, groups = datasets.build_multi_file(200, bank_only_refs=bank_only)
    actual, expected = assert_oracle(files, groups, ("bank", "ledger", "settlement"))
    assert expected["unmatched"] == 3
    assert expected["matched"] == 197


def test_duplicate_records_in_bank_are_duplicate():
    dupes = {f"TXN-{i:06d}" for i in range(2)}
    files, groups = datasets.build_multi_file(200, duplicate_bank_refs=dupes)
    actual, expected = assert_oracle(files, groups, ("bank", "ledger", "settlement"))
    assert expected["duplicate"] == 2
    assert expected["matched"] == 198


def test_missing_settlement_file_still_matches_bank_and_ledger():
    files, groups = datasets.build_multi_file(200, omit_settlement_file=True)
    actual, expected = assert_oracle(
        files, groups, ("bank", "ledger"), settlement_supplied=False
    )
    assert expected["total"] == 200
    assert expected["matched"] == 200
    assert expected["partial"] == 0


def test_shuffled_bank_ordering_does_not_change_results():
    files, groups = datasets.build_multi_file(
        500, mismatch_refs={f"TXN-{i:06d}": 75 for i in range(50, 60)}
    )
    bank_csv = files["bank"]
    header, _, body = bank_csv.decode().partition("\n")
    lines = body.strip().split("\n")
    lines.reverse()
    files["bank"] = (header + "\n" + "\n".join(lines) + "\n").encode()

    assert_oracle(files, groups, ("bank", "ledger", "settlement"))


def test_repeated_upload_of_identical_files_is_deterministic():
    files, groups = datasets.build_multi_file(
        300, mismatch_refs={f"TXN-{i:06d}": 50 for i in range(100, 120)}
    )
    first = reconcile_files(files, ("bank", "ledger", "settlement"))
    second = reconcile_files(files, ("bank", "ledger", "settlement"))
    assert first == second


def test_1000_row_multi_file_matrix():
    files, groups = datasets.build_multi_file(
        1000,
        mismatch_refs={f"TXN-{i:06d}": 150 for i in range(700, 720)},
        missing_settlement_refs={f"TXN-{i:06d}" for i in range(720, 730)},
        bank_only_refs={f"TXN-{i:06d}" for i in range(730, 735)},
        duplicate_bank_refs={f"TXN-{i:06d}" for i in range(735, 738)},
    )
    actual, expected = assert_oracle(files, groups, ("bank", "ledger", "settlement"))
    assert expected["total"] == 1000
    assert expected["mismatch"] == 20
    assert expected["partial"] == 10
    assert expected["unmatched"] == 5
    assert expected["duplicate"] == 3
    assert expected["matched"] == 962
    assert expected["variance"] == pytest.approx(20 * 150, abs=0.01)


def test_malformed_settlement_file_raises_validation_error():
    files, _ = datasets.build_multi_file(50)
    files["settlement"] = b"reference,settlement_amount\nT1,not-a-number\n"
    with pytest.raises(MultiFileValidationError, match="Invalid amount"):
        reconcile_files(files, ("bank", "ledger", "settlement"))


def test_empty_settlement_file_raises_validation_error():
    files, _ = datasets.build_multi_file(50)
    files["settlement"] = b""
    with pytest.raises(MultiFileValidationError, match="empty"):
        reconcile_files(files, ("bank", "ledger", "settlement"))