PRAGMA foreign_keys = ON;

DROP VIEW IF EXISTS customer_support_tickets;
DROP VIEW IF EXISTS production_usage_daily;
DROP VIEW IF EXISTS active_customer_accounts;

DROP TABLE IF EXISTS metric_notes;
DROP TABLE IF EXISTS data_quality_cases;
DROP TABLE IF EXISTS tickets;
DROP TABLE IF EXISTS incidents;
DROP TABLE IF EXISTS usage_daily;
DROP TABLE IF EXISTS subscriptions;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS accounts;

CREATE TABLE accounts (
    account_id TEXT PRIMARY KEY,
    account_name TEXT NOT NULL,
    segment TEXT NOT NULL CHECK (segment IN ('enterprise', 'commercial', 'startup', 'internal')),
    region TEXT NOT NULL CHECK (region IN ('NA', 'EMEA', 'APAC', 'LATAM')),
    account_status TEXT NOT NULL CHECK (account_status IN ('active', 'paused', 'churned', 'test')),
    owner_team TEXT NOT NULL,
    is_internal INTEGER NOT NULL CHECK (is_internal IN (0, 1)),
    created_at TEXT NOT NULL
);

CREATE TABLE products (
    product_id TEXT PRIMARY KEY,
    product_name TEXT NOT NULL,
    product_family TEXT NOT NULL,
    is_active INTEGER NOT NULL CHECK (is_active IN (0, 1))
);

CREATE TABLE subscriptions (
    subscription_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES accounts(account_id),
    product_id TEXT NOT NULL REFERENCES products(product_id),
    plan_code TEXT NOT NULL CHECK (plan_code IN ('enterprise', 'growth', 'standard', 'trial', 'internal')),
    subscription_status TEXT NOT NULL CHECK (subscription_status IN ('active', 'paused', 'ended', 'trial')),
    start_date TEXT NOT NULL,
    end_date TEXT,
    CHECK (end_date IS NULL OR end_date >= start_date)
);

CREATE TABLE usage_daily (
    usage_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES accounts(account_id),
    product_id TEXT NOT NULL REFERENCES products(product_id),
    activity_date TEXT NOT NULL,
    environment TEXT NOT NULL CHECK (environment IN ('production', 'staging', 'sandbox', 'internal')),
    source_system TEXT NOT NULL CHECK (source_system IN ('telemetry_v1', 'telemetry_v2', 'import_patch')),
    seats_active INTEGER NOT NULL CHECK (seats_active >= 0),
    api_calls INTEGER NOT NULL CHECK (api_calls >= 0),
    compute_hours REAL NOT NULL CHECK (compute_hours >= 0),
    data_gb REAL NOT NULL CHECK (data_gb >= 0),
    is_backfill INTEGER NOT NULL CHECK (is_backfill IN (0, 1)),
    recorded_at TEXT NOT NULL,
    audit_reason TEXT,
    audit_updated_at TEXT
);

CREATE TABLE incidents (
    incident_id TEXT PRIMARY KEY,
    product_id TEXT NOT NULL REFERENCES products(product_id),
    started_at TEXT NOT NULL,
    resolved_at TEXT NOT NULL,
    severity TEXT NOT NULL CHECK (severity IN ('SEV1', 'SEV2', 'SEV3')),
    impacted_region TEXT NOT NULL CHECK (impacted_region IN ('NA', 'EMEA', 'APAC', 'LATAM', 'GLOBAL')),
    public_status TEXT NOT NULL CHECK (public_status IN ('resolved', 'monitoring', 'closed')),
    CHECK (resolved_at >= started_at)
);

CREATE TABLE tickets (
    ticket_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES accounts(account_id),
    product_id TEXT NOT NULL REFERENCES products(product_id),
    created_at TEXT NOT NULL,
    closed_at TEXT,
    status TEXT NOT NULL CHECK (status IN ('open', 'in_progress', 'resolved', 'canceled')),
    severity TEXT NOT NULL CHECK (severity IN ('P1', 'P2', 'P3', 'P4')),
    category TEXT NOT NULL CHECK (category IN ('bug', 'outage', 'performance', 'data_loss', 'how_to', 'billing', 'feature_request', 'internal_test')),
    customer_impact INTEGER NOT NULL CHECK (customer_impact IN (0, 1)),
    is_duplicate INTEGER NOT NULL CHECK (is_duplicate IN (0, 1)),
    duplicate_of TEXT REFERENCES tickets(ticket_id),
    linked_incident_id TEXT REFERENCES incidents(incident_id),
    sla_due_at TEXT NOT NULL,
    audit_reason TEXT,
    audit_updated_at TEXT,
    CHECK (closed_at IS NULL OR closed_at >= created_at)
);

CREATE TABLE data_quality_cases (
    case_id TEXT PRIMARY KEY,
    case_type TEXT NOT NULL CHECK (case_type IN ('usage_product_correction', 'ticket_duplicate_correction')),
    case_status TEXT NOT NULL CHECK (case_status IN ('approved', 'draft', 'rejected')),
    target_table TEXT NOT NULL,
    target_ids_csv TEXT NOT NULL,
    field_name TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT NOT NULL,
    approval_code TEXT NOT NULL,
    audit_reason TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE metric_notes (
    note_id TEXT PRIMARY KEY,
    topic TEXT NOT NULL,
    note_text TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX idx_accounts_segment_region ON accounts(segment, region);
CREATE INDEX idx_subscriptions_account_product ON subscriptions(account_id, product_id);
CREATE INDEX idx_usage_account_product_date ON usage_daily(account_id, product_id, activity_date);
CREATE INDEX idx_usage_source_env_date ON usage_daily(source_system, environment, activity_date);
CREATE INDEX idx_tickets_account_product_created ON tickets(account_id, product_id, created_at);
CREATE INDEX idx_tickets_duplicate_of ON tickets(duplicate_of);
CREATE INDEX idx_tickets_incident ON tickets(linked_incident_id);
CREATE INDEX idx_dq_cases_status_type ON data_quality_cases(case_status, case_type);

CREATE VIEW active_customer_accounts AS
SELECT account_id, account_name, segment, region, owner_team, created_at
FROM accounts
WHERE is_internal = 0
  AND account_status IN ('active', 'paused');

CREATE VIEW production_usage_daily AS
SELECT usage_id, account_id, product_id, activity_date, source_system,
       seats_active, api_calls, compute_hours, data_gb, is_backfill, recorded_at
FROM usage_daily
WHERE environment = 'production';

CREATE VIEW customer_support_tickets AS
SELECT ticket_id, account_id, product_id, created_at, closed_at, status,
       severity, category, customer_impact, is_duplicate, duplicate_of,
       linked_incident_id, sla_due_at
FROM tickets
WHERE category <> 'internal_test';
