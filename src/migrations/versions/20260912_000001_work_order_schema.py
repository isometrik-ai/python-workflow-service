"""Initial work_order schema (adapted from ats-home-craft-supabase).

Standalone Postgres: IDs are text (application-assigned prefixes) matching SQLAlchemy ORM models.
RLS is not enabled in this migration; authorization is enforced in the application layer.

Revision ID: 20260912_000001
Revises:
Create Date: 2026-09-12
"""

from alembic import op

revision = "20260912_000001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS work_order")

    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE work_order.work_order_record_status AS ENUM ('active', 'deleted');
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
        """
    )
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE work_order.work_order_asset_status AS ENUM (
                'operational', 'under_repair', 'faulty', 'decommissioned'
            );
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
        """
    )
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE work_order.work_order_contract_status AS ENUM (
                'active', 'expired', 'terminated', 'paused'
            );
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
        """
    )
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE work_order.work_order_visit_frequency AS ENUM (
                'daily', 'weekly', 'fortnightly', 'monthly', 'quarterly', 'half_yearly', 'yearly'
            );
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
        """
    )
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE work_order.work_order_payment_frequency AS ENUM (
                'monthly', 'quarterly', 'half_yearly', 'yearly', 'one_time'
            );
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
        """
    )
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE work_order.work_order_work_order_state AS ENUM (
                'upcoming', 'in_progress', 'in_review', 'completed', 'terminated'
            );
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
        """
    )
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE work_order.work_order_work_order_priority AS ENUM (
                'low', 'medium', 'high', 'urgent'
            );
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
        """
    )
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE work_order.work_order_work_order_source AS ENUM (
                'contract', 'ad_hoc', 'recurring'
            );
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
        """
    )
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE work_order.work_order_invoice_status AS ENUM (
                'submitted', 'revision_requested', 'resubmitted', 'approved', 'rejected', 'paid'
            );
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
        """
    )
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE work_order.work_order_payment_method AS ENUM (
                'bank_transfer', 'cheque', 'cash', 'upi', 'other'
            );
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
        """
    )
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE work_order.work_order_payment_status AS ENUM (
                'pending', 'completed', 'failed', 'voided'
            );
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
        """
    )
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE work_order.work_order_trigger_entity AS ENUM (
                'work_order', 'contract', 'invoice', 'payment'
            );
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
        """
    )
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE work_order.work_order_trigger_event AS ENUM (
                'created', 'updated', 'deleted', 'status_changed'
            );
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
        """
    )
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE work_order.work_order_audit_action AS ENUM (
                'created', 'updated', 'deleted', 'status_changed'
            );
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
        """
    )
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE work_order.work_order_audit_source AS ENUM (
                'fm', 'vendor_portal', 'scheduler', 'api'
            );
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS work_order.asset_categories (
            id text PRIMARY KEY,
            tenant_id text NOT NULL,
            project_id text NOT NULL,
            name text NOT NULL,
            description text NOT NULL DEFAULT '',
            parent_id text REFERENCES work_order.asset_categories (id) ON DELETE SET NULL,
            record_status work_order.work_order_record_status NOT NULL DEFAULT 'active',
            deleted_at timestamptz,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_wo_asset_categories_tenant_project
            ON work_order.asset_categories (tenant_id, project_id, record_status)
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS work_order.assets (
            id text PRIMARY KEY,
            tenant_id text NOT NULL,
            project_id text NOT NULL,
            name text NOT NULL,
            code text NOT NULL,
            make text,
            model text,
            serial_number text,
            description text,
            category_id text NOT NULL REFERENCES work_order.asset_categories (id),
            status work_order.work_order_asset_status NOT NULL DEFAULT 'operational',
            facility_id text,
            location_text text,
            landmark_note text,
            photo_paths text[] NOT NULL DEFAULT '{}',
            associated_parts jsonb NOT NULL DEFAULT '[]'::jsonb,
            purchase_date date,
            purchase_cost_minor bigint,
            currency text NOT NULL DEFAULT 'INR',
            supplier_name text,
            vendor_id text,
            purchase_order_number text,
            invoice_ref text,
            install_date date,
            warranty_start date,
            warranty_expiry date,
            warranty_terms text,
            document_paths text[] NOT NULL DEFAULT '{}',
            custom_fields jsonb NOT NULL DEFAULT '[]'::jsonb,
            contract_id text,
            record_status work_order.work_order_record_status NOT NULL DEFAULT 'active',
            deleted_at timestamptz,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT assets_code_project_uq UNIQUE (project_id, code)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_wo_assets_tenant_project
            ON work_order.assets (tenant_id, project_id, record_status)
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS work_order.form_templates (
            id text PRIMARY KEY,
            tenant_id text NOT NULL,
            project_id text NOT NULL,
            name text NOT NULL,
            description text NOT NULL DEFAULT '',
            schema jsonb NOT NULL DEFAULT '{}'::jsonb,
            record_status work_order.work_order_record_status NOT NULL DEFAULT 'active',
            deleted_at timestamptz,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS work_order.maintenance_contracts (
            id text PRIMARY KEY,
            tenant_id text NOT NULL,
            project_id text NOT NULL,
            title text NOT NULL,
            vendor_id text NOT NULL,
            asset_ids text[] NOT NULL DEFAULT '{}',
            start_date date NOT NULL,
            end_date date,
            visit_frequency work_order.work_order_visit_frequency NOT NULL DEFAULT 'quarterly',
            payment_frequency work_order.work_order_payment_frequency NOT NULL DEFAULT 'quarterly',
            value_minor bigint,
            currency text NOT NULL DEFAULT 'INR',
            status work_order.work_order_contract_status NOT NULL DEFAULT 'active',
            next_visit_date date,
            last_serviced_date date,
            auto_generate_lead_days smallint,
            scope_included text,
            scope_excluded text,
            form_template_id text REFERENCES work_order.form_templates (id) ON DELETE SET NULL,
            pre_start_form_template_id text REFERENCES work_order.form_templates (id) ON DELETE SET NULL,
            document_paths text[] NOT NULL DEFAULT '{}',
            termination_reason text,
            record_status work_order.work_order_record_status NOT NULL DEFAULT 'active',
            deleted_at timestamptz,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )

    op.execute(
        """
        DO $$ BEGIN
            ALTER TABLE work_order.assets
                ADD CONSTRAINT assets_contract_id_fkey
                FOREIGN KEY (contract_id) REFERENCES work_order.maintenance_contracts (id) ON DELETE SET NULL;
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS work_order.work_orders (
            id text PRIMARY KEY,
            tenant_id text NOT NULL,
            project_id text NOT NULL,
            title text NOT NULL,
            description text,
            asset_ids text[] NOT NULL DEFAULT '{}',
            contract_id text REFERENCES work_order.maintenance_contracts (id) ON DELETE SET NULL,
            vendor_id text,
            form_template_id text REFERENCES work_order.form_templates (id) ON DELETE SET NULL,
            pre_start_form_template_id text REFERENCES work_order.form_templates (id) ON DELETE SET NULL,
            state work_order.work_order_work_order_state NOT NULL DEFAULT 'upcoming',
            priority work_order.work_order_work_order_priority NOT NULL DEFAULT 'medium',
            source work_order.work_order_work_order_source NOT NULL DEFAULT 'ad_hoc',
            scheduled_date date,
            started_at timestamptz,
            completed_at timestamptz,
            assignee_name text,
            assignee_user_id text,
            line_items jsonb NOT NULL DEFAULT '[]'::jsonb,
            form_values jsonb NOT NULL DEFAULT '{}'::jsonb,
            pre_start_form_values jsonb NOT NULL DEFAULT '{}'::jsonb,
            estimated_cost_minor bigint,
            access_notes text,
            is_recurring boolean NOT NULL DEFAULT false,
            recurring_frequency work_order.work_order_visit_frequency,
            recurring_days smallint[] NOT NULL DEFAULT '{}',
            recurring_end_date date,
            recurring_parent_id text REFERENCES work_order.work_orders (id) ON DELETE SET NULL,
            recurring_next_date date,
            invoice_ids text[] NOT NULL DEFAULT '{}',
            vendor_token_hash text,
            timeline jsonb NOT NULL DEFAULT '[]'::jsonb,
            termination_reason text,
            record_status work_order.work_order_record_status NOT NULL DEFAULT 'active',
            deleted_at timestamptz,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_wo_work_orders_vendor_token
            ON work_order.work_orders (vendor_token_hash)
            WHERE vendor_token_hash IS NOT NULL
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS work_order.vendor_invoices (
            id text PRIMARY KEY,
            tenant_id text NOT NULL,
            project_id text NOT NULL,
            work_order_id text NOT NULL REFERENCES work_order.work_orders (id) ON DELETE RESTRICT,
            vendor_id text NOT NULL,
            invoice_number text NOT NULL,
            invoice_date date,
            line_items jsonb NOT NULL DEFAULT '[]'::jsonb,
            subtotal_minor bigint NOT NULL DEFAULT 0,
            tax_minor bigint NOT NULL DEFAULT 0,
            total_minor bigint NOT NULL DEFAULT 0,
            currency text NOT NULL DEFAULT 'INR',
            status work_order.work_order_invoice_status NOT NULL DEFAULT 'submitted',
            file_paths text[] NOT NULL DEFAULT '{}',
            timeline jsonb NOT NULL DEFAULT '[]'::jsonb,
            revisions jsonb NOT NULL DEFAULT '[]'::jsonb,
            payment_id text,
            record_status work_order.work_order_record_status NOT NULL DEFAULT 'active',
            deleted_at timestamptz,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT vendor_invoices_number_project_uq UNIQUE (project_id, invoice_number)
        )
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS work_order.payments (
            id text PRIMARY KEY,
            tenant_id text NOT NULL,
            project_id text NOT NULL,
            invoice_id text REFERENCES work_order.vendor_invoices (id) ON DELETE SET NULL,
            work_order_id text REFERENCES work_order.work_orders (id) ON DELETE SET NULL,
            amount_minor bigint NOT NULL,
            currency text NOT NULL DEFAULT 'INR',
            method work_order.work_order_payment_method NOT NULL DEFAULT 'bank_transfer',
            reference text,
            payment_date date,
            status work_order.work_order_payment_status NOT NULL DEFAULT 'completed',
            receipt_path text,
            notes text,
            record_status work_order.work_order_record_status NOT NULL DEFAULT 'active',
            deleted_at timestamptz,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )

    op.execute(
        """
        DO $$ BEGIN
            ALTER TABLE work_order.vendor_invoices
                ADD CONSTRAINT vendor_invoices_payment_id_fkey
                FOREIGN KEY (payment_id) REFERENCES work_order.payments (id) ON DELETE SET NULL;
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS work_order.trigger_configs (
            id text PRIMARY KEY,
            tenant_id text NOT NULL,
            project_id text NOT NULL,
            name text NOT NULL,
            entity work_order.work_order_trigger_entity NOT NULL,
            event work_order.work_order_trigger_event NOT NULL,
            is_active boolean NOT NULL DEFAULT true,
            webhook_url text NOT NULL,
            secret text,
            record_status work_order.work_order_record_status NOT NULL DEFAULT 'active',
            deleted_at timestamptz,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS work_order.audit_events (
            id text PRIMARY KEY,
            tenant_id text NOT NULL,
            project_id text NOT NULL,
            entity work_order.work_order_trigger_entity NOT NULL,
            entity_id text NOT NULL,
            entity_label text,
            action work_order.work_order_audit_action NOT NULL,
            actor_name text,
            actor_user_id text,
            source work_order.work_order_audit_source NOT NULL DEFAULT 'fm',
            changes jsonb NOT NULL DEFAULT '[]'::jsonb,
            snapshot jsonb NOT NULL DEFAULT '{}'::jsonb,
            created_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS work_order.webhook_deliveries (
            id text PRIMARY KEY,
            tenant_id text NOT NULL,
            project_id text NOT NULL,
            trigger_id text REFERENCES work_order.trigger_configs (id) ON DELETE SET NULL,
            entity work_order.work_order_trigger_entity,
            entity_id text,
            event text NOT NULL,
            request_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
            response_status smallint,
            error text,
            attempt smallint NOT NULL DEFAULT 1,
            duration_ms integer NOT NULL DEFAULT 0,
            delivered boolean NOT NULL DEFAULT false,
            created_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS work_order.api_keys (
            id text PRIMARY KEY,
            tenant_id text NOT NULL,
            project_id text NOT NULL,
            name text NOT NULL,
            key_prefix text NOT NULL,
            key_hash text NOT NULL,
            last_used_at timestamptz,
            record_status work_order.work_order_record_status NOT NULL DEFAULT 'active',
            deleted_at timestamptz,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT uq_wo_api_keys_tenant_project UNIQUE (tenant_id, project_id)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_wo_api_keys_hash
            ON work_order.api_keys (key_hash)
        """
    )


def downgrade() -> None:
    op.execute("DROP SCHEMA IF EXISTS work_order CASCADE")
