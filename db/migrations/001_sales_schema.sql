-- =========================================================================
-- 001: Sales domain schema (PostgreSQL 16)
-- Ported from the SQLite unified schema (SuperAgent/super_agent/utils/database.py).
-- Timestamps stay ISO-8601 TEXT for compatibility with existing tool logic.
-- =========================================================================

-- ----------------------------------------------------------------------
-- Discovery domain (owner: discovery_agent)
-- ----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS accounts (
    "Company Name"         TEXT PRIMARY KEY,
    "Parent Company"       TEXT,
    "Industry"             TEXT,
    "Territory/Region"     TEXT,
    "Street"               TEXT,
    "City"                 TEXT,
    "State"                TEXT,
    zip_code               TEXT NOT NULL,
    address_line2          TEXT,
    "Website"              TEXT,
    "Existing Customer"    TEXT,
    "Current Products"     TEXT,
    "Products of Interest" TEXT,
    customer_id            TEXT,
    created_at             TEXT,
    updated_at             TEXT
);
CREATE INDEX IF NOT EXISTS idx_accounts_customer_id ON accounts(customer_id);

CREATE TABLE IF NOT EXISTS contacts (
    "Company Name"            TEXT,
    "Name"                    TEXT,
    "Title"                   TEXT,
    "Role in Decision Making" TEXT,
    "Email"                   TEXT,
    "Phone"                   TEXT,
    "Notes"                   TEXT,
    created_at                TEXT
);
CREATE INDEX IF NOT EXISTS idx_contacts_company ON contacts("Company Name");

CREATE TABLE IF NOT EXISTS spend (
    "Company Name"           TEXT,
    "Estimated Annual Spend" BIGINT,
    "Digital"                BIGINT,
    "Programmatic"           BIGINT,
    "TV"                     BIGINT,
    "Audio"                  BIGINT,
    "OOH"                    BIGINT,
    "Search"                 BIGINT,
    "Social"                 BIGINT,
    "Primary Agency"         TEXT
);
CREATE INDEX IF NOT EXISTS idx_spend_company ON spend("Company Name");

CREATE TABLE IF NOT EXISTS opportunities (
    "Company Name"         TEXT,
    "Opportunity Name"     TEXT,
    "Stage"                TEXT,
    "Total MRC (Est)"      BIGINT,
    "Budget"               TEXT,
    "Authority"            TEXT,
    "Need"                 TEXT,
    "Timeline (days)"      BIGINT,
    "Target Close Date"    TEXT,
    "Next Step"            TEXT,
    "BANT_Budget_Score"    BIGINT,
    "BANT_Authority_Score" BIGINT,
    "BANT_Need_Score"      BIGINT,
    "BANT_Timing_Score"    BIGINT,
    "BANT_Weighted_0to3"   DOUBLE PRECISION,
    "BANT_Score_0to100"    DOUBLE PRECISION,
    "BANT_Priority_Bucket" TEXT,
    "BANT_Data_Gaps"       TEXT,
    created_at             TEXT,
    updated_at             TEXT
);
CREATE INDEX IF NOT EXISTS idx_opportunities_company ON opportunities("Company Name");

CREATE TABLE IF NOT EXISTS insights (
    "Company Name"            TEXT,
    "Buying Signals"          TEXT,
    "Pain Points"             TEXT,
    "Recommended Positioning" TEXT
);
CREATE INDEX IF NOT EXISTS idx_insights_company ON insights("Company Name");

CREATE TABLE IF NOT EXISTS actions (
    "Company Name"          TEXT,
    "Owner"                 TEXT,
    "Priority"              TEXT,
    "Initial Outreach Date" TEXT,
    "Follow-Up Cadence"     TEXT
);
CREATE INDEX IF NOT EXISTS idx_actions_company ON actions("Company Name");

