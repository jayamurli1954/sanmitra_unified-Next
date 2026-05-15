-- Phase 1: Foundation - Create Audit Logs Table
-- This table tracks all critical actions for compliance and debugging

-- Audit logs table (PostgreSQL)
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Entity being audited
    entity_type VARCHAR(100) NOT NULL,      -- "donation", "journal_entry", "user_role"
    entity_id VARCHAR(255) NOT NULL,        -- ID of the entity

    -- Action details
    action VARCHAR(50) NOT NULL,            -- "created", "updated", "deleted"
    user_id VARCHAR(255),                   -- User who performed action
    tenant_id VARCHAR(255) NOT NULL,        -- Multi-tenant isolation

    -- State tracking
    before_state JSONB,                     -- Previous values (NULL for create)
    after_state JSONB,                      -- New values

    -- Timing and context
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(45),                 -- IPv4 or IPv6
    user_agent TEXT,

    -- Constraints
    CONSTRAINT audit_logs_pkey PRIMARY KEY (id)
);

-- Indexes for query performance
CREATE INDEX IF NOT EXISTS idx_audit_logs_tenant_entity
ON audit_logs(tenant_id, entity_type, entity_id);

CREATE INDEX IF NOT EXISTS idx_audit_logs_tenant_timestamp
ON audit_logs(tenant_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_audit_logs_entity_type_action
ON audit_logs(entity_type, action);

CREATE INDEX IF NOT EXISTS idx_audit_logs_user_timestamp
ON audit_logs(user_id, timestamp DESC);


-- ============================================================================
-- Accounting Tables (Foundation for Phase 2)
-- ============================================================================

-- Chart of Accounts
CREATE TABLE IF NOT EXISTS accounting_accounts (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(255) NOT NULL,
    account_number VARCHAR(50) NOT NULL,
    account_name VARCHAR(255) NOT NULL,
    account_type VARCHAR(50) NOT NULL,    -- asset, liability, equity, income, expense
    account_category VARCHAR(100),
    description TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(tenant_id, account_number),
    CONSTRAINT chk_account_type CHECK (account_type IN ('asset', 'liability', 'equity', 'income', 'expense'))
);

CREATE INDEX IF NOT EXISTS idx_accounts_tenant_active
ON accounting_accounts(tenant_id, is_active);


-- Journal Entries (main transaction record)
CREATE TABLE IF NOT EXISTS journal_entries (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(255) NOT NULL,
    entry_date DATE NOT NULL,
    description VARCHAR(500) NOT NULL,
    reference VARCHAR(100),                -- External reference (donation:123, payment:xyz)
    status VARCHAR(50) DEFAULT 'draft',    -- draft, posted, reversed, cancelled
    created_by VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    posted_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_status CHECK (status IN ('draft', 'posted', 'reversed', 'cancelled')),
    UNIQUE(tenant_id, reference)           -- Prevent duplicate posting via reference ID
);

CREATE INDEX IF NOT EXISTS idx_journal_entries_tenant_date
ON journal_entries(tenant_id, entry_date DESC);

CREATE INDEX IF NOT EXISTS idx_journal_entries_status
ON journal_entries(tenant_id, status);


-- Journal Lines (individual debits and credits)
CREATE TABLE IF NOT EXISTS journal_lines (
    id SERIAL PRIMARY KEY,
    entry_id INTEGER NOT NULL REFERENCES journal_entries(id) ON DELETE CASCADE,
    account_id INTEGER NOT NULL REFERENCES accounting_accounts(id),
    debit NUMERIC(15,2) DEFAULT 0,
    credit NUMERIC(15,2) DEFAULT 0,
    description VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_amounts CHECK (debit >= 0 AND credit >= 0),
    CONSTRAINT chk_not_both_zero CHECK (debit > 0 OR credit > 0)
);

CREATE INDEX IF NOT EXISTS idx_journal_lines_entry
ON journal_lines(entry_id);

CREATE INDEX IF NOT EXISTS idx_journal_lines_account
ON journal_lines(account_id);


-- ============================================================================
-- Reporting Views (Foundation for Phase 4)
-- ============================================================================

-- Trial Balance View
CREATE OR REPLACE VIEW trial_balance_view AS
SELECT
    a.id as account_id,
    a.account_number,
    a.account_name,
    a.account_type,
    j.tenant_id,
    COALESCE(SUM(jl.debit), 0) as total_debit,
    COALESCE(SUM(jl.credit), 0) as total_credit,
    COALESCE(SUM(jl.debit), 0) - COALESCE(SUM(jl.credit), 0) as balance
FROM accounting_accounts a
LEFT JOIN journal_lines jl ON a.id = jl.account_id
LEFT JOIN journal_entries j ON jl.entry_id = j.id AND j.status = 'posted'
WHERE a.is_active = true
GROUP BY a.id, a.account_number, a.account_name, a.account_type, j.tenant_id;


-- ============================================================================
-- Multi-tenant Isolation Enforcement
-- ============================================================================

-- Row-level security: Only show data for current tenant
-- Note: Implement in application layer for now (app dependencies)
-- This is documented in app/core/phase1_dependencies.py
