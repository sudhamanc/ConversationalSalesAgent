-- =========================================================================
-- 004: Network coverage (owner: serviceability service)
-- One row per ZIP code. Seeded from the legacy MOCK_COVERAGE_DATA by
-- scripts/export_coverage_seed.py (db/seed/003_coverage.sql).
-- Serviceable rows always carry an infrastructure object; sparse legacy
-- records are filled from the technology defaults at export time.
-- =========================================================================

CREATE TABLE IF NOT EXISTS coverage_zones (
    zip_code                     TEXT PRIMARY KEY CHECK (zip_code ~ '^[0-9]{5}$'),
    city                         TEXT,
    state                        TEXT CHECK (state IS NULL OR state ~ '^[A-Z]{2}$'),
    serviceable                  BOOLEAN NOT NULL DEFAULT FALSE,
    service_zone                 TEXT,
    infrastructure_type          TEXT,
    infrastructure               JSONB,
    max_speed_mbps               INTEGER,
    estimated_install_days       INTEGER,
    available_products           JSONB NOT NULL DEFAULT '[]'::jsonb,
    available_product_categories JSONB NOT NULL DEFAULT '[]'::jsonb,
    reason                       TEXT,
    CONSTRAINT coverage_serviceable_has_infrastructure
        CHECK (NOT serviceable OR (infrastructure IS NOT NULL AND infrastructure_type IS NOT NULL))
);
CREATE INDEX IF NOT EXISTS idx_coverage_zones_zone ON coverage_zones(service_zone);
