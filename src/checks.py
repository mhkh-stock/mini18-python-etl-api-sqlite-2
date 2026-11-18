"""Data-quality checks for Mini #18 (run: python3 src/checks.py).

These assert STRUCTURE and INVARIANTS of a live pipeline — never
fixed prices or counts, because a re-run fetches the current
catalogue. The strong checks reconcile SQL against an independent
pure-Python recompute from the saved raw JSON: if the load corrupted
anything, or the API changed shape, these fail loudly.

The checks anchor to the run stored in the database (fetched_date
from run_meta, matched to the raw file on disk) — not to today's
date — so they verify any stored run on any later day. A buyer who
clones the repo tomorrow must see the same green run.
"""

import json
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "products.db"
RAW = ROOT / "data" / "raw"
SUMMARY = ROOT / "outputs" / "summary.md"

passed = failed = 0


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print(f"PASS: {name}")
    else:
        failed += 1
        print(f"FAIL: {name} {detail}")


def approx(a, b, tol=0.01):
    return abs(a - b) <= tol


# --- load the raw payload (ground truth) ---------------------------
raw_files = sorted(RAW.glob("products_*.json"))
check("at least one saved raw API response exists", len(raw_files) >= 1)
if not raw_files:
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1)
raw_file = raw_files[-1]
payload = json.loads(raw_file.read_text(encoding="utf-8"))
products = payload["products"]
raw_date = raw_file.stem.replace("products_", "")
check("raw payload has a non-empty products list",
      isinstance(products, list) and len(products) > 0,
      f"got {len(products)}")
check("raw payload total matches products returned",
      payload.get("total") == len(products),
      f"total={payload.get('total')} len={len(products)}")

# --- independent Python recompute from the raw JSON ----------------
py_n = len(products)
py_reviews = sum(len(p.get("reviews", [])) for p in products)
py_tags = sum(len(set(p.get("tags", []))) for p in products)
py_categories = sorted({p["category"] for p in products})
py_brands = sorted({p["brand"] for p in products if p.get("brand")})
py_stock = sum(p["stock"] for p in products)
py_value = sum(p["price"] * p["stock"] for p in products)
py_avg_price = sum(p["price"] for p in products) / py_n
py_avg_rating = sum(p["rating"] for p in products) / py_n
py_priciest = max(products, key=lambda p: p["price"])
py_cheapest = min(products, key=lambda p: p["price"])
py_by_cat = defaultdict(float)
for p in products:
    py_by_cat[p["category"]] += p["price"] * p["stock"]
py_top_cat = max(py_by_cat, key=py_by_cat.get)
py_tag_counts = Counter(t for p in products for t in set(p.get("tags", [])))
py_top_tag = py_tag_counts.most_common(1)[0][0]
py_out = sum(1 for p in products if p["stock"] == 0)
py_low = sum(1 for p in products if 0 < p["stock"] < 10)
py_by_id = {p["id"]: p for p in products}

# --- database ------------------------------------------------------
check("database exists", DB.exists())
con = sqlite3.connect(DB)
tables = {r[0] for r in con.execute(
    "SELECT name FROM sqlite_master WHERE type='table'")}
for t in ("dim_category", "dim_brand", "fact_product", "fact_review",
          "bridge_product_tag", "run_meta"):
    check(f"table {t} exists", t in tables)

# run_meta
check("run_meta has exactly one row",
      con.execute("SELECT COUNT(*) FROM run_meta").fetchone()[0] == 1)
meta = con.execute(
    "SELECT fetched_date, source_url, api_total, products_loaded, "
    "reviews_loaded, tags_loaded FROM run_meta").fetchone()
check("run_meta fetched_date matches the raw file date",
      meta[0] == raw_date, f"db={meta[0]} raw={raw_date}")
check("run_meta source names dummyjson.com", "dummyjson.com" in meta[1])
check("run_meta api_total matches raw total", meta[2] == len(products),
      f"db={meta[2]} raw={len(products)}")

# row counts reconcile with the raw payload
check("product count matches raw payload",
      con.execute("SELECT COUNT(*) FROM fact_product").fetchone()[0] == py_n)
check("review count matches raw payload",
      con.execute("SELECT COUNT(*) FROM fact_review").fetchone()[0]
      == py_reviews, f"db vs raw {py_reviews}")
check("tag count matches raw payload",
      con.execute("SELECT COUNT(*) FROM bridge_product_tag").fetchone()[0]
      == py_tags)
check("category count matches raw payload",
      con.execute("SELECT COUNT(*) FROM dim_category").fetchone()[0]
      == len(py_categories))
check("brand count matches raw payload",
      con.execute("SELECT COUNT(*) FROM dim_brand").fetchone()[0]
      == len(py_brands))
