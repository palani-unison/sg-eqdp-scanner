# PLAN.md — 15-day execution plan

Detailed day-by-day breakdown of the sprint laid out in `STRATEGY.md` §8. Each day has concrete deliverables, acceptance criteria, and dependencies.

Two parallel tracks:
- **Track A — Python analytical core** (Days 1–10)
- **Track B — Streamlit data-science app** (Days 6–13)
- **Track C — Launch & QA** (Days 14–15)

> **Pivot — 2026-05-04.** Track B was originally a Next.js + Vercel web app. The project has been flipped to **Streamlit** hosted on **Streamlit Community Cloud** (free tier). The new surface lives in `streamlit_app/`. The legacy `web/` directory is retained for reference only and will be deleted once the Streamlit app reaches feature parity.

---

## Track A — Python analytical core

### Day 1 — Universe & repo bootstrap
**Deliverables:**
- `src/universe.py` exposing `get_t1()`, `get_t2()`, `get_t3()`, `get_control()`, returning typed dataclasses
- T1 starter universe (initially empty, populated by SGXNet scraper on Day 6)
- T2 hand-curated seed (~50 names from `docs/TICKERS.md`) + filter logic stub
- T3 from RHB-30 / Maybank-18 / Edge-69 lists baked in
- Control = STI-30 from a static constants file (no scraping yet)
- Apply `db/schema.sql` to your Supabase project

**Acceptance:** `python -c "from src.universe import get_t2; print(len(get_t2()))"` returns ≥48 tickers; `tickers` table populated in Supabase.

### Day 2 — Price ingest & Phase 0 backfill
**Deliverables:**
- `src/data/prices.py` — yfinance adapter with retry (tenacity), schema validation, row-count + date-range + null-rate assertions
- `pipelines/backfill.py` — wraps `daily_score.py` with a wider window, idempotent upserts to `prices_daily`
- Run backfill locally: `python -m pipelines.backfill --start 2020-01-01 --end yesterday`
- Smoke test: `tests/test_prices.py` verifies CapitaLand split is correctly handled

**Acceptance:** `prices_daily` in Supabase has ≥250,000 rows covering ≥200 tickers across 5 years.

### Day 3 — CAPM abnormal returns + Amihud
**Deliverables:**
- `src/returns.py` — CAPM β estimator on a 252-day pre-event window; abnormal return per stock per day; CAR over window
- `src/liquidity.py` — Amihud illiquidity ratio per stock-day; rolling 60-day mean
- Regression-tested against the existing Phase 1 notebook output
- `tests/test_returns.py` and `tests/test_liquidity.py` — toy-example sanity checks

**Acceptance:** unit tests pass; outputs match Phase 1 notebook to within rounding for the 48-stock baseline.

### Day 4 — Event windows + matched-pair DiD
**Deliverables:**
- `src/events.py` — event-window slicing for the four EQDP dates plus arbitrary placebo dates
- `src/matching.py` — propensity-score / nearest-neighbour pairing on (sector, market-cap quintile, pre-event β, pre-event Amihud)
- DiD coefficient with `linearmodels.PanelOLS`, time + entity fixed effects
- Programme-level CAR by tier and by event date

**Acceptance:** DiD coefficient computed for treatment vs matched control across all four event dates; results upserted to `abnormal_returns` table.

### Day 5 — Synthetic control + placebo
**Deliverables:**
- `src/synthetic.py` — CausalImpact wrapper, runs synthetic control for top 15 named beneficiaries on each event date
- `src/tests.py` — placebo runner: same pipeline on 20 random non-event Wednesdays in 2024
- Posterior intervals for per-stock effects; null-distribution for placebo p-values

**Acceptance:** `synthetic_controls` and `placebo_results` tables populated; placebo p-value distribution is approximately uniform (sanity check that the method finds null where it should).

### Day 6 — SGXNet scraper + T1 universe live
**Deliverables:**
- `scrapers/sgxnet/parser.py` — parses substantial-shareholder filings; bi-temporal columns (`effective_date`, `filing_date`)
- `scrapers/sgxnet/manager_aliases.py` — resolves "BlackRock", "BlackRock Inc.", "BlackRock Investment Management Singapore" etc. to one canonical entity
- `scrapers/sgxnet/ratelimit.py` — polite UA + exponential backoff
- `pipelines/weekly_filings.py` — runs the scraper, dedupes, upserts `filings_t1`
- T1 universe populated from real filings

