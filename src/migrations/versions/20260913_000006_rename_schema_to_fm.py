"""Rename PostgreSQL schema work_order to fm.

Revision ID: 20260913_000006
Revises: 20260912_000005
Create Date: 2026-09-13
"""

from alembic import op

revision = "20260913_000006"
down_revision = "20260912_000005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.schemata WHERE schema_name = 'work_order'
            ) AND NOT EXISTS (
                SELECT 1 FROM information_schema.schemata WHERE schema_name = 'fm'
            ) THEN
                ALTER SCHEMA work_order RENAME TO fm;
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.schemata WHERE schema_name = 'fm'
            ) AND NOT EXISTS (
                SELECT 1 FROM information_schema.schemata WHERE schema_name = 'work_order'
            ) THEN
                ALTER SCHEMA fm RENAME TO work_order;
            END IF;
        END $$;
        """
    )