check("run_meta loaded counts match the tables",
      meta[3] == py_n and meta[4] == py_reviews and meta[5] == py_tags)
check("one fetched_date only (no mixed runs)",
      con.execute("SELECT COUNT(DISTINCT fetched_date) FROM fact_product")
      .fetchone()[0] == 1)

# nulls and ranges
check("no null titles",
      con.execute("SELECT COUNT(*) FROM fact_product WHERE title IS NULL")
      .fetchone()[0] == 0)
check("no null categories",
      con.execute("SELECT COUNT(*) FROM fact_product WHERE category IS NULL")
      .fetchone()[0] == 0)
check("no null prices or availability",
      con.execute("SELECT COUNT(*) FROM fact_product WHERE price IS NULL "
                  "OR availability IS NULL").fetchone()[0] == 0)
check("prices never negative",
      con.execute("SELECT COUNT(*) FROM fact_product WHERE price < 0")
      .fetchone()[0] == 0)
check("discounts within 0-100%",
      con.execute("SELECT COUNT(*) FROM fact_product WHERE discount_pct < 0 "
                  "OR discount_pct > 100").fetchone()[0] == 0)
check("product ratings within 0-5",
      con.execute("SELECT COUNT(*) FROM fact_product WHERE rating < 0 "
                  "OR rating > 5").fetchone()[0] == 0)
check("stock never negative",
      con.execute("SELECT COUNT(*) FROM fact_product WHERE stock < 0")
      .fetchone()[0] == 0)
check("min order quantity at least 1",
      con.execute("SELECT COUNT(*) FROM fact_product "
                  "WHERE min_order_qty < 1").fetchone()[0] == 0)
check("review ratings within 1-5",
      con.execute("SELECT COUNT(*) FROM fact_review WHERE rating < 1 "
                  "OR rating > 5").fetchone()[0] == 0)
check("no null review dates",
      con.execute("SELECT COUNT(*) FROM fact_review WHERE review_date "
                  "IS NULL").fetchone()[0] == 0)
check("review dates are YYYY-MM-DD",
      con.execute("SELECT COUNT(*) FROM fact_review "
                  "WHERE LENGTH(review_date) != 10").fetchone()[0] == 0)

# uniqueness and referential integrity
check("no duplicate product ids",
      con.execute("SELECT COUNT(*) - COUNT(DISTINCT product_id) "
                  "FROM fact_product").fetchone()[0] == 0)
check("no duplicate SKUs",
      con.execute("SELECT COUNT(*) - COUNT(DISTINCT sku) FROM fact_product "
                  "WHERE sku IS NOT NULL").fetchone()[0] == 0)
check("no duplicate product-tag pairs",
      con.execute("SELECT COUNT(*) - COUNT(DISTINCT product_id || '|' || tag) "
                  "FROM bridge_product_tag").fetchone()[0] == 0)
check("no orphan reviews (every review has a product)",
      con.execute("SELECT COUNT(*) FROM fact_review r LEFT JOIN "
                  "fact_product p ON p.product_id = r.product_id "
                  "WHERE p.product_id IS NULL").fetchone()[0] == 0)
check("no orphan tags (every tag has a product)",
      con.execute("SELECT COUNT(*) FROM bridge_product_tag t LEFT JOIN "
                  "fact_product p ON p.product_id = t.product_id "
                  "WHERE p.product_id IS NULL").fetchone()[0] == 0)
check("no orphan products (category in dim_category)",
      con.execute("SELECT COUNT(*) FROM fact_product p LEFT JOIN "
                  "dim_category c ON c.category = p.category "
                  "WHERE c.category IS NULL").fetchone()[0] == 0)
check("no orphan brands (brand in dim_brand or null)",
      con.execute("SELECT COUNT(*) FROM fact_product p LEFT JOIN "
                  "dim_brand b ON b.brand = p.brand "
                  "WHERE p.brand IS NOT NULL AND b.brand IS NULL")
      .fetchone()[0] == 0)
check("PRAGMA foreign_key_check is clean",
      con.execute("PRAGMA foreign_key_check").fetchall() == [])

# per-product detail matches the raw payload
db_reviews = dict(con.execute(
    "SELECT product_id, COUNT(*) FROM fact_review GROUP BY product_id"))
py_reviews_by_id = {p["id"]: len(p.get("reviews", [])) for p in products}
check("review count per product matches raw for every product",
      all(db_reviews.get(pid, 0) == n
          for pid, n in py_reviews_by_id.items()))
db_tags = dict(con.execute(
    "SELECT product_id, COUNT(*) FROM bridge_product_tag "
    "GROUP BY product_id"))
