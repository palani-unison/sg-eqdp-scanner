# CLAUDE.md — sg-eqdp-scanner

This file guides Claude Code when working anywhere in this repo. Read it before touching code.

Personal-research project by **Palaniappan Chidambaram**. Reverse-engineers the impact of the Singapore MAS Equity Market Development Programme (EQDP) on SGX-listed equities and publishes the findings as a public, email-gated **EQDP Brief** web application.

## Mission

Identify which SGX-listed companies actually benefited from EQDP — price appreciation, volume lift, liquidity improvement — versus which did not. MAS does not disclose specific holdings of the appointed managers, so beneficiary identification is *inferential*: combine eligibility filters, broker beneficiary lists, market-microstructure changes around event dates, and SGXNet substantial-shareholder filings (5%+).

## Identity — this is not investment advice

This is the **personal research of Palaniappan Chidambaram**, **not affiliated with Unison Group** or any other entity. The audience is public — anyone may register. Every page carries a disclaimer banner. Tone is forensic, evenhanded, and explicit about what we do and don't know.

## Architecture

```
GitHub Actions (Python)        DuckDB-in-repo          Streamlit Cloud
─────────────────────────      ──────────────          ─────────────────
pipelines/*.py        ───►    data/eqdp.duckdb  ◄────  streamlit_app/
yfinance, statsmodels         (committed file)         reads via duckdb
CausalImpact, scrapers                                 (read-only)
```

- **Python** (`src/`, `scrapers/`, `pipelines/`) does all analysis. Single-node pandas + DuckDB. No Spark, no Delta.
- **DuckDB-in-repo** is the system of record. The single file `data/eqdp.duckdb` is committed to the repo. Schema: `db/schema_duckdb.sql`. There is no managed database, no auth, no external service — pipelines write the file, the dashboard reads it.
- **Pipeline write path** uses `src/db.py::get_supabase()` (legacy name, returns a `DuckStore`). The shim in `src/store.py` exposes a `supabase-py`-compatible chainable API (`.table().upsert()/.select().eq().order().execute()`) so the pipelines did not need rewrites when Supabase was removed. Read it before adding new pipeline code.
- **Streamlit** (`streamlit_app/`) is the public site — multi-page data-science app with Plotly charts, candlestick TA view, event studies, candidate-score tracker. Entry point: `streamlit_app/Home.py`. Reads DuckDB directly via `streamlit_app/lib/store.py`. No secrets needed.
- **GitHub Actions** runs the daily/weekly/monthly Python jobs and commits the updated `data/eqdp.duckdb` back to the repo. Free for the public repo. Streamlit Cloud auto-redeploys on push.

> The `web/` directory holds an earlier Next.js prototype. It is no longer the active surface; do not extend it. Add features to `streamlit_app/`.

## Phase split

- **Phase 0 — laptop backfill** (one-shot, ~30–60 min): 5 years of OHLCV for ~200 tickers, CAPM betas, full event-study CARs around the four EQDP dates, synthetic-control fits for top 15 named beneficiaries, bootstrap CIs, full placebo run. Writes to Supabase Postgres.
- **Phase 1 — cloud increments** (daily/weekly/monthly, < 10 min each): yesterday's prices, today's abnormal returns, today's candidate scores, weekly filings scrape, monthly synth-control refit. Same code, smaller date range.

`pipelines/backfill.py` is `pipelines/daily_score.py` with a wider window. There is no second codebase.

## The single biggest mistake to avoid

**Do not measure returns with returns.**

The candidate score uses only inputs that are not the outcome:

- Liquidity rise (Amihud change)
- Institutional proxy (close-vs-VWAP days)
- Index inclusion dummy (iEdge SG Next 50)
- Broker-named count (T3 lists)
- Filing presence dummy (T1 SGXNet)

Returns appear only on the *right-hand side* of the impact regression, never as an input to the screen. A stock that rallied 245 % gets a high candidate score only if the underlying flow signals fired — never simply because the price moved.

## The Three-Tier Universe

- **T1 — Confirmed**: stocks where ≥1 of the nine EQDP-appointed managers filed a substantial-shareholder disclosure on or after 2025-07-21. Source: SGXNet.
- **T2 — Eligible**: programmatic application of EQDP eligibility (small/mid-cap, SGX Mainboard or Catalist, daily-traded, not in STI-30, not restricted sectors).
- **T3 — Named**: stocks named by RHB-30, Maybank-18, Edge-69, and other broker beneficiary notes.
- **Control**: STI-30 large caps (EQDP de-emphasises these — natural counterfactual).

A stock can sit in multiple tiers; highest tier wins for headline classification.

## Data integrity rules (non-negotiable)

- **Never use look-ahead bias.** Index membership, substantial-shareholder filings, and analyst initiations all have a publication lag. Track both `effective_date` and `filing_date` on every row.
- **Adjust for corporate actions.** Use yfinance's `auto_adjust=True`; spot-check splits/dividends manually for the top 20 names.
- **Document data provenance** for every fact: source, fetch UTC timestamp, parser version. Stored on the row.
- **Decoupled detector vs estimator.** Candidate score does not see returns. Impact estimator does not score. Confidence layer interrogates the estimator.

