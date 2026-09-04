from __future__ import annotations

import csv
import io
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

MONETARY_TOLERANCE = 0.01
ALIASES = {
    "reference": ("transaction_id", "payment_id", "txn_id", "transaction_reference", "payment_reference", "reference", "order_id", "settlement_id", "settlement_reference", "utr", "utr_no", "utr_number", "bank_reference", "ledger_reference", "record_id", "invoice_id", "invoice"),
    "amount": ("amount", "transaction_amount", "payment_amount", "paid_amount", "gross_amount", "total_amount", "transaction_value", "txn_amount"),
    "bank_amount": ("bank_amount", "bank_value", "bank_total", "credit", "credit_amount", "debit", "debit_amount"),
    "ledger_amount": ("ledger_amount", "ledger_value", "ledger_total", "ledger_payment_amount"),
    "settlement_amount": ("settlement_amount", "settled_amount", "settled_value", "settlement_value", "settled", "settlement", "payout_amount", "net_settlement", "net_settled", "settlement_total"),
    "fee": ("fee", "fees", "processing_fee", "gateway_fee", "transaction_fee", "bank_charge", "bank_charges", "charges"),
    "refund": ("refund", "refund_amount", "refunded_amount", "refunds"),
    "adjustment": ("adjustment", "adjustments", "discount", "positive_adjustment"),
    "date": ("date", "transaction_date", "payment_date", "settlement_date", "bank_date", "ledger_date", "created_at", "timestamp", "value_date", "posting_date"),
    "party": ("vendor", "merchant", "merchant_name", "customer", "account", "beneficiary", "supplier", "party"),
    "currency": ("currency", "currency_code", "ccy"),
    "description": ("description", "narration", "remarks", "remark", "memo", "details", "particulars", "payment_description"),
}
ROLE_SIGNALS = {
    "BANK": ("bank_reference", "utr", "bank_amount", "bank_date", "credit", "debit", "value_date"),
    "LEDGER": ("ledger_reference", "ledger_amount", "ledger_date", "invoice_id", "account", "erp", "journal", "posting_date"),
    "SETTLEMENT": ("settlement_id", "settlement_reference", "settlement_amount", "settlement_date", "settlement_batch", "processing_fee", "gateway_fee"),
}


class MultiFileValidationError(ValueError):
    def __init__(self, source: str, message: str, available_columns=None, suggested_columns=None):
        super().__init__(message)
        self.source, self.message = source, message
        self.available_columns, self.suggested_columns = available_columns or [], suggested_columns or []

    def as_dict(self):
        result = {"source": self.source, "error": self.message}
        if self.available_columns: result["available_columns"] = self.available_columns
        if self.suggested_columns: result["suggested_columns"] = self.suggested_columns
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
    party: str = ""
    fields: dict[str, Any] | None = None
    raw: dict[str, str] | None = None


def _normalise_column(value: str) -> str:
    value = (value or "").replace("\ufeff", "")
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", value.strip().lower())).strip("_")


def _score(name: str, aliases: tuple[str, ...]) -> int:
    if name in aliases: return 1000 - aliases.index(name)
    tokens = set(name.split("_"))
    return max((700 - 10 * len(tokens - set(alias.split("_"))) for alias in aliases if set(alias.split("_")) <= tokens), default=0)


def _detect_columns(fieldnames: list[str], source: str) -> dict[str, str]:
    available = {_normalise_column(name): name for name in fieldnames if name}
    selected = {}
    for semantic, aliases in ALIASES.items():
        candidates = [(score, available[name]) for name in available if (score := _score(name, aliases))]
        if candidates: selected[semantic] = max(candidates)[1]
    if "amount" not in selected:
        credit = next((available[n] for n in available if n in ("credit", "credit_amount", "credit_amt")), None)
        debit = next((available[n] for n in available if n in ("debit", "debit_amount", "debit_amt")), None)
        if credit and debit:
            selected.update(amount="__signed_credit_debit__", credit=credit, debit=debit)
        elif credit or debit: selected["amount"] = credit or debit
    if not any(selected.get(key) for key in ("reference", "amount", "bank_amount", "ledger_amount", "settlement_amount")):
        raise MultiFileValidationError(source, "Unable to reconcile this file because no transaction/payment/reference identifier and no usable amount field were detected.", fieldnames, ["transaction_id", "payment_id", "reference", "amount", "settlement_amount"])
    return selected


