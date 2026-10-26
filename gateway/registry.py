
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from db import SessionLocal
from models import McpServer


class ServerNotFoundError(Exception):
    """Raised when a requested MCP server does not exist."""


class ServerAlreadyExistsError(Exception):
    """Raised when a server ID is already registered."""


class ServerRegistry:
    """PostgreSQL-backed registry for upstream MCP servers."""

    def __init__(self, session_factory=SessionLocal):
        self.session_factory = session_factory

    @staticmethod
    def _serialize(server: McpServer) -> dict[str, Any]:
        return {
            "id": server.id,
            "name": server.name,
            "url": server.url,
            "description": server.description,
            "enabled": server.enabled,
            "status": server.status,
            "request_timeout_seconds": server.request_timeout_seconds,
            "max_concurrent_requests": server.max_concurrent_requests,
            "last_checked_at": (
                server.last_checked_at.isoformat()
                if server.last_checked_at
                else None
            ),
            "last_error": server.last_error,
            "created_at": (
                server.created_at.isoformat()
                if server.created_at
                else None
            ),
            "updated_at": (
                server.updated_at.isoformat()
                if server.updated_at
                else None
            ),
        }

    def list_servers(self, enabled_only: bool = False) -> list[dict[str, Any]]:
        with self.session_factory() as db:
            statement = select(McpServer).order_by(McpServer.name)

            if enabled_only:
                statement = statement.where(McpServer.enabled.is_(True))

            servers = db.scalars(statement).all()
            return [self._serialize(server) for server in servers]

    def get_server(self, server_id: str) -> dict[str, Any]:
        with self.session_factory() as db:
            server = db.get(McpServer, server_id)

            if server is None:
                raise ServerNotFoundError(
                    f"MCP server '{server_id}' was not found"
                )

            return self._serialize(server)

    def register_server(
        self,
        *,
        server_id: str,
        name: str,
        url: str,
        description: str | None = None,
        created_by: Any = None,
        request_timeout_seconds: int = 30,
        max_concurrent_requests: int = 10,
    ) -> dict[str, Any]:
        server_id = server_id.strip()
        name = name.strip()
        url = url.strip()

        if not server_id or not name or not url:
            raise ValueError("server_id, name, and url are required")

        if not url.startswith(("http://", "https://")):
            raise ValueError("Server URL must start with http:// or https://")

        if not 1 <= request_timeout_seconds <= 300:
            raise ValueError("Timeout must be between 1 and 300 seconds")

        if not 1 <= max_concurrent_requests <= 1000:
            raise ValueError("Concurrency must be between 1 and 1000")

        with self.session_factory() as db:
            existing = db.get(McpServer, server_id)

            if existing is not None:
                raise ServerAlreadyExistsError(
                    f"MCP server '{server_id}' is already registered"
                )

            server = McpServer(
                id=server_id,
                name=name,
                url=url,
                description=description,
                enabled=True,
                status="unknown",
                request_timeout_seconds=request_timeout_seconds,
                max_concurrent_requests=max_concurrent_requests,
                created_by=created_by,
                updated_by=created_by,
            )

            db.add(server)
            db.commit()
            db.refresh(server)

            return self._serialize(server)

    def set_enabled(
        self,
        server_id: str,
        enabled: bool,
        updated_by: Any = None,
    ) -> dict[str, Any]:
        with self.session_factory() as db:
            server = db.get(McpServer, server_id)

            if server is None:
                raise ServerNotFoundError(
                    f"MCP server '{server_id}' was not found"
                )

            server.enabled = enabled
            server.status = "unknown" if enabled else "disabled"
            server.updated_by = updated_by
            server.updated_at = datetime.now(timezone.utc)

            db.commit()
            db.refresh(server)

            return self._serialize(server)

    def delete_server(self, server_id: str) -> None:
        with self.session_factory() as db:
            server = db.get(McpServer, server_id)

            if server is None:
                raise ServerNotFoundError(
                    f"MCP server '{server_id}' was not found"
                )

            db.delete(server)
            db.commit()

    def update_health(
        self,
        server_id: str,
        *,
        status: str,
        last_error: str | None = None,
    ) -> dict[str, Any]:
        if status not in {"unknown", "healthy", "unhealthy", "disabled"}:
            raise ValueError("Invalid server status")

        with self.session_factory() as db:
            server = db.get(McpServer, server_id)

            if server is None:
                raise ServerNotFoundError(
                    f"MCP server '{server_id}' was not found"
                )

            if not server.enabled:
                server.status = "disabled"
            else:
                server.status = status

            server.last_checked_at = datetime.now(timezone.utc)
            server.last_error = last_error
            server.updated_at = datetime.now(timezone.utc)

            db.commit()
            db.refresh(server)

            return self._serialize(server)
