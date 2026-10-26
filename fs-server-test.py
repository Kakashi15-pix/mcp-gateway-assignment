import asyncio
import json
import sys

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


URL = "http://127.0.0.1:8002/mcp/"


def tool_data(result):
    """Return the JSON object returned by an MCP tool."""
    if getattr(result, "is_error", False):
        return {"_mcp_error": True}

    for item in result.content:
        text = getattr(item, "text", None)
        if text is not None:
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return {"_raw": text}

    return {}


def check(condition, name, failures):
    print(f"{'PASS' if condition else 'FAIL'}  {name}")
    if not condition:
        failures.append(name)


async def main():
    failures = []

    async with streamable_http_client(URL) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            tools = await session.list_tools()
            tool_names = {tool.name for tool in tools.tools}
            for name in ("list_files", "read_file", "search_files"):
                check(name in tool_names, f"tool registered: {name}", failures)

            listing = tool_data(await session.call_tool("list_files", {"path": ""}))
            check(
                listing.get("count", 0) > 0
                and any(entry["name"] == "hello.txt" for entry in listing["entries"]),
                "list_files finds the fixture files",
                failures,
            )

            read_result = tool_data(
                await session.call_tool("read_file", {"path": "hello.txt"})
            )
            check(
                read_result.get("content", "").splitlines()
                == ["Filesystem MCP is working"],
                "read_file returns fixture content",
                failures,
            )
            check(
                read_result.get("truncated") is False,
                "read_file reports an untruncated fixture",
                failures,
            )

            search_result = tool_data(
                await session.call_tool(
                    "search_files",
                    {"query": "working", "path": ""},
                )
            )
            check(
                any(match.get("file") == "hello.txt"
                    for match in search_result.get("matches", [])),
                "search_files finds matching file contents",
                failures,
            )

            missing = tool_data(
                await session.call_tool(
                    "read_file",
                    {"path": "does-not-exist.txt"},
                )
            )
            check(
                missing.get("error") == "file not found",
                "read_file reports a missing file",
                failures,
            )

            traversal = tool_data(
                await session.call_tool("read_file", {"path": "../hello.txt"})
            )
            check(
                "error" in traversal,
                "read_file rejects paths outside the root",
                failures,
            )

            empty_search = tool_data(
                await session.call_tool(
                    "search_files",
                    {"query": "   ", "path": ""},
                )
            )
            check(
                empty_search.get("error") == "query is required",
                "search_files rejects an empty query",
                failures,
            )

    print(
        f"\n{len(failures)} failure(s)"
        if failures
        else "\nAll filesystem server checks passed"
    )
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
