"""add dashboard sessions and invitations

Revision ID: 4c6b9f2d1a7e
Revises: 1e99fb528b53
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "4c6b9f2d1a7e"
down_revision: Union[str, Sequence[str], None] = "1e99fb528b53"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "session_tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(
        "idx_session_tokens_user",
        "session_tokens",
        ["user_id"],
    )
    op.create_index(
        "idx_session_tokens_active",
        "session_tokens",
        ["token_hash", "expires_at"],
    )

    op.create_table(
        "invitations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column(
            "role",
            sa.String(length=20),
            server_default="member",
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("invited_by", sa.Uuid(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "role IN ('admin', 'member')",
            name="ck_invitations_role",
        ),
        sa.ForeignKeyConstraint(
            ["invited_by"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("idx_invitations_email", "invitations", ["email"])
    op.create_index(
        "idx_invitations_active",
        "invitations",
        ["token_hash", "expires_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_invitations_active", table_name="invitations")
    op.drop_index("idx_invitations_email", table_name="invitations")
    op.drop_table("invitations")
    op.drop_index("idx_session_tokens_active", table_name="session_tokens")
    op.drop_index("idx_session_tokens_user", table_name="session_tokens")
    op.drop_table("session_tokens")
