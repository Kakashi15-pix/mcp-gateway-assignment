"""add server health checks

Revision ID: 8b3c5d7e9f10
Revises: 7a2e4b9c1d6f
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "8b3c5d7e9f10"
down_revision: Union[str, Sequence[str], None] = "7a2e4b9c1d6f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "server_health_checks",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("server_id", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column(
            "checked_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["server_id"], ["mcp_servers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_server_health_checks_server_time",
        "server_health_checks",
        ["server_id", "checked_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_server_health_checks_server_time",
        table_name="server_health_checks",
    )
    op.drop_table("server_health_checks")