## Methodology stack (see `docs/METHODOLOGY.md` for formulae)

1. CAPM-adjusted abnormal returns — β estimated on a 252-day pre-event window.
2. Fama-French 3-factor as robustness.
3. Amihud illiquidity ratio.
4. Matched-pair difference-in-differences (sector, market-cap, β, pre-event Amihud).
5. Bayesian synthetic control (CausalImpact) for top 10–15 named beneficiaries.
6. Placebo tests on non-event dates.
7. Block-bootstrap confidence intervals (5,000 reps).

## Code style

- **Python 3.11+**, type hints on every function signature, `mypy --strict` clean.
- Pure functions in `src/`; notebooks and pipelines orchestrate, do not implement.
- All financial dates: `pd.Timestamp` with explicit `tz_localize(None)`.
- Bi-temporal columns on every fact with publication lag (`effective_date`, `filing_date`).
- Every analytical metric needs: unit test on a toy example, sanity-check plot, comparison against a known benchmark.
- Every data fetch needs: row-count assertion, date-range assertion, null-rate check.

## Web app (`streamlit_app/`)

- Streamlit multi-page app — `Home.py` + `pages/*`. Plotly for all charts, dark "forensic" template registered in `lib/theme.py`.
- Reads from DuckDB at `data/eqdp.duckdb` (read-only mode) via `lib.store`. Cached with `@st.cache_data(ttl=...)`. Never imports Python pipeline code.
- Pages: **Home** (snapshot + DiD forest), **Tracker** (full candidate-score table with filters), **Event Studies** (CARs by event/benchmark, treated vs control), **Universe** (T1/T2/T3 explorer), **Ticker Analyzer** (candlestick + RSI/MACD/Bollinger/Amihud + event lines + filing markers), **Filings** (T1 SGXNet feed), **Methodology**, **Brief** (placeholder), **About**, **Disclaimer**.
- Disclaimer banner (`lib/components.disclaimer_banner`) renders at the top of every page; full text on the Disclaimer page reads `docs/DISCLAIMER.md` directly so the canonical text lives in one place.
- TA helpers (`lib/ta.py`) are pure pandas — no `pandas-ta` to dodge pkg_resources/numpy issues on Streamlit Cloud.
- Deploy: Streamlit Community Cloud → main file `streamlit_app/Home.py`. No secrets required — the DuckDB file ships with the repo.

## Common workflows

Run Phase 0 backfill on laptop:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m scripts.init_duckdb                 # creates data/eqdp.duckdb
python -m pipelines.backfill --start 2020-01-01 --end yesterday
```

Run a single increment locally for debugging:

```bash
python -m pipelines.daily_score --date 2026-05-02
```

Run the Streamlit app locally:

```bash
streamlit run streamlit_app/Home.py
```

Apply DB schema changes:

```bash
# DuckDB-in-repo edition: edit db/schema_duckdb.sql, then re-init.
# (init is idempotent — every CREATE uses IF NOT EXISTS.)
python -m scripts.init_duckdb
```

## What NOT to do

- Don't reintroduce `total_return` into the candidate score.
- Don't introduce Spark, Delta, pyspark, or any distributed compute. Single-node pandas + DuckDB until a measured limit forces otherwise.
- Don't commit analytical data into git. Gold tables live in Supabase Postgres. Only schema, code, configs in git.
- Don't use the `requests` library against SGXNet without rate limiting and a polite User-Agent.
- Don't hardcode the admin email anywhere except a single env var.
- Don't add features without first writing the test that would fail without them.
- Don't paper over data-quality issues with imputation; surface them with a stale-data banner on the site.

## Skills to invoke

When relevant, use:

- `data:write-query` for SQL.
- `data:analyze` for ad-hoc data questions.
- `data:explore-data` when encountering a new table.
- `productivity:memory-management` for ongoing context retention — keep `memory.md` up to date at the end of each session.

## File map

| What | Where |
|---|---|
| Strategy doc (canonical) | `docs/STRATEGY.md` |
| Day-by-day plan | `docs/PLAN.md` |
| Methodology details + math | `docs/METHODOLOGY.md` |
| Disclaimer text | `docs/DISCLAIMER.md` |
| DuckDB schema (active) | `db/schema_duckdb.sql` |
| Legacy Postgres schema | `db/schema.sql` (kept for reference) |
| Tier 1/2/3 starter universe | `docs/TICKERS.md` |
| Working memory (live) | `memory.md` |
| Public README | `README.md` |
| Python analytical core | `src/` |
| Scrapers (SGXNet) | `scrapers/` |
| Scheduled pipelines | `pipelines/` |
| Web app (active) | `streamlit_app/` |
| Legacy Next.js prototype | `web/` (deprecated; do not extend) |
| Tests | `tests/` |
| GitHub Actions cron | `.github/workflows/` |
