
import asyncio
import logging


from router import route_tool_call


logger = logging.getLogger(__name__)


TESTS = [
    {
        "server": "woocommerce",
        "tool": "woocommerce__list_products",
        "arguments": {},
    },
    {
        "server": "filesystem",
        "tool": "filesystem__list_files",
        "arguments": {},
    },
]


async def test_upstream(test_case):
    server = test_case["server"]
    tool = test_case["tool"]

    print(f"\n{'=' * 55}")
    print(f"Testing server: {server}")
    print(f"Tool: {tool}")
    print("=" * 55)

    try:
        result = await route_tool_call(
            public_name=tool,
            arguments=test_case["arguments"],
        )

        if result.get("is_error"):
            print("TOOL ERROR: The upstream returned an MCP tool error.")
            print(result)
        else:
            print("SUCCESS: Router received a response.")
            print(result)

    except Exception as exc:
        print(f"FAILED: {server} could not complete the tool call.")
        print(f"Reason: {type(exc).__name__}: {exc}")


async def main():
    for test_case in TESTS:
        await test_upstream(test_case)

    print("\nFinished testing both upstream servers.")


if __name__ == "__main__":
    asyncio.run(main())
