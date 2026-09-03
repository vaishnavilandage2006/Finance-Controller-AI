import csv
import io
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from difflib import SequenceMatcher
from typing import Any


ALIASES = {
    "reference": [
        "reference",
        "bank_reference",
        "ledger_reference",
        "transaction_id",
        "utr",
        "transaction_reference",
        "utr_no",
        "utr_number",
        "utr_reference",
        "payment_id",
        "txn_id",
        "transaction_number",
        "transaction_no",
        "reference_number",
        "reference_no",
    ],
    "date": [
        "date",
        "transaction_date",
        "transaction_date_time",
        "transaction_datetime",
        "value_date",
        "posting_date",
        "payment_date",
        "bank_date",
        "ledger_date",
        "settlement_date",
    ],
    "amount": [
        "amount",
        "bank_amount",
        "ledger_amount",
        "transaction_amount",
        "txn_amount",
        "transaction_value",
        "credit_amount",
        "credit_amt",
        "debit_amount",
        "debit_amt",
        "settlement_amount",
    ],
    "description": [
        "description",
        "narration",
        "remarks",
        "remark",
        "memo",
        "details",
        "transaction_details",
        "particulars",
        "payment_description",
    ],
    "settlement_id": [
        "settlement_id",
        "settlement_reference",
        "batch_id",
        "batch_number",
    ],
    "fee": [
        "fee",
        "fees",
        "charges",
        "charge",
        "transaction_fee",
        "processing_fee",
        "bank_charge",
        "bank_charges",
    ],
    "currency": [
        "currency",
        "currency_code",
        "ccy",
    ],
}
REQUIRED_FIELDS = ("reference", "amount")


class MultiFileValidationError(ValueError):
    def __init__(self, source: str, message: str, available_columns=None, suggested_columns=None):
        super().__init__(message)
        self.source = source
        self.message = message
        self.available_columns = available_columns or []
        self.suggested_columns = suggested_columns or []

    def as_dict(self):
        result = {"source": self.source, "error": self.message}
        if self.available_columns:
            result["available_columns"] = self.available_columns
        if self.suggested_columns:
            result["suggested_columns"] = self.suggested_columns
        return result


@dataclass(frozen=True)
class CanonicalRecord:
    source: str
    date: date | None
    reference: str
    amount: float
    description: str
    settlement_id: str
    fee: float
    currency: str
    row_number: int


def _normalise_column(value: str) -> str:
    value = value.replace("\ufeff", "")
    value = re.sub(r"[^a-z0-9]+", "_", value.strip().lower())
    return re.sub(r"_+", "_", value).strip("_")


def _parse_date(value: str, source: str, row_number: int) -> date | None:
    text = (value or "").strip()
    if not text:
        return None

    candidates = [text, text[:10]]
    formats = (
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%Y/%m/%d",
        "%d-%m-%Y",
    )
    for candidate in candidates:
        try:
            return date.fromisoformat(candidate)
        except ValueError:
            pass
        for date_format in formats:
            try:
                return datetime.strptime(candidate, date_format).date()
            except ValueError:
                pass

    raise MultiFileValidationError(
        source,
        f"Invalid date at row {row_number}: {text}",
    )


def _parse_amount(value: str, source: str, row_number: int) -> float:
    text = (value or "").strip().replace(",", "")
    text = re.sub(r"[^0-9.()\-]", "", text)
    if text.startswith("(") and text.endswith(")"):
        text = f"-{text[1:-1]}"
    try:
        amount = float(text)
    except (TypeError, ValueError):
        raise MultiFileValidationError(
            source,
            f"Invalid amount at row {row_number}: {value}",
        )
    return amount


def _pick_columns(fieldnames: list[str], source: str) -> dict[str, str]:
    normalised = {
        _normalise_column(field): field
        for field in fieldnames
        if field
    }
    selected = {}
    for canonical, aliases in ALIASES.items():
        matches = [normalised[alias] for alias in aliases if alias in normalised]
        if matches:
            selected[canonical] = matches[0]

    debit = next(
        (normalised.get(alias) for alias in ("debit", "debit_amount", "debit_amt") if normalised.get(alias)),
        None,
    )
    credit = next(
        (normalised.get(alias) for alias in ("credit", "credit_amount", "credit_amt") if normalised.get(alias)),
        None,
    )
    if debit and credit:
        selected["amount"] = "__signed_credit_debit__"
        selected["_credit"] = credit
        selected["_debit"] = debit
    elif "amount" not in selected:
        if credit:
            selected["amount"] = credit
        elif debit:
            selected["amount"] = debit

    for required in REQUIRED_FIELDS:
        if required not in selected:
            suggestions = {
                "reference": ["UTR", "Transaction ID", "Reference", "Payment ID"],
                "date": ["Date", "Transaction Date", "Posting Date"],
                "amount": ["Amount", "Credit Amount", "Debit Amount", "Transaction Amount"],
            }
            raise MultiFileValidationError(
                source,
                f"Unable to detect {required} column for {source.upper()} source",
                fieldnames,
                suggestions[required],
            )
    return selected


