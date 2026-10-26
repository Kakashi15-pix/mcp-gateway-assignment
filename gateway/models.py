
# models.py
# SQLAlchemy models for the MCP Gateway database.

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import Uuid


class Base(DeclarativeBase):
    """Base class used by all gateway database models."""
    pass


# ============================================================
# 1. Users
# ============================================================

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(
        String(320), unique=True, nullable=False
    )
    display_name: Mapped[str | None] = mapped_column(String(150))
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, default="member", server_default="member"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    password_hash: Mapped[str | None] = mapped_column(Text)
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "role IN ('admin', 'member')",
            name="ck_users_role",
        ),
        Index("idx_users_role", "role"),
        Index("idx_users_active", "is_active"),
    )


class SessionToken(Base):
    __tablename__ = "session_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("idx_session_tokens_user", "user_id"),
        Index("idx_session_tokens_active", "token_hash", "expires_at"),
    )


class Invitation(Base):
    __tablename__ = "invitations"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, default="member", server_default="member"
    )
    token_hash: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False
    )
    invited_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "role IN ('admin', 'member')",
            name="ck_invitations_role",
        ),
        Index("idx_invitations_email", "email"),
    )


# ============================================================
# 2. Gateway API keys
# ============================================================

class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    key_hash: Mapped[str] = mapped_column(
        Text, unique=True, nullable=False
    )
    key_prefix: Mapped[str] = mapped_column(
        String(24), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    __table_args__ = (
        CheckConstraint(
            "expires_at IS NULL OR expires_at > created_at",
            name="ck_api_keys_expiry",
        ),
        Index("idx_api_keys_user", "user_id"),
        Index(
            "idx_api_keys_active",
            "user_id",
            "expires_at",
            postgresql_where=text("revoked_at IS NULL"),
        ),
    )


# ============================================================
# 3. Registered upstream MCP servers
# ============================================================

class McpServer(Base):
    __tablename__ = "mcp_servers"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(
        Text, nullable=False, default="", server_default=""
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="unknown",
        server_default="unknown"
    )
    request_timeout_seconds: Mapped[int] = mapped_column(
        Integer, nullable=False, default=15, server_default="15"
    )
    max_concurrent_requests: Mapped[int] = mapped_column(
        Integer, nullable=False, default=20, server_default="20"
    )
    last_checked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    last_error: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('unknown', 'healthy', 'unhealthy', 'disabled')",
            name="ck_mcp_servers_status",
        ),
        CheckConstraint(
            "request_timeout_seconds BETWEEN 1 AND 300",
            name="ck_mcp_servers_timeout",
        ),
        CheckConstraint(
            "max_concurrent_requests > 0",
            name="ck_mcp_servers_concurrency",
        ),
        Index("idx_mcp_servers_enabled", "enabled"),
        Index("idx_mcp_servers_status", "status"),
    )


class ServerHealthCheck(Base):
    __tablename__ = "server_health_checks"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    server_id: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("mcp_servers.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(500))
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("idx_server_health_checks_server_time", "server_id", "checked_at"),
    )


# ============================================================
# 4. Upstream server credentials
# ============================================================

class ServerCredential(Base):
    __tablename__ = "server_credentials"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    server_id: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("mcp_servers.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    auth_type: Mapped[str] = mapped_column(String(30), nullable=False)
    header_name: Mapped[str | None] = mapped_column(String(200))

    # Either a secret reference OR an encrypted value.
    # Never store a plaintext upstream credential here.
    secret_ref: Mapped[str | None] = mapped_column(Text)
    encrypted_value: Mapped[bytes | None] = mapped_column(LargeBinary)
    encryption_key_ref: Mapped[str | None] = mapped_column(Text)

    enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "auth_type IN ('bearer', 'custom_header')",
            name="ck_server_credentials_auth_type",
        ),
        CheckConstraint(
            "(secret_ref IS NOT NULL AND encrypted_value IS NULL) OR "
            "(secret_ref IS NULL AND encrypted_value IS NOT NULL)",
            name="ck_server_credentials_secret_storage",
        ),
        CheckConstraint(
            "auth_type <> 'custom_header' OR header_name IS NOT NULL",
            name="ck_server_credentials_header",
        ),
        Index("idx_server_credentials_server", "server_id"),
    )


# ============================================================
# 5. Discovered MCP tools
# ============================================================

