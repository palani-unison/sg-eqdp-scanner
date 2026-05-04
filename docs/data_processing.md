# Data processing — what is calculated and saved

This is the single reference for what every number on the website maps to: which Postgres table it lives in, which Python pipeline produced it, and what it means.

---

## TL;DR

The system has three layers:

```
RAW LAYER       Yahoo Finance OHLCV + STI index returns
                ────────────────────────────────────────
DERIVED LAYER   CAPM β · Abnormal returns · Amihud liquidity
                Bootstrap CIs · Cohort cumulative returns
                ────────────────────────────────────────
SCREEN LAYER    Candidate score · Per-ticker summaries
                ────────────────────────────────────────
                                ↓ read by
WEB APP         /brief charts · /market chart · /admin · /tracker
```

Eleven Postgres tables in Supabase. Seven Python pipelines under `pipelines/`. Every number on the site maps to exactly one query against exactly one of these tables.

---

## Pipeline order (run this top-to-bottom on a fresh database)

| # | Command | What it does | Wall time |
|---|---|---|---|
| 0 | `python -m scripts.db_push` (or `supabase db push`) | Apply `db/schema.sql` + migrations under `supabase/migrations/` | <30s |
| 1 | `python -m pipelines.backfill --start 2020-01-01 --end yesterday` | Seed `tickers` + `eqdp_managers`, fetch OHLCV into `prices_daily` | ~1 min |
| 2 | `python -m pipelines.compute_metrics` | STI returns → `factor_returns`; CAPM β → `betas`; Amihud → `liquidity_metrics` | ~1 min |
| 3 | `python -m pipelines.compute_did` | Build matched panels per event; CAR + DiD → `abnormal_returns` | ~30s |
| 4 | `python -m pipelines.compute_bootstrap --reps 5000` | Cluster bootstrap on entities → `bootstrap_cis` (12 rows) | ~10 min |
| 5 | `python -m pipelines.score_pipeline --as-of today` | Compose 5 raw signals into `candidate_scores` (one snapshot row per ticker) | ~30s |
| 6 | `python -m pipelines.compute_summaries` | Per-ticker `ticker_summaries` + per-day `cohort_timeseries` for the brief charts | ~10s |
| 7 | `python -m pipelines.weekly_filings --fixtures-dir <dir>` | Parse pre-saved SGXNet HTML into `filings_t1` (live scrape deferred — Akamai-blocked) | seconds |

Every pipeline writes a row to `pipeline_runs` with a JSON metrics blob, so a missed step is auditable.

---

## The eleven tables, one by one

### 1. `tickers` — the universe

Populated by `pipelines/backfill.py:_seed_tickers` from `src/universe.py`.

| Column | Meaning |
|---|---|
| `ticker` (PK) | yfinance symbol, e.g. `D05.SI` |
| `name`, `sector` | Human-readable identity |
| `in_sti30` | Boolean — control cohort |
| `in_next50` | Boolean — iEdge SG Next 50 (currently false for all; needs hand-curate) |
| `t1_flag`, `t2_flag`, `t3_flag` | Tier flags. T1 = confirmed via filing, T2 = programmatic eligibility, T3 = broker-named |
| `broker_named_count` | Count of broker beneficiary lists naming this stock |

Headline state: **72 rows** (52 T2 ∪ 27 T3 ∪ 20 control, with overlaps).

### 2. `eqdp_managers` — the nine appointed asset managers

| Column | Meaning |
|---|---|
| `manager_id` (PK) | Lowercase slug, e.g. `blackrock`, `jpmorgan_asset_management` |
| `canonical_name` | Display name |
| `tranche` | 1 or 2 |

Used as the foreign key from `filings_t1`. The slug map lives in `scrapers/sgxnet/manager_aliases.py` so SGX legal-entity-name variants (e.g. *BlackRock Investment Management (Singapore) Pte. Ltd.*) resolve to one canonical id.

State: **9 rows**.

### 3. `prices_daily` — raw OHLCV

