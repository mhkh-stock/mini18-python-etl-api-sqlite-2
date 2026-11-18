# Mini #18 — Product catalogue ETL run (2026-11-18)

Full DummyJSON product catalogue, fetched live and loaded into `data/products.db`.

- Products loaded: **194**
- Reviews loaded: **582**
- Tags loaded: **364**
- Total stock value (price x stock): **$17,172,492.31**
- Average price: **$1,570.10**
- Biggest category by stock value: **vehicle**, $10,707,996.59
- Most expensive product: **Durango SXT RWD**, $36,999.99
- Highest-rated product: **Amazon Echo Plus**, 4.99 / 5

Re-run any time: `python3 src/etl.py` fetches the current catalogue; `python3 src/etl.py --rebuild` reloads from the saved raw JSON without an API call; `python3 src/checks.py` verifies the load.