def detect_source_mapping(fieldnames: list[str], source: str) -> dict[str, str | None]:
    columns = _pick_columns(fieldnames, source)
    mapping: dict[str, str | None] = {
        canonical: (
            "credit/debit"
            if column == "__signed_credit_debit__"
            else column
        )
        for canonical, column in columns.items()
        if not canonical.startswith("_")
    }
    mapping.setdefault("date", None)
    return mapping


def detect_mapping_from_bytes(data: bytes, source: str) -> dict[str, str]:
    if not data:
        raise MultiFileValidationError(source, "File is empty")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise MultiFileValidationError(source, "File must be UTF-8 encoded")
    reader = csv.reader(io.StringIO(text))
    fieldnames = next(reader, [])
    if not fieldnames:
        raise MultiFileValidationError(source, "CSV header is missing")
    return detect_source_mapping(fieldnames, source)


def parse_source(data: bytes, source: str) -> list[CanonicalRecord]:
    if not data:
        raise MultiFileValidationError(source, "File is empty")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise MultiFileValidationError(source, "File must be UTF-8 encoded")

    reader = csv.DictReader(io.StringIO(text))
    fieldnames = reader.fieldnames or []
    if not fieldnames:
        raise MultiFileValidationError(source, "CSV header is missing")
    columns = _pick_columns(fieldnames, source)
    records = []
    for row_number, row in enumerate(reader, 2):
        reference = (row.get(columns["reference"]) or "").strip()
        if not reference:
            raise MultiFileValidationError(
                source,
                f"Reference is empty at row {row_number}",
            )
        records.append(
            CanonicalRecord(
                source=source.upper(),
                date=(
                    _parse_date(row.get(columns["date"]), source, row_number)
                    if "date" in columns
                    else None
                ),
                reference=reference,
                amount=(
                    _parse_amount(row.get(columns["amount"]), source, row_number)
                    if columns["amount"] != "__signed_credit_debit__"
                    else _parse_amount(row.get(columns["_credit"]), source, row_number)
                    - _parse_amount(row.get(columns["_debit"]), source, row_number)
                ),
                description=(row.get(columns.get("description", "")) or "").strip(),
                settlement_id=(row.get(columns.get("settlement_id", "")) or "").strip(),
                fee=_parse_amount(row.get(columns.get("fee", "0")) or "0", source, row_number),
                currency=(row.get(columns.get("currency", "")) or "INR").strip() or "INR",
                row_number=row_number,
            )
        )
    return records


def _date_score(left: date | None, right: date | None) -> tuple[int, str]:
    if left is None or right is None:
        return 0, "Date unavailable in source"
    difference = abs((left - right).days)
    if difference == 0:
        return 20, "Transaction date matched"
    if difference <= 1:
        return 10, "Transaction date within one day"
    if difference <= 3:
        return 5, "Transaction date within three days"
    return 0, "Transaction date differs"


def _description_score(left: str, right: str) -> int:
    if not left or not right:
        return 0
    similarity = SequenceMatcher(None, left.lower(), right.lower()).ratio()
    return 10 if similarity >= 0.8 else 5 if similarity >= 0.5 else 0


def _amount_text(value: float) -> str:
    return f"{value:.2f}"


def _best_record(records: list[CanonicalRecord]) -> CanonicalRecord | None:
    return records[0] if records else None


