# DATA_MODEL.md

The Postgres schema used by `sg-eqdp-scanner`. Source of truth is `db/schema.sql`. This document explains *why* each table exists and how the web app queries it.

All tables share:
- `created_at timestamptz default now()` — when the row was written
- `pipeline_run_id uuid references pipeline_runs(run_id)` — for traceability

Tables with publication lag carry both `effective_date` and `filing_date`.

---

## Universe

### `tickers`
One row per SGX-listed security tracked by the scanner.

| Column | Type | Notes |
|---|---|---|
| ticker | text PK | yfinance form (e.g. `E28.SI`) |
| sgx_code | text | local SGX code (e.g. `E28`) |
| name | text | full company name |
| sector | text | GICS sector |
| market_cap_band | text | small / mid / large |
| listing_board | text | Mainboard / Catalist |
| in_sti30 | boolean | |
| in_next50 | boolean | iEdge SG Next 50 membership |
| restricted_sector | boolean | excluded from EQDP eligibility |
| t1_flag | boolean | confirmed (any T1 filing) |
| t2_flag | boolean | eligible (programmatic filter) |
| t3_flag | boolean | named on a broker beneficiary list |
| broker_named_count | int | how many T3 lists name this stock |
| first_seen | date | |
| last_seen | date | |

### `eqdp_managers`
The nine EQDP-appointed asset managers + alias resolution.

| Column | Type | Notes |
|---|---|---|
| manager_id | text PK | canonical short name |
| canonical_name | text | display |
| aliases | text[] | "BlackRock", "BlackRock Inc.", "BlackRock Investment Management Singapore", ... |
| tranche | int | 1, 2, or null |
| appointed_date | date | |

---

## Prices and factors

### `prices_daily`
| Column | Type | Notes |
|---|---|---|
| ticker | text | FK → tickers |
| trade_date | date | |
| open, high, low, close, adj_close | numeric | adjusted for corporate actions |
| volume | bigint | |
| dollar_volume | numeric | computed = adj_close × volume |
| _PK | (ticker, trade_date) | |

Indexed on `(ticker, trade_date desc)` for fast latest-price lookups.

### `factor_returns`
Daily Fama-French 3-factor returns constructed from our SGX universe.

| Column | Type | Notes |
|---|---|---|
| trade_date | date PK | |
| market | numeric | STI ETF return |
| smb | numeric | small-minus-big |
| hml | numeric | high-minus-low book-to-market |

### `betas`
Rolling CAPM β estimates per ticker.

| Column | Type | Notes |
|---|---|---|
| ticker | text | |
| window_end | date | last day of the estimation window |
| window_days | int | typically 252 |
| alpha, beta | numeric | |
| r_squared | numeric | |
| _PK | (ticker, window_end) | |

---

## Impact estimation

### `abnormal_returns`
| Column | Type | Notes |
|---|---|---|
| ticker | text | |
| event_id | text | one of `announcement, tranche_1, tranche_2, expansion`, plus placebo IDs |
| t | int | trading days from event date (e.g. -5 to +20) |
| ar | numeric | abnormal return |
| car | numeric | cumulative AR up to and including day t |
| benchmark | text | `capm` or `ff3` |
| _PK | (ticker, event_id, t, benchmark) | |

### `liquidity_metrics`
| Column | Type | Notes |
|---|---|---|
| ticker | text | |
| trade_date | date | |
| amihud | numeric | abs(return) / dollar_volume |
| amihud_60d | numeric | 60-day rolling mean |
| turnover_velocity | numeric | volume / shares_out |
| _PK | (ticker, trade_date) | |

### `synthetic_controls`
Per-stock observed-vs-counterfactual paths from `tfcausalimpact`.

| Column | Type | Notes |
|---|---|---|
| ticker | text | |
| event_id | text | |
| t | int | trading days from event date (allowed range -180 to +60) |
| observed | numeric | actual price (rebased = 1 at t=-30) |
| counterfactual | numeric | posterior mean |
| ci_lower, ci_upper | numeric | 95% credible interval |
| _PK | (ticker, event_id, t) | |

### `placebo_results`
| Column | Type | Notes |
|---|---|---|
| placebo_date | date | |
| panel | text | `treatment` / `t2_eligible` / `t3_named` / etc. |
| metric | text | `car`, `amihud_change`, etc. |
| value | numeric | the placebo effect |
| _PK | (placebo_date, panel, metric) | |

### `bootstrap_cis`
Confidence intervals for headline metrics.

