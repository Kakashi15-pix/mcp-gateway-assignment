
from __future__ import annotations
import logging
import os
from datetime import datetime, timezone
from typing import Any

import asyncio

import httpx2
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from sqlalchemy import select

from db import SessionLocal
from models import McpServer, McpTool, ServerCredential

logger = logging.getLogger(__name__)


def record_upstream_failure(server_id: str, error: str) -> None:
    """Record an upstream failure without crashing the router."""
    try:
        with SessionLocal() as db:
            server = db.get(McpServer, server_id)

            if server is None:
                return

            if not server.enabled:
                server.status = "disabled"
            else:
                server.status = "unhealthy"

            server.last_error = error[:2000]
            server.last_checked_at = datetime.now(timezone.utc)
            server.updated_at = datetime.now(timezone.utc)

            db.commit()

    except Exception:
        logger.exception(
            "Could not record failure status for upstream %s",
            server_id,
        )


def record_upstream_success(server_id: str) -> None:
    """Record a successful upstream call without disrupting the response."""
    try:
        with SessionLocal() as db:
            server = db.get(McpServer, server_id)

            if server is None:
                return

            server.status = "disabled" if not server.enabled else "healthy"
            server.last_error = None
            server.last_checked_at = datetime.now(timezone.utc)
            server.updated_at = datetime.now(timezone.utc)
            db.commit()

    except Exception:
        logger.exception(
            "Could not record success status for upstream %s",
            server_id,
        )


class RoutingError(Exception):
    """Raised when a tool call cannot be routed."""


class ToolNotFoundError(RoutingError):
    pass


class ToolDisabledError(RoutingError):
    pass


class UpstreamCallError(RoutingError):
    pass


def resolve_secret(ref: str) -> str:
    """Resolve an environment-backed upstream secret reference."""
    if ref.startswith("env://"):
        value = os.environ.get(ref[6:])
        if value:
            return value

    raise UpstreamCallError("Upstream credential could not be resolved")


def decrypt_value(blob: bytes | None, key_ref: str | None) -> str:
    """Reject encrypted credentials until a KMS-backed decryptor is available."""
    raise UpstreamCallError("Encrypted credentials are not supported yet")


def build_auth_headers(db, server_id: str) -> dict[str, str]:
    """Resolve the enabled credential for an upstream server."""
    credential = db.scalars(
        select(ServerCredential).where(
            ServerCredential.server_id == server_id,
            ServerCredential.enabled.is_(True),
        )
    ).first()

    if credential is None:
        return {}

    secret = (
        resolve_secret(credential.secret_ref)
        if credential.secret_ref
        else decrypt_value(
            credential.encrypted_value,
            credential.encryption_key_ref,
        )
    )

    if credential.auth_type == "bearer":
        return {"Authorization": f"Bearer {secret}"}

    if credential.auth_type == "custom_header" and credential.header_name:
        return {credential.header_name: secret}

    raise UpstreamCallError("Upstream credential configuration is invalid")


def build_auth_headers(db, server_id: str) -> dict[str, str]:
    """Resolve the enabled credential for an upstream server."""
    credential = db.scalars(
        select(ServerCredential).where(
            ServerCredential.server_id == server_id,
            ServerCredential.enabled.is_(True),
        )
    ).first()

    if credential is None:
        return {}

    secret = (
        resolve_secret(credential.secret_ref)
        if credential.secret_ref
        else decrypt_value(
            credential.encrypted_value,
            credential.encryption_key_ref,
        )
    )

    if credential.auth_type == "bearer":
        return {"Authorization": "Bearer " + secret}

    if credential.auth_type == "custom_header" and credential.header_name:
        return {credential.header_name: secret}

    raise UpstreamCallError("Upstream credential configuration is invalid")


def get_routing_details(public_name: str) -> dict[str, Any]:
    """Load a tool and its upstream configuration from PostgreSQL."""

    with SessionLocal() as db:
        tool = db.scalars(
            select(McpTool).where(McpTool.public_name == public_name)
        ).first()

        if tool is None:
            raise ToolNotFoundError(f"Tool '{public_name}' was not found")

        if not tool.enabled or tool.deprecated:
            raise ToolDisabledError(
                f"Tool '{public_name}' is disabled or deprecated"
            )

        server = db.get(McpServer, tool.server_id)

        if server is None or not server.enabled:
            raise ToolDisabledError(
                f"Upstream for '{public_name}' is missing or disabled"
            )

        return {
            "server_id": server.id,
            "url": server.url,
            "timeout": server.request_timeout_seconds,
            "original_name": tool.original_name,
            "headers": build_auth_headers(db, server.id),
        }


async def call_upstream_tool(
    url: str,
    original_name: str,
    arguments: dict[str, Any],
    timeout_seconds: int,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Call a tool on one upstream using MCP Streamable HTTP."""

    async def _call() -> dict[str, Any]:
        async with httpx2.AsyncClient(
            headers=headers or {},
            trust_env=False,
        ) as http_client:
            async with streamable_http_client(
                url,
                http_client=http_client,
            ) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    result = await session.call_tool(
                        original_name,
                        arguments=arguments,
                    )

                    return {
                        "is_error": result.is_error,
                        "content": [
                            item.model_dump(mode="json", by_alias=True)
                            if hasattr(item, "model_dump")
                            else str(item)
                            for item in result.content
                        ],
                        "structured_content": getattr(
                            result, "structured_content", None
                        ),
                    }

    try:
        return await asyncio.wait_for(
            _call(),
            timeout=timeout_seconds,
        )
    except Exception as exc:
        error_message = str(exc)
        for header_value in (headers or {}).values():
            if header_value:
                error_message = error_message.replace(
                    header_value,
                    "[REDACTED]",
                )
        raise UpstreamCallError(
            f"Upstream call to '{original_name}' failed: {error_message}"
        ) from exc



    
async def route_tool_call(
    public_name: str,
    arguments: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve a public tool name and isolate upstream failures."""

    details: dict[str, Any] | None = None

    try:
        details = get_routing_details(public_name)
        result = await call_upstream_tool(
            url=details["url"],
            original_name=details["original_name"],
            arguments=arguments or {},
            timeout_seconds=details["timeout"],
            headers=details["headers"],
        )

        # An MCP tool can return is_error=True without raising an exception.
        if result.get("is_error"):
            record_upstream_failure(
                details["server_id"],
                f"Tool '{details['original_name']}' returned an MCP error",
            )
        else:
            record_upstream_success(details["server_id"])

        return result

    except UpstreamCallError as exc:
        if details is not None:
            record_upstream_failure(details["server_id"], str(exc))
        raise
