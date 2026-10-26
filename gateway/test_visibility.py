"""Integration test for disabled-server tool visibility.

Required environment variables:
  GATEWAY_URL, SERVER_ID, TOOL_NAME, ADMIN_SESSION, MEMBER_SESSION,
  MEMBER_API_KEY
"""

import json
import os
import urllib.error
import urllib.request


BASE_URL = os.environ["GATEWAY_URL"].rstrip("/")
SERVER_ID = os.environ["SERVER_ID"]
TOOL_NAME = os.environ["TOOL_NAME"]
ADMIN_SESSION = os.environ["ADMIN_SESSION"]
MEMBER_SESSION = os.environ["MEMBER_SESSION"]
MEMBER_API_KEY = os.environ["MEMBER_API_KEY"]


def request(method, path, token, payload=None):
    body = None if payload is None else json.dumps(payload).encode()
    request_obj = urllib.request.Request(
        BASE_URL + path,
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(request_obj, timeout=30) as response:
            return response.status, json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read() or b"{}")


def assert_visible_tools(status, payload, expected):
    assert status == 200, (status, payload)
    names = {tool.get("name") for tool in payload.get("tools", [])}
    assert (TOOL_NAME in names) is expected, names


def main():
    disabled = False
    try:
        status, _ = request(
            "POST",
            f"/admin/servers/{SERVER_ID}/disable",
            ADMIN_SESSION,
        )
        assert status == 200
        disabled = True

        status, payload = request("GET", "/tools", MEMBER_API_KEY)
        assert_visible_tools(status, payload, False)

        status, payload = request("GET", "/tools/available", MEMBER_SESSION)
        assert_visible_tools(status, payload, False)

        status, payload = request(
            "POST",
            "/mcp/",
            MEMBER_API_KEY,
            {"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
        )
        assert status == 200
        assert TOOL_NAME not in {
            tool.get("name")
            for tool in payload.get("result", {}).get("tools", [])
        }

        status, _ = request(
            "POST",
            f"/tools/{TOOL_NAME}/call",
            MEMBER_API_KEY,
            {"arguments": {}},
        )
        assert status == 502

        status, _ = request(
            "POST",
            f"/admin/servers/{SERVER_ID}/enable",
            ADMIN_SESSION,
        )
        assert status == 200
        disabled = False

        status, payload = request("GET", "/tools", MEMBER_API_KEY)
        assert_visible_tools(status, payload, True)

        status, payload = request("GET", "/tools/available", MEMBER_SESSION)
        assert_visible_tools(status, payload, True)
    finally:
        if disabled:
            request("POST", f"/admin/servers/{SERVER_ID}/enable", ADMIN_SESSION)

    print("Tool visibility checks passed")


if __name__ == "__main__":
    main()
