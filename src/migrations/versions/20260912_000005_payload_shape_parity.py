"""Align asset, recurring_days, and audit column names with reference backend.

Revision ID: 20260912_000005
Revises: 20260912_000004
Create Date: 2026-09-12
"""

from alembic import op

revision = "20260912_000005"
down_revision = "20260912_000004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE work_order.assets
            RENAME COLUMN supplier_name TO supplier
        """
    )
    op.execute(
        """
        ALTER TABLE work_order.assets
            RENAME COLUMN vendor_id TO supplier_vendor_id
        """
    )

    op.execute(
        """
        UPDATE work_order.work_orders wo
        SET recurring_days = COALESCE(
            (
                SELECT jsonb_agg(
                    CASE
                        WHEN wo.recurring_frequency IN ('weekly', 'fortnightly')
                             AND d BETWEEN 1 AND 7 THEN
                            (ARRAY[
                                'Monday', 'Tuesday', 'Wednesday', 'Thursday',
                                'Friday', 'Saturday', 'Sunday'
                            ])[d]
                        ELSE d::text
                    END
                )
                FROM unnest(wo.recurring_days) AS d
            ),
            '[]'::jsonb
        )
        """
    )
    op.execute(
        """
        ALTER TABLE work_order.work_orders
            ALTER COLUMN recurring_days DROP DEFAULT
        """
    )
    op.execute(
        """
        ALTER TABLE work_order.work_orders
            ALTER COLUMN recurring_days TYPE jsonb
            USING recurring_days::jsonb
        """
    )
    op.execute(
        """
        ALTER TABLE work_order.work_orders
            ALTER COLUMN recurring_days SET DEFAULT '[]'::jsonb
        """
    )

    op.execute(
        """
        ALTER TABLE work_order.audit_events
            RENAME COLUMN actor_name TO actor
        """
    )
    op.execute(
        """
        ALTER TABLE work_order.audit_events
            DROP COLUMN actor_user_id
        """
    )
    op.execute(
        """
        ALTER TABLE work_order.audit_events
            RENAME COLUMN created_at TO at
        """
    )
    op.execute(
        """
        DROP INDEX IF EXISTS work_order.idx_wo_audit_events_tenant_project_created
        """
    )
    op.execute(
        """
        CREATE INDEX idx_wo_audit_events_tenant_project_at
            ON work_order.audit_events (tenant_id, project_id, at)
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP INDEX IF EXISTS work_order.idx_wo_audit_events_tenant_project_at
        """
    )
    op.execute(
        """
        ALTER TABLE work_order.audit_events
            RENAME COLUMN at TO created_at
        """
    )
    op.execute(
        """
        ALTER TABLE work_order.audit_events
            ADD COLUMN actor_user_id text
        """
    )
    op.execute(
        """
        ALTER TABLE work_order.audit_events
            RENAME COLUMN actor TO actor_name
        """
    )
    op.execute(
        """
        CREATE INDEX idx_wo_audit_events_tenant_project_created
            ON work_order.audit_events (tenant_id, project_id, created_at)
        """
    )

    op.execute(
        """
        ALTER TABLE work_order.work_orders
            ALTER COLUMN recurring_days DROP DEFAULT
        """
    )
    op.execute(
        """
        ALTER TABLE work_order.work_orders
            ALTER COLUMN recurring_days TYPE smallint[]
            USING (
                SELECT COALESCE(
                    array_agg(
                        CASE
                            WHEN jsonb_typeof(elem) = 'number' THEN (elem #>> '{}')::smallint
                            WHEN jsonb_typeof(elem) = 'string'
                                 AND (elem #>> '{}') ~ '^[0-9]+$' THEN (elem #>> '{}')::smallint
                            ELSE NULL::smallint
                        END
                    ),
                    '{}'::smallint[]
                )
                FROM jsonb_array_elements(recurring_days) AS elem
            )
        """
    )
    op.execute(
        """
        ALTER TABLE work_order.work_orders
            ALTER COLUMN recurring_days SET DEFAULT '{}'::smallint[]
        """
    )

    op.execute(
        """
        ALTER TABLE work_order.assets
            RENAME COLUMN supplier_vendor_id TO vendor_id
        """
    )
    op.execute(
        """
        ALTER TABLE work_order.assets
            RENAME COLUMN supplier TO supplier_name
        """
    )
