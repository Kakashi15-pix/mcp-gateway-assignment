
import asyncio

from discovery import discover_and_sync
from registry import ServerRegistry

async def main():
    registry = ServerRegistry()
    servers = registry.list_servers(enabled_only=True)

    if not servers:
        print("No enabled upstream servers are registered yet.")
        print("Register your WooCommerce, Kubernetes, and filesystem servers first.")
        return

    for server in servers:
        print(f"\nDiscovering tools from {server['id']} ({server['url']})")
        try:
            tools = await discover_and_sync(server["id"])
            print(f"Discovered/synchronized {len(tools)} stored tools:")
            for tool in tools:
                print(f"  {tool['public_name']} — {tool['description']}")
        except Exception as exc:
            print(f"FAILED: {exc}")

if __name__ == "__main__":
    asyncio.run(main())
