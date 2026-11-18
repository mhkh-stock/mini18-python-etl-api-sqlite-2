"""Mini #18 — Python ETL #2: DummyJSON product catalogue -> SQLite.

Extract: the full product catalogue from the DummyJSON API
(free, no key, no sign-up): one GET returns every product.
Transform: flatten each product into a tidy row, its nested reviews
into fact_review, and its tags into bridge_product_tag.
Load: SQLite star-lite schema (fact_product + dim_category +
dim_brand + fact_review + bridge_product_tag) with data-quality
checks run on every load.

This is a LIVE pipeline: re-running fetches the current catalogue,
so the numbers can change if DummyJSON updates its data. The checks
assert structure and invariants (row counts, ranges, no duplicates,
SQL-vs-Python reconciliation) — never fixed prices or counts. The
raw API response is saved under data/raw/ so any run can be replayed
offline with --rebuild.

Run:  python3 src/etl.py             (fetch live + load)
      python3 src/etl.py --rebuild  (reload from saved raw JSON, no API call)
      python3 src/checks.py         (verify the loaded database)
      python3 src/run_queries.py    (run the 10 analysis queries)
"""

import argparse
import json
import sqlite3
import sys
import time
from datetime import date
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
DB = ROOT / "data" / "products.db"
SUMMARY = ROOT / "outputs" / "summary.md"

API = "https://dummyjson.com/products"
API_PARAMS = {"limit": 0}  # limit=0 returns the whole catalogue in one call
REQUIRED_FIELDS = ("id", "title", "category", "price", "rating",
                   "stock", "discountPercentage", "availabilityStatus")


def fetch():
    """One API call with retries; returns the parsed JSON."""
    last_err = None
    for attempt in (1, 2, 3):
        try:
            r = requests.get(API, params=API_PARAMS, timeout=30)
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            last_err = e
            time.sleep(2 * attempt)
    raise RuntimeError(f"DummyJSON failed after 3 attempts: {last_err}")


def validate(payload):
    """Fail loudly if the API shape is not what we expect."""
    if not isinstance(payload, dict) or "products" not in payload:
        raise ValueError("payload has no 'products' key")
    products = payload["products"]
    if not isinstance(products, list) or not products:
        raise ValueError("payload 'products' is empty or not a list")
    if "total" in payload and payload["total"] != len(products):
        raise ValueError(
            f"API total {payload['total']} != products returned "
            f"{len(products)}")
    ids = [p.get("id") for p in products]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate product ids in payload")
    for p in products:
        missing = [f for f in REQUIRED_FIELDS if f not in p or p[f] is None]
        if missing:
            raise ValueError(f"product {p.get('id')}: missing {missing}")
        if not isinstance(p.get("reviews", []), list):
            raise ValueError(f"product {p['id']}: 'reviews' is not a list")
        if not isinstance(p.get("tags", []), list):
            raise ValueError(f"product {p['id']}: 'tags' is not a list")
    return products


def load(products, fetched_date, source_url, api_total):
    """Rebuild the database from a validated product list."""
    if DB.exists():
        DB.unlink()
    con = sqlite3.connect(DB)
    con.executescript((ROOT / "sql" / "schema.sql").read_text())

    categories = sorted({p["category"] for p in products})
    brands = sorted({p["brand"] for p in products if p.get("brand")})
    con.executemany("INSERT INTO dim_category VALUES (?)",
                    [(c,) for c in categories])
    con.executemany("INSERT INTO dim_brand VALUES (?)",
                    [(b,) for b in brands])

    product_rows = [{
        "product_id": p["id"],
        "title": p["title"],
        "category": p["category"],
        "brand": p.get("brand"),
        "price": p["price"],
        "discount_pct": p["discountPercentage"],
        "rating": p["rating"],
        "stock": p["stock"],
        "min_order_qty": p.get("minimumOrderQuantity", 1),
        "weight_kg": p.get("weight"),
        "sku": p.get("sku"),
        "availability": p["availabilityStatus"],
        "fetched_date": fetched_date,
    } for p in products]
    con.executemany(
        "INSERT INTO fact_product VALUES "
        "(:product_id, :title, :category, :brand, :price, :discount_pct, "
        ":rating, :stock, :min_order_qty, :weight_kg, :sku, :availability, "
        ":fetched_date)", product_rows)

    review_rows = []
    for p in products:
        for r in p.get("reviews", []):
            review_rows.append((
                p["id"], r.get("reviewerName", "Anonymous"),
                r["rating"], r.get("comment"), r["date"][:10]))
    con.executemany(
        "INSERT INTO fact_review "
        "(product_id, reviewer, rating, comment, review_date) "
        "VALUES (?, ?, ?, ?, ?)", review_rows)

    tag_rows = []
    for p in products:
        for t in p.get("tags", []):
            tag_rows.append((p["id"], t))
    con.executemany("INSERT OR IGNORE INTO bridge_product_tag VALUES (?, ?)",
                    tag_rows)

    con.execute(
        "INSERT INTO run_meta VALUES (?, ?, ?, ?, ?, ?)",
        (fetched_date, source_url, api_total, len(products),
         len(review_rows), len(tag_rows)))
    con.commit()
    return con, len(review_rows), len(tag_rows)