def detect_source_role(fieldnames: list[str], filename: str = "") -> dict[str, Any]:
    names = {_normalise_column(name) for name in fieldnames}
    scores = {role: sum(signal in names for signal in signals) for role, signals in ROLE_SIGNALS.items()}
    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    role, top = ranked[0]
    if top == 0: return {"role": "UNKNOWN", "confidence": 0, "assumption": "No source-specific columns were detected.", "scores": scores}
    tied = top == ranked[1][1]
    return {"role": role, "confidence": min(99, 55 + top * 12 + (20 if not tied else 0)), "assumption": "Source role is ambiguous; selected the strongest available schema signal." if tied else None, "scores": scores}


def _parse_date(value: str | None, source: str, row: int) -> date | None:
    text = (value or "").strip()
    if not text: return None
    for candidate in (text, text[:10]):
        try: return date.fromisoformat(candidate)
        except ValueError: pass
        for fmt in ("%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d", "%d-%m-%Y", "%d.%m.%Y"):
            try: return datetime.strptime(candidate, fmt).date()
            except ValueError: pass
    raise MultiFileValidationError(source, f"Invalid date at row {row}: {text}")


def _parse_amount(value: str | None, source: str, row: int) -> float | None:
    text = (value or "").strip()
    if not text: return None
    negative = text.startswith("(") and text.endswith(")")
    text = re.sub(r"[^0-9.\-]", "", text.replace(",", ""))
    try: number = float(text)
    except (TypeError, ValueError): raise MultiFileValidationError(source, f"Invalid amount at row {row}: {value}")
    return -abs(number) if negative else number


def _rows(data: bytes, source: str) -> tuple[list[str], list[dict[str, str]]]:
    if not data: raise MultiFileValidationError(source, "File is empty")
    try: text = data.decode("utf-8-sig")
    except UnicodeDecodeError: raise MultiFileValidationError(source, "File must be UTF-8 encoded")
    reader = csv.DictReader(io.StringIO(text)); fields = reader.fieldnames or []
    if not fields or not any(name.strip() for name in fields): raise MultiFileValidationError(source, "CSV header is missing")
    return fields, [dict(row) for row in reader if any((value or "").strip() for value in row.values())]


def detect_source_mapping(fieldnames: list[str], source: str) -> dict[str, str | None]:
    columns = _detect_columns(fieldnames, source)
    result = {key: ("credit/debit" if value == "__signed_credit_debit__" else value) for key, value in columns.items() if key not in ("credit", "debit")}
    result.setdefault("date", None)
    return result


def detect_mapping_from_bytes(data: bytes, source: str) -> dict[str, str | None]:
    fields, _ = _rows(data, source); return detect_source_mapping(fields, source)


def _get(row: dict[str, str], columns: dict[str, str], key: str) -> str:
    column = columns.get(key); return ((row.get(column, "") if column else "") or "")


def parse_source(data: bytes, source: str) -> list[CanonicalRecord]:
    fields, rows = _rows(data, source); columns = _detect_columns(fields, source); records = []
    for row_number, row in enumerate(rows, 2):
        amount = _parse_amount(_get(row, columns, "amount"), source, row_number) if columns.get("amount") != "__signed_credit_debit__" else ((_parse_amount(_get(row, columns, "credit"), source, row_number) or 0) - (_parse_amount(_get(row, columns, "debit"), source, row_number) or 0))
        values = {key: _parse_amount(_get(row, columns, key), source, row_number) for key in ("bank_amount", "ledger_amount", "settlement_amount", "fee", "refund", "adjustment") if columns.get(key)}
        if amount is not None: values["amount"] = amount
        for key in ("date", "party", "currency", "description"):
            if columns.get(key): values[key] = _get(row, columns, key).strip()
        usable = next((values.get(key) for key in ("amount", "bank_amount", "ledger_amount", "settlement_amount") if values.get(key) is not None), None)
        reference = _get(row, columns, "reference").strip()
        if not reference and usable is None: raise MultiFileValidationError(source, f"Row {row_number} has neither a usable identifier nor a usable amount.")
        records.append(CanonicalRecord(source.upper(), _parse_date(values.get("date"), source, row_number) if values.get("date") else None, reference or f"ROW-{row_number - 1}", float(usable or 0), str(values.get("description", "")), _get(row, columns, "settlement_id").strip(), float(values.get("fee") or 0), str(values.get("currency") or "INR"), row_number, str(values.get("party", "")), values, {key: value or "" for key, value in row.items()}))
    return records


