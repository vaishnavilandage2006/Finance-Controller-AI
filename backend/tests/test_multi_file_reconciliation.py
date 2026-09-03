import pytest

from app.services.reconciliation.multi_file import (
    MultiFileValidationError,
    detect_mapping_from_bytes,
    parse_source,
    reconcile_sources,
)


def test_common_source_header_variations_are_detected():
    bank = b"Transaction Date,UTR No,Credit Amount,Narration\n2026-01-01,U1,100,Sale\n"
    ledger = b"Posting Date,Transaction Reference,Transaction Amount,Remarks\n2026-01-01,U1,100,Sale\n"
    settlement = b"Settlement Date,Transaction ID,Settlement Amount,Charges\n2026-01-01,U1,98,2\n"

    assert detect_mapping_from_bytes(bank, "bank")["reference"] == "UTR No"
    assert detect_mapping_from_bytes(ledger, "ledger")["date"] == "Posting Date"
    assert detect_mapping_from_bytes(settlement, "settlement")["amount"] == "Settlement Amount"


def test_normalization_handles_bom_spaces_hyphens_and_case():
    data = "\ufeff TRANSACTION-Date , UTR-Number , TRANSACTION-VALUE \n2026-01-01,U1,100\n".encode()

    mapping = detect_mapping_from_bytes(data, "bank")
    record = parse_source(data, "bank")[0]

    assert mapping == {
        "reference": " UTR-Number ",
        "date": " TRANSACTION-Date ",
        "amount": " TRANSACTION-VALUE ",
    }
    assert record.reference == "U1"
    assert record.amount == 100


def test_existing_bank_and_ledger_date_aliases_are_detected():
    bank = b"bank_reference,bank_amount,bank_date\nU1,100,2026-01-01\n"
    ledger = b"ledger_reference,ledger_amount,ledger_date\nU1,100,2026-01-01\n"

    assert detect_mapping_from_bytes(bank, "bank")["date"] == "bank_date"
    assert detect_mapping_from_bytes(ledger, "ledger")["date"] == "ledger_date"


def test_optional_columns_are_not_required():
    data = b"date,reference,amount\n2026-01-01,U1,100\n"

    record = parse_source(data, "ledger")[0]

    assert record.description == ""
    assert record.settlement_id == ""
    assert record.fee == 0
    assert record.currency == "INR"


def test_bank_and_ledger_without_dates_are_supported():
    bank = b"record_id,vendor,payment_id,bank_reference,utr,bank_amount\n1,Vendor A,pay_00001,pay_00001,U1,1001.75\n"
    ledger = b"record_id,vendor,payment_id,ledger_reference,ledger_amount\n1,Vendor A,pay_00001,pay_00001,1001.75\n"

    bank_mapping = detect_mapping_from_bytes(bank, "bank")
    ledger_mapping = detect_mapping_from_bytes(ledger, "ledger")
    bank_record = parse_source(bank, "bank")[0]
    ledger_record = parse_source(ledger, "ledger")[0]
    result = reconcile_sources([bank_record], [ledger_record], [])[0]

    assert bank_mapping["reference"] == "bank_reference"
    assert bank_mapping["amount"] == "bank_amount"
    assert bank_mapping["date"] is None
    assert ledger_mapping["reference"] == "ledger_reference"
    assert ledger_mapping["amount"] == "ledger_amount"
    assert ledger_mapping["date"] is None
    assert bank_record.date is None
    assert ledger_record.date is None
    assert result["confidence_score"] == 70
    assert "Date unavailable in source" in result["evidence"]
    assert "Date unavailable in source" in result["reason"]


def test_credit_and_debit_are_signed_without_arbitrary_selection():
    data = b"date,reference,credit_amount,debit_amt\n2026-01-01,U1,100,25\n"

    mapping = detect_mapping_from_bytes(data, "bank")
    record = parse_source(data, "bank")[0]

    assert mapping["amount"] == "credit/debit"
    assert record.amount == 75


def test_missing_required_column_has_actionable_error():
    data = b"Transaction Date,Credit Amount,Description\n2026-01-01,100,Sale\n"

    with pytest.raises(MultiFileValidationError) as error:
        parse_source(data, "bank")

    result = error.value.as_dict()
    assert result["source"] == "bank"
    assert "reference" in result["error"]
    assert result["available_columns"] == [
        "Transaction Date",
        "Credit Amount",
        "Description",
    ]
    assert "UTR" in result["suggested_columns"]


def test_empty_and_invalid_amount_are_rejected():
    with pytest.raises(MultiFileValidationError, match="empty"):
        parse_source(b"", "bank")

    with pytest.raises(MultiFileValidationError, match="empty"):
        detect_mapping_from_bytes(b"", "bank")

    with pytest.raises(MultiFileValidationError, match="Invalid amount"):
        parse_source(b"date,reference,amount\n2026-01-01,U1,nope\n", "bank")
