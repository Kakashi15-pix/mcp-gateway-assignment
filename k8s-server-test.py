
import asyncio
import json
import sys

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def main():
    url = "http://127.0.0.1:8001/mcp/"

    async with streamable_http_client(url) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            result = await session.list_tools()
            tool_names = {tool.name for tool in result.tools}
            failures = []

            print("Connected to Kubernetes Health MCP Server")
            print("\nAvailable tools:")

            for tool in result.tools:
                print(f"- {tool.name}: {tool.description}")

            required_tools = (
                "get_cluster_health",
                "get_pod_details",
                "list_unhealthy_pods",
            )
            for name in required_tools:
                passed = name in tool_names
                print(f"{'PASS' if passed else 'FAIL'}  tool registered: {name}")
                if not passed:
                    failures.append(name)

            print("\nChecking cluster health...")
            health = await session.call_tool(
                "get_cluster_health",
                {},
            )

            health_data = {}
            for item in health.content:
                if hasattr(item, "text"):
                    print(item.text)
                    try:
                        health_data = json.loads(item.text)
                    except json.JSONDecodeError:
                        pass

            valid_health = (
                not health.is_error
                and isinstance(health_data, dict)
                and health_data.get("api_accessible") is True
            )
            print(
                f"{'PASS' if valid_health else 'FAIL'}  "
                "get_cluster_health returns a structured response"
            )
            if not valid_health:
                failures.append("get_cluster_health response")

            print(
                f"\n{len(failures)} failure(s)"
                if failures
                else "\nAll Kubernetes server checks passed"
            )
            return 1 if failures else 0

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