| Column | Type | Notes |
|---|---|---|
| metric | text | e.g. `programme_car_t1` |
| scope | text | e.g. `t1_universe`, `ticker:E28.SI` |
| point_estimate | numeric | |
| lower_5 | numeric | 5th percentile of bootstrap distribution |
| upper_95 | numeric | 95th percentile |
| n_replications | int | typically 5000 |
| computed_at | timestamptz | |
| _PK | (metric, scope) | |

---

## Candidate score (the screen)

### `candidate_scores`
The decoupled candidate score per ticker per snapshot date. Returns are not an input.

| Column | Type | Notes |
|---|---|---|
| ticker | text | |
| score_date | date | |
| liquidity_rise | numeric | |
| institutional_proxy | numeric | |
| index_inclusion | int | 0/1 |
| broker_named | numeric | normalised count |
| filing_present | int | 0/1 |
| total_score | numeric | weighted sum |
| eqdp_tier | text | `T1`, `T2`, `T3`, or `control` |
| _PK | (ticker, score_date) | |

The web app reads `WHERE score_date = (SELECT max(score_date) FROM candidate_scores)` for "latest snapshot" views.

---

## Ground truth

### `filings_t1`
SGXNet substantial-shareholder filings by EQDP managers (5%+).

| Column | Type | Notes |
|---|---|---|
| filing_id | text PK | SGXNet's identifier |
| manager_id | text | FK → eqdp_managers |
| ticker | text | FK → tickers |
| effective_date | date | when the manager crossed the threshold |
| filing_date | date | when the filing was made public |
| stake_pct | numeric | as filed |
| direction | text | `acquired` / `disposed` |
| source_url | text | direct link to SGXNet filing |

Backtests filter on `filing_date <= as_of_date` to avoid look-ahead bias.

---

## Operations

### `pipeline_runs`
One row per pipeline execution (daily, weekly, monthly).

| Column | Type | Notes |
|---|---|---|
| run_id | uuid PK | |
| job_name | text | `daily_score`, `weekly_filings`, `monthly_full_run`, `backfill` |
| started_at | timestamptz | |
| completed_at | timestamptz | nullable until finished |
| status | text | `running` / `succeeded` / `partial` / `failed` |
| metrics_json | jsonb | row counts, timings, anomalies |
| error_message | text | nullable |

The web app reads `last_success_at` per job to drive the staleness banner.

---

## Users + engagement

### Auth-managed
- `auth.users` — managed by Supabase Auth.

### `user_profiles`
| Column | Type | Notes |
|---|---|---|
| user_id | uuid PK | FK → auth.users |
| name | text | |
| firm | text | optional |
| country | text | optional |
| disclaimer_accepted_at | timestamptz | |
| email_optin | boolean | default true |
| registered_at | timestamptz | |
| unsubscribed_at | timestamptz | nullable |

### `engagement_events`
| Column | Type | Notes |
|---|---|---|
| event_id | uuid PK | |
| user_id | uuid | nullable for anonymous (public) pages |
| session_id | text | |
| route | text | `/brief`, `/tracker`, etc. |
| section_anchor | text | e.g. `findings-stock` |
| time_on_section_ms | int | |
| event_at | timestamptz | |

Indexed on `(user_id, event_at desc)` for the admin view.

---

## Common queries

```sql
-- Latest candidate scores, T1 + T2 only
SELECT * FROM candidate_scores
WHERE score_date = (SELECT max(score_date) FROM candidate_scores)
  AND eqdp_tier IN ('T1', 'T2')
ORDER BY total_score DESC;

-- T1 filings in the last 30 days, with company names
SELECT f.filing_date, m.canonical_name AS manager,
       t.name AS company, f.stake_pct, f.source_url
FROM filings_t1 f
JOIN eqdp_managers m USING (manager_id)
JOIN tickers t USING (ticker)
WHERE f.filing_date >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY f.filing_date DESC;

-- Programme-level CAR around tranche 1, treatment vs control
SELECT eqdp_tier, t,
       avg(car) AS mean_car,
       count(*) AS n_stocks
FROM abnormal_returns ar
JOIN candidate_scores cs USING (ticker)
WHERE event_id = 'tranche_1'
  AND benchmark = 'capm'
  AND cs.score_date = (SELECT max(score_date) FROM candidate_scores)
GROUP BY eqdp_tier, t
ORDER BY eqdp_tier, t;

-- Staleness check
SELECT job_name, max(completed_at) AS last_success
FROM pipeline_runs
WHERE status = 'succeeded'
GROUP BY job_name;
```