Populated by `pipelines/backfill.py` via `src/data/prices.py:fetch_prices`. Yahoo Finance is the upstream source, accessed through yfinance ≥ 1.3.0 with a `curl_cffi` Chrome-impersonation session (Yahoo's Akamai layer rejects requests without a real browser TLS fingerprint).

| Column | Meaning |
|---|---|
| `ticker`, `trade_date` (PK) | One row per (ticker, day) |
| `open`, `high`, `low`, `close` | Raw OHLC |
| `adj_close` | Split- and dividend-adjusted close (the input to all return calculations) |
| `volume` | Shares traded |
| `dollar_volume` | Computed: `adj_close × volume` (Postgres GENERATED column) |

State: **109,465 rows × 69 tickers, 2020-01-02 → 2026-05-01**. Three universe tickers (`C61U.SI`, `F1E.SI`, `J91U.SI`) returned no data from Yahoo — likely renamed/delisted; sit in `tickers` with no `prices_daily` rows and need hand correction.

**Adjustment policy.** We call `yfinance.download(auto_adjust=False)` and keep both the raw close *and* the adjusted close, so the audit trail is preserved. Returns and abnormal returns are computed off `adj_close`. Spot-check: the CapitaLand C38U.SI split is correctly reflected in `adj_close`.

### 4. `factor_returns` — STI market return

Populated by `pipelines/compute_metrics.py`.

| Column | Meaning |
|---|---|
| `trade_date` (PK) | One row per trading day |
| `market` | Daily simple return on the STI Index (`^STI` on yfinance) |
| `smb`, `hml` | Fama-French Small-Minus-Big and High-Minus-Low (currently null — Day-9 robustness pass) |

State: **1,589 rows, 2020-01-02 → 2026-05-01**.

### 5. `betas` — CAPM coefficients

Populated by `pipelines/compute_metrics.py:estimate_beta` from `src/returns.py`.

For each ticker we fit:

```
R_i,t = α_i + β_i · R_market,t + ε_i,t
```

on a 252-trading-day window ending 30 days *before* the EQDP announcement (2025-02-21). The 30-day gap prevents the estimation window from leaking event-window information.

| Column | Meaning |
|---|---|
| `ticker`, `window_end` (PK) | One row per (ticker, fit) |
| `window_days` | Length of the estimation window in trading days |
| `alpha`, `beta` | OLS coefficients |
| `r_squared` | Goodness-of-fit |

State: **69 rows**. Sector sanity passes: banks β ≈ 1.1–1.4 (R² ≈ 0.5–0.7), industrials β ≈ 1.0, semiconductor β ≈ 1.0–1.2 with low R² (idiosyncratic), US REITs β ≈ 1.1 with very low R² (uncorrelated with STI).

### 6. `liquidity_metrics` — Amihud illiquidity

Populated by `pipelines/compute_metrics.py:amihud_daily` + `rolling_amihud` from `src/liquidity.py`.

```
Amihud_i,t = |R_i,t| / DollarVolume_i,t
```

Lower = more liquid (the same daily return achieved on more dollar volume = a deeper market).

| Column | Meaning |
|---|---|
| `ticker`, `trade_date` (PK) | One row per (ticker, day) |
| `amihud` | Per-day raw ratio |
| `amihud_60d` | 60-day rolling mean (the smooth signal used for `liquidity_rise`) |
| `turnover_velocity` | volume / shares-outstanding (currently null — needs shares-outstanding source) |

State: **101,466 rows**.

### 7. `abnormal_returns` — per-event AR + CAR

Populated by `pipelines/compute_did.py`.

For each event we:

1. Build the matched-pair panel: every treated stock (T1/T2/T3 with valid β + Amihud) + its nearest STI-30 control by sector / β / Amihud.
2. Compute per-day AR over the event window using `(α, β)` from `betas`:

   ```
   AR_i,t = R_i,t − (α_i + β_i · R_market,t)
   ```

3. Cumulate to CAR and store one row per `(ticker, event_id, t)`.

| Column | Meaning |
|---|---|
| `ticker`, `event_id`, `t`, `benchmark` (PK) | t = trading-day offset relative to event date |
| `ar` | Per-day abnormal return |
| `car` | Cumulative AR from window start to t |

State: **4,110 rows × 4 events × benchmark = `capm`**.

The DiD δ for each event is *not* stored in `abnormal_returns` — it's a per-event scalar saved on `pipeline_runs.metrics_json` and (with CIs) in `bootstrap_cis`. From `compute_did`:

| Event | Window | δ | p (analytical) |
|---|---|---:|---:|
| announcement | [-5, 20] | -0.0063 | 0.004 ★ |
| tranche_1 | [-1, 10] | -0.0025 | 0.47 |
| tranche_2 | [-1, 10] | +0.0072 | 0.016 ★ |
| expansion | [-1, 20] | +0.0082 | 0.23 |

### 8. `bootstrap_cis` — confidence intervals

Populated by `pipelines/compute_bootstrap.py`.

For each event we cluster-bootstrap entities (resample treated tickers and control tickers separately with replacement, refit `PanelOLS` with entity + time FE, record δ; 5,000 reps). Same for cohort mean-CAR.

| Column | Meaning |
|---|---|
| `metric`, `scope` (PK) | `did_delta`, `car_treated`, `car_control` × event_id |
| `point_estimate` | Full-sample value |
| `lower_5`, `upper_95` | 5–95 percentile CI from the bootstrap distribution |
| `n_replications` | 5,000 |

State: **12 rows**. Headline result:

| Metric | Scope | Point | 5% | 95% | Read |
|---|---|---:|---:|---:|---|
| did_delta | announcement | -0.0063 | -0.0099 | -0.0030 | ★ negative |
| did_delta | tranche_1 | -0.0025 | -0.0077 | +0.0030 | null |
| did_delta | tranche_2 | +0.0072 | +0.0025 | +0.0118 | ★ positive |
| did_delta | expansion | +0.0082 | -0.0018 | +0.0198 | null |

Only **tranche_2** (the actual S$2.85bn deployment in Nov 2025) shows a CI cleanly above 0.

### 9. `candidate_scores` — the screen

Populated by `pipelines/score_pipeline.py` from `src/score.py`.

The candidate score is the **screen for plausibility, not impact** — it does *not* see returns. Per `docs/METHODOLOGY.md` §3:

```
Score = 0.30 · LiquidityRise         (rank-normalised Δ amihud_60d, pre vs post)
      + 0.20 · InstitutionalProxy    (rank-normalised fraction of close > 30d VWAP)
      + 0.15 · IndexInclusion        (dummy: in iEdge SG Next 50?)
      + 0.15 · BrokerNamed           (broker_named_count / max in universe)
      + 0.20 · FilingPresent         (dummy: any T1 filing in last 12 months?)
```

Every signal is in [0, 1] before weighting; the total is in [0, 1]. The unit test `tests/test_score.py::test_score_invariant_to_cumulative_return_level` enforces that varying the cumulative return outcome with identical flow signals does not change the score.

| Column | Meaning |
|---|---|
| `ticker`, `score_date` (PK) | Snapshot date |
| `liquidity_rise`, `institutional_proxy`, `broker_named` | Raw signals in [0, 1] |
| `index_inclusion`, `filing_present` | Dummies (0 or 1) |
| `total_score` | Weighted sum |
| `eqdp_tier` | T1 / T2 / T3 / control / none |

State: **72 rows** for snapshot `2026-05-03`.

Top-3 right now: E28.SI (Frencken, T3, 0.488), 5DD.SI (Innotek, T2, 0.486 — non-broker-named, lifted purely by flow signals — methodology working), AWX.SI (AEM, T3, 0.478).

### 10. `ticker_summaries` — per-ticker aggregates (drives the Beneficiary scatter)

Populated by `pipelines/compute_summaries.py`.

For each ticker:

- `car_total` = sum of CAR across the four EQDP events (each event contributes its last-`t` CAR row)
- `car_mean` = mean of those four event-level CARs
- `volume_lift_pct` = mean over events of `(post_60d_avg_volume / pre_60d_avg_volume) − 1`
- `n_events` = number of events the ticker has CAR data for

| Column | Meaning |
|---|---|
| `ticker` (PK) | |
| `car_total`, `car_mean`, `volume_lift_pct`, `amihud_change`, `n_events` | Aggregates |

State: **72 rows**. Drives the `BeneficiaryScatter` chart on `/brief` (CAR vs volume lift, treatment vs control).

### 11. `cohort_timeseries` — per-day cohort cumulative return (drives the Cumulative-Returns line)

Populated by `pipelines/compute_summaries.py`. Indexed to a baseline date (default `2024-01-02`).

For each trading day we compute the **mean simple return across each cohort**, then take the cumulative log-return:

```
treatment_cum_log_return_t = Σ ln(1 + mean_simple_return_treatment_τ)   for τ ≤ t
control_cum_log_return_t   = Σ ln(1 + mean_simple_return_control_τ)
sti_cum_log_return_t       = Σ ln(1 + factor_returns.market_τ)
```

Treatment cohort = all tickers with `t1_flag OR t2_flag OR t3_flag = true`. Control cohort = all tickers with `in_sti30 = true`.

| Column | Meaning |
|---|---|
| `trade_date` (PK) | |
| `treatment_cum`, `control_cum`, `sti_cum` | Cumulative log-return |
| `n_treatment`, `n_control` | Cohort sizes (constant per snapshot) |

State: **587 rows, 2024-01-02 → 2026-05-01**. Drives the `CumulativeReturnsChart` on `/brief`.

### 12. `pipeline_runs` — operational log

One row per pipeline execution.

| Column | Meaning |
|---|---|
| `run_id` (PK) | UUID |
| `job_name` | `backfill`, `compute_metrics`, `compute_did:all`, `compute_bootstrap:all`, `score_pipeline`, `compute_summaries` |
| `status` | `running` / `succeeded` / `partial` / `failed` |
| `metrics_json` | Free-form JSON capturing rows written, per-event δ values, fetch failures, etc. |

Read by `/admin` (recent runs) and `/tracker` (stale-data banner — flips yellow if last successful run > 36h old).

### 13. `filings_t1` — confirmed buyers (currently empty)

Schema is in place; population is **deferred**. SGX's company-announcements portal is a JS-SPA fronted by Akamai (`403 Access Denied` for plain GET, headless Playwright, and Playwright + stealth alike). Until a residential-proxy bypass is in place, `pipelines/weekly_filings.py` runs in `--fixtures-dir` mode and replays manually-saved filing HTML through the parser.

When populated, each row will be:

| Column | Meaning |
|---|---|
| `filing_id` (PK) | SGX-side identifier or synthetic surrogate |
| `manager_id` | FK → `eqdp_managers` (resolved through `manager_aliases.py`) |
| `ticker` | FK → `tickers` |
| `effective_date`, `filing_date` | Bi-temporal — when the stake actually changed vs when the public learned |
| `stake_pct`, `direction` | Post-transaction stake; acquired / disposed / crossed_up / crossed_down |
| `source_url` | Provenance URL |

When `filings_t1` populates, the `filing_present` signal in `candidate_scores` flips from 0 to a real 0/1 and T1 names jump in the score (worth +0.20).

### 14–15. `synthetic_controls`, `placebo_results` — Day 5 (deferred)

Schema is in place; the Bayesian synthetic-control pipeline (`tfcausalimpact`) is deferred until a Python-3.14-compatible install path is sorted (TensorFlow Probability lacks Py3.14 wheels at the time of writing). Fallback path: hand-rolled Abadie-Diamond-Hainmueller constrained-least-squares.

### 16–18. `users`, `user_profiles`, `engagement_events`

Auth-side. `auth.users` is managed by Supabase Auth; `user_profiles` carries the registration metadata (name, firm, country, disclaimer-accepted-at, email opt-in). `engagement_events` will track per-section reads on the brief once we wire client-side analytics.

State: **1 row in `user_profiles`** — the admin user `pachidam@outlook.com` (id `47399ba3-…`), created via `supabase.auth.admin.create_user` with `email_confirm=True`.

---

## How the website maps to these tables

| Page | Table(s) read |
|---|---|
| `/brief` | `candidate_scores` (top-15 + full export) · `bootstrap_cis` (forest plot) · `abnormal_returns` (event-study lines) · `cohort_timeseries` (cumulative-returns line) · `ticker_summaries` (beneficiary scatter) |
| `/market` | `factor_returns` (STI cumulative line + 4-card summary) |
| `/admin` | `pipeline_runs` (recent runs table) · `user_profiles` (count) · `candidate_scores` (count) · `filings_t1` (count) |
| `/admin/users` | `user_profiles` (full list) |
| `/tracker` | `pipeline_runs` (stale banner) · `candidate_scores` (snapshot date) |

The web app reads these via `@supabase/ssr` server clients on every request (or every 6 hours for `/tracker` via Next.js ISR). Server components page through the 1,000-row PostgREST cap with `.range()` loops; analytical aggregations that span the full universe go through the Supabase CLI's Management API (`supabase db query --linked`) to bypass the cap.

---

## Provenance and reproducibility commitment

- **Every fact carries a `pipeline_run_id`** linking back to the run that produced it. No row is anonymous.
- **Every metric maps to a Python function + unit test.** 111 Python tests pin behaviour against fixed historical snapshots (`pytest tests/`).
- **Every chart can be reproduced from the public schema** by cloning the repo, applying `db/schema.sql`, and running pipelines 1–6 in order.
- **No analytical data is committed to git.** Only schema, code, configs.

---

## Local export (for backup or offline analysis)

`scripts/export_data.py` (run with `python -m scripts.export_data`) pulls every analytical table to `data/exports/<table>.csv`. Useful when:

- You want the underlying data outside of Supabase.
- You're investigating a row-level discrepancy and want pandas next to the brief.
- You're handing the dataset to a peer reviewer.

`data/exports/` is gitignored — never committed.
