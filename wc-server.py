
import os

import requests
from mcp.server.mcpserver import MCPServer
from woocommerce import API
import woocommerce.api as woocommerce_api

required = ("WC_STORE_URL", "WC_CONSUMER_KEY", "WC_CONSUMER_SECRET")
missing = [name for name in required if not os.getenv(name)]
if missing:
    raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")

HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8003"))
if os.getenv("WC_HOST_HEADER"):
    store_session = requests.Session()

    def request_with_store_host(method, url, **kwargs):
        headers = dict(kwargs.pop("headers", {}))
        headers["Host"] = os.environ["WC_HOST_HEADER"]
        return store_session.request(method, url, headers=headers, **kwargs)

    woocommerce_api.request = request_with_store_host

mcp = MCPServer("woocommerce-local")
VALID_STATUSES = {"pending", "processing", "on-hold", "completed",
                  "cancelled", "refunded", "failed"}

wcapi = API(
    url=os.environ["WC_STORE_URL"],
    consumer_key=os.environ["WC_CONSUMER_KEY"],
    consumer_secret=os.environ["WC_CONSUMER_SECRET"],
    wp_api=True,
    version="wc/v3",
    timeout=15,
)
def _order_summary(o: dict) -> dict:
    billing = o.get("billing", {})
    return {
        "id": o["id"],
        "status": o["status"],
        "total": o["total"],
        "currency": o["currency"],
        "date_created": o["date_created"],
        "customer": f'{billing.get("first_name", "")} {billing.get("last_name", "")}'.strip(),
        "items": [{"name": i["name"], "quantity": i["quantity"]} for i in o["line_items"]],
    }

@mcp.tool()
def list_products(
    search: str = "",
    page: int = 1,
    per_page: int = 10,
) -> dict:
    """List WooCommerce products, optionally filtering by search text."""
    if page < 1:
        return {"error": "page must be at least 1"}
    if per_page < 1 or per_page > 100:
        return {"error": "per_page must be between 1 and 100"}

    params = {"page": page, "per_page": per_page}
    if search.strip():
        params["search"] = search.strip()

    response = wcapi.get("products", params=params)

    if not response.ok:
        return {
            "error": "WooCommerce API request failed",
            "status": response.status_code,
            "details": response.text[:1000],
        }

    products = response.json()
    return {
        "count": len(products),
        "products": [
            {
                "id": p["id"],
                "name": p["name"],
                "price": p["price"],
                "status": p["status"],
                "stock_quantity": p["stock_quantity"],
            }
            for p in products
        ],
    }


@mcp.tool()
def get_product(product_id: int) -> dict:
    """Get a WooCommerce product by its numeric ID."""
    if product_id < 1:
        return {"error": "product_id must be positive"}

    response = wcapi.get(f"products/{product_id}")

    if not response.ok:
        return {
            "error": "WooCommerce API request failed",
            "status": response.status_code,
            "details": response.text[:1000],
        }

    p = response.json()
    return {
        "id": p["id"],
        "name": p["name"],
        "price": p["price"],
        "regular_price": p["regular_price"],
        "sale_price": p["sale_price"],
        "status": p["status"],
        "stock_quantity": p["stock_quantity"],
        "description": p["description"],
    }

@mcp.tool()
def list_orders(
    after: str = "",
    before: str = "",
    status: str = "",
    page: int = 1,
    per_page: int = 10,
) -> dict:
    """List WooCommerce orders, newest first. after/before are ISO 8601
    datetimes (e.g. 2026-10-15T00:00:00) for filtering by creation date.
    status: pending, processing, on-hold, completed, cancelled, refunded, failed."""
    if page < 1:
        return {"error": "page must be at least 1"}
    if per_page < 1 or per_page > 100:
        return {"error": "per_page must be between 1 and 100"}
    if status and status not in VALID_STATUSES:
        return {"error": f"status must be one of {sorted(VALID_STATUSES)}"}

    params = {"page": page, "per_page": per_page, "orderby": "date", "order": "desc"}
    if after.strip():
        params["after"] = after.strip()
    if before.strip():
        params["before"] = before.strip()
    if status:
        params["status"] = status

    response = wcapi.get("orders", params=params)

    if not response.ok:
        return {
            "error": "WooCommerce API request failed",
            "status": response.status_code,
            "details": response.text[:1000],
        }

    orders = response.json()
    return {"count": len(orders), "orders": [_order_summary(o) for o in orders]}


@mcp.tool()
def get_order(order_id: int) -> dict:
    """Get a WooCommerce order by its numeric ID, including items and billing email."""
    if order_id < 1:
        return {"error": "order_id must be positive"}

    response = wcapi.get(f"orders/{order_id}")

    if not response.ok:
        return {
            "error": "WooCommerce API request failed",
            "status": response.status_code,
            "details": response.text[:1000],
        }

    o = response.json()
    return {
        **_order_summary(o),
        "payment_method": o.get("payment_method_title", ""),
        "billing_email": o.get("billing", {}).get("email", ""),
    }
from decimal import Decimal, InvalidOperation


@mcp.tool()
def create_product(
    name: str,
    price: str,
    description: str = "",
    stock_quantity: int | None = None,
    status: str = "publish",
) -> dict:
    """Create a WooCommerce product. price is a number as a string, e.g. "499.00".
    status: publish (visible on storefront), draft, pending or private."""
    if not name.strip():
        return {"error": "name is required"}
    try:
        if Decimal(price) < 0:
            return {"error": "price must not be negative"}
    except InvalidOperation:
        return {"error": "price must be a number, e.g. 499.00"}
    if status not in {"publish", "draft", "pending", "private"}:
        return {"error": "status must be publish, draft, pending or private"}
    if stock_quantity is not None and stock_quantity < 0:
        return {"error": "stock_quantity must not be negative"}

    data = {
        "name": name.strip(),
        "type": "simple",
        "regular_price": str(price),
        "status": status,
        "description": description,
    }
    if stock_quantity is not None:
        data["manage_stock"] = True
        data["stock_quantity"] = stock_quantity

    response = wcapi.post("products", data)

    if not response.ok:
        return {
            "error": "WooCommerce API request failed",
            "status": response.status_code,
            "details": response.text[:1000],
        }

    p = response.json()
    return {
        "id": p["id"],
        "name": p["name"],
        "price": p["price"],
        "status": p["status"],
        "stock_quantity": p["stock_quantity"],
        "url": p["permalink"],
    }


@mcp.tool()
def update_order_status(order_id: int, status: str) -> dict:
    """Change a WooCommerce order's status.
    status: pending, processing, on-hold, completed, cancelled, refunded, failed."""
    if order_id < 1:
        return {"error": "order_id must be positive"}
    if status not in VALID_STATUSES:
        return {"error": f"status must be one of {sorted(VALID_STATUSES)}"}

    response = wcapi.put(f"orders/{order_id}", {"status": status})

    if not response.ok:
        return {
            "error": "WooCommerce API request failed",
            "status": response.status_code,
            "details": response.text[:1000],
        }

    return _order_summary(response.json())


if __name__ == "__main__":
    allowed_hosts = [
        item.strip() for item in os.getenv("ALLOWED_HOSTS", "").split(",") if item.strip()
    ]
    transport_security = None
    if allowed_hosts:
        from mcp.server.transport_security import TransportSecuritySettings

        transport_security = TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=allowed_hosts,
        )
    mcp.run(transport="streamable-http",
            host=HOST,
        port=PORT,
        json_response=True,
        stateless_http=True,
        transport_security=transport_security,
        )