def _money(value: float | None) -> str: return f"₹{float(value or 0):.2f}"


def _single_result(record: CanonicalRecord, duplicate: bool) -> dict[str, Any]:
    fields = record.fields or {}; amounts = [float(fields[key]) for key in ("bank_amount", "ledger_amount", "settlement_amount") if fields.get(key) is not None]
    gross = fields.get("amount") or (amounts[0] if amounts else None); actual = fields.get("settlement_amount")
    # Explicit amounts are compared directly. When both an explicit amount and an
    # explicit settlement_amount exist, variance = amount - settlement_amount.
    # Fees, refunds, and adjustments are context/evidence only and are never
    # automatically deducted to form an expected settlement amount.
    expected = float(gross) if gross is not None else None
    variance = (float(gross) - float(actual)) if gross is not None and actual is not None else (max(amounts) - min(amounts) if len(amounts) > 1 else 0)
    if duplicate: status, reason = "DUPLICATE", f"Duplicate {record.reference} detected; identifier uniqueness is expected."
    elif len(amounts) > 1 or actual is not None and expected is not None:
        status = "MATCHED" if abs(variance) <= MONETARY_TOLERANCE else "MISMATCH"
        if status == "MATCHED":
            reason = "All available financial evidence agrees within the configured tolerance."
        elif actual is not None:
            reason = f"Settlement amount differs from transaction amount by {_money(abs(variance))}."
        else:
            reason = f"Available transaction amounts differ by {_money(abs(variance))}."
    else: status, reason = "PARTIAL", "Transaction amount is available, but settlement-level verification is unavailable."
    if record.date is None: reason += " Date unavailable; date matching was skipped."
    return {"id": record.row_number - 1, "transaction_id": record.reference, "reference": record.reference, "status": status, "variance": round(abs(variance), 2), "variance_signed": round(variance, 2), "expected_amount": round(expected, 2) if expected is not None else None, "actual_amount": round(actual, 2) if actual is not None else None, "variance_percentage": round(abs(variance) / abs(expected) * 100, 2) if expected else None, "reason": reason, "calculation": (f"explicit amount {_money(expected)} vs settlement amount {_money(actual)}; fees/refunds/adjustments reported separately and not deducted" if gross is not None and actual is not None else (f"amounts compared directly: {', '.join(_money(value) for value in amounts)}" if amounts else f"single amount {_money(gross)} available; no counterpart to compare")), "evidence": [f"{key}: {_money(fields[key])}" for key in ("amount", "bank_amount", "ledger_amount", "settlement_amount") if fields.get(key) is not None], "confidence": 100 if status == "MATCHED" else 90 if status == "MISMATCH" else 70 if status == "PARTIAL" else 0, "confidence_score": 100 if status == "MATCHED" else 90 if status == "MISMATCH" else 70 if status == "PARTIAL" else 0, "amount": record.amount, "bank_amount": fields.get("bank_amount"), "ledger_amount": fields.get("ledger_amount"), "settlement_amount": fields.get("settlement_amount"), "vendor": record.party or None, "date": record.date, "currency": record.currency, "matched_sources": [key.replace("_amount", "").upper() for key in ("bank_amount", "ledger_amount", "settlement_amount") if fields.get(key) is not None], "source_values": record.raw or {}}


def parse_single_file(data: bytes) -> tuple[list[dict[str, Any]], dict[str, str | None]]:
    fields, _ = _rows(data, "single_file"); records = parse_source(data, "single_file"); occurrences = defaultdict(int)
    for record in records: occurrences[record.reference] += 1
    return [_single_result(record, occurrences[record.reference] > 1) for record in records], detect_source_mapping(fields, "single_file")


def detect_single_mapping_from_bytes(data: bytes) -> dict[str, str | None]:
    fields, _ = _rows(data, "single_file"); return detect_source_mapping(fields, "single_file")


def _compatible(left: CanonicalRecord, right: CanonicalRecord) -> bool:
    return abs(left.amount - right.amount) <= MONETARY_TOLERANCE and (not left.date or not right.date or abs((left.date - right.date).days) <= 3) and (not left.party or not right.party or left.party.lower() == right.party.lower())


