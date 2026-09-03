import pytest

from app.services.reconciliation.adaptive import (
    MultiFileValidationError,
    detect_source_role,
    parse_single_file,
    parse_source,
    reconcile_sources,
)


def test_standard_single_file_matches():
    records, mapping = parse_single_file(b"transaction_id,amount,settlement_amount\nTX-1,100,100\n")
    assert mapping["reference"] == "transaction_id"
    assert records[0]["status"] == "MATCHED"
    assert records[0]["expected_amount"] == 100


def test_alternative_names_and_arbitrary_filename():
    records, mapping = parse_single_file(b"Payment Reference,Gross Amount,Settled Amount\np-1,250,250\n")
    assert mapping["reference"] == "Payment Reference"
    assert records[0]["status"] == "MATCHED"


def test_generic_settled_value_is_compared_with_gross_amount():
    records, mapping = parse_single_file(
        b"id,payment_reference,gross_amount,settled_value,merchant_name,transaction_date\n"
        b"1,p-1,1000,1000,Acme,2026-01-01\n"
        b"2,p-2,2500,2400,Acme,2026-01-02\n"
    )
    assert mapping["amount"] == "gross_amount"
    assert mapping["settlement_amount"] == "settled_value"
    assert [record["status"] for record in records] == ["MATCHED", "MISMATCH"]
    assert [record["variance"] for record in records] == [0, 100]
    assert all(record["status"] != "PARTIAL" for record in records)


def test_two_hundred_rows_with_settled_value_are_filename_independent():
    mismatches = [50] * 39 + [1625]
    rows = [
        f"{index},payment-{index},{1000 + index},{1000 + index},Merchant,2026-01-01"
        if index < 160
        else f"{index},payment-{index},{1000 + index},{1000 + index - mismatches[index - 160]},Merchant,2026-01-01"
        for index in range(200)
    ]
    data = (
        "id,payment_reference,gross_amount,settled_value,merchant_name,transaction_date\n"
        + "\n".join(rows)
        + "\n"
    ).encode()
    first, first_mapping = parse_single_file(data)
    second, second_mapping = parse_single_file(data)
    for mapping in (first_mapping, second_mapping):
        assert mapping["amount"] == "gross_amount"
        assert mapping["settlement_amount"] == "settled_value"
    for records in (first, second):
        assert len(records) == 200
        assert sum(record["status"] == "MATCHED" for record in records) == 160
        assert sum(record["status"] == "MISMATCH" for record in records) == 40
        assert sum(record["status"] == "PARTIAL" for record in records) == 0
        assert sum(record["variance"] for record in records) == 3575


def test_optional_date_and_party_do_not_fail():
    records, _ = parse_single_file(b"payment_id,amount\np-1,100\n")
    assert records[0]["status"] == "PARTIAL"
    assert "Date unavailable" in records[0]["reason"]


def test_explicit_settlement_is_compared_directly_and_fees_are_not_deducted():
    data = b"payment_id,gross_amount,processing_fee,refund_amount,adjustment,settled_amount\np-1,1000,25,10,5,970\n"
    records, _ = parse_single_file(data)
    assert records[0]["expected_amount"] == 1000
    assert records[0]["actual_amount"] == 970
    assert records[0]["status"] == "MISMATCH"
    assert records[0]["variance"] == 30
    assert records[0]["variance_signed"] == 30


def test_equal_explicit_amounts_match_even_when_fees_are_present():
    data = b"payment_id,gross_amount,processing_fee,refund_amount,settled_amount\np-1,1000,30,0,1000\n"
    records, _ = parse_single_file(data)
    assert records[0]["status"] == "MATCHED"
    assert records[0]["variance"] == 0
    assert records[0]["expected_amount"] == 1000
    assert records[0]["actual_amount"] == 1000


def test_mismatch_is_not_hidden_as_partial():
    records, _ = parse_single_file(b"payment_id,amount,settlement_amount\np-1,1000,900\n")
    assert records[0]["status"] == "MISMATCH"
    assert records[0]["variance"] == 100
    assert records[0]["variance_percentage"] == 10


def test_duplicate_identifier_is_reported_for_each_row():
    records, _ = parse_single_file(b"payment_id,amount,settlement_amount\np-1,100,100\np-1,100,100\n")
    assert [record["status"] for record in records] == ["DUPLICATE", "DUPLICATE"]


def test_missing_identifier_can_use_stable_row_reference():
    records, _ = parse_single_file(b"amount,settlement_amount\n100,100\n")
    assert records[0]["reference"] == "ROW-1"
    assert records[0]["status"] == "MATCHED"


def test_invalid_file_has_actionable_error():
    with pytest.raises(MultiFileValidationError, match="no transaction/payment/reference"):
        parse_single_file(b"description,category\nhello,food\n")


def test_multi_file_uses_different_schema_names_and_preserves_raw_values():
    bank = parse_source(b"UTR,Credit,Value Date\nU1,100,2026-01-01\n", "BANK")
    ledger = parse_source(b"Invoice,Ledger Total,Posting Date\nU1,100,2026-01-01\n", "LEDGER")
    results = reconcile_sources(bank, ledger, [])
    assert results[0]["status"] == "MATCHED"
    assert results[0]["reference"] == "U1"
    assert results[0]["source_records"]["BANK"]["UTR"] == "U1"


def test_multi_file_amount_date_fallback_match():
    bank = parse_source(b"bank_amount,bank_date,merchant\n100,2026-01-01,Acme\n", "BANK")
    ledger = parse_source(b"ledger_amount,ledger_date,account\n100,2026-01-02,Acme\n", "LEDGER")
    results = reconcile_sources(bank, ledger, [])
    assert results[0]["status"] == "MATCHED"


def test_multi_file_explicit_settlement_amount_is_compared_directly():
    bank = parse_source(b"bank_reference,bank_amount\nU1,100\n", "BANK")
    ledger = parse_source(b"ledger_reference,ledger_amount\nU1,100\n", "LEDGER")
    settlement = parse_source(b"settlement_reference,settlement_amount,processing_fee\nU1,95,5\n", "SETTLEMENT")
    results = reconcile_sources(bank, ledger, settlement)
    assert results[0]["status"] == "MISMATCH"
    assert results[0]["variance"] == 5


def test_multi_file_equal_amounts_match_when_settlement_fee_is_present():
    bank = parse_source(b"bank_reference,bank_amount\nU1,100\n", "BANK")
    ledger = parse_source(b"ledger_reference,ledger_amount\nU1,100\n", "LEDGER")
    settlement = parse_source(b"settlement_reference,settlement_amount,processing_fee\nU1,100,5\n", "SETTLEMENT")
    results = reconcile_sources(bank, ledger, settlement)
    assert results[0]["status"] == "MATCHED"
    assert results[0]["variance"] == 0


def test_multi_file_missing_counterpart_and_duplicate():
    bank = parse_source(b"bank_reference,bank_amount\nB1,100\nB1,100\n", "BANK")
    ledger = parse_source(b"ledger_reference,ledger_amount\nL1,100\n", "LEDGER")
    results = reconcile_sources(bank, ledger, [])
    assert {record["status"] for record in results} >= {"DUPLICATE", "UNMATCHED"}


def test_source_role_detection_reports_ambiguity():
    result = detect_source_role(["reference", "amount"])
    assert result["role"] == "UNKNOWN"
    assert result["assumption"]


def test_currency_and_unknown_columns_are_preserved():
    records = parse_source(b"payment_id,amount,currency,custom_flag\np-1,12.50,USD,yes\n", "SINGLE")
    assert records[0].currency == "USD"
    assert records[0].raw["custom_flag"] == "yes"
