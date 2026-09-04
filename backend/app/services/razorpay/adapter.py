from __future__ import annotations

import base64
import csv
import io
import json
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class RazorpayConfigurationError(RuntimeError):
    pass


class RazorpayAPIError(RuntimeError):
    pass


def normalize_payment(payment: dict) -> dict:
    """Convert one Razorpay payment into the existing import contract."""
    payment_id = str(payment.get("id") or "").strip()
    if not payment_id:
        raise ValueError("Razorpay payment has no id")
    created = payment.get("created_at")
    if created:
        date_value = datetime.fromtimestamp(int(created), tz=timezone.utc).date().isoformat()
    else:
        date_value = datetime.now(timezone.utc).date().isoformat()
    amount = float(payment.get("amount") or 0) / 100
    refunded = float(payment.get("amount_refunded") or 0) / 100
    status = str(payment.get("status") or "unknown").upper()
    return {
        "transaction_id": payment_id,
        "date": date_value,
        "amount": amount,
        "type": "payment",
        "status": status,
        "merchant": payment.get("description") or None,
        "vendor": payment.get("email") or None,
        "settlement_id": payment.get("order_id") or None,
        "settlement_amount": None,
        "fee": float(payment.get("fee") or 0) / 100,
        "refund_amount": refunded,
        "customer": payment.get("contact") or None,
        "currency": str(payment.get("currency") or "INR"),
    }


def _auth_header(key_id: str, key_secret: str) -> str:
    token = base64.b64encode(f"{key_id}:{key_secret}".encode()).decode()
    return f"Basic {token}"


def fetch_test_payments(key_id: str | None, key_secret: str | None, limit: int = 100) -> list[dict]:
    if not key_id or not key_secret:
        raise RazorpayConfigurationError("Razorpay test credentials are not configured")
    request = Request(
        f"https://api.razorpay.com/v1/payments?count={min(max(limit, 1), 100)}",
        headers={"Authorization": _auth_header(key_id, key_secret), "Accept": "application/json"},
    )
    try:
        with urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        raise RazorpayAPIError("Unable to retrieve Razorpay test payments") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        raise RazorpayAPIError("Razorpay returned an invalid payments response")
    return [normalize_payment(item) for item in payload["items"]]


def payments_csv(payments: list[dict]) -> bytes:
    fields = [
        "transaction_id", "date", "amount", "type", "status", "merchant", "vendor",
        "settlement_id", "settlement_amount", "fee", "refund_amount", "customer", "currency",
    ]
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    writer.writerows({field: payment.get(field) for field in fields} for payment in payments)
    return output.getvalue().encode("utf-8")
