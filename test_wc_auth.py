import os
import sys
from woocommerce import API

wcapi = API(
    url="http://localhost:8081",
    consumer_key=os.environ["WC_CONSUMER_KEY"],
    consumer_secret=os.environ["WC_CONSUMER_SECRET"],
    wp_api=True,
    version="wc/v3",
    timeout=15,
)

response = wcapi.get("products", params={"per_page": 5})

if not response.ok:
    print("FAIL  WooCommerce products request")
    print("Status:", response.status_code)
    print("Response:", response.text[:2000])
    sys.exit(1)

try:
    products = response.json()
except ValueError:
    print("FAIL  WooCommerce response is not valid JSON")
    print("Response:", response.text[:2000])
    sys.exit(1)

if not isinstance(products, list):
    print("FAIL  WooCommerce products response is not a list")
    sys.exit(1)

print("PASS  WooCommerce products request")
print(f"Returned {len(products)} product(s)")