# Mini #18 — Python ETL #2: Product API → SQLite

**What it is:** a small, complete ETL pipeline. It fetches the full
product catalogue (194 products) from the DummyJSON API (free, no
key, no sign-up), flattens the nested JSON into tidy tables, loads
them into SQLite, and runs data-quality checks on every load.

**Why this mini exists:** Mini #7 proved live-data loading with a
weather API (6 cities × 7 days). This one proves the same skill on
a different shape of data — a **product catalogue**: nested reviews
and tags, a star-lite schema with real joins, and analysis that
answers catalogue questions a store owner would actually ask
("where is my stock value sitting?", "where are the biggest
discounts?", "do the reviews agree with the listed rating?").

## Business question it answers

> "Can I pull a live product catalogue into a database I can query —
> and how would I know the moment the load goes wrong?"

## What is inside

| File | What it does |
|---|---|
| `src/etl.py` | Extract (DummyJSON API, 3 retries) → Validate → Load (SQLite). `--rebuild` reloads from the saved raw JSON with no API call |
| `src/run_queries.py` | Rebuilds the DB from saved raw JSON (or `--live` to fetch first), runs all 10 analysis queries, writes one CSV per query + `outputs/findings.md` |
| `src/checks.py` | Data-quality checks as code — **58 checks, all passing** |
| `sql/schema.sql` | `fact_product` + `dim_category` + `dim_brand` + `fact_review` + `bridge_product_tag` + `run_meta` |
| `sql/analysis_queries.sql` | 10 numbered questions over the loaded data |
| `data/raw/products_2026-11-18.json` | The raw API response for this run — replayable offline |
| `data/products.db` | The loaded database (rebuilt by every run; **not uploaded** — rebuildable from the scripts + raw JSON) |
| `outputs/` | One CSV per query + `summary.md` + `findings.md` |
| `.gitignore` | Keeps the rebuilt `data/products.db`, bytecode and local venvs out of the repo |

## Verified numbers (this run, fetched 2026-11-18)

| Headline | Value |
|---|---|
| Products loaded | **194** (API `total` = 194) |
| Categories / brands | **24 / 63** |
| Reviews loaded | **582** (3 per product) |
| Tags loaded | **364** |
| Total stock value (price × stock) | **$17,172,492.31** |
| Average price | **$1,570.10** |
| Average rating | **3.80 / 5** |
| Average discount | **10.56%** |
| Out-of-stock products | **4** |
| Biggest category by stock value | **vehicle — $10,707,996.59** (5 products, avg price $31,199.99) |
| Most expensive product | **Durango SXT RWD — $36,999.99** |
| Highest-rated product | **Amazon Echo Plus — 4.99 / 5** |
| Deepest single discount | **Tennis Racket — 19.61% off** |
| Cheapest product | **Lemon — $0.79** |
| Most common tag | **"kitchen tools" — 19 products** |

### Findings worth noting

- **Vehicles dominate the stock value**: 5 vehicles hold 62% of the
  catalogue's $17.2M stock value; the next category (men's watches)
  holds $2.7M.
- **Pricier does not mean better rated.** The $50–$199 band averages
  4.07/5 — the highest of any price band — while the $1,000+ band
  averages only 3.60/5, the lowest.
- **Ratings skew middling**: 40.2% of products sit at 3.0–3.9, only
  22.7% reach 4.5 or above.
- **Discounts are widest in skin-care** (16.09% average) and
  narrowest in sunglasses (4.72% average).
- **Reviews often disagree with listed ratings.** The biggest gap
  is Dress Pea: listed 4.88/5 but its 3 reviews average 2.33
  (−2.55). Seven of the ten biggest gaps are products listed near
  5 stars whose reviews average under 3 — the catalogue rating
  should not be trusted on its own.

## How to run it

1. `pip install -r requirements.txt`
2. `python3 src/etl.py` — fetches the catalogue live and loads the database.
3. `python3 src/checks.py` — 58 checks, all passing.
4. `python3 src/run_queries.py` — runs the 10 analysis queries, writes
   `outputs/*.csv` + `outputs/findings.md`.
5. Offline replay: `python3 src/etl.py --rebuild` — reloads from the
   saved raw JSON with no API call.

## What the checks prove (invariants, not fixed values)

