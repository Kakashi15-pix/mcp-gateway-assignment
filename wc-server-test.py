
import json
import itertools
import sys
import urllib.request
import urllib.error
from datetime import datetime

URL = "http://127.0.0.1:8000/mcp/"
_ids = itertools.count(100)


def rpc(method, params=None):
    request_id = next(_ids)

    payload = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": method,
    }

    if params is not None:
        payload["params"] = params

    request = urllib.request.Request(
        URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
            if not body:
                return {}
            return json.loads(body)

    except urllib.error.HTTPError as exc:
        print("HTTP status:", exc.code)
        print(exc.read().decode("utf-8", errors="replace"))
        raise


# 1. Initialize
def call_tool(name, arguments):
    """Call an MCP tool over Streamable HTTP."""
    response = rpc("tools/call", {
        "name": name,
        "arguments": arguments,
    })

    if "error" in response:
        return {"_protocol_error": response["error"]}

    result = response.get("result", {})

    if result.get("isError"):
        return {"_is_error": True, "_raw": result.get("content", [])}

    if "structuredContent" in result:
        return result["structuredContent"]

    content = result.get("content", [])

    if content and content[0].get("text"):
        text = content[0]["text"]
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"_raw": text}

    return result


failures = []


def check(name, cond, info=""):
    print(f"{'PASS' if cond else 'FAIL'}  {name} {info}")
    if not cond:
        failures.append(name)


def is_error(r):
    return "error" in r or "_protocol_error" in r or r.get("_is_error")


# ---- replace everything from `if any(t["name"] == "list_products"...` with this ----
# ---- 1. Initialize MCP connection ----
print("1. Initialize MCP connection...")

init_response = rpc("initialize", {
    "protocolVersion": "2024-11-05",
    "capabilities": {},
    "clientInfo": {
        "name": "woocommerce-http-test",
        "version": "1.0.0",
    },
})

print(json.dumps(init_response, indent=2))

if "error" in init_response:
    raise RuntimeError(f"Initialization failed: {init_response['error']}")

# Notify the server that initialization is complete.
notification = {
    "jsonrpc": "2.0",
    "method": "notifications/initialized",
}

request = urllib.request.Request(
    URL,
    data=json.dumps(notification).encode("utf-8"),
    headers={
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    },
    method="POST",
)

with urllib.request.urlopen(request, timeout=30) as response:
    print("Initialization notification:", response.status)
# ---- 2. Discover available tools ----
print("\n2. Registered tools:")
tools_response = rpc("tools/list", {})
print("\n2. Registered tools:")
print(json.dumps(tools_response, indent=2))

if "error" in tools_response:
    raise RuntimeError(f"Tool discovery failed: {tools_response['error']}")

tools = tools_response.get("result", {}).get("tools", [])
names = {t["name"] for t in tools}
for required in ("list_products", "get_product", "list_orders", "get_order","create_product","update_order_status"):
    check(f"tool registered: {required}", required in names)

print("\n3. Testing products...")
r = call_tool("list_products", {"page": 1, "per_page": 5})
check("list_products returns products", "products" in r, f"count={r.get('count')}")
check("list_products rejects page 0", is_error(call_tool("list_products", {"page": 0})))
check("list_products rejects per_page 101", is_error(call_tool("list_products", {"per_page": 101})))

if r.get("products"):
    pid = r["products"][0]["id"]
    p = call_tool("get_product", {"product_id": pid})
    check("get_product returns matching id", p.get("id") == pid)
check("get_product rejects id 0", is_error(call_tool("get_product", {"product_id": 0})))
check("get_product missing id errors", is_error(call_tool("get_product", {"product_id": 999999})))

print("\n4. Testing orders...")
o = call_tool("list_orders", {"per_page": 5})
check("list_orders returns orders", "orders" in o, f"count={o.get('count')}")

today = datetime.now().strftime("%Y-%m-%dT00:00:00")
t = call_tool("list_orders", {"after": today})
check("list_orders today filter works", "orders" in t, f"count={t.get('count')}")
check("list_orders status filter works",
      "orders" in call_tool("list_orders", {"status": "processing"}))
check("list_orders rejects bad status",
      is_error(call_tool("list_orders", {"status": "banana"})))
check("list_orders rejects page 0", is_error(call_tool("list_orders", {"page": 0})))

if o.get("orders"):
    oid = o["orders"][0]["id"]
    d = call_tool("get_order", {"order_id": oid})
    check("get_order returns matching id", d.get("id") == oid)
    check("get_order includes billing_email", "billing_email" in d)
else:
    print("SKIP  no orders in store, place a COD order and rerun")
check("get_order rejects id 0", is_error(call_tool("get_order", {"order_id": 0})))
check("get_order missing id errors", is_error(call_tool("get_order", {"order_id": 999999})))

print(f"\n{len(failures)} failure(s)" if failures else "\nAll checks passed")

# ---- 5. Test product write operations ----
print("\n5. Testing writes...")

created_product = call_tool(
    "create_product",
    {"name": "MCP Test Product", "price": "49.00"}
)

check(
    "create_product succeeds",
    "id" in created_product
    and created_product.get("status") == "publish",
    f"id={created_product.get('id')}"
)

check(
    "create_product rejects empty name",
    is_error(call_tool(
        "create_product",
        {"name": " ", "price": "10"}
    ))
)

check(
    "create_product rejects bad price",
    is_error(call_tool(
        "create_product",
        {"name": "MCP Invalid Price Test", "price": "abc"}
    ))
)

check(
    "create_product rejects negative price",
    is_error(call_tool(
        "create_product",
        {"name": "MCP Negative Price Test", "price": "-5"}
    ))
)

if "id" in created_product:
    created_id = created_product["id"]

    g = call_tool("get_product", {"product_id": created_id})

    check(
        "created product readable via get_product",
        g.get("name") == "MCP Test Product"
    )


# ---- 6. Test order status write operations ----
print("\n6. Testing order status updates...")

check(
    "update_order_status rejects bad status",
    is_error(call_tool(
        "update_order_status",
        {"order_id": 1, "status": "banana"}
    ))
)

check(
    "update_order_status missing order errors",
    is_error(call_tool(
        "update_order_status",
        {"order_id": 999999, "status": "completed"}
    ))
)

if o.get("orders"):
    oid = o["orders"][0]["id"]
    original_status = o["orders"][0]["status"]

    try:
        updated = call_tool(
            "update_order_status",
            {"order_id": oid, "status": "on-hold"}
        )

        check(
            "update_order_status changes status",
            updated.get("status") == "on-hold"
        )

    finally:
        # Attempt to restore the original order status.
        restored = call_tool(
            "update_order_status",
            {"order_id": oid, "status": original_status}
        )

        check(
            "order status restored",
            restored.get("status") == original_status
        )
else:
    print("SKIP  no orders available for status update testing")


# ---- 7. Final result ----
print(
    f"\n{len(failures)} failure(s)"
    if failures
    else "\nAll checks passed"
)
sys.exit(1 if failures else 0)
