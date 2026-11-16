-- =========================================================================
-- 006: Stored serviceability checks (owner: serviceability_agent).
-- A returning customer's last check is reused instead of re-running it
-- (spec: sales-data-store "Serviceability checks are stored").
-- =========================================================================
CREATE TABLE IF NOT EXISTS serviceability_checks (
    id              BIGSERIAL PRIMARY KEY,
    customer_id     TEXT,
    street          TEXT,
    city            TEXT,
    state           TEXT,
    zip_code        TEXT NOT NULL,
    is_serviceable  BOOLEAN NOT NULL,
    result_json     TEXT NOT NULL,
    checked_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_svc_checks_customer ON serviceability_checks(customer_id, checked_at DESC);
CREATE INDEX IF NOT EXISTS idx_svc_checks_zip ON serviceability_checks(zip_code);