**Acceptance:** `filings_t1` table has ≥1 row per active EQDP manager; scraper unit tests green; structural-change detector configured.

### Day 7 — Decoupled candidate score + Supabase export
**Deliverables:**
- `src/score.py` — implements §4.7 of `STRATEGY.md`: `Score = w₁·LiquidityRise + w₂·InstitutionalProxy + w₃·IndexInclusion + w₄·BrokerNamed + w₅·FilingPresent`
- Returns are not an input. A test asserts this.
- `src/export.py` — writes the canonical "snapshot view" to `candidate_scores` table with `score_date` partitioning
- `tests/test_score.py` — round-trip test: feed varying returns, score must be invariant

**Acceptance:** `candidate_scores` populated for the latest snapshot; round-trip test confirms zero return sensitivity.

### Day 8 — All three pipelines wired
**Deliverables:**
- `pipelines/daily_score.py` — full daily refresh: fetch new prices, recompute CAPM AR, recompute Amihud, recompute candidate score, upsert all gold tables, POST `/api/revalidate?path=/tracker`
- `pipelines/weekly_filings.py` — wraps Day 6 scraper + dedupe
- `pipelines/monthly_full_run.py` — full re-fit including event study + synthetic control + bootstrap CIs
- Each pipeline is a `typer` CLI command with `--dry-run` and `--date` flags
- `pipeline_runs` table records every execution

**Acceptance:** running `python -m pipelines.daily_score --dry-run` against today's date completes < 10 minutes and reports zero rows changed (idempotent on a stable day).

### Day 9 — Bootstrap CIs + robustness pass
**Deliverables:**
- `src/bootstrap.py` — block-bootstrap with 5,000 reps, 5–95 percentile CIs for every headline metric
- Robustness sweep: re-run impact estimator with three β windows (126d, 252d, 504d) and three matching specs
- `bootstrap_cis` table populated; each headline number on the website pulls from this table

**Acceptance:** every chart on `/brief` has a CI shaded around it; robustness sweep results stored and visualisable.

### Day 10 — GitHub Actions wired
**Deliverables:**
- `.github/workflows/daily.yml`, `weekly.yml`, `monthly.yml` cron jobs
- Repo secrets: `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `REVALIDATE_TOKEN`, `RESEND_API_KEY`
- A failing-job email alert via Resend
- `pipeline_runs.status = 'partial' | 'failed'` flag drives the `/tracker` stale banner

**Acceptance:** all three workflows succeed on `workflow_dispatch`; a manually broken job correctly flips the staleness flag.

---

## Track B — Next.js web application

### Day 6 (in parallel with Track A) — `web/` scaffold
**Deliverables:**
- `npx create-next-app@latest web` (App Router, TypeScript, Tailwind)
- shadcn/ui initialised, base components (Button, Card, Table, Tabs, Toast)
- Supabase project provisioned, anon + service keys captured
- Resend domain verified
- Vercel project linked to GitHub, root directory = `web/`
- Disclaimer banner component live, visible on every page from day one

**Acceptance:** `https://<vercel-preview-url>` loads a placeholder hero with the disclaimer banner.

### Day 7 — Public pages
**Deliverables:**
- `/` — landing hero with headline finding, CTA "Read the Brief (free, email required)"
- `/about` — personal-research framing, author bio, link to Disclaimer
- `/disclaimer` — full text from `docs/DISCLAIMER.md`
- Footer disclaimer + copyright on every page

**Acceptance:** all three public routes render correctly; Lighthouse a11y score ≥95.

### Day 8 — Email gate + auth
**Deliverables:**
- `/api/register` — captures name, email, optional firm, optional country, disclaimer consent
- Supabase Auth magic-link flow via Resend
- `EmailGate` component wrapping all gated content
- `/admin/users` — single-admin route listing registrations with engagement metrics (only `ADMIN_EMAIL` may view)