-- ----------------------------------------------------------------------
-- Offer domain (owner: offer_management_agent)
-- ----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS quotes (
    offer_id        TEXT PRIMARY KEY,
    customer_id     TEXT,
    company_name    TEXT,
    items_json      TEXT NOT NULL,
    term_months     INTEGER NOT NULL DEFAULT 12,
    bant_score      DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    subtotal        DOUBLE PRECISION NOT NULL,
    total_discount  DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    total_price     DOUBLE PRECISION NOT NULL,
    monthly_total   DOUBLE PRECISION NOT NULL,
    yearly_total    DOUBLE PRECISION NOT NULL,
    full_quote_json TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'active',
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    expires_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_quotes_customer ON quotes(customer_id);
CREATE INDEX IF NOT EXISTS idx_quotes_company  ON quotes(company_name);
CREATE INDEX IF NOT EXISTS idx_quotes_status   ON quotes(status);

-- ----------------------------------------------------------------------
-- Order domain (owner: order_agent)
-- ----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS carts (
    cart_id       TEXT PRIMARY KEY,
    customer_id   TEXT NOT NULL,
    total_amount  DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    status        TEXT NOT NULL DEFAULT 'active',
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL,
    expires_at    TEXT
);
CREATE INDEX IF NOT EXISTS idx_carts_customer ON carts(customer_id);
CREATE INDEX IF NOT EXISTS idx_carts_status   ON carts(status);

CREATE TABLE IF NOT EXISTS cart_items (
    id            BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    cart_id       TEXT NOT NULL REFERENCES carts(cart_id) ON DELETE CASCADE,
    service_type  TEXT NOT NULL,
    price         DOUBLE PRECISION NOT NULL,
    quantity      INTEGER NOT NULL DEFAULT 1,
    subtotal      DOUBLE PRECISION NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cart_items_cart ON cart_items(cart_id);

CREATE TABLE IF NOT EXISTS orders (
    order_id        TEXT PRIMARY KEY,
    customer_name   TEXT NOT NULL,
    customer_id     TEXT NOT NULL,
    service_address TEXT NOT NULL,
    contact_phone   TEXT NOT NULL,
    contact_email   TEXT,
    offer_id        TEXT REFERENCES quotes(offer_id),
    status          TEXT NOT NULL DEFAULT 'draft',
    total_amount    DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    expires_at      TEXT
);
CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_offer    ON orders(offer_id);
CREATE INDEX IF NOT EXISTS idx_orders_status   ON orders(status);

CREATE TABLE IF NOT EXISTS order_items (
    id            BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    order_id      TEXT NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
    service_type  TEXT NOT NULL,
    price         DOUBLE PRECISION NOT NULL,
    quantity      INTEGER NOT NULL DEFAULT 1,
    subtotal      DOUBLE PRECISION NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id);

-- ----------------------------------------------------------------------
-- Payment domain (owner: payment_agent)
-- ----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS payments (
    payment_id       TEXT PRIMARY KEY,
    order_id         TEXT NOT NULL REFERENCES orders(order_id),
    customer_id      TEXT NOT NULL,
    transaction_id   TEXT,
    idempotency_key  TEXT UNIQUE,
    amount           DOUBLE PRECISION NOT NULL,
    currency         TEXT NOT NULL DEFAULT 'USD',
    status           TEXT NOT NULL DEFAULT 'initiated',
    credit_score     INTEGER,
    payment_method   TEXT,
    failure_reason   TEXT,
    attempt_count    INTEGER NOT NULL DEFAULT 1,
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL,
    expires_at       TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_payments_order ON payments(order_id)
    WHERE status IN ('processing', 'completed');
CREATE INDEX IF NOT EXISTS idx_payments_order    ON payments(order_id);
CREATE INDEX IF NOT EXISTS idx_payments_customer ON payments(customer_id);
CREATE INDEX IF NOT EXISTS idx_payments_status   ON payments(status);

CREATE TABLE IF NOT EXISTS payment_events (
    event_id    TEXT PRIMARY KEY,
    payment_id  TEXT NOT NULL REFERENCES payments(payment_id),
    from_status TEXT,
    to_status   TEXT NOT NULL,
    actor       TEXT NOT NULL DEFAULT 'payment_agent',
    note        TEXT,
    created_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_payment_events_payment ON payment_events(payment_id);

CREATE TABLE IF NOT EXISTS payment_rate_limit (
    customer_id   TEXT NOT NULL,
    window_start  TEXT NOT NULL,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (customer_id, window_start)
);

CREATE TABLE IF NOT EXISTS customer_payment_methods (
    method_id     TEXT PRIMARY KEY,
    customer_id   TEXT NOT NULL,
    payment_type  TEXT NOT NULL,
    token         TEXT NOT NULL UNIQUE,
    card_brand    TEXT,
    last_four     TEXT,
    account_type  TEXT,
    is_default    INTEGER NOT NULL DEFAULT 0,
    nickname      TEXT,
    token_expiry  TEXT,
    status        TEXT NOT NULL DEFAULT 'active',
    created_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cpm_customer ON customer_payment_methods(customer_id);

-- ----------------------------------------------------------------------
-- Fulfillment + customer domain (owner: service_fulfillment_agent)
-- ----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fulfillments (
    fulfillment_id   TEXT PRIMARY KEY,
    order_id         TEXT NOT NULL REFERENCES orders(order_id),
    customer_id      TEXT NOT NULL,
    dispatch_id      TEXT,
    activation_id    TEXT,
    circuit_id       TEXT,
    account_id       TEXT,
    appointment_date TEXT,
    status           TEXT NOT NULL DEFAULT 'scheduled',
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_fulfillments_order    ON fulfillments(order_id);
CREATE INDEX IF NOT EXISTS idx_fulfillments_customer ON fulfillments(customer_id);
CREATE INDEX IF NOT EXISTS idx_fulfillments_status   ON fulfillments(status);

CREATE TABLE IF NOT EXISTS customer_master (
    customer_id         TEXT PRIMARY KEY,
    company_name        TEXT NOT NULL,
    street              TEXT NOT NULL,
    city                TEXT NOT NULL,
    state               TEXT NOT NULL,
    zip_code            TEXT NOT NULL,
    contact_name        TEXT,
    contact_email       TEXT,
    contact_phone       TEXT,
    first_order_id      TEXT REFERENCES orders(order_id),
    circuit_id          TEXT,
    account_id          TEXT,
    contracted_products TEXT,
    monthly_revenue     DOUBLE PRECISION,
    activated_at        TEXT NOT NULL,
    created_at          TEXT NOT NULL,
    updated_at          TEXT NOT NULL
);

-- ----------------------------------------------------------------------
-- Communication domain (owner: customer_communication_agent)
-- notifications doubles as the transactional outbox: producers insert
-- status='pending'; the communication service dispatches them.
-- ----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS notifications (
    notification_id   TEXT PRIMARY KEY,
    notification_type TEXT NOT NULL,
    recipient_email   TEXT,
    recipient_phone   TEXT,
    subject           TEXT,
    message           TEXT,
    metadata_json     TEXT,
    customer_id       TEXT,
    order_id          TEXT,
    status            TEXT NOT NULL DEFAULT 'pending',
    channels_json     TEXT NOT NULL DEFAULT '[]',
    attempts          INTEGER NOT NULL DEFAULT 0,
    created_at        TEXT NOT NULL,
    updated_at        TEXT,
    sent_at           TEXT,
    error             TEXT
);
CREATE INDEX IF NOT EXISTS idx_notif_email    ON notifications(recipient_email);
CREATE INDEX IF NOT EXISTS idx_notif_type     ON notifications(notification_type);
CREATE INDEX IF NOT EXISTS idx_notif_customer ON notifications(customer_id);
CREATE INDEX IF NOT EXISTS idx_notif_order    ON notifications(order_id);
CREATE INDEX IF NOT EXISTS idx_notif_pending  ON notifications(created_at) WHERE status = 'pending';

CREATE TABLE IF NOT EXISTS dedup_cache (
    dedup_key  TEXT PRIMARY KEY,
    sent_at    TEXT NOT NULL
);
