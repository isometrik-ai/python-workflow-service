"""Parity modules: custom fields, business profile, PDF templates, API call logs.

Also renames assets.custom_fields -> custom_field_values (list to dict).

Revision ID: 20260912_000002
Revises: 20260912_000001
Create Date: 2026-09-12
"""

from alembic import op

revision = "20260912_000002"
down_revision = "20260912_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE work_order.assets
            RENAME COLUMN custom_fields TO custom_field_values
        """
    )
    op.execute(
        """
        ALTER TABLE work_order.assets
            ALTER COLUMN custom_field_values SET DEFAULT '{}'::jsonb
        """
    )
    op.execute(
        """
        UPDATE work_order.assets
        SET custom_field_values = '{}'::jsonb
        WHERE jsonb_typeof(custom_field_values) = 'array'
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS work_order.custom_fields (
            id text PRIMARY KEY,
            tenant_id text NOT NULL,
            project_id text NOT NULL,
            field_name text NOT NULL,
            field_key text NOT NULL,
            field_type text NOT NULL,
            type_config jsonb NOT NULL DEFAULT '{}'::jsonb,
            is_required boolean NOT NULL DEFAULT false,
            is_active boolean NOT NULL DEFAULT true,
            sort_order integer NOT NULL DEFAULT 0,
            show_on_create boolean NOT NULL DEFAULT true,
            show_on_detail boolean NOT NULL DEFAULT true,
            scope text NOT NULL DEFAULT 'global',
            category_id text REFERENCES work_order.asset_categories (id) ON DELETE SET NULL,
            record_status work_order.work_order_record_status NOT NULL DEFAULT 'active',
            deleted_at timestamptz,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_wo_custom_fields_tenant_project
            ON work_order.custom_fields (tenant_id, project_id, record_status)
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS work_order.business_profile (
            id text PRIMARY KEY DEFAULT 'default',
            tenant_id text NOT NULL,
            project_id text NOT NULL,
            name text NOT NULL DEFAULT '',
            legal_name text NOT NULL DEFAULT '',
            gstin text NOT NULL DEFAULT '',
            address_line text NOT NULL DEFAULT '',
            city text NOT NULL DEFAULT '',
            state text NOT NULL DEFAULT '',
            pincode text NOT NULL DEFAULT '',
            phone text NOT NULL DEFAULT '',
            email text NOT NULL DEFAULT '',
            website text NOT NULL DEFAULT '',
            logo jsonb NOT NULL DEFAULT '{}'::jsonb,
            bank_name text NOT NULL DEFAULT '',
            bank_account text NOT NULL DEFAULT '',
            bank_ifsc text NOT NULL DEFAULT '',
            default_wo_notes text NOT NULL DEFAULT '',
            default_wo_terms text NOT NULL DEFAULT '',
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT uq_wo_business_profile_tenant_project UNIQUE (tenant_id, project_id)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_wo_business_profile_tenant_project
            ON work_order.business_profile (tenant_id, project_id)
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS work_order.pdf_templates (
            id text PRIMARY KEY,
            tenant_id text NOT NULL,
            project_id text NOT NULL,
            name text NOT NULL,
            doc_type text NOT NULL DEFAULT 'work_order',
            is_default boolean NOT NULL DEFAULT false,
            base_pdf text,
            schemas jsonb NOT NULL DEFAULT '[]'::jsonb,
            record_status work_order.work_order_record_status NOT NULL DEFAULT 'active',
            deleted_at timestamptz,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_wo_pdf_templates_tenant_project
            ON work_order.pdf_templates (tenant_id, project_id, record_status)
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS work_order.api_call_logs (
            id text PRIMARY KEY,
            tenant_id text NOT NULL,
            project_id text NOT NULL,
            at timestamptz NOT NULL DEFAULT now(),
            method text NOT NULL,
            path text NOT NULL,
            status_code integer NOT NULL,
            duration_ms integer NOT NULL DEFAULT 0,
            source text,
            request_body jsonb NOT NULL DEFAULT '{}'::jsonb,
            response_body jsonb NOT NULL DEFAULT '{}'::jsonb
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_wo_api_call_logs_tenant_project_at
            ON work_order.api_call_logs (tenant_id, project_id, at DESC)
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS work_order.api_call_logs")
    op.execute("DROP TABLE IF EXISTS work_order.pdf_templates")
    op.execute("DROP TABLE IF EXISTS work_order.business_profile")
    op.execute("DROP TABLE IF EXISTS work_order.custom_fields")

    op.execute(
        """
        UPDATE work_order.assets
        SET custom_field_values = '[]'::jsonb
        WHERE jsonb_typeof(custom_field_values) = 'object'
        """
    )
    op.execute(
        """
        ALTER TABLE work_order.assets
            ALTER COLUMN custom_field_values SET DEFAULT '[]'::jsonb
        """
    )
    op.execute(
        """
        ALTER TABLE work_order.assets
            RENAME COLUMN custom_field_values TO custom_fields
        """
    )
