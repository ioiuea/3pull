"""init sqlite

Revision ID: 429214a93c4b
Revises:
Create Date: 2025-10-16 05:11:07.599888

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "429214a93c4b"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """データベースをアップグレードする"""
    op.create_table(
        "folders",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("doc", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "chat_threads",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("doc", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """データベースをダウングレードする"""
    op.drop_table("chat_threads")
    op.drop_table("folders")
