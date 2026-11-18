"""Mini #18 — run the 10 analysis queries and write outputs.

Builds the database from the saved raw JSON (offline replay), or
fetches live first with --live, then runs every query in
sql/analysis_queries.sql and writes one CSV per query plus a
findings note into outputs/.

Run:  python3 src/run_queries.py          (rebuild from saved raw JSON)
      python3 src/run_queries.py --live   (fetch live, then run queries)
"""

import argparse
import csv
import json
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "products.db"
OUT = ROOT / "outputs"
SQL_FILE = ROOT / "sql" / "analysis_queries.sql"


def parse_queries(text):
    """Split analysis_queries.sql into (number, question, sql) triples."""
    queries = []
    current = {"num": None, "question": None, "lines": []}
    for line in text.splitlines():
        m = re.match(r"-- Q(\d+)\.\s*(.*)", line)
        if m:
            if current["num"] is not None:
                queries.append(current)
            current = {"num": int(m.group(1)), "question": m.group(2).strip(),
                       "lines": []}
            continue
        if line.strip().startswith("--"):
            if current["question"] and not current["lines"]:
                # continuation of the question comment
                current["question"] += " " + line.strip().lstrip("-").strip()
            continue
        if line.strip():
            current["lines"].append(line)
    if current["num"] is not None:
        queries.append(current)
    out = []
    for q in queries:
        sql = "\n".join(q["lines"]).strip().rstrip(";")
        out.append((q["num"], q["question"], sql))
    return out


def slug(text):
    s = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return s[:60] or "query"


# Short, readable output names (the full question text would make
# 60-char truncated filenames — see the slug() cap above).
SHORT_SLUGS = {
    1: "category_stock_value",
    2: "category_avg_price",
    3: "top10_most_expensive",
    4: "avg_discount_by_category",
    5: "low_stock_products",
    6: "products_per_brand",
    7: "rating_distribution",
    8: "rating_by_price_band",
    9: "most_common_tags",
    10: "reviews_vs_listed_rating",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true",
                        help="fetch the catalogue live before running")
    args = parser.parse_args()

    if args.live:
        subprocess.run([sys.executable, str(ROOT / "src" / "etl.py")],
                       check=True)
    else:
        subprocess.run([sys.executable, str(ROOT / "src" / "etl.py"),
                        "--rebuild"], check=True)

    queries = parse_queries(SQL_FILE.read_text(encoding="utf-8"))
    assert len(queries) == 10, f"expected 10 queries, found {len(queries)}"
    OUT.mkdir(parents=True, exist_ok=True)

    con = sqlite3.connect(DB)
    n_products = con.execute("SELECT COUNT(*) FROM fact_product").fetchone()[0]
    fetched_date = con.execute(
        "SELECT fetched_date FROM run_meta").fetchone()[0]
    findings = [f"# Mini #18 — Findings ({fetched_date})\n",
                f"10 questions over {n_products} products from the "
                f"DummyJSON catalogue, loaded into `data/products.db`.\n"]

    for num, question, sql in queries:
        cur = con.execute(sql)
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
        assert rows, f"Q{num} returned no rows"
        name = f"q{num:02d}_{SHORT_SLUGS[num]}"
        csv_path = OUT / f"{name}.csv"
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(cols)
            w.writerows(rows)
        print(f"Q{num}: {len(rows)} rows -> {csv_path.name}")
        findings.append(f"## Q{num}. {question}\n")
        findings.append(f"Result: `{csv_path.name}` "
                        f"({len(rows)} rows).\n")
        top = rows[0]
        findings.append(f"Top row: {dict(zip(cols, top))}\n")

    (OUT / "findings.md").write_text("\n".join(findings), encoding="utf-8")
    con.close()
    print(f"wrote 10 CSVs + findings.md to {OUT}")


if __name__ == "__main__":
    main()
