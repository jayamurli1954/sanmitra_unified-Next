"""
Phase 3: MandirMitra Database Schema

Creates database tables for:
- Temples and Bank Accounts (Phase 3C)
- Donations and Donation Categories (Phase 3A)
- Sevas, Seva Bookings (Phase 3B)

Run: psql -U user -d database -f 002_phase3_mandir_tables.sql
"""

-- ============================================================================
-- PHASE 3C: TEMPLES AND BANK ACCOUNTS
-- ============================================================================

CREATE TABLE IF NOT EXISTS mandir_temples (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    primary_deity VARCHAR(255),
    address TEXT,
    phone VARCHAR(20),
    email VARCHAR(255),
    bank_account_id INTEGER,
    upi_id VARCHAR(100),

    -- Configuration
    financial_year_start VARCHAR(5) DEFAULT '04-01',  -- MM-DD format
    module_donations BOOLEAN DEFAULT TRUE,
    module_sevas BOOLEAN DEFAULT TRUE,
    module_devotees BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_temple_name_per_tenant UNIQUE (tenant_id, name),
    CONSTRAINT ck_financial_year_start CHECK (financial_year_start ~ '^\d{2}-\d{2}$')
);

CREATE INDEX idx_temples_tenant ON mandir_temples(tenant_id);

-- Bank Accounts
CREATE TABLE IF NOT EXISTS mandir_bank_accounts (
    id SERIAL PRIMARY KEY,
    temple_id INTEGER NOT NULL REFERENCES mandir_temples(id) ON DELETE CASCADE,
    account_number VARCHAR(50) NOT NULL,
    ifsc VARCHAR(11) NOT NULL,  -- Indian Financial System Code
    account_holder VARCHAR(255) NOT NULL,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_temple_account_number UNIQUE (temple_id, account_number),
    CONSTRAINT ck_ifsc_length CHECK (length(ifsc) = 11)
);

CREATE INDEX idx_bank_accounts_temple ON mandir_bank_accounts(temple_id);


-- ============================================================================
-- PHASE 3A: DONATIONS
-- ============================================================================

-- Donation Categories (income account mapping)
CREATE TABLE IF NOT EXISTS mandir_donation_categories (
    id SERIAL PRIMARY KEY,
    temple_id INTEGER NOT NULL REFERENCES mandir_temples(id) ON DELETE CASCADE,
    tenant_id VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    account_id INTEGER NOT NULL,  -- Income account ID (from core_accounting.accounts)
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_donation_category_per_temple UNIQUE (temple_id, name)
);

CREATE INDEX idx_donation_categories_temple ON mandir_donation_categories(temple_id);

-- Donations
CREATE TABLE IF NOT EXISTS mandir_donations (
    id SERIAL PRIMARY KEY,
    temple_id INTEGER NOT NULL REFERENCES mandir_temples(id) ON DELETE CASCADE,
    tenant_id VARCHAR(255) NOT NULL,
    amount NUMERIC(12, 2) NOT NULL,
    donor_name VARCHAR(255),
    payment_mode VARCHAR(20) NOT NULL,  -- cash, bank, upi, cheque, card
    donation_category_id INTEGER NOT NULL REFERENCES mandir_donation_categories(id),
    donation_date DATE NOT NULL,
    receipt_number VARCHAR(50),
    reference VARCHAR(255),  -- Idempotency key: "donation:{donation_id}"
    journal_entry_id INTEGER,  -- Reference to accounting module
    notes TEXT,
    is_cancelled BOOLEAN DEFAULT FALSE,
    cancellation_reason TEXT,
    created_by VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT ck_donation_amount_positive CHECK (amount > 0),
    CONSTRAINT ck_payment_mode CHECK (payment_mode IN ('cash', 'bank', 'upi', 'cheque', 'card')),
    CONSTRAINT uq_receipt_number UNIQUE (temple_id, receipt_number),
    CONSTRAINT uq_donation_reference UNIQUE (reference)
);

CREATE INDEX idx_donations_temple ON mandir_donations(temple_id);
CREATE INDEX idx_donations_category ON mandir_donations(donation_category_id);
CREATE INDEX idx_donations_date ON mandir_donations(donation_date);
CREATE INDEX idx_donations_status ON mandir_donations(is_cancelled);


-- ============================================================================
-- PHASE 3B: SEVAS (TEMPLE SERVICES)
-- ============================================================================

