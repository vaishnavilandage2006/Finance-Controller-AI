from app.services.reconciliation.multi_file import (
    detect_single_mapping_from_bytes,
    parse_single_file,
)


def test_single_file_combined_schema_matches_equal_amounts():
    data = (
        b"record_id,vendor,payment_id,ledger_reference,bank_reference,utr,"
        b"settlement_amount,ledger_amount,bank_amount\n"
        b"1,Vendor A,pay_00001,pay_00001,pay_00001,U1,1001.75,1001.75,1001.75\n"
    )

    records, mapping = parse_single_file(data)

    assert mapping["reference"] == "record_id"
    assert mapping["date"] is None
    assert records[0]["status"] == "MATCHED"
    assert records[0]["variance"] == 0
    assert records[0]["date"] is None


def test_single_file_amount_variance_is_partial():
    data = b"payment_id,bank_amount,ledger_amount\npay_00001,5000,4950\n"

    records, _ = parse_single_file(data)

    assert records[0]["status"] == "PARTIAL"
    assert records[0]["variance"] == 50
    assert records[0]["date"] is None


def test_single_file_detects_common_date_and_vendor_aliases():
    data = b"payment id,merchant name,bank date,bank payment amount\npay_00001,Vendor A,2026-01-01,100\n"

    mapping = detect_single_mapping_from_bytes(data)

    assert mapping["reference"] == "payment id"
    assert mapping["vendor"] == "merchant name"
    assert mapping["date"] == "bank date"
    assert mapping["bank_amount"] == "bank payment amount"