def _multi_result(reference: str, grouped: dict[str, list[CanonicalRecord]], settlement_supplied: bool) -> dict[str, Any]:
    records = [record for values in grouped.values() for record in values]; roles = {record.source for record in records}; amounts = [record.amount for record in records]; variance = max(amounts) - min(amounts) if len(amounts) > 1 else 0
    # Explicit source amounts are compared directly; settlement fees are evidence only and never auto-deducted.
    settlement = next((record for record in records if record.source == "SETTLEMENT"), None)
    duplicate_roles = [role for role, values in grouped.items() if len(values) > 1]
    if duplicate_roles: status, reason = "DUPLICATE", f"Duplicate identifier detected in {', '.join(duplicate_roles)} source."
    elif len(roles) < 2: status, reason = "UNMATCHED", f"No counterpart record found for {next(iter(roles), 'source').lower()} record."
    elif abs(variance) > MONETARY_TOLERANCE: status, reason = "MISMATCH", f"Settlement amount differs from transaction amount by {_money(abs(variance))}." if settlement else f"Source amounts differ by {_money(abs(variance))}."
    elif settlement_supplied and "SETTLEMENT" not in roles: status, reason = "PARTIAL", "Bank and ledger amounts agree, but settlement evidence is missing."
    else: status, reason = "MATCHED", "Exact identifier and available source amounts agree within the configured tolerance."
    return {"reference": reference, "transaction_id": reference, "status": status, "confidence_score": 100 if status == "MATCHED" else 80 if status == "MISMATCH" else 60, "confidence": 100 if status == "MATCHED" else 80 if status == "MISMATCH" else 60, "matched_sources": sorted(roles), "variance": round(abs(variance), 2), "variance_signed": round(variance, 2), "expected_amount": round(min(amounts), 2) if amounts else None, "actual_amount": round(max(amounts), 2) if amounts else None, "variance_percentage": round(variance / abs(min(amounts)) * 100, 2) if amounts and min(amounts) else None, "reason": reason + (" Date unavailable for at least one source; date matching was skipped." if any(not record.date for record in records) else ""), "evidence": [f"{record.source}: {_money(record.amount)}" for record in records], "source_records": {record.source: record.raw or {} for record in records}, "date": next((record.date for record in records if record.date), None), "vendor": next((record.party for record in records if record.party), None), "amount": records[0].amount if records else None, "settlement_amount": next((record.amount for record in records if record.source == "SETTLEMENT"), None)}


def reconcile_sources(bank_records: list[CanonicalRecord], ledger_records: list[CanonicalRecord], settlement_records: list[CanonicalRecord]) -> list[dict[str, Any]]:
    all_records = bank_records + ledger_records + settlement_records; groups = defaultdict(lambda: defaultdict(list))
    for record in all_records: groups[record.reference.strip().lower()][record.source].append(record)
    match_index = defaultdict(set)
    for group_key, group in groups.items():
        if not all(len(values) == 1 for values in group.values()):
            continue
        for values in group.values():
            record = values[0]
            amount_cents = round(record.amount * 100)
            for source in ("BANK", "LEDGER", "SETTLEMENT"):
                if source not in group:
                    for candidate_cents in (amount_cents - 1, amount_cents, amount_cents + 1):
                        match_index[(source, candidate_cents)].add(group_key)
    for records in (bank_records, ledger_records, settlement_records):
        for record in records:
            key = record.reference.strip().lower()
            if key not in groups or len(groups[key].get(record.source, [])) != 1:
                continue
            if len(groups[key]) > 1:
                continue
            amount_cents = round(record.amount * 100)
            candidates = [
                groups[group_key] for group_key in {
                    candidate_key
                    for candidate_cents in (amount_cents - 1, amount_cents, amount_cents + 1)
                    for candidate_key in match_index.get((record.source, candidate_cents), ())
                    if candidate_key in groups
                }
                if groups[group_key].get(record.source) is None
                and all(len(values) == 1 for values in groups[group_key].values())
                and any(_compatible(record, other) for values in groups[group_key].values() for other in values)
            ]
            if len(candidates) == 1:
                target = candidates[0]; del groups[key]; target[record.source].append(record)
    return [
        _multi_result(
            next(record.reference for values in groups[reference].values() for record in values),
            groups[reference],
            bool(settlement_records),
        )
        for reference in sorted(groups)
    ]


def classify_counts(records: list[dict[str, Any]]) -> dict[str, int]:
    counts = {status: 0 for status in ("MATCHED", "PARTIAL", "MISMATCH", "UNMATCHED", "DUPLICATE")}
    for record in records: counts[record["status"]] = counts.get(record["status"], 0) + 1
    return counts