A live pipeline cannot assert fixed prices — the catalogue can
change. So the checks assert what must *always* be true: product /
review / tag counts match the raw payload exactly, no null titles or
prices, prices ≥ 0, discounts 0–100%, ratings 0–5 (products) and
1–5 (reviews), stock ≥ 0, no duplicate ids or SKUs, no orphan
reviews / tags / products, `PRAGMA foreign_key_check` clean — and
the strong check: **SQL totals reconcile against an independent
pure-Python recompute from the raw JSON** (total stock value, total
stock, average price, average rating, priciest / cheapest product,
top category, most common tag, out-of-stock and low-stock counts).
The date checks anchor to the `fetched_date` stored in the database,
not to today's date, so they verify any stored run on any later day.

## Data dictionary

| Table | Column | Type | Meaning |
|---|---|---|---|
| `dim_category` | `category` | TEXT PK | Product category (beauty, vehicle, groceries…) |
| `dim_brand` | `brand` | TEXT PK | Product brand |
| `fact_product` | `product_id` | INTEGER PK | DummyJSON product id |
|  | `title` | TEXT NOT NULL | Product name |
|  | `category` | TEXT NOT NULL, FK → `dim_category` | Category |
|  | `brand` | TEXT, FK → `dim_brand` | Brand (null where the API gives none) |
|  | `price` | REAL NOT NULL, ≥ 0 | List price, USD |
|  | `discount_pct` | REAL NOT NULL, 0–100 | Discount percentage |
|  | `rating` | REAL NOT NULL, 0–5 | Catalogue-listed rating |
|  | `stock` | INTEGER NOT NULL, ≥ 0 | Units in stock |
|  | `min_order_qty` | INTEGER NOT NULL, ≥ 1 | Minimum order quantity |
|  | `weight_kg` | REAL | Product weight, kg |
|  | `sku` | TEXT UNIQUE | Stock-keeping unit |
|  | `availability` | TEXT NOT NULL | e.g. "In Stock", "Low Stock" |
|  | `fetched_date` | TEXT NOT NULL (`YYYY-MM-DD`) | The date the catalogue was fetched |
| `fact_review` | `review_id` | INTEGER PK (auto) | Review row id |
|  | `product_id` | INTEGER NOT NULL, FK → `fact_product` | Product reviewed |
|  | `reviewer` | TEXT NOT NULL | Reviewer name |
|  | `rating` | INTEGER NOT NULL, 1–5 | Review rating |
|  | `comment` | TEXT | Review text |
|  | `review_date` | TEXT NOT NULL (`YYYY-MM-DD`) | Review date |
| `bridge_product_tag` | `product_id`, `tag` | PK (both) | One row per product–tag pair |
| `run_meta` | `fetched_date` | TEXT PK | Run stamp |
|  | `source_url` | TEXT NOT NULL | API URL fetched |
|  | `api_total` | INTEGER NOT NULL | `total` reported by the API |
|  | `products_loaded` / `reviews_loaded` / `tags_loaded` | INTEGER NOT NULL | Rows loaded per table |

## Tools

- Python 3 + requests (the only dependency, pinned in `requirements.txt`)
- DummyJSON API — free, no key: `https://dummyjson.com`
- SQLite

## Limits

- **Demo catalogue, not a real store.** DummyJSON's products are
  made-up sample data for testing — prices, stock and reviews are
  illustrative, not real sales data. Nothing here is presented as
  real client work.
- **One run kept.** Every run rebuilds `data/products.db`, so only
  the latest catalogue is in the database. History lives in
  `data/raw/`, which keeps one JSON file per run date.
- **One API call per run.** `limit=0` returns the whole catalogue in
  a single GET; well inside DummyJSON's free tier.
- **API can change.** If DummyJSON renames a field or changes the
  catalogue, `validate()` in `src/etl.py` fails loudly instead of
  loading bad data — and `--rebuild` still works from the saved raw
  JSON.
- **REST Countries was the first choice, and it failed.** The
  planned source (restcountries.com v3.1) now returns a deprecation
  error, and its replacement host (`api.restcountries.com`) requires
  an authorization key — so it is no longer a free no-key API.
  DummyJSON was verified live (HTTP 200, 194 products) before
  building on it, and the choice is recorded here honestly.

## Data source note

**Live public data.** DummyJSON product API, fetched at run time;
nothing is sampled or invented. The raw response is saved so any
run can be audited after the fact.
