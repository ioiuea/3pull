"""change async job type columns to varchar

Revision ID: b785960f3fdb
Revises: e4f286c03b94
Create Date: 2026-02-28 04:40:29.164928

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b785960f3fdb'
down_revision: Union[str, Sequence[str], None] = 'e4f286c03b94'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # enum -> varchar 変換時に USING を明示して安全にキャストする。
    op.alter_column(
        "async_job_artifacts",
        "artifact_type",
        existing_type=postgresql.ENUM(
            "auth_audit_export_file", name="async_job_artifact_type"
        ),
        type_=sa.String(length=64),
        existing_nullable=False,
        postgresql_using="artifact_type::text",
    )
    op.alter_column(
        "async_jobs",
        "job_type",
        existing_type=postgresql.ENUM("auth_audit_export", name="async_job_type"),
        type_=sa.String(length=64),
        existing_nullable=False,
        postgresql_using="job_type::text",
    )

    # 変換後は DB enum 型が不要になるため掃除する。
    op.execute("DROP TYPE IF EXISTS async_job_artifact_type")
    op.execute("DROP TYPE IF EXISTS async_job_type")


def downgrade() -> None:
    """Downgrade schema."""
    # 想定外の値が存在する場合は enum へ戻せないため、先に検査して明示エラーにする。
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM async_jobs
                WHERE job_type NOT IN ('auth_audit_export', 'sample_wait_blob')
            ) THEN
                RAISE EXCEPTION
                    'downgrade blocked: async_jobs.job_type has unsupported values';
            END IF;
        END
        $$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM async_job_artifacts
                WHERE artifact_type NOT IN (
                    'auth_audit_export_file',
                    'sample_wait_blob_file'
                )
            ) THEN
                RAISE EXCEPTION
                    'downgrade blocked: '
                    'async_job_artifacts.artifact_type has unsupported values';
            END IF;
        END
        $$;
        """
    )

    # enum 型を復元してから列型を戻す。
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'async_job_type') THEN
                CREATE TYPE async_job_type AS ENUM (
                    'auth_audit_export',
                    'sample_wait_blob'
                );
            END IF;
        END
        $$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_type WHERE typname = 'async_job_artifact_type'
            ) THEN
                CREATE TYPE async_job_artifact_type AS ENUM (
                    'auth_audit_export_file',
                    'sample_wait_blob_file'
                );
            END IF;
        END
        $$;
        """
    )
    op.alter_column(
        "async_jobs",
        "job_type",
        existing_type=sa.String(length=64),
        type_=postgresql.ENUM(
            "auth_audit_export",
            "sample_wait_blob",
            name="async_job_type",
            create_type=False,
        ),
        existing_nullable=False,
        postgresql_using="job_type::async_job_type",
    )
    op.alter_column(
        "async_job_artifacts",
        "artifact_type",
        existing_type=sa.String(length=64),
        type_=postgresql.ENUM(
            "auth_audit_export_file",
            "sample_wait_blob_file",
            name="async_job_artifact_type",
            create_type=False,
        ),
        existing_nullable=False,
        postgresql_using="artifact_type::async_job_artifact_type",
    )