def _build_record(reference: str, grouped: dict[str, list[CanonicalRecord]], settlement_supplied: bool) -> dict[str, Any]:
    bank = _best_record(grouped.get("BANK", []))
    ledger = _best_record(grouped.get("LEDGER", []))
    settlement = _best_record(grouped.get("SETTLEMENT", []))
    duplicates = [source for source, records in grouped.items() if len(records) > 1]
    evidence = []
    scores = 0
    variance = 0.0
    reasons = []

    if bank and ledger:
        scores += 40
        evidence.append("Reference matched")
        amount_difference = abs(bank.amount - ledger.amount)
        if amount_difference <= 0.01:
            scores += 30
            evidence.append("Amount matched")
        else:
            variance = max(variance, amount_difference)
            evidence.extend([
                f"Bank amount: {_amount_text(bank.amount)}",
                f"Ledger amount: {_amount_text(ledger.amount)}",
                f"Variance: {_amount_text(amount_difference)}",
            ])
            reasons.append("Reference matched but amount differs")
        date_points, date_reason = _date_score(bank.date, ledger.date)
        scores += date_points
        evidence.append(date_reason)
        if date_points == 0:
            reasons.append(date_reason)
        scores += _description_score(bank.description, ledger.description)
        if bank.description and ledger.description:
            evidence.append("Description similarity evaluated")
    elif bank:
        reasons.append("Missing ledger record")
        evidence.append("Bank record has no ledger counterpart")
    elif ledger:
        reasons.append("Missing bank record")
        evidence.append("Ledger record has no bank counterpart")

    matched_sources = [source for source, record in (
        ("BANK", bank), ("LEDGER", ledger), ("SETTLEMENT", settlement)
    ) if record]
    if settlement_supplied and not settlement:
        reasons.append("Missing settlement record")
        evidence.append("No settlement counterpart found")
    elif settlement and bank:
        settlement_difference = abs(bank.amount - settlement.amount)
        variance = max(variance, settlement_difference)
        evidence.append(f"Settlement amount: {_amount_text(settlement.amount)}")
        if settlement_difference > 0.01:
            reasons.append("Settlement amount differs")
            evidence.append(f"Settlement variance: {_amount_text(settlement_difference)}")
        if settlement.fee:
            evidence.append(f"Settlement fee: {_amount_text(settlement.fee)}")

    if duplicates:
        status = "DUPLICATE"
        reasons.insert(0, f"Duplicate reference in {', '.join(duplicates)} source")
        evidence.insert(0, "Duplicate reference detected; records were not deleted")
    elif not bank or not ledger:
        status = "UNMATCHED"
    elif settlement_supplied and not settlement:
        status = "PARTIAL" if scores >= 70 else "UNMATCHED"
    elif scores >= 90 and not reasons:
        status = "MATCHED"
    elif scores >= 70:
        status = "PARTIAL"
    else:
        status = "EXCEPTION"

    if not reasons:
        reasons.append("Reference, amount, date, and description matched")
    return {
        "reference": reference,
        "status": status,
        "confidence_score": scores,
        "matched_sources": matched_sources,
        "variance": round(variance, 2),
        "reason": "; ".join(reasons),
        "evidence": evidence,
    }


def reconcile_sources(
    bank_records: list[CanonicalRecord],
    ledger_records: list[CanonicalRecord],
    settlement_records: list[CanonicalRecord],
) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, list[CanonicalRecord]]] = defaultdict(lambda: defaultdict(list))
    for records in (bank_records, ledger_records, settlement_records):
        for record in records:
            grouped[record.reference][record.source].append(record)
    return [
        _build_record(reference, grouped[reference], bool(settlement_records))
        for reference in sorted(grouped)
    ]


SINGLE_REFERENCE_ALIASES = [
    "record_id",
    "transaction_id",
    "transaction_reference",
    "payment_id",
    "reference",
    "bank_reference",
    "ledger_reference",
    "settlement_reference",
    "utr",
]
SINGLE_AMOUNT_ALIASES = {
    "bank_amount": ["bank_amount", "bank_value", "bank_total", "bank_payment_amount"],
    "ledger_amount": ["ledger_amount", "ledger_value", "ledger_total", "ledger_payment_amount"],
    "settlement_amount": ["settlement_amount", "settled_amount", "settled_value", "settlement_value", "settled", "settlement", "payout_amount", "net_settlement", "net_settled", "settlement_total"],
}
SINGLE_DATE_ALIASES = [
    "date",
    "transaction_date",
    "payment_date",
    "bank_date",
    "ledger_date",
    "settlement_date",
]
SINGLE_VENDOR_ALIASES = ["vendor", "merchant", "merchant_name", "supplier"]


