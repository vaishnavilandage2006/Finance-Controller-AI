import csv, io, math, re, datetime

REQUIRED = {"transaction_id", "date", "amount", "type", "status"}
MAX_BYTES = 10 * 1024 * 1024
MAX_ROWS = 100_000
MAX_ABS_AMOUNT = 1e12

# Columns whose content is numeric (formula-injection check is skipped).
NUMERIC_COLUMNS = {
    "amount", "settlement_amount", "fee", "refund_amount",
    "bank_amount", "ledger_amount", "gross_amount", "settled_value",
}

# Cells beginning with any of these characters are treated as potential
# spreadsheet formula injection (they are interpreted as formulas by Excel).
FORMULA_LEADERS = ("=", "+", "@", "\t", "\r", "\x00")

DATE_COLUMNS = {
    "date", "due_date", "transaction_date", "payment_date",
    "settlement_date", "created_at", "timestamp",
}

_AMOUNT_ERROR = "Row {row}: {column} must be a finite number"


def _looks_like_formula(value: str, column: str) -> bool:
    """Detect CSV/formula injection without breaking legitimate values.

    Numeric and date columns are excluded: negative numbers ("-125") and
    ISO dates ("-2026-01-01" style text) must keep parsing normally.
    """
    if not value:
        return False
    stripped = value.strip()
    if not stripped:
        return False
    if column in NUMERIC_COLUMNS or column in DATE_COLUMNS:
        return False
    if stripped[0] in FORMULA_LEADERS:
        return True
    # '-cmd' style: leading minus followed by a letter (Excel formula).
    if stripped[0] == "-" and len(stripped) > 1 and re.match(r"[A-Za-z(]", stripped[1]):
        return True
    return False


def _check_number(row, column, errors, line):
    """Validate that a numeric cell is a finite, bounded number."""
    raw = (row.get(column) or "").strip()
    if not raw:
        return
    try:
        value = float(raw)
    except (TypeError, ValueError):
        errors.append(_AMOUNT_ERROR.format(row=line, column=column))
        return
    if not math.isfinite(value):
        errors.append(f"Row {line}: {column} must be a finite number")
    elif abs(value) > MAX_ABS_AMOUNT:
        errors.append(
            f"Row {line}: {column} exceeds the supported magnitude "
            f"({MAX_ABS_AMOUNT:.0f})"
        )


def validate_csv(data: bytes):
    """Parse and validate a finance CSV.

    Returns (rows, errors). `errors` is empty only when every row is valid;
    on any error the caller must not import the file (rows may be partial).
    """
    if len(data) > MAX_BYTES:
        return [], ["File exceeds 10 MB"]
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return [], ["File must be UTF-8 encoded"]

    reader = csv.DictReader(io.StringIO(text))
    columns = set(reader.fieldnames or [])
    missing = REQUIRED - columns
    if missing:
        return [], [f"Missing required columns: {', '.join(sorted(missing))}"]

    if "\x00" in text:
        return [], ["File contains NUL bytes and is not a valid CSV"]

    rows = []
    errors = []
    seen_ids = {}

    for index, row in enumerate(reader, start=2):
        if index - 1 > MAX_ROWS:
            errors.append(f"File exceeds {MAX_ROWS} data rows")
            break

        transaction_id = (row.get("transaction_id") or "").strip()
        if not transaction_id:
            errors.append(f"Row {index}: transaction_id is empty")
            continue
        if transaction_id in seen_ids:
            errors.append(
                f"Row {index}: duplicate transaction_id '{transaction_id}' "
                f"(first seen on row {seen_ids[transaction_id]})"
            )
            continue
        seen_ids[transaction_id] = index

        try:
            amount_value = float(row["amount"])
        except (TypeError, ValueError):
            errors.append(f"Row {index}: amount is not a valid number")
            continue
        if not math.isfinite(amount_value):
            errors.append(f"Row {index}: amount must be a finite number")
            continue
        if abs(amount_value) > MAX_ABS_AMOUNT:
            errors.append(
                f"Row {index}: amount exceeds the supported magnitude "
                f"({MAX_ABS_AMOUNT:.0f})"
            )
            continue

        try:
            datetime.date.fromisoformat((row["date"] or "").strip()[:10])
        except ValueError:
            errors.append(f"Row {index}: invalid date '{row.get('date')}'")
            continue

        # Optional numeric columns must also be finite and bounded.
        for column in NUMERIC_COLUMNS:
            if column in row:
                _check_number(row, column, errors, index)

        # Formula / CSV injection guard on textual cells.
        for column, value in row.items():
            if not value:
                continue
            if _looks_like_formula(value, column or ""):
                errors.append(
                    f"Row {index}: column '{column}' starts with a character "
                    "that can trigger spreadsheet formula execution"
                )

        rows.append(row)

    return rows, errors