py_tags_by_id = {p["id"]: len(set(p.get("tags", []))) for p in products}
check("tag count per product matches raw for every product",
      all(db_tags.get(pid, 0) == n
          for pid, n in py_tags_by_id.items()))
db_rows = {r[0]: r for r in con.execute(
    "SELECT product_id, title, price, rating, stock, sku "
    "FROM fact_product")}
check("every product's price, rating, stock and SKU match the raw JSON",
      all(db_rows[pid][2] == p["price"]
          and db_rows[pid][3] == p["rating"]
          and db_rows[pid][4] == p["stock"]
          and db_rows[pid][5] == p.get("sku")
          for pid, p in py_by_id.items()))

# SQL vs independent Python recompute
db_value = con.execute(
    "SELECT SUM(price * stock) FROM fact_product").fetchone()[0]
check("total stock value: SQL matches Python recompute",
      approx(db_value, py_value), f"sql={db_value} py={py_value}")
db_stock = con.execute("SELECT SUM(stock) FROM fact_product").fetchone()[0]
check("total stock: SQL matches Python recompute",
      db_stock == py_stock, f"sql={db_stock} py={py_stock}")
db_avg_price = con.execute(
    "SELECT AVG(price) FROM fact_product").fetchone()[0]
check("average price: SQL matches Python recompute",
      approx(db_avg_price, py_avg_price),
      f"sql={db_avg_price} py={py_avg_price}")
db_avg_rating = con.execute(
    "SELECT AVG(rating) FROM fact_product").fetchone()[0]
check("average rating: SQL matches Python recompute",
      approx(db_avg_rating, py_avg_rating),
      f"sql={db_avg_rating} py={py_avg_rating}")
db_priciest = con.execute(
    "SELECT product_id FROM fact_product ORDER BY price DESC LIMIT 1"
    ).fetchone()[0]
check("most expensive product: SQL matches Python recompute",
      db_priciest == py_priciest["id"])
db_cheapest = con.execute(
    "SELECT product_id FROM fact_product ORDER BY price ASC LIMIT 1"
    ).fetchone()[0]
check("cheapest product: SQL matches Python recompute",
      db_cheapest == py_cheapest["id"])
db_top_cat = con.execute(
    "SELECT category FROM fact_product GROUP BY category "
    "ORDER BY SUM(price * stock) DESC LIMIT 1").fetchone()[0]
check("top category by stock value: SQL matches Python recompute",
      db_top_cat == py_top_cat, f"sql={db_top_cat} py={py_top_cat}")
db_top_tag = con.execute(
    "SELECT tag FROM bridge_product_tag GROUP BY tag "
    "ORDER BY COUNT(*) DESC, tag ASC LIMIT 1").fetchone()[0]
check("most common tag: SQL matches Python recompute",
      db_top_tag == py_top_tag, f"sql={db_top_tag} py={py_top_tag}")
db_out = con.execute(
    "SELECT COUNT(*) FROM fact_product WHERE stock = 0").fetchone()[0]
check("out-of-stock count: SQL matches Python recompute",
      db_out == py_out, f"sql={db_out} py={py_out}")
db_low = con.execute(
    "SELECT COUNT(*) FROM fact_product WHERE stock > 0 AND stock < 10"
    ).fetchone()[0]
check("low-stock (1-9 units) count: SQL matches Python recompute",
      db_low == py_low, f"sql={db_low} py={py_low}")

# the analysis queries' own invariants
check("rating buckets (Q7) sum to the product count",
      con.execute(
          "SELECT SUM(cnt) FROM (SELECT COUNT(*) AS cnt FROM fact_product "
          "GROUP BY CASE WHEN rating < 3 THEN 'a' WHEN rating < 4 THEN 'b' "
          "WHEN rating < 4.5 THEN 'c' ELSE 'd' END)").fetchone()[0] == py_n)
check("price bands (Q8) sum to the product count",
      con.execute(
          "SELECT SUM(cnt) FROM (SELECT COUNT(*) AS cnt FROM fact_product "
          "GROUP BY CASE WHEN price < 10 THEN 'a' WHEN price < 50 THEN 'b' "
          "WHEN price < 200 THEN 'c' WHEN price < 1000 THEN 'd' "
          "ELSE 'e' END)").fetchone()[0] == py_n)
check("every category has at least one product",
      con.execute(
          "SELECT COUNT(*) FROM dim_category c WHERE NOT EXISTS "
          "(SELECT 1 FROM fact_product p WHERE p.category = c.category)")
      .fetchone()[0] == 0)

# run summary
check("run summary exists and names this run's date",
      SUMMARY.exists() and f"({raw_date})" in SUMMARY.read_text())
check("run summary states the product count",
      SUMMARY.exists() and str(py_n) in SUMMARY.read_text())
con.close()

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
