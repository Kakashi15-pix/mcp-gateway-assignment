"""reconcile invitation lifecycle columns and foreign key

Revision ID: 7a2e4b9c1d6f
Revises: 4c6b9f2d1a7e
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7a2e4b9c1d6f"
down_revision: Union[str, Sequence[str], None] = "4c6b9f2d1a7e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "invitations",
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.alter_column(
        "invitations",
        "invited_by",
        existing_type=sa.Uuid(),
        nullable=True,
    )
    op.drop_constraint(
        "invitations_invited_by_fkey",
        "invitations",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "invitations_invited_by_fkey",
        "invitations",
        "users",
        ["invited_by"],
        ["id"],
        ondelete="SET NULL",
    )
    op.drop_index("idx_invitations_active", table_name="invitations")


def downgrade() -> None:
    op.create_index(
        "idx_invitations_active",
        "invitations",
        ["token_hash", "expires_at"],
    )
    op.drop_constraint(
        "invitations_invited_by_fkey",
        "invitations",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "invitations_invited_by_fkey",
        "invitations",
        "users",
        ["invited_by"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.alter_column(
        "invitations",
        "invited_by",
        existing_type=sa.Uuid(),
        nullable=False,
    )
    op.drop_column("invitations", "revoked_at")
