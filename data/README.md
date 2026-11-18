# Data

## Source

**DummyJSON product catalogue** — `https://dummyjson.com/products?limit=0`
(free, no key, no sign-up). One GET returns the whole catalogue:
products with price, discount, rating, stock, brand, tags and
customer reviews.

> **This is public reference data, not client data.** DummyJSON is a
> demo API whose catalogue is made-up sample data for testing — it is
> not a real store's sales data, and nothing here is presented as
> real client work.

## What is saved here

| File | What it is |
|---|---|
| `raw/products_YYYY-MM-DD.json` | The exact API response for that run — replayable offline |
| `products.db` | The loaded SQLite database (rebuilt by every run; **not uploaded** — rebuildable from the scripts + raw JSON) |

## This run

- Fetched: **2026-11-18**
- Products: **194** (API `total` = 194)
- Reviews: **582** (3 per product)
- Tags: **see `run_meta` in the database**
- Categories: **24**, brands: **see `dim_brand`**

## Schema

- `dim_category` — one row per category (24)
- `dim_brand` — one row per brand
- `fact_product` — one row per product (PK `product_id`): title,
  category, brand, price, discount %, rating, stock, minimum order
  quantity, weight, SKU, availability, `fetched_date`
- `fact_review` — one row per customer review (PK auto-increment):
  product, reviewer, rating 1–5, comment, review date
- `bridge_product_tag` — one row per product–tag pair
- `run_meta` — one row per run: fetch date, source URL, API total,
  products / reviews / tags loaded

## Replay

No API call needed — rebuild the database from the saved raw JSON:

```
python3 src/etl.py --rebuild
```

A re-fetch on a later day may return a different catalogue if
DummyJSON updates its data; the checks assert structure and
invariants, never fixed prices or counts, so a changed catalogue
still verifies clean as long as the shape holds.
