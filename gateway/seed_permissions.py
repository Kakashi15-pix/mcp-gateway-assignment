# seed_permissions.py
from sqlalchemy import select
from db import SessionLocal
from models import McpTool, ToolPermission

with SessionLocal() as db:
    for tool in db.scalars(select(McpTool)).all():
        read_only = tool.original_name.startswith(("list_", "get_"))
        for role, allowed in (("admin", True), ("member", read_only)):
            row = db.scalars(select(ToolPermission).where(
                ToolPermission.tool_id == tool.id,
                ToolPermission.role == role)).first()
            if row is None:
                db.add(ToolPermission(tool_id=tool.id, role=role, allowed=allowed))
            else:
                row.allowed = allowed
    db.commit()
    print("permissions seeded")