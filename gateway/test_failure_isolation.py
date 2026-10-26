
import asyncio

from router import route_tool_call
from registry import ServerRegistry

registry = ServerRegistry()


async def call_and_report(server, tool):
    try:
        result = await route_tool_call(tool, {})
        print(f"{server}: response received")
        print(f"  MCP tool error: {result.get('is_error', False)}")
        return True
    except Exception as exc:
        print(f"{server}: call failed")
        print(f"  {type(exc).__name__}: {exc}")
        return False


async def main():
    print("\n1. Baseline: both upstreams should be available")
    baseline_woocommerce_ok = await call_and_report(
        "WooCommerce",
        "woocommerce__list_products",
    )
    baseline_filesystem_ok = await call_and_report(
        "Filesystem",
        "filesystem__list_files",
    )
    assert baseline_woocommerce_ok, "WooCommerce baseline call should succeed"
    assert baseline_filesystem_ok, "Filesystem baseline call should succeed"

    print("\n2. Failure isolation")
    print(
        "Stop the filesystem MCP server in its own terminal, "
        "then press Enter here."
    )
    await asyncio.to_thread(input)

    filesystem_ok = await call_and_report(
        "Filesystem",
        "filesystem__list_files",
    )

    woocommerce_ok = await call_and_report(
        "WooCommerce",
        "woocommerce__list_products",
    )

    print("\n3. Recorded server status")
    filesystem_status = registry.get_server("filesystem")
    print(filesystem_status)

    print("\n4. Summary")
    print(f"Filesystem call failed as expected: {not filesystem_ok}")
    print(f"WooCommerce still responds: {woocommerce_ok}")

    assert not filesystem_ok, "Filesystem should be unavailable after shutdown"
    assert woocommerce_ok, "WooCommerce should remain available"
    assert filesystem_status["status"] == "unhealthy", (
        "Filesystem failure should be recorded as unhealthy"
    )


if __name__ == "__main__":
    asyncio.run(main())
