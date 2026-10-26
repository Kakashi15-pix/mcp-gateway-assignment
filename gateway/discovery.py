
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from mcp.client import ClientSession
from mcp.client.streamable_http import streamable_http_client
from sqlalchemy import select
from sqlalchemy.orm import Session

from db import SessionLocal
from models import McpServer, McpTool, ToolPermission


logger = logging.getLogger(__name__)


class DiscoveryError(Exception):
    """Raised when an upstream MCP server cannot be discovered."""


def normalize_mcp_url(url: str) -> str:
    normalized = url.strip()
    return normalized + "/" if normalized.endswith("/mcp") else normalized


async def discover_upstream_tools(
    url: str,
    timeout_seconds: int = 30,
) -> list[dict[str, Any]]:
    """Connect to an upstream MCP server and return its advertised tools."""

    async def _discover() -> list[dict[str, Any]]:
        async with streamable_http_client(url) as (
            read_stream,
            write_stream,
        ):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                response = await session.list_tools()

                discovered = []
                for tool in response.tools:
                    discovered.append(
                        {
                            "original_name": tool.name,
                            "description": tool.description or "",
                            "input_schema": tool.input_schema or {},
                        }
                    )

                return discovered

    try:
        return await asyncio.wait_for(
            _discover(),
            timeout=timeout_seconds,
        )
    except Exception as exc:
        raise DiscoveryError(
            f"Failed to discover tools from {url}: {exc}"
        ) from exc


def ensure_admin_permission(db: Session, tool: McpTool) -> None:
    """Create an admin allow permission only if no admin role permission exists."""

    existing_permission = db.scalar(
        select(ToolPermission).where(
            ToolPermission.tool_id == tool.id,
            ToolPermission.role == "admin",
            ToolPermission.user_id.is_(None),
        )
    )

    if existing_permission is None:
        db.add(
            ToolPermission(
                tool_id=tool.id,
                role="admin",
                user_id=None,
                allowed=True,
            )
        )


def synchronize_tools(
    server_id: str,
    discovered_tools: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Upsert discovered tools and mark removed tools as disabled.

    Newly created tools receive an admin permission by default.
    Existing permission decisions are preserved.
    """

    with SessionLocal() as db:
        server = db.get(McpServer, server_id)

        if server is None:
            raise ValueError(f"Unknown MCP server: {server_id}")

        discovered_names = {
            item["original_name"] for item in discovered_tools
        }

        existing_tools = db.scalars(
            select(McpTool).where(McpTool.server_id == server_id)
        ).all()

        existing_by_name = {
            tool.original_name: tool for tool in existing_tools
        }

        for item in discovered_tools:
            original_name = item["original_name"]
            public_name = f"{server_id}__{original_name}"

            tool = existing_by_name.get(original_name)

            if tool is None:
                tool = McpTool(
                    server_id=server_id,
                    original_name=original_name,
                    public_name=public_name,
                    description=item["description"],
                    input_schema=item["input_schema"],
                    enabled=True,
                    deprecated=False,
                )
                db.add(tool)

                # Generate the database ID before creating its permission.
                db.flush()

                # Grant admin access without changing existing decisions.
                

            else:
                tool.public_name = public_name
                tool.description = item["description"]
                tool.input_schema = item["input_schema"]
                
                # Preserve admin-disabled tools and deprecation flags.
                # Rediscovery does not override existing admin decisions.
            ensure_admin_permission(db, tool)    

        for tool in existing_tools:
            if tool.original_name not in discovered_names:
                tool.enabled = False
                tool.deprecated = True
                tool.deprecated_at = datetime.now(timezone.utc)
                tool.deprecation_message = (
                    "Tool vanished during discovery"
                )

        db.commit()

        saved_tools = db.scalars(
            select(McpTool)
            .where(McpTool.server_id == server_id)
            .order_by(McpTool.public_name)
        ).all()

        return [
            {
                "id": tool.id,
                "server_id": tool.server_id,
                "original_name": tool.original_name,
                "public_name": tool.public_name,
                "description": tool.description,
                "enabled": tool.enabled,
                "deprecated": tool.deprecated,
            }
            for tool in saved_tools
        ]


async def discover_and_sync(
    server_id: str,
) -> list[dict[str, Any]]:
    """Discover tools for one registered, enabled upstream and persist them."""

    with SessionLocal() as db:
        server = db.get(McpServer, server_id)

        if server is None:
            raise ValueError(f"Unknown MCP server: {server_id}")

        if not server.enabled:
            raise ValueError(
                f"MCP server '{server_id}' is disabled"
            )

        url = normalize_mcp_url(server.url)
        timeout_seconds = server.request_timeout_seconds

    try:
        tools = await discover_upstream_tools(
            url=url,
            timeout_seconds=timeout_seconds,
        )

        saved = synchronize_tools(server_id, tools)

        with SessionLocal() as db:
            server = db.get(McpServer, server_id)

            if server is not None:
                server.status = "healthy"
                server.last_error = None
                server.last_checked_at = datetime.now(timezone.utc)
                db.commit()

        return saved

    except Exception as exc:
        logger.exception(
            "Tool discovery failed for %s",
            server_id,
        )

        with SessionLocal() as db:
            server = db.get(McpServer, server_id)

            if server is not None:
                server.status = "unhealthy"
                server.last_error = str(exc)[:2000]
                server.last_checked_at = datetime.now(timezone.utc)
                db.commit()

        raise DiscoveryError(
            f"Discovery failed for '{server_id}': {exc}"
        ) from exc