**Acceptance:** registration → magic-link email → click-through → gated content visible. Unauthorised user redirected. Admin route 403s for everyone else.

### Day 9 — `/brief` long-form layout
**Deliverables:**
- `/brief` route with section anchors: programme, problem, universe, methodology, data, findings-programme, findings-stock, findings-non, sector, robustness, limitations
- Static prose written in author's voice (no third-party text)
- Sticky in-page TOC; smooth-scroll
- Disclaimer at top + bottom of full Brief

**Acceptance:** all sections present (placeholder for charts); reading time ≈30 minutes; mobile readability OK.

### Day 10 — Static charts (event studies, sector heatmap)
**Deliverables:**
- `EventStudyChart.tsx` (Recharts) — treatment vs control CAR around each event date, with shaded CI
- Sector heatmap of effect sizes
- Programme-level treatment-vs-control bar chart
- Tier-toggle on universe table

**Acceptance:** charts read directly from Supabase; values match the Python pipeline output to the rounding shown.

### Day 11 — Findings-stock interactive table + per-stock synth-control
**Deliverables:**
- `BeneficiaryTable.tsx` — sortable, filterable, paginated; columns include candidate-score, AR, Amihud Δ, synthetic-control divergence, latest filing
- Per-stock detail drawer or `/brief/stock/[ticker]` route with the synthetic-control fan chart (Plotly, lazy-loaded)
- Footnote linking each filing claim to the SGXNet source URL

**Acceptance:** table works on a 200-row dataset without jank; a click on any row brings up the per-stock chart in <500 ms.

### Day 12 — `/tracker` live page
**Deliverables:**
- `/tracker` with three tabs: Tier 1, Tier 2, Tier 3
- Latest filings feed
- Candidate-score table (current snapshot) and abnormal-return table (latest event window)
- ISR `revalidate: 21600`; manual revalidate via webhook
- Stale-data banner driven by `pipeline_runs.last_success_at`

**Acceptance:** `/tracker` re-renders within 6 hours of a daily-pipeline run completing; stale banner appears if last success > 36 h ago.

### Day 13 — On-demand PDF export + `/methodology`
**Deliverables:**
- `/api/pdf` route — server-side renders the gated `/brief` content into a printable PDF (puppeteer or `@react-pdf/renderer`)
- `/methodology` standalone deep page with formulae and parameter choices
- Edge function for `pg_cron` email blast on new T1 filing

**Acceptance:** PDF download from `/brief` produces a complete, branded export; new T1 filing triggers email to all registered users (test on a single test account first).

---

## Track C — Launch & QA

### Day 14 — End-to-end QA
**Deliverables:**
- Cross-browser registration test (Chrome, Safari, Firefox)
- Every chart cross-checked against the underlying Postgres rows
- Analytics events firing as expected (`engagement_events`)
- Revalidation webhook proved end-to-end
- Phrasing-overlap check vs the third-party PDF — confirm zero verbatim text

**Acceptance:** QA checklist signed off; no high-priority issues open.

### Day 15 — Soft-launch
**Deliverables:**
- Domain pointed to Vercel; TLS cert issued
- Soft-launch to ~10 trusted readers (you pick)
- One-page launch announcement (separate channels — LinkedIn, X, email)
- Archive baseline snapshot of every gold table (Supabase Storage)
- `memory.md` updated with go-live timestamp and post-launch monitoring plan

**Acceptance:** site live on the public domain; first 10 registrations captured; no errors in `pipeline_runs` for 24 h.

---

## Dependencies (which day blocks which)

| Day | Blocks |
|---|---|
| 1 (universe) | Days 2–9 |
| 2 (prices) | Days 3, 4, 5, 7, 8, 9 |
| 6 (SGXNet) | Days 7, 11, 12 (T1 features depend on real filings) |
| 6 (web scaffold) | Days 7–13 |
| 7 (score + export) | Days 8–13 (web reads from Supabase) |
| 10 (GH Actions) | Day 14 (QA needs the daily refresh proven) |

Days 6+ can run in parallel between Tracks A and B once the schema is in place and the Supabase tables exist.