def _single_columns(fieldnames: list[str]) -> dict[str, str | None]:
    normalised = {
        _normalise_column(field): field
        for field in fieldnames
        if field
    }
    columns: dict[str, str | None] = {}
    for canonical in ("reference", "date", "vendor"):
        aliases = {
            "reference": SINGLE_REFERENCE_ALIASES,
            "date": SINGLE_DATE_ALIASES,
            "vendor": SINGLE_VENDOR_ALIASES,
        }[canonical]
        columns[canonical] = next(
            (normalised[alias] for alias in aliases if alias in normalised),
            None,
        )
    for canonical, aliases in SINGLE_AMOUNT_ALIASES.items():
        columns[canonical] = next(
            (normalised[alias] for alias in aliases if alias in normalised),
            None,
        )
    if columns["reference"] is None:
        raise MultiFileValidationError(
            "single_file",
            "Unable to detect reference column for SINGLE_FILE source",
            fieldnames,
            ["record_id", "payment_id", "reference", "bank_reference", "ledger_reference", "UTR"],
        )
    if not any(columns[name] for name in SINGLE_AMOUNT_ALIASES):
        raise MultiFileValidationError(
            "single_file",
            "Unable to detect a bank, ledger, or settlement amount column for SINGLE_FILE source",
            fieldnames,
            ["bank_amount", "ledger_amount", "settlement_amount"],
        )
    return columns


def detect_single_mapping_from_bytes(data: bytes) -> dict[str, str | None]:
    if not data:
        raise MultiFileValidationError("single_file", "File is empty")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise MultiFileValidationError("single_file", "File must be UTF-8 encoded")
    fieldnames = next(csv.reader(io.StringIO(text)), [])
    if not fieldnames:
        raise MultiFileValidationError("single_file", "CSV header is missing")
    columns = _single_columns(fieldnames)
    return {
        "reference": columns["reference"],
        "date": columns["date"],
        "vendor": columns["vendor"],
        "bank_amount": columns["bank_amount"],
        "ledger_amount": columns["ledger_amount"],
        "settlement_amount": columns["settlement_amount"],
    }


def parse_single_file(data: bytes) -> tuple[list[dict[str, Any]], dict[str, str | None]]:
    if not data:
        raise MultiFileValidationError("single_file", "File is empty")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise MultiFileValidationError("single_file", "File must be UTF-8 encoded")
    reader = csv.DictReader(io.StringIO(text))
    fieldnames = reader.fieldnames or []
    if not fieldnames:
        raise MultiFileValidationError("single_file", "CSV header is missing")
    columns = _single_columns(fieldnames)
    mapping = detect_single_mapping_from_bytes(data)
    records = []
    for row_number, row in enumerate(reader, 2):
        reference = (row.get(columns["reference"]) or "").strip()
        if not reference:
            raise MultiFileValidationError("single_file", f"Reference is empty at row {row_number}")
        values = {}
        for name in SINGLE_AMOUNT_ALIASES:
            column = columns[name]
            values[name] = (
                _parse_amount(row.get(column), "single_file", row_number)
                if column
                else None
            )
        date_value = (
            _parse_date(row.get(columns["date"]), "single_file", row_number)
            if columns["date"]
            else None
        )
        available = [value for value in values.values() if value is not None]
        if not available:
            raise MultiFileValidationError("single_file", f"No amount value at row {row_number}")
        variance = round(max(available) - min(available), 2)
        present_sources = [
            source
            for source, name in (
                ("BANK", "bank_amount"),
                ("LEDGER", "ledger_amount"),
                ("SETTLEMENT", "settlement_amount"),
            )
            if values[name] is not None
        ]
        comparisons = len(available) > 1
        if not comparisons:
            status = "UNMATCHED"
            reason = "Only one financial source amount is available."
        elif variance <= 0.01:
            status = "MATCHED"
            source_text = ", ".join(source.lower() for source in present_sources)
            reason = f"{source_text.capitalize()} amounts match."
        else:
            status = "PARTIAL"
            reason = f"Financial source amounts differ by ₹{variance:.2f}."
        evidence = [
            f"{source.capitalize()} amount: {_amount_text(values[name])}"
            for source, name in (
                ("bank", "bank_amount"),
                ("ledger", "ledger_amount"),
                ("settlement", "settlement_amount"),
            )
            if values[name] is not None
        ]
        if date_value is None:
            evidence.append("Date unavailable in source.")
            reason = f"{reason} Date unavailable in source."
        records.append({
            "id": row_number - 1,
            "transaction_id": reference,
            "reference": reference,
            "status": status,
            "variance": variance,
            "reason": reason,
            "evidence": evidence,
            "confidence": 100 if status == "MATCHED" else 70 if status == "PARTIAL" else 0,
            "confidence_score": 100 if status == "MATCHED" else 70 if status == "PARTIAL" else 0,
            "amount": values["bank_amount"] or values["ledger_amount"] or values["settlement_amount"],
            **values,
            "vendor": (row.get(columns["vendor"]) or "").strip() if columns["vendor"] else None,
            "date": date_value,
            "matched_sources": present_sources,
        })
    return records, mapping
