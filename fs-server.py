
import os
from pathlib import Path

import uvicorn
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.requests import Request

from mcp.server.mcpserver import MCPServer


# Local development defaults to a dedicated directory.
# In Kubernetes, set FS_ROOT=/data.
ROOT = Path(
    os.environ.get(
        "FS_ROOT",
        str(Path(__file__).parent / "mcp-files"),
    )
).resolve()

TOKEN = os.environ.get("MCP_AUTH_TOKEN", "")
MAX_READ_BYTES = 100_000
MAX_RESULTS = 50
MAX_ENTRIES = 200

ROOT.mkdir(parents=True, exist_ok=True)

mcp = MCPServer("filesystem")


def _safe_path(rel: str) -> Path:
    """Resolve a relative path and prevent traversal outside ROOT."""
    p = (ROOT / rel.lstrip("/\\")).resolve()

    if p != ROOT and not p.is_relative_to(ROOT):
        raise ValueError("path is outside the allowed directory")

    return p


@mcp.tool()
def list_files(path: str = "") -> dict:
    """List files and folders under the shared root."""
    try:
        directory = _safe_path(path)

        if not directory.is_dir():
            return {"error": "not a directory"}

        entries = []

        for child in sorted(directory.iterdir())[:MAX_ENTRIES]:
            # Do not expose metadata from symlinks pointing outside ROOT.
            resolved = child.resolve()
            if resolved != ROOT and not resolved.is_relative_to(ROOT):
                continue

            entries.append({
                "name": child.name,
                "type": "dir" if child.is_dir() else "file",
                "size": child.stat().st_size if child.is_file() else None,
            })

        return {
            "path": path or "/",
            "count": len(entries),
            "entries": entries,
        }

    except (ValueError, OSError) as exc:
        return {"error": str(exc)}


@mcp.tool()
def read_file(path: str) -> dict:
    """Read a UTF-8 text file, truncating content at 100 KB."""
    try:
        file_path = _safe_path(path)

        if not file_path.is_file():
            return {"error": "file not found"}

        with file_path.open("rb") as file:
            raw = file.read(MAX_READ_BYTES + 1)

        truncated = len(raw) > MAX_READ_BYTES

        try:
            content = raw[:MAX_READ_BYTES].decode("utf-8")
        except UnicodeDecodeError:
            return {"error": "file is not valid UTF-8 text"}

        return {
            "path": path,
            "truncated": truncated,
            "content": content,
        }

    except (ValueError, OSError) as exc:
        return {"error": str(exc)}


@mcp.tool()
def search_files(query: str, path: str = "") -> dict:
    """Search file names and UTF-8 text contents, case-insensitively."""
    if not query.strip():
        return {"error": "query is required"}

    try:
        base = _safe_path(path)

        if not base.is_dir():
            return {"error": "not a directory"}

        query_lower = query.lower()
        matches = []

        for file_path in sorted(base.rglob("*")):
            if len(matches) >= MAX_RESULTS:
                break

            try:
                resolved = file_path.resolve()

                if not resolved.is_relative_to(ROOT):
                    continue

                if not file_path.is_file():
                    continue

                relative = str(file_path.relative_to(ROOT))

                if query_lower in file_path.name.lower():
                    matches.append({
                        "file": relative,
                        "match": "file name",
                    })
                    continue

                # Bound the scan to avoid reading arbitrarily large files.
                with file_path.open("rb") as file:
                    raw = file.read(MAX_READ_BYTES)

                try:
                    content = raw.decode("utf-8")
                except UnicodeDecodeError:
                    continue

                for line_number, line in enumerate(content.splitlines(), 1):
                    if query_lower in line.lower():
                        matches.append({
                            "file": relative,
                            "line": line_number,
                            "text": line.strip()[:200],
                        })
                        break

            except OSError:
                continue

        return {
            "count": len(matches),
            "matches": matches,
        }

    except (ValueError, OSError) as exc:
        return {"error": str(exc)}


class BearerAuth(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if TOKEN and request.url.path != "/health":
            authorization = request.headers.get("authorization", "")

            if authorization != f"Bearer {TOKEN}":
                return JSONResponse(
                    {"error": "unauthorized"},
                    status_code=401,
                )

        return await call_next(request)


# Use the MCPServer API style from your existing server.
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8002"))
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

app = mcp.streamable_http_app(
    host=HOST,
    transport_security=transport_security,
)
app.add_middleware(BearerAuth)


async def health(request: Request):
    return PlainTextResponse("ok")


app.add_route("/health", health, methods=["GET"])


if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT)