def write_summary(con, fetched_date, n_products, n_reviews, n_tags):
    """Headline numbers for this run, from the loaded database."""
    top_cat = con.execute(
        "SELECT category, ROUND(SUM(price * stock), 2) FROM fact_product "
        "GROUP BY category ORDER BY 2 DESC LIMIT 1").fetchone()
    priciest = con.execute(
        "SELECT title, price FROM fact_product ORDER BY price DESC "
        "LIMIT 1").fetchone()
    best = con.execute(
        "SELECT title, rating FROM fact_product ORDER BY rating DESC, "
        "stock DESC LIMIT 1").fetchone()
    total_value = con.execute(
        "SELECT ROUND(SUM(price * stock), 2) FROM fact_product").fetchone()[0]
    avg_price = con.execute(
        "SELECT ROUND(AVG(price), 2) FROM fact_product").fetchone()[0]
    out = (
        f"# Mini #18 — Product catalogue ETL run ({fetched_date})\n\n"
        f"Full DummyJSON product catalogue, fetched live and loaded into "
        f"`data/products.db`.\n\n"
        f"- Products loaded: **{n_products}**\n"
        f"- Reviews loaded: **{n_reviews}**\n"
        f"- Tags loaded: **{n_tags}**\n"
        f"- Total stock value (price x stock): **${total_value:,.2f}**\n"
        f"- Average price: **${avg_price:,.2f}**\n"
        f"- Biggest category by stock value: **{top_cat[0]}**, "
        f"${top_cat[1]:,.2f}\n"
        f"- Most expensive product: **{priciest[0]}**, ${priciest[1]:,.2f}\n"
        f"- Highest-rated product: **{best[0]}**, {best[1]:.2f} / 5\n\n"
        f"Re-run any time: `python3 src/etl.py` fetches the current "
        f"catalogue; `python3 src/etl.py --rebuild` reloads from the "
        f"saved raw JSON without an API call; `python3 src/checks.py` "
        f"verifies the load.\n")
    (ROOT / "outputs").mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text(out, encoding="utf-8")
    print(f"loaded {n_products} products, {n_reviews} reviews, "
          f"{n_tags} tags for {fetched_date}")
    print(f"stock value: ${total_value:,.2f} | avg price: ${avg_price:,.2f}")
    print(f"top category: {top_cat[0]} (${top_cat[1]:,.2f}) | "
          f"priciest: {priciest[0]} (${priciest[1]:,.2f})")


def latest_raw_file():
    files = sorted(RAW.glob("products_*.json"))
    return files[-1] if files else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rebuild", action="store_true",
                        help="reload from saved raw JSON, no API call")
    parser.add_argument("--raw", type=Path, default=None,
                        help="raw JSON file to rebuild from")
    args = parser.parse_args()

    RAW.mkdir(parents=True, exist_ok=True)
    (ROOT / "outputs").mkdir(parents=True, exist_ok=True)
    fetched_date = date.today().isoformat()

    if args.rebuild:
        raw_file = args.raw or latest_raw_file()
        if raw_file is None:
            print("no saved raw JSON found — run without --rebuild first",
                  file=sys.stderr)
            sys.exit(1)
        print(f"rebuilding from {raw_file} (no API call)")
        payload = json.loads(raw_file.read_text(encoding="utf-8"))
        fetched_date = raw_file.stem.replace("products_", "")
        source_url = API
    else:
        payload = fetch()
        raw_file = RAW / f"products_{fetched_date}.json"
        raw_file.write_text(json.dumps(payload, indent=2),
                            encoding="utf-8")
        print(f"saved raw response to {raw_file}")
        source_url = API + "?limit=0"

    products = validate(payload)
    api_total = payload.get("total", len(products))
    con, n_reviews, n_tags = load(products, fetched_date, source_url,
                                  api_total)
    write_summary(con, fetched_date, len(products), n_reviews, n_tags)
    con.close()


if __name__ == "__main__":
    main()