-- Seva Categories
CREATE TABLE IF NOT EXISTS mandir_seva_categories (
    id SERIAL PRIMARY KEY,
    temple_id INTEGER NOT NULL REFERENCES mandir_temples(id) ON DELETE CASCADE,
    tenant_id VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_seva_category_per_temple UNIQUE (temple_id, name)
);

CREATE INDEX idx_seva_categories_temple ON mandir_seva_categories(temple_id);

-- Sevas (Service Definitions)
CREATE TABLE IF NOT EXISTS mandir_sevas (
    id SERIAL PRIMARY KEY,
    temple_id INTEGER NOT NULL REFERENCES mandir_temples(id) ON DELETE CASCADE,
    tenant_id VARCHAR(255) NOT NULL,
    category_id INTEGER NOT NULL REFERENCES mandir_seva_categories(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    price NUMERIC(12, 2) NOT NULL,
    account_id INTEGER NOT NULL,  -- Income account (from accounting module)
    is_available BOOLEAN DEFAULT TRUE,
    requires_advance BOOLEAN DEFAULT FALSE,
    advance_amount NUMERIC(12, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT ck_seva_price_positive CHECK (price > 0),
    CONSTRAINT ck_seva_advance_positive CHECK (advance_amount IS NULL OR advance_amount > 0),
    CONSTRAINT uq_seva_name_per_temple UNIQUE (temple_id, name)
);

CREATE INDEX idx_sevas_temple ON mandir_sevas(temple_id);
CREATE INDEX idx_sevas_category ON mandir_sevas(category_id);

-- Seva Bookings
CREATE TABLE IF NOT EXISTS mandir_seva_bookings (
    id SERIAL PRIMARY KEY,
    temple_id INTEGER NOT NULL REFERENCES mandir_temples(id) ON DELETE CASCADE,
    tenant_id VARCHAR(255) NOT NULL,
    seva_id INTEGER NOT NULL REFERENCES mandir_sevas(id) ON DELETE CASCADE,

    -- Customer info
    customer_name VARCHAR(255) NOT NULL,
    customer_phone VARCHAR(20),
    customer_email VARCHAR(255),
    customer_notes TEXT,

    -- Booking details
    quantity INTEGER DEFAULT 1 NOT NULL,
    unit_price NUMERIC(12, 2) NOT NULL,
    total_price NUMERIC(12, 2) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',  -- pending, confirmed, completed, cancelled, refund_requested
    booking_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    scheduled_date TIMESTAMP,
    completion_date TIMESTAMP,

    -- Payment tracking
    advance_paid NUMERIC(12, 2) DEFAULT 0,
    advance_payment_date TIMESTAMP,
    advance_journal_entry_id INTEGER,

    completion_paid NUMERIC(12, 2) DEFAULT 0,
    completion_payment_date TIMESTAMP,
    completion_journal_entry_id INTEGER,

    -- Refund tracking
    refund_amount NUMERIC(12, 2) DEFAULT 0,
    refund_reason TEXT,
    refund_date TIMESTAMP,
    refund_journal_entry_id INTEGER,

    -- Idempotency references
    advance_reference VARCHAR(255),
    completion_reference VARCHAR(255),

    -- Cancellation
    is_cancelled BOOLEAN DEFAULT FALSE,
    cancellation_reason TEXT,
    cancelled_by VARCHAR(255),
    cancelled_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(255),

    CONSTRAINT ck_booking_unit_price_positive CHECK (unit_price > 0),
    CONSTRAINT ck_booking_total_price_positive CHECK (total_price > 0),
    CONSTRAINT ck_booking_quantity_positive CHECK (quantity > 0),
    CONSTRAINT ck_booking_advance_paid_non_negative CHECK (advance_paid >= 0),
    CONSTRAINT ck_booking_completion_paid_non_negative CHECK (completion_paid >= 0),
    CONSTRAINT ck_booking_refund_non_negative CHECK (refund_amount >= 0),
    CONSTRAINT ck_booking_status CHECK (status IN ('pending', 'confirmed', 'completed', 'cancelled', 'refund_requested')),
    CONSTRAINT uq_advance_reference UNIQUE (advance_reference),
    CONSTRAINT uq_completion_reference UNIQUE (completion_reference)
);

CREATE INDEX idx_seva_bookings_temple ON mandir_seva_bookings(temple_id);
CREATE INDEX idx_seva_bookings_seva ON mandir_seva_bookings(seva_id);
CREATE INDEX idx_seva_bookings_status ON mandir_seva_bookings(status);
CREATE INDEX idx_seva_bookings_scheduled_date ON mandir_seva_bookings(scheduled_date);


-- ============================================================================
-- DATABASE VIEWS FOR REPORTING
-- ============================================================================

-- Daily Donation Report View
CREATE OR REPLACE VIEW mandir_donation_daily_report AS
SELECT
    DATE(d.donation_date) as donation_date,
    d.temple_id,
    d.tenant_id,
    dc.name as category_name,
    COUNT(d.id) as count,
    SUM(d.amount) as total,
    COUNT(DISTINCT d.payment_mode) as payment_modes
FROM mandir_donations d
LEFT JOIN mandir_donation_categories dc ON d.donation_category_id = dc.id
WHERE d.is_cancelled = FALSE
GROUP BY DATE(d.donation_date), d.temple_id, d.tenant_id, dc.name;

-- Donation Summary by Category
CREATE OR REPLACE VIEW mandir_donation_category_report AS
SELECT
    d.temple_id,
    d.tenant_id,
    dc.name as category_name,
    COUNT(d.id) as donation_count,
    SUM(d.amount) as total_amount,
    ROUND(100.0 * SUM(d.amount) /
        (SELECT SUM(amount) FROM mandir_donations WHERE temple_id = d.temple_id AND tenant_id = d.tenant_id AND is_cancelled = FALSE),
        2) as percentage
FROM mandir_donations d
LEFT JOIN mandir_donation_categories dc ON d.donation_category_id = dc.id
WHERE d.is_cancelled = FALSE
GROUP BY d.temple_id, d.tenant_id, dc.name;

-- Seva Booking Schedule View
CREATE OR REPLACE VIEW mandir_seva_booking_schedule AS
SELECT
    DATE(sb.scheduled_date) as scheduled_date,
    sb.temple_id,
    sb.tenant_id,
    s.id as seva_id,
    s.name as seva_name,
    COUNT(sb.id) as booking_count,
    STRING_AGG(DISTINCT sb.customer_name, ', ') as customer_names,
    SUM(sb.total_price) as total_amount
FROM mandir_seva_bookings sb
LEFT JOIN mandir_sevas s ON sb.seva_id = s.id
WHERE sb.status = 'confirmed' AND sb.is_cancelled = FALSE
GROUP BY DATE(sb.scheduled_date), sb.temple_id, sb.tenant_id, s.id, s.name;

-- Seva Revenue Report View
CREATE OR REPLACE VIEW mandir_seva_revenue_report AS
SELECT
    s.temple_id,
    s.tenant_id,
    s.id as seva_id,
    s.name as seva_name,
    COUNT(sb.id) as total_bookings,
    COUNT(CASE WHEN sb.status = 'completed' THEN 1 END) as completed_bookings,
    SUM(sb.total_price) as total_revenue,
    ROUND(AVG(sb.total_price), 2) as average_booking_price
FROM mandir_sevas s
LEFT JOIN mandir_seva_bookings sb ON s.id = sb.seva_id AND sb.is_cancelled = FALSE
GROUP BY s.temple_id, s.tenant_id, s.id, s.name;


-- ============================================================================
-- ADD FOREIGN KEY FOR TEMPLES.bank_account_id
-- ============================================================================

ALTER TABLE mandir_temples
ADD CONSTRAINT fk_temple_bank_account
FOREIGN KEY (bank_account_id)
REFERENCES mandir_bank_accounts(id) ON DELETE SET NULL;


-- ============================================================================
-- DONE
-- ============================================================================

-- Summary of tables created:
-- - mandir_temples (master data)
-- - mandir_bank_accounts (payment accounts)
-- - mandir_donation_categories (donation type mapping)
-- - mandir_donations (donation records with journal linking)
-- - mandir_seva_categories (seva type grouping)
-- - mandir_sevas (service definitions)
-- - mandir_seva_bookings (booking records with workflow status)
--
-- Views:
-- - mandir_donation_daily_report (daily donation aggregates)
-- - mandir_donation_category_report (donation breakdown by category)
-- - mandir_seva_booking_schedule (upcoming bookings by date)
-- - mandir_seva_revenue_report (revenue by seva)
--
-- Total: 7 tables + 4 views covering all Phase 3 functionality
