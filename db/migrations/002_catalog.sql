-- =========================================================================
-- 002: Product catalog (owner: catalog service, services/catalog)
-- Single source of truth for the sellable SKUs. unit_price and family are
-- internal (used by offer management); the catalog API never discloses them.
-- =========================================================================

CREATE TABLE IF NOT EXISTS products (
    product_id    TEXT PRIMARY KEY,
    product_name  TEXT NOT NULL,
    category      TEXT NOT NULL,
    technology    TEXT NOT NULL,
    speeds        JSONB NOT NULL DEFAULT '{}'::jsonb,
    description   TEXT NOT NULL DEFAULT '',
    features      JSONB NOT NULL DEFAULT '[]'::jsonb,
    available     BOOLEAN NOT NULL DEFAULT TRUE,
    unit_price    NUMERIC(10, 2),
    family        TEXT,
    sort_order    INTEGER NOT NULL DEFAULT 0,
    CONSTRAINT products_id_upper CHECK (product_id = upper(product_id))
);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(lower(category));
CREATE INDEX IF NOT EXISTS idx_products_family   ON products(family);
