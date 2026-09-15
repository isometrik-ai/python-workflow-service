"""Rename maintenance_contracts.document_paths to documents.

Revision ID: 20260912_000004
Revises: 20260912_000003
Create Date: 2026-09-12
"""

from alembic import op

revision = "20260912_000004"
down_revision = "20260912_000003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE work_order.maintenance_contracts
            RENAME COLUMN document_paths TO documents
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE work_order.maintenance_contracts
            RENAME COLUMN documents TO document_paths
        """
    )
