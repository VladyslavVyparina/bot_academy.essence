import hashlib
import hmac
import time
from datetime import datetime

import httpx

from app.config import settings


def _signature_string(parts: list[str]) -> str:
    return ";".join(parts)


def make_payment_payload(order_ref: str, amount_uah: int, product_name: str = "Event ticket") -> dict:
    now = int(time.time())
    payload = {
        "merchantAccount": settings.wayforpay_merchant_login,
        "merchantDomainName": settings.app_base_url.replace("https://", "").replace("http://", ""),
        "orderReference": order_ref,
        "orderDate": now,
        "amount": f"{amount_uah:.2f}",
        "currency": "UAH",
        "productName": [product_name],
        "productCount": [1],
        "productPrice": [f"{amount_uah:.2f}"],
        "merchantSignature": "",
        "returnUrl": settings.wayforpay_return_url,
        "serviceUrl": settings.wayforpay_service_url,
    }
    sign_data = _signature_string(
        [
            payload["merchantAccount"],
            payload["merchantDomainName"],
            payload["orderReference"],
            str(payload["orderDate"]),
            payload["amount"],
            payload["currency"],
            product_name,
            "1",
            payload["amount"],
        ]
    )
    payload["merchantSignature"] = hmac.new(
        settings.wayforpay_secret_key.encode("utf-8"),
        sign_data.encode("utf-8"),
        hashlib.md5,
    ).hexdigest()
    return payload


def verify_callback(data: dict) -> bool:
    signature = data.get("merchantSignature", "")
    products = data.get("productName", [])
    counts = data.get("productCount", [])
    prices = data.get("productPrice", [])
    if not isinstance(products, list):
        products = [products] if products else []
    if not isinstance(counts, list):
        counts = [counts] if counts else []
    if not isinstance(prices, list):
        prices = [prices] if prices else []

    parts = [
        str(data.get("merchantAccount", "")),
        str(data.get("orderReference", "")),
        str(data.get("amount", "")),
        str(data.get("currency", "")),
        str(data.get("authCode", "")),
        str(data.get("cardPan", "")),
        str(data.get("transactionStatus", "")),
        str(data.get("reasonCode", "")),
    ]
    for i in range(len(products)):
        parts.extend([str(products[i]), str(counts[i]), str(prices[i])])

    control_sign = hmac.new(
        settings.wayforpay_secret_key.encode("utf-8"),
        ";".join(parts).encode("utf-8"),
        hashlib.md5,
    ).hexdigest()
    return signature == control_sign


def _invoice_signature(order_ref: str, order_date: int, amount: str, currency: str, product_name: str, product_count: str, product_price: str) -> str:
    data = ";".join([
        settings.wayforpay_merchant_login,
        settings.app_base_url.replace("https://", "").replace("http://", "").split("/")[0] or "localhost",
        order_ref,
        str(order_date),
        amount,
        currency,
        product_name,
        product_count,
        product_price,
    ])
    return hmac.new(settings.wayforpay_secret_key.encode("utf-8"), data.encode("utf-8"), hashlib.md5).hexdigest()


async def create_invoice(
    order_ref: str,
    amount_uah: float,
    product_name: str,
    client_email: str = "",
    client_phone: str = "",
    client_name: str = "",
) -> str | None:
    """
    Create WayForPay invoice via API. Returns invoiceUrl for payment, or None on error.
    """
    order_date = int(time.time())
    amount_str = f"{amount_uah:.2f}"
    domain = settings.app_base_url.replace("https://", "").replace("http://", "").split("/")[0] or "localhost"
    if ":" in domain:
        domain = domain.split(":")[0]

    signature = _invoice_signature(order_ref, order_date, amount_str, "UAH", product_name, "1", amount_str)

    client_parts = (client_name or "").split()
    client_first = client_parts[0] if client_parts else "-"
    client_last = " ".join(client_parts[1:]) if len(client_parts) > 1 else "-"

    payload = {
        "transactionType": "CREATE_INVOICE",
        "merchantAccount": settings.wayforpay_merchant_login,
        "merchantDomainName": domain,
        "merchantSignature": signature,
        "apiVersion": 1,
        "language": "UA",
        "serviceUrl": settings.wayforpay_service_url,
        "returnUrl": settings.wayforpay_return_url,
        "orderReference": order_ref,
        "orderDate": order_date,
        "amount": amount_uah,
        "currency": "UAH",
        "orderTimeout": 86400,
        "productName": [product_name],
        "productCount": [1],
        "productPrice": [amount_str],
        "clientEmail": client_email,
        "clientPhone": client_phone or "",
        "clientFirstName": client_first,
        "clientLastName": client_last,
    }
    print(f"[WayForPay] create_invoice: order_ref={order_ref} amount={amount_uah} domain={domain}")
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post("https://api.wayforpay.com/api", json=payload)
        if r.status_code != 200:
            print(f"[WayForPay] HTTP {r.status_code}: {r.text[:500]}")
            return None
        data = r.json()
        print(f"[WayForPay] Відповідь: reasonCode={data.get('reasonCode')} reason={data.get('reason','')} invoiceUrl={data.get('invoiceUrl','')}")
        if str(data.get("reasonCode")) != "1100":
            print(f"[WayForPay] API помилка: {data.get('reason', '')} code={data.get('reasonCode')}")
        return data.get("invoiceUrl")


async def check_payment_status(order_ref: str) -> str | None:
    """
    Перевірка статусу оплати через API (без callback).
    Повертає transactionStatus: Approved, InProcessing, Pending тощо.
    """
    sign_data = f"{settings.wayforpay_merchant_login};{order_ref}"
    sign = hmac.new(
        settings.wayforpay_secret_key.encode("utf-8"),
        sign_data.encode("utf-8"),
        hashlib.md5,
    ).hexdigest()
    payload = {
        "transactionType": "CHECK_STATUS",
        "merchantAccount": settings.wayforpay_merchant_login,
        "orderReference": order_ref,
        "merchantSignature": sign,
        "apiVersion": 1,
    }
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post("https://api.wayforpay.com/api", json=payload)
        if r.status_code != 200:
            return None
        data = r.json()
        return data.get("transactionStatus")


def success_ack(order_reference: str) -> dict:
    response_time = int(datetime.now().timestamp())
    data = f"{order_reference};accept;{response_time}"
    sign = hmac.new(settings.wayforpay_secret_key.encode(), data.encode(), hashlib.md5).hexdigest()
    return {"orderReference": order_reference, "status": "accept", "time": response_time, "signature": sign}
