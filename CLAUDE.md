# CLAUDE.md — sg-eqdp-scanner

This file guides Claude Code when working anywhere in this repo. Read it before touching code.

A quantitative case study built for **education and institutional-grade analysis** — a search for the **iEdge SG Next 50** (small/mid-cap SGX equities) using public market data, with a forensic, technical-analyst aesthetic.

## Identity — this is not investment advice

Every page carries a disclaimer banner stating that the site is a technical study and analysis intended for discussion, not investment advice. Tone is forensic, evenhanded, and explicit about what we do and don't know.

## Architecture

```
GitHub Actions (Python)        DuckDB-in-repo          Streamlit Cloud
─────────────────────────      ──────────────          ─────────────────
pipelines/*.py        ───►    data/eqdp.duckdb  ◄────  streamlit_app/
yfinance, statsmodels         (committed file)         reads via duckdb
                                                       (read-only)
```

- **Python** (`src/`, `pipelines/`) does all analysis. Single-node pandas + DuckDB. No Spark, no Delta.
- **DuckDB-in-repo** is the system of record. The single file `data/eqdp.duckdb` is committed to the repo. Schema: `db/schema_duckdb.sql`. There is no managed database, no auth, no external service — pipelines write the file, the dashboard reads it.
- **Pipeline write path** uses `src/db.py::get_supabase()` (legacy name, returns a `DuckStore`). The shim in `src/store.py` exposes a `supabase-py`-compatible chainable API (`.table().upsert()/.select().eq().order().execute()`) — kept for migration ergonomics; new code can call `get_store()` directly.
- **Streamlit** (`streamlit_app/`) is the public site — multi-page data-science app with Plotly charts, candlestick TA view, event studies, candidate-score tracker. Entry point: `streamlit_app/EQDP_Brief.py`. Reads DuckDB directly via `streamlit_app/lib/store.py`. No secrets needed.
- **GitHub Actions** runs the daily/weekly/monthly Python jobs and commits the updated `data/eqdp.duckdb` back to the repo. Streamlit Cloud auto-redeploys on push.

## Phase split

- **Phase 0 — laptop backfill** (one-shot, ~5–10 min on Python 3.12): 5+ years of OHLCV across the universe, CAPM betas, full event-study CARs around the four event dates, bootstrap CIs, candidate scores. Writes to `data/eqdp.duckdb`.
- **Phase 1 — cloud increments** (daily/weekly/monthly, < 10 min each): yesterday's prices, today's abnormal returns, today's candidate scores. Same code, smaller date range.

## The single biggest mistake to avoid

**Do not measure returns with returns.**

The candidate score uses only inputs that are not the outcome:

- Liquidity rise (Amihud change)
- Institutional proxy (close-vs-VWAP days)
- Index inclusion dummy (iEdge SG Next 50)
- Broker-named count (T3 lists)
- Filing presence dummy (T1 SGXNet)

Returns appear only on the *right-hand side* of the impact regression, never as an input to the screen. A stock that rallied 245% gets a high candidate score only if the underlying flow signals fired — never simply because the price moved.

## The Three-Tier Universe

- **T1 — Confirmed**: stocks where ≥1 of the appointed managers filed a substantial-shareholder disclosure. (Currently empty — public-data scrape is deferred.)
- **T2 — Eligible**: programmatic application of eligibility (small/mid-cap, SGX Mainboard or Catalist, daily-traded, not in STI-30, not restricted sectors).
- **T3 — Named**: stocks named by RHB-30, Maybank-18, Edge-69, and other broker beneficiary notes.
- **Control**: STI-30 large caps (programme de-emphasises these — natural counterfactual).

A stock can sit in multiple tiers; highest tier wins for headline classification.

## Data integrity rules (non-negotiable)

- **Never use look-ahead bias.** Index membership, substantial-shareholder filings, and analyst initiations all have a publication lag. Track both `effective_date` and `filing_date` on every row.
- **Adjust for corporate actions.** Use yfinance's `auto_adjust=True`; spot-check splits/dividends manually for the top 20 names.
- **Document data provenance** for every fact: source, fetch UTC timestamp.
- **Decoupled detector vs estimator.** Candidate score does not see returns. Impact estimator does not score. Confidence layer interrogates the estimator.

## Methodology stack

1. CAPM-adjusted abnormal returns — β estimated on a 252-day pre-event window.
2. Fama-French 3-factor as robustness.
3. Amihud illiquidity ratio.
4. Matched-pair difference-in-differences (sector, market-cap, β, pre-event Amihud).
5. Bayesian synthetic control — *deferred*.
6. Block-bootstrap confidence intervals (5,000 reps).

## Code style

- **Python 3.12+**, type hints on every function signature.
- Pure functions in `src/`; pipelines orchestrate, do not implement.
- All financial dates: `pd.Timestamp` with explicit `tz_localize(None)`.
- Bi-temporal columns on every fact with publication lag (`effective_date`, `filing_date`).
- Every analytical metric needs: unit test on a toy example.

## Web app (`streamlit_app/`)

- Streamlit multi-page app — `EQDP_Brief.py` (entry) + `pages/*`. Plotly for all charts, dark theme registered in `lib/theme.py`.
- Reads DuckDB at `data/eqdp.duckdb` (read-only) via `lib.store`. Cached with `@st.cache_data(ttl=...)`. Never imports Python pipeline code.
- Pages: **EQDP Brief** (snapshot + DiD forest), **What is EQDP**, **Investment Thesis**, **Event Studies**, **Methodology**, **Tracker**, **Universe**, **Ticker Analyzer**, **About**, **Disclaimer**.
- Disclaimer banner (`lib/components.disclaimer_banner`) renders at the top of every page.
- TA helpers (`lib/ta.py`) are pure pandas — no `pandas-ta`.
- Deploy: Streamlit Community Cloud → main file `streamlit_app/EQDP_Brief.py`. No secrets required.

## Common workflows

Run Phase 0 backfill on laptop:

```bash
python -m venv .venv && source .venv/bin/activate     # Python 3.12
pip install -r requirements.txt -r requirements-dev.txt   # dashboard + pipelines
python -m scripts.init_duckdb                          # creates data/eqdp.duckdb
python -m pipelines.backfill --start 2020-01-01 --end yesterday
python -m pipelines.compute_metrics
python -m pipelines.compute_did
python -m pipelines.compute_bootstrap
python -m pipelines.score_pipeline
```

Run a single increment locally for debugging:

```bash
python -m pipelines.score_pipeline
```

Run the Streamlit app locally:

```bash
streamlit run streamlit_app/EQDP_Brief.py
```

Apply DB schema changes:

```bash
# Edit db/schema_duckdb.sql, then re-init (idempotent — every CREATE uses IF NOT EXISTS).
python -m scripts.init_duckdb
```

## What NOT to do

- Don't reintroduce `total_return` into the candidate score.
- Don't introduce Spark, Delta, pyspark, or any distributed compute. Single-node pandas + DuckDB until a measured limit forces otherwise.
- Don't add features without first writing the test that would fail without them.
- Don't paper over data-quality issues with imputation; surface them with a stale-data banner on the site.

## File map

| What | Where |
|---|---|
| DuckDB schema | `db/schema_duckdb.sql` |
| DB init script | `scripts/init_duckdb.py` |
| Python analytical core | `src/` |
| Scheduled pipelines | `pipelines/` |
| Web app | `streamlit_app/` |
| Tests | `tests/` |
| GitHub Actions cron | `.github/workflows/` *(planned)* |
