# permissions.py
import uuid
from sqlalchemy import select, or_
from db import SessionLocal
from models import McpServer, McpTool, ToolPermission, AuditLog


def visible_tools(identity: dict) -> list[McpTool]:
    """Return only enabled, non-deprecated, permitted tools."""
    uid = uuid.UUID(str(identity["user_id"]))
    role = identity["role"]
    with SessionLocal() as db:
        tools = db.scalars(
            select(McpTool)
            .join(McpServer, McpServer.id == McpTool.server_id)
            .where(
                McpServer.enabled.is_(True),
                McpTool.enabled.is_(True),
                McpTool.deprecated.is_(False),
            )
            .order_by(McpTool.public_name)
        ).all()
        permissions = db.scalars(
            select(ToolPermission).where(
                ToolPermission.tool_id.in_(tool.id for tool in tools),
                or_(ToolPermission.user_id == uid, ToolPermission.role == role),
            )
        ).all()
        by_tool: dict[int, list[ToolPermission]] = {}
        for permission in permissions:
            by_tool.setdefault(permission.tool_id, []).append(permission)

        visible = []
        for tool in tools:
            rows = by_tool.get(tool.id, [])
            user_rule = next((row for row in rows if row.user_id is not None), None)
            if user_rule is not None:
                allowed = user_rule.allowed
            else:
                role_rule = next((row for row in rows if row.role is not None), None)
                allowed = role_rule.allowed if role_rule is not None else False
            if allowed:
                visible.append(tool)
        return visible


def is_tool_allowed(user_id: str, role: str, public_name: str) -> bool:
    """User rule beats role rule. No matching rule means deny."""
    return any(
        tool.public_name == public_name
        for tool in visible_tools({"user_id": user_id, "role": role})
    )


def write_audit(identity, public_name, outcome, duration_ms=None, details=None):
    server_id = public_name.split("__", 1)[0] if "__" in public_name else None
    with SessionLocal() as db:
        db.add(AuditLog(
            user_id=uuid.UUID(identity["user_id"]),
            api_key_id=(
                uuid.UUID(str(identity["api_key_id"]))
                if identity.get("api_key_id") else None
            ),
            server_id=server_id,
            tool_name=public_name,
            action="tool_call",
            outcome=outcome,
            duration_ms=duration_ms,
            details=details or {},   # metadata only, never arguments or results
        ))
        db.commit()