class McpTool(Base):
    __tablename__ = "mcp_tools"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    server_id: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("mcp_servers.id", ondelete="CASCADE"),
        nullable=False,
    )
    original_name: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    public_name: Mapped[str] = mapped_column(
        String(356), unique=True, nullable=False
    )
    description: Mapped[str] = mapped_column(
        Text, nullable=False, default="", server_default=""
    )
    input_schema: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    deprecated: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    deprecated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    deprecation_message: Mapped[str | None] = mapped_column(Text)
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "server_id", "original_name",
            name="uq_mcp_tools_server_original_name",
        ),
        Index("idx_mcp_tools_server", "server_id"),
        Index(
            "idx_mcp_tools_available",
            "server_id", "enabled", "deprecated",
        ),
    )


# ============================================================
# 6. Per-user and per-role tool permissions
# ============================================================

class ToolPermission(Base):
    __tablename__ = "tool_permissions"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    tool_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("mcp_tools.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
    )
    role: Mapped[str | None] = mapped_column(String(20))
    allowed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "role IS NULL OR role IN ('admin', 'member')",
            name="ck_tool_permissions_role",
        ),
        CheckConstraint(
            "(user_id IS NOT NULL AND role IS NULL) OR "
            "(user_id IS NULL AND role IS NOT NULL)",
            name="ck_tool_permissions_subject",
        ),
        Index(
            "uq_tool_permission_user",
            "tool_id", "user_id",
            unique=True,
            postgresql_where=text("user_id IS NOT NULL"),
        ),
        Index(
            "uq_tool_permission_role",
            "tool_id", "role",
            unique=True,
            postgresql_where=text("role IS NOT NULL"),
        ),
        Index("idx_tool_permissions_user", "user_id"),
    )


# ============================================================
# 7. Rate-limit policies
# ============================================================

class RateLimitPolicy(Base):
    __tablename__ = "rate_limit_policies"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    scope_type: Mapped[str] = mapped_column(String(20), nullable=False)

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    api_key_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("api_keys.id", ondelete="CASCADE")
    )
    server_id: Mapped[str | None] = mapped_column(
        String(100), ForeignKey("mcp_servers.id", ondelete="CASCADE")
    )
    tool_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("mcp_tools.id", ondelete="CASCADE")
    )

    max_requests: Mapped[int] = mapped_column(Integer, nullable=False)
    window_seconds: Mapped[int] = mapped_column(Integer, nullable=False)

    enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "scope_type IN ('global', 'user', 'api_key', 'server', 'tool')",
            name="ck_rate_limit_policies_scope",
        ),
        CheckConstraint(
            "max_requests > 0",
            name="ck_rate_limit_policies_max_requests",
        ),
        CheckConstraint(
            "window_seconds > 0",
            name="ck_rate_limit_policies_window",
        ),
        CheckConstraint(
            "(scope_type = 'global' AND user_id IS NULL "
            "AND api_key_id IS NULL AND server_id IS NULL AND tool_id IS NULL) "
            "OR (scope_type = 'user' AND user_id IS NOT NULL "
            "AND api_key_id IS NULL AND server_id IS NULL AND tool_id IS NULL) "
            "OR (scope_type = 'api_key' AND api_key_id IS NOT NULL "
            "AND user_id IS NULL AND server_id IS NULL AND tool_id IS NULL) "
            "OR (scope_type = 'server' AND server_id IS NOT NULL "
            "AND user_id IS NULL AND api_key_id IS NULL AND tool_id IS NULL) "
            "OR (scope_type = 'tool' AND tool_id IS NOT NULL "
            "AND user_id IS NULL AND api_key_id IS NULL AND server_id IS NULL)",
            name="ck_rate_limit_policies_scope_target",
        ),
        Index("idx_rate_limit_policies_enabled", "scope_type", "enabled"),
    )


# ============================================================
# 8. Audit logs
# ============================================================

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    api_key_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("api_keys.id", ondelete="SET NULL")
    )

    # Keep these as historical identifiers, not foreign keys.
    # Audit records should survive server/tool removal.
    server_id: Mapped[str | None] = mapped_column(String(100))
    tool_name: Mapped[str | None] = mapped_column(String(356))

    action: Mapped[str] = mapped_column(String(100), nullable=False)
    outcome: Mapped[str] = mapped_column(String(30), nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    details: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "outcome IN "
            "('success', 'failure', 'denied', 'timeout', 'rate_limited')",
            name="ck_audit_logs_outcome",
        ),
        CheckConstraint(
            "duration_ms IS NULL OR duration_ms >= 0",
            name="ck_audit_logs_duration",
        ),
        Index("idx_audit_logs_created", "created_at"),
        Index("idx_audit_logs_user_created", "user_id", "created_at"),
        Index("idx_audit_logs_server_created", "server_id", "created_at"),
        Index("idx_audit_logs_action", "action", "created_at"),
    )
