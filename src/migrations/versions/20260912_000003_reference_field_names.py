"""Align column names with reference backend field naming.

Revision ID: 20260912_000003
Revises: 20260912_000002
Create Date: 2026-09-12
"""

from alembic import op

revision = "20260912_000003"
down_revision = "20260912_000002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE work_order.assets RENAME COLUMN facility_id TO location_id;
        ALTER TABLE work_order.assets RENAME COLUMN photo_paths TO photos;
        ALTER TABLE work_order.assets RENAME COLUMN document_paths TO documents;
        ALTER TABLE work_order.assets RENAME COLUMN purchase_cost_minor TO purchase_cost;

        ALTER TABLE work_order.maintenance_contracts RENAME COLUMN value_minor TO value;

        ALTER TABLE work_order.work_orders RENAME COLUMN assignee_name TO assignee;
        ALTER TABLE work_order.work_orders RENAME COLUMN estimated_cost_minor TO estimated_cost;

        ALTER TABLE work_order.vendor_invoices RENAME COLUMN invoice_date TO date;
        ALTER TABLE work_order.vendor_invoices RENAME COLUMN subtotal_minor TO subtotal;
        ALTER TABLE work_order.vendor_invoices RENAME COLUMN tax_minor TO tax;
        ALTER TABLE work_order.vendor_invoices RENAME COLUMN total_minor TO total;
        ALTER TABLE work_order.vendor_invoices
            ADD COLUMN document jsonb NOT NULL DEFAULT '{}'::jsonb;
        ALTER TABLE work_order.vendor_invoices
            ADD COLUMN files jsonb NOT NULL DEFAULT '[]'::jsonb;
        UPDATE work_order.vendor_invoices
            SET files = to_jsonb(file_paths)
            WHERE file_paths IS NOT NULL AND cardinality(file_paths) > 0;
        ALTER TABLE work_order.vendor_invoices DROP COLUMN file_paths;

        ALTER TABLE work_order.payments RENAME COLUMN amount_minor TO amount;
        ALTER TABLE work_order.payments RENAME COLUMN payment_date TO date;
        ALTER TABLE work_order.payments
            ADD COLUMN receipt jsonb NOT NULL DEFAULT '{}'::jsonb;
        UPDATE work_order.payments
            SET receipt = jsonb_build_object('url', receipt_path)
            WHERE receipt_path IS NOT NULL AND receipt_path <> '';
        ALTER TABLE work_order.payments DROP COLUMN receipt_path;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE work_order.assets RENAME COLUMN location_id TO facility_id;
        ALTER TABLE work_order.assets RENAME COLUMN photos TO photo_paths;
        ALTER TABLE work_order.assets RENAME COLUMN documents TO document_paths;
        ALTER TABLE work_order.assets RENAME COLUMN purchase_cost TO purchase_cost_minor;

        ALTER TABLE work_order.maintenance_contracts RENAME COLUMN value TO value_minor;

        ALTER TABLE work_order.work_orders RENAME COLUMN assignee TO assignee_name;
        ALTER TABLE work_order.work_orders RENAME COLUMN estimated_cost TO estimated_cost_minor;

        ALTER TABLE work_order.vendor_invoices RENAME COLUMN date TO invoice_date;
        ALTER TABLE work_order.vendor_invoices RENAME COLUMN subtotal TO subtotal_minor;
        ALTER TABLE work_order.vendor_invoices RENAME COLUMN tax TO tax_minor;
        ALTER TABLE work_order.vendor_invoices RENAME COLUMN total TO total_minor;
        ALTER TABLE work_order.vendor_invoices
            ADD COLUMN file_paths text[] NOT NULL DEFAULT '{}';
        UPDATE work_order.vendor_invoices
            SET file_paths = ARRAY(
                SELECT jsonb_array_elements_text(files)
            )
            WHERE jsonb_typeof(files) = 'array';
        ALTER TABLE work_order.vendor_invoices DROP COLUMN document;
        ALTER TABLE work_order.vendor_invoices DROP COLUMN files;

        ALTER TABLE work_order.payments RENAME COLUMN amount TO amount_minor;
        ALTER TABLE work_order.payments RENAME COLUMN date TO payment_date;
        ALTER TABLE work_order.payments ADD COLUMN receipt_path text;
        UPDATE work_order.payments
            SET receipt_path = receipt->>'url'
            WHERE receipt IS NOT NULL AND receipt <> '{}'::jsonb;
        ALTER TABLE work_order.payments DROP COLUMN receipt;
        """
    )
