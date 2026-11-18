-- Mini #18 — ETL target schema (SQLite).
-- Star-lite schema for the DummyJSON product catalogue.
-- One row per product in fact_product; reviews and tags are their
-- own tables so the joins are real. fetched_date stamps the run so
-- a re-fetch never silently mixes with an older load; this load
-- keeps one run only (the loader rebuilds the DB), which the checks
-- prove. run_meta records the fetch so the load is auditable.

CREATE TABLE dim_category (
    category  TEXT PRIMARY KEY
);

CREATE TABLE dim_brand (
    brand  TEXT PRIMARY KEY
);

CREATE TABLE fact_product (
    product_id        INTEGER PRIMARY KEY,
    title             TEXT NOT NULL,
    category          TEXT NOT NULL REFERENCES dim_category(category),
    brand             TEXT REFERENCES dim_brand(brand),
    price             REAL NOT NULL CHECK (price >= 0),
    discount_pct      REAL NOT NULL CHECK (discount_pct >= 0 AND discount_pct <= 100),
    rating            REAL NOT NULL CHECK (rating >= 0 AND rating <= 5),
    stock             INTEGER NOT NULL CHECK (stock >= 0),
    min_order_qty     INTEGER NOT NULL CHECK (min_order_qty >= 1),
    weight_kg         REAL CHECK (weight_kg IS NULL OR weight_kg > 0),
    sku               TEXT UNIQUE,
    availability      TEXT NOT NULL,
    fetched_date      TEXT NOT NULL
);

CREATE TABLE fact_review (
    review_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id    INTEGER NOT NULL REFERENCES fact_product(product_id),
    reviewer      TEXT NOT NULL,
    rating        INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    comment       TEXT,
    review_date   TEXT NOT NULL
);

CREATE TABLE bridge_product_tag (
    product_id  INTEGER NOT NULL REFERENCES fact_product(product_id),
    tag         TEXT NOT NULL,
    PRIMARY KEY (product_id, tag)
);

CREATE TABLE run_meta (
    fetched_date    TEXT PRIMARY KEY,
    source_url      TEXT NOT NULL,
    api_total       INTEGER NOT NULL,
    products_loaded INTEGER NOT NULL,
    reviews_loaded  INTEGER NOT NULL,
    tags_loaded     INTEGER NOT NULL
);

CREATE INDEX idx_product_category ON fact_product(category);
CREATE INDEX idx_product_brand ON fact_product(brand);
CREATE INDEX idx_review_product ON fact_review(product_id);
CREATE INDEX idx_tag_tag ON bridge_product_tag(tag);
