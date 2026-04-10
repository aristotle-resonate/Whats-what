"""add magic_links table

Revision ID: a1b2c3d4e5f6
Revises: e6008dfbc2f9
Create Date: 2026-04-10 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "e6008dfbc2f9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "magic_links",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("token", sa.String(86), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_magic_links_email", "magic_links", ["email"])
    op.create_index("ix_magic_links_token", "magic_links", ["token"])


def downgrade() -> None:
    op.drop_index("ix_magic_links_token", table_name="magic_links")
    op.drop_index("ix_magic_links_email", table_name="magic_links")
    op.drop_table("magic_links")
