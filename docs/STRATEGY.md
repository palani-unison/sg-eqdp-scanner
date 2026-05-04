# EQDP Programme — Unified Research & Monitoring Strategy

**Author:** Palaniappan Chidambaram — personal research. Not affiliated with, endorsed by, or representative of Unison Group.
**Synthesised from:** ChatGPT (signal engineering), KimiClaw / OpenClaw (working tracker), and Claude (four-phase roadmap).
**Date:** 2026-05-03
**Revised:** 2026-05-03 — pivot from DOCX/PDF deliverable to a public, email-gated **Next.js web application** with native interactive visualisations and registration tracking.
**Status:** Strategic plan. Drives the analytical codebase, the web build, and the deployment that follow.

---

## 1. Why this document exists

Three independent agents have each proposed an EQDP analysis. The ChatGPT brief gives a tight signal-engineering taxonomy. KimiClaw / OpenClaw shipped working Python that produced a real 49-stock ranking. Claude's roadmap proposes a four-phase, statistically defensible build. Each is partial.

We need:

1. **A public-facing Next.js web application** presenting the research as an email-gated, interactive brief — replacing the static PDF format with a live, visualised, registration-tracked site. Audience is unrestricted (anyone may register), so disclaimers and the personal-research framing are explicit on every page.
2. **A Python analytical codebase** (`src/`) that backs every chart and number on the site and is shareable to a peer who wants to reproduce the work. Analysis, signal engineering, and backtesting are all Python. Scraping is a separate Python module — or initial seeds I pull manually before automation lands.
3. **Continuous refresh** so the site is not a one-shot — new SGXNet filings, new tranches, new price action all update the beneficiary list and the live charts on a weekly / monthly schedule.

This strategy specifies how to do all three.

---

## 2. The single biggest mistake to avoid

**Do not measure returns with returns.**

The OpenClaw `eqdp_tracker_v2.py` "EQDP Score" is built from `total_return`, `volume_change`, `52w_proximity`, `drawdown`, `30d_momentum`. The first and the last are the *outcome we are trying to explain*. A stock that rallied 245 % gets a top score — but that is the question, not the answer. Whether EQDP caused the rally is precisely what the score should not assume.

The core reframing is:

| Component | Inputs | Job |
|---|---|---|
| **Candidate detector** | EQDP-eligibility filters: market-cap band, liquidity, exclusion of STI-30, broker beneficiary lists, SGXNet filings | Identify the *plausible universe* of beneficiaries before any return data |
| **Impact estimator** | Abnormal returns, abnormal volume, abnormal liquidity vs matched control | Quantify the effect on those candidates |
| **Confidence layer** | Bootstrap CIs, placebo tests, synthetic control fit | Tell us how much to trust the impact estimate |

These three are **independent** — the detector cannot see returns; the estimator does not score; the confidence layer interrogates the estimator. This is what separates a forensic study from a momentum chart.

---

## 3. The Three-Tier Beneficiary Universe

We commit to a tiered taxonomy used everywhere in the report and the code.

### Tier 1 — Confirmed
Stocks where one of the nine EQDP-appointed managers has filed a substantial-shareholder disclosure with SGXNet (5 %+ stake) on or after 2025-07-21. Source: SGXNet filings, scraped weekly, with `effective_date` and `filing_date` both retained.

### Tier 2 — Eligible
Stocks that survive a programmatic application of EQDP eligibility criteria (small/mid-cap, SGX Mainboard or Catalist, traded daily, not in STI-30, not in restricted sectors). Computed mechanically from SGX listings + price data; no analyst input.

### Tier 3 — Named
Stocks named by RHB (30 names), Maybank (18), Edge (69), and other broker beneficiary notes. Subjective but useful as a sanity comparator and to bracket inference where filings haven't yet appeared.

### Control — Excluded
STI-30 large caps. EQDP is explicitly de-emphasising these — they are the natural counterfactual for our event studies.

A stock can sit in multiple tiers; the highest tier wins for headline classification. The interesting empirical question is **the overlap and disagreement between tiers**, e.g. how many T3-named names have shown up in T1 filings yet.

---

## 4. Methodology — what we are actually computing

### 4.1 Abnormal returns, not raw returns

For each stock *i* and each event date *t*, abnormal return is:

> AR_{i,t} = R_{i,t} − E[R_{i,t}]

where the expected return is one of:

- **Market-adjusted** (Phase 1, baseline): `E[R] = R_market` where market = STI ETF.
- **CAPM-adjusted** (default for the report): estimate `α_i, β_i` on a 252-day pre-event window ending 30 days before the announcement, then `E[R] = α_i + β_i · R_market`.
- **Fama-French 3-factor** (robustness): adds size and value factors so we do not confuse small-cap rotation with EQDP.

Cumulative abnormal return (CAR) is summed over the event window, e.g. [−5, +20] trading days.

### 4.2 Liquidity — Amihud illiquidity ratio

For each stock-day:

> Amihud_{i,t} = |R_{i,t}| / DollarVolume_{i,t}

Lower is better (the same return is achieved on more volume = deeper market). We compute the change in 60-day rolling Amihud from pre-event to post-event windows. This is the cleanest liquidity signal achievable from daily OHLCV.

### 4.3 Matched-pair difference-in-differences

For each treatment stock, find the closest control by sector, market-cap quintile, pre-event β, and pre-event Amihud. The DiD coefficient is the EQDP effect after partialling out everything the matched control absorbs.

### 4.4 Bayesian synthetic control

For the top 10–15 named beneficiaries, build a synthetic counterfactual price series using a weighted basket of non-EQDP stocks fit to the pre-event period. The post-event divergence is the per-stock effect with full posterior intervals (CausalImpact).

### 4.5 Placebo tests

Run the entire pipeline on dates where nothing happened (e.g. random Wednesdays in 2024). The null distribution of "effects" gives the empirical false-positive rate. If our placebo p-values are not roughly uniform, the method is broken.

### 4.6 Bootstrap confidence intervals

Block-bootstrap the panel 5,000 times; report 5th / 95th percentiles for every headline number. Small samples + fat tails make analytic CIs unreliable.

### 4.7 The candidate score (separate from the impact estimator)

The candidate score is a screen for *plausibility*, not impact, and uses **only inputs the screen cannot circularly observe**:

> Score = w₁ · LiquidityRise + w₂ · InstitutionalProxy + w₃ · IndexInclusion + w₄ · BrokerNamed + w₅ · FilingPresent

where:

- LiquidityRise: change in Amihud, *not* return.
- InstitutionalProxy: ratio of close-to-VWAP days (sustained accumulation).
- IndexInclusion: dummy for iEdge SG Next 50 / mid-cap index membership.
- BrokerNamed: count of T3 lists naming the stock.
- FilingPresent: dummy for any T1 filing.

Total return is **not** an input. Returns appear only on the right-hand side of the impact regression, never as an input to the screen.

---

## 5. The deliverable — a Next.js web application, not a PDF

### 5.1 Why a web app, not a PDF

A static PDF is a snapshot. Our subject is moving — new tranches, new filings, new prices every day. A web app gives:

- **Live charts** that re-render when the underlying data refreshes, instead of frozen images.
- **Email gate + registration tracking** so we know who the readers are (name, email, optional firm), can re-engage them when the brief updates, and can see which sections drive the most engagement.
- **Selective drill-down** — readers see the executive summary unlocked, then trade an email for the full evidence; the rest is interactive.
- **Cheap iteration** — a fix to a number propagates instantly across the site instead of waiting for a regenerated DOCX → PDF cycle.

The PDF format is retained only as an **on-demand export** from the web app for readers who explicitly want one (a "Download PDF of full brief" button) — generated server-side at request time.

### 5.2 Originality and identity

The 3rd-party reference PDF is a descriptive overview. Our site commits to a different identity:

> **A forensic, public-data inference of which Singapore-listed companies the MAS EQDP appointed managers actually bought, with explicit statistical confidence intervals and a clear non-beneficiary list.**

Specifics:

- **No verbatim text** lifted from the 3rd-party PDF, MAS press releases, or broker notes. All programme description is in our voice.
- **All charts ours** — Plotly / Recharts / D3, generated from our pipeline, with our colour palette.
- **Our taxonomy** (T1 confirmed / T2 eligible / T3 named) is original to this work.
- **Our headline finding** drives the framing — to be filled in by the actual analytical results, not back-fitted to a desired narrative.

### 5.3 Site map (what the 30 "pages" become)

The 30-page brief maps to a long-form scrolling site with section anchors plus a few dedicated routes. Email gate sits between executive summary and full content.

| Route | Section | Gate | Purpose |
|---|---|---|---|
| `/` | Landing — hero, headline finding, disclaimer banner, CTA "Read the brief (free, email required)" | Public | Hooks the reader |
| `/brief` | Executive summary — top-line finding, methodology one-paragraph, key chart | Public preview | Sells the registration |
| `/brief#programme` | Programme background in our voice | Gated | Who, what, when, how much |
| `/brief#problem` | The analytical problem | Gated | Why "who benefited" is non-trivial |
| `/brief#universe` | T1 / T2 / T3 universe construction with interactive tier-toggle table | Gated | Show the tiers |
| `/brief#methodology` | CAPM AR, DiD, synthetic control, placebo — accessible to non-quants, with collapsible math | Gated | Credibility |
| `/brief#data` | Data sources & provenance with fetch timestamps | Gated | Reproducibility |
| `/brief#findings-programme` | Programme-level event-study charts (4 event dates × treatment vs control) | Gated | The empirical core |
| `/brief#findings-stock` | Top-20 beneficiaries — sortable interactive table, click-through to per-stock synthetic-control charts | Gated | The actionable list |
| `/brief#findings-non` | Non-beneficiaries & negative results | Gated | Honesty signal |
| `/brief#sector` | Sector / style decomposition | Gated | Where the alpha concentrated |
| `/brief#robustness` | Robustness & placebo tests | Gated | The credibility appendix |
| `/brief#limitations` | Limitations & open questions | Gated | What this study cannot prove |
| `/tracker` | **Live tracker** — refreshed daily; T1 / T2 / T3 tabs, latest filings feed, candidate-score table, abnormal-return table | Gated | The recurring-visit page |
| `/methodology` | Standalone deep-methodology page with formulae, parameter choices, code references | Gated | For quants |
| `/about` | Personal-research framing, author bio, disclaimer, contact | Public | Required for trust |
| `/disclaimer` | Full disclaimer text | Public | Must be reachable from every footer |
| `/api/register` | Email capture endpoint | n/a | Backend |
| `/api/data/*` | Read-only JSON feeds for charts | Gated | Backend |

A "Download PDF" button on `/brief` calls a server-side route that renders the gated content to PDF on demand — the PDF is the by-product, the web app is the canonical artefact.

### 5.4 Email gate and registration tracking

- **Capture fields**: name, email, optional firm/role, optional country. Tick-box for "I have read the disclaimer."
- **Verification**: magic-link email (one-tap, no password). Recommended provider: **Resend** for transactional email + **Supabase Auth** for the magic-link flow and the user table.
- **Database**: Supabase (Postgres) for users, sessions, and event log. Free tier is plenty.
- **Tracking captured per session**: pageviews per section, time on page, last-active timestamp, downloaded-PDF flag, returned-after-email-update flag.
- **Privacy stance**: explicit on the registration page — "We track which sections you read. We will email you when the analysis updates. We do not share your email. You can unsubscribe with one click."
- **Owner view**: a `/admin/users` route (single hardcoded admin email = Palani's) listing registrations + engagement metrics. Not visible to anyone else.

### 5.5 Hosting & stack (defaults — confirm or override)

- **Frontend**: Next.js 15 (App Router) + TypeScript + Tailwind + shadcn/ui. Hosted on **Vercel** (free hobby tier; upgrade only if traffic demands it).
- **Charts**: Recharts for simple cases, Plotly.js (lazy-loaded) for the heavier interactive ones (synthetic-control fan charts, event-study time-series).
- **Auth, DB, and gold-tier storage**: **Supabase** — Auth (magic links), Postgres (the analytical gold layer + user tables), Storage (large blobs / Parquet snapshots). Free tier sufficient for years.
- **Email**: Resend transactional API (free tier: 3,000/month).
- **Pipeline runner**: **Hybrid (see §7)**. **GitHub Actions** runs the heavy Python jobs — yfinance refresh, SGXNet scrape, statsmodels regressions, CausalImpact synthetic control. **Supabase Edge Functions** (Deno/TypeScript) handle the lightweight glue — magic-link helpers, the `/api/revalidate` webhook, and the `pg_cron`-triggered email blast when a new T1 filing appears. Edge Functions cannot run Python and have a 150-second free-tier cap, so they are wrong for the analytical pipeline — but right for short request-time logic.
- **Repository**: a single public GitHub monorepo named **`sg-eqdp-scanner`**, MIT licensed, containing `src/`, `scrapers/`, `pipelines/`, `web/`, `db/`, `tests/`. Vercel deploys the `web/` directory; GitHub Actions runs the pipeline; Supabase reads/writes the database.
- **Domain**: TBD — `eqdp-brief.com` is the working proposal.
- **Analytics**: Vercel Analytics (built-in, privacy-friendly) + a custom `engagement_events` table in Supabase for section-level tracking that the `/admin/users` page reads.

### 5.6 Data flow into the web app

The data does **not** live in the git repo. Daily prices, abnormal returns, candidate scores, T1 filings — all of it lives in Supabase Postgres tables. Git stays clean of analytical churn; the data is queryable from anywhere; historical depth grows without bloating the repo.

```
GitHub Actions runner (Python)        Supabase                  Vercel (Next.js)
─────────────────────────────         ────────                  ─────────────────
pipelines/daily_score.py
   ├─ yfinance fetch
   ├─ src/returns.py (CAPM AR)        Postgres tables            web app reads via
   ├─ src/score.py                    ─────────────              Supabase JS client
   └─ supabase-py upsert  ──────────► prices_daily      ◄──────  /tracker (ISR 6 h)
                                      abnormal_returns           /brief charts
                                      candidate_scores           /admin/users
pipelines/weekly_filings.py           filings_t1
   ├─ scrapers/sgxnet/parser.py       betas, factor_returns
   └─ supabase-py upsert  ──────────► synthetic_controls
                                      placebo_results            edge function:
pipelines/monthly_full_run.py         pipeline_runs              ─────────────
   ├─ event-study refresh             ──────────────             POST /api/revalidate
   ├─ synthetic-control refresh       Edge Functions             on row insert via
   └─ supabase-py upsert  ──────────► (Deno/TypeScript)          pg_cron / triggers
                                      ──────────────
                                      /api/register
                                      /api/email-blast (T1)
                                      /api/revalidate-hook
```

The web app reads the latest snapshot of each Postgres table on every request (with appropriate Next.js caching: `revalidate: 21600` for `/tracker`, full SSG for static `/brief` charts that only change on the monthly rerun). When a new T1 filing is inserted, a Postgres trigger fires an Edge Function that (a) sends the email blast via Resend and (b) calls the Vercel revalidate webhook to refresh `/tracker` immediately.

---

## 6. Code architecture

The current state is a single Phase-1 notebook (`notebooks/eqdp_analysis.ipynb`) and a Databricks-format mirror (`eqdp_analysis_databricks.py`), plus the OpenClaw tracker scripts in `Research/OpenClaw/`. The target is a modular `src/` tree the report and the monitor both consume.

```
eqdp_project/
├── src/                              # Python analytical core
│   ├── universe.py                   # T1/T2/T3 ticker construction + control
│   ├── data/
│   │   ├── prices.py                 # yfinance adapter, retry, schema validation
│   │   ├── sgxnet.py                 # substantial-shareholder scraper, polite + cached
│   │   ├── index.py                  # iEdge SG Next 50 + STI constituent loaders
│   │   └── factors.py                # FF3 factor returns (constructed from SGX universe)
│   ├── returns.py                    # CAPM β estimation, abnormal returns, CAR
│   ├── liquidity.py                  # Amihud, turnover velocity
│   ├── events.py                     # event-window slicing, panel construction
│   ├── matching.py                   # propensity-score / nearest-neighbour pairing
│   ├── synthetic.py                  # CausalImpact / Augmented synthetic control
│   ├── tests.py                      # placebo, bootstrap CIs
│   ├── score.py                      # candidate screen (no return inputs)
│   ├── viz.py                        # static figure builders (matplotlib for PDF export only)
│   └── export.py                     # writes gold tables to web/public/data/*.json
├── notebooks/
│   ├── eqdp_analysis.ipynb           # legacy Phase 1 notebook (kept)
│   └── eqdp_analysis_databricks.py   # Databricks-source-format mirror
├── pipelines/
│   ├── daily_score.py                # refresh prices + recompute candidate scores
│   ├── weekly_filings.py             # SGXNet scrape + T1 universe update
│   ├── monthly_full_run.py           # full re-run + JSON regeneration
│   └── trigger_revalidation.py       # POST to Vercel revalidate webhook
├── scrapers/                         # explicit folder — separable from analytical code
│   └── sgxnet/
│       ├── parser.py                 # HTML structure handling
│       ├── manager_aliases.py        # BlackRock entity-resolution map etc.
│       └── ratelimit.py
├── data/
│   ├── raw/                          # immutable, append-only, partitioned by date
│   ├── silver/                       # cleaned, deduplicated, conformed
│   └── gold/                         # analytics-ready joined panels (Parquet)
├── web/                              # Next.js application
│   ├── app/
│   │   ├── page.tsx                  # /  (landing, public)
│   │   ├── brief/page.tsx          # /brief (gated content)
│   │   ├── tracker/page.tsx          # /tracker (live, ISR)
│   │   ├── methodology/page.tsx
│   │   ├── about/page.tsx            # personal-research framing
│   │   ├── disclaimer/page.tsx
│   │   ├── admin/users/page.tsx      # admin-only registration view
│   │   └── api/
│   │       ├── register/route.ts     # email capture + magic link
│   │       ├── pdf/route.ts          # on-demand PDF generation
│   │       └── revalidate/route.ts   # webhook from Python pipeline
│   ├── components/
│   │   ├── EmailGate.tsx
│   │   ├── DisclaimerBanner.tsx
│   │   ├── EventStudyChart.tsx       # Recharts
│   │   ├── SyntheticControlChart.tsx # Plotly (lazy-loaded)
│   │   ├── BeneficiaryTable.tsx      # sortable, filterable
│   │   └── TierToggle.tsx
│   ├── lib/
│   │   ├── supabase.ts               # client + server helpers
│   │   ├── auth.ts                   # magic-link flow
│   │   ├── tracking.ts               # section-pageview events
│   │   └── data.ts                   # JSON loaders
│   ├── public/                       # static assets only — favicons, OG images
│   └── package.json
│   # Note: gold-tier analytical data lives in Supabase Postgres, not under web/public/data/.
│   # The Next.js app reads via the Supabase JS client at request/build time.
├── db/
│   ├── schema.sql                    # canonical Postgres schema (mirror of §7.3 data model)
│   ├── migrations/                   # versioned SQL migrations
│   ├── triggers/                     # Postgres triggers (e.g. on filings_t1 insert → edge fn)
│   └── edge_functions/               # Deno/TypeScript edge functions
│       ├── email-blast/index.ts      # invoked by pg_cron when new T1 filing detected
│       ├── revalidate-hook/index.ts  # idempotent revalidate proxy to Vercel
│       └── pipeline-alert/index.ts   # alerting on pipeline_runs.status = 'failed'
├── report/                           # only used for the on-demand PDF export
│   └── pdf_template/                 # @react-pdf/renderer or puppeteer template
└── tests/
    ├── test_returns.py               # CAPM AR on a toy example
    ├── test_liquidity.py             # Amihud on a toy example
    ├── test_score.py                 # candidate score isolated from returns
    ├── test_pipeline.py              # end-to-end smoke test
    └── web/                          # Playwright tests for the registration flow
```

The legacy notebook becomes a ~50-line orchestration shell. All Python logic lives in `src/`, all logic is tested. The Next.js app reads only the JSON files in `web/public/data/` — it never imports Python or runs analytical code itself.

### Code-quality non-negotiables

- Type hints on every function signature; `mypy --strict` clean.
- Every fact carries provenance: source, fetch UTC timestamp, parser version.
- All financial dates: `pd.Timestamp` with explicit `tz_localize(None)`.
- Bi-temporal columns (`effective_date`, `filing_date`) on everything that has a publication lag — index inclusions, filings, analyst initiations.
- Unit tests for every analytical metric, regression test on a fixed historical snapshot.
- No look-ahead — the test that fails before `filing_date` is enforced is the most important test in the repo.

---

## 7. Pipeline & deployment — the hybrid runner architecture

The OpenClaw scripts in `Research/OpenClaw/` already produce a useful daily snapshot. They become the *seed* of the production pipeline that feeds the web app — but the production pipeline is split across two execution environments because no single runner is good at both heavy Python and lightweight request-time TypeScript.

### 7.0 Phase 0 — laptop-first backfill, then cloud-incremental

The work splits cleanly into two compute regimes:

| Phase | What runs | Where | Cadence | Cost |
|---|---|---|---|---|
| **Phase 0 — backfill** | 5 years of historical OHLCV for ~200 tickers, initial CAPM betas, full event-study CARs around all four EQDP dates, synthetic-control fits for top 15 named beneficiaries, bootstrap CIs, full placebo run | **Palani's laptop** | One-shot | $0 |
| **Phase 1 — incremental** | Yesterday's prices, today's abnormal returns, today's candidate scores, weekly new-filing scrape, monthly synth-control refit | Cloud runner (see §7.1) | Daily / weekly / monthly | $0–5 / month |

The backfill is the only slow run (~30–60 minutes the first time, depending on yfinance throttling). After it, every cloud job processes one day's increment and finishes in under 10 minutes. This means *any* of the cloud runners listed in §7.1 is fast enough — the choice is about ops simplicity, not compute power.

The laptop backfill writes to the same Supabase Postgres tables the cloud runner will eventually upsert into. There is no second codebase: `pipelines/backfill.py` is just `pipelines/daily_score.py` with a wider date range. This means the moment the cloud runner is wired up, it picks up from where the laptop left off.

### 7.1 Why hybrid (and not pure-GitHub-Actions or pure-Edge-Functions)

| | GitHub Actions | Supabase Edge Functions |
|---|---|---|
| Language / runtime | Any (we use Python 3.11) | Deno + TypeScript only |
| Max runtime | 6 hours | 150 s (free), 400 s (Pro) |
| Pandas / statsmodels / CausalImpact | ✅ first-class | ❌ no Python equivalents |
| yfinance / scraping | ✅ | weak (no requests/BS4) |
| Scheduled jobs | ✅ via cron expressions | ✅ via `pg_cron` |
| Direct Postgres access | indirect (HTTP) | ✅ native low-latency |
| Cost at our scale | $0 (public-repo unlimited) | $0 (free tier) |
| Right job | **Heavy analytical pipeline** | **Auth helpers, webhooks, alerts** |

So:

- **GitHub Actions** runs everything that says `import pandas` — the daily refresh, the weekly scrape, the monthly full rerun, the placebo tests, the synthetic control. It writes results directly into Supabase Postgres via `supabase-py`. No git data churn.
- **Supabase Edge Functions** handle short, request-time logic — magic-link email send, the `/api/revalidate` webhook handler, the `pg_cron`-triggered email blast when a new T1 filing row appears. They never run analytical code; they trigger and respond.
- **Supabase Postgres** is the single source of truth for analytical results and user state. The web app reads from it directly via the Supabase JS client. The Python pipeline writes to it from GitHub Actions.

### 7.2 What changes from the existing OpenClaw scripts

- The "EQDP Score" is replaced by the **decoupled candidate score** from §4.7 — no total-return input.
- A separate column reports **abnormal return** computed against a CAPM benchmark, clearly labelled — so momentum and abnormality are visible in the same row without being conflated.
- Three rankings, not one: T1 confirmed, T2 eligible, T3 named. Each table answers a different question on the web app.
- Every row carries an `eqdp_tier` column.
- Coverage extends from the Next 50 to the full T2-eligible universe (~150–200 names) once the SGX listing scraper lands.
- Output destination changes from `~/.openclaw/workspace/*.csv` to **Supabase Postgres tables** — the CSV is regenerated as a downloadable artefact, not as the system of record.

### 7.3 The Postgres data model (gold layer)

The minimum viable schema. All tables get `created_at timestamptz default now()` and an explicit `pipeline_run_id` for traceability.

| Table | Purpose | Primary key | Approx rows/year |
|---|---|---|---|
| `tickers` | Universe metadata | `ticker` | ~300 (one-shot) |
| `prices_daily` | OHLCV per ticker per trading day | `(ticker, trade_date)` | ~50,000 |
| `factor_returns` | FF3 factors (market, smb, hml) | `trade_date` | ~250 |
| `betas` | Rolling CAPM β estimates | `(ticker, window_end)` | ~3,000 |
| `abnormal_returns` | AR & CAR per ticker per event window | `(ticker, event_id, t)` | ~25,000 |
| `liquidity_metrics` | Amihud illiquidity, turnover velocity | `(ticker, trade_date)` | ~50,000 |
| `candidate_scores` | Decoupled score per ticker per snapshot date | `(ticker, score_date)` | ~50,000 |
| `synthetic_controls` | Observed vs counterfactual price paths | `(ticker, event_id, t)` | ~10,000 |
| `placebo_results` | Null-distribution effects on non-event dates | `(placebo_date, panel)` | ~500 |
| `bootstrap_cis` | Confidence intervals for headline metrics | `(metric, scope)` | ~200 |
| `filings_t1` | SGXNet substantial-shareholder filings by EQDP managers | `filing_id` | ~50–200 |
| `pipeline_runs` | One row per pipeline execution | `run_id` | ~400 |
| `users` | Supabase Auth managed | `auth.users.id` | bounded by registrations |
| `user_profiles` | Name, firm, country, registered_at | `user_id` | same |
| `engagement_events` | Section pageviews, time on page | `(user_id, event_at)` | grows with traffic |

Total raw rows after one year: low single-digit millions. Supabase free tier (500 MB) handles this comfortably with proper indexes; we'll add table partitioning by year before approaching limits.

### 7.4 The schedule

| Cadence | Runner | Job | Action | Web-app effect |
|---|---|---|---|---|
| Daily 18:30 SGT | GitHub Actions | `pipelines/daily_score.py` | yfinance refresh, recompute candidate scores + abnormal returns, upsert into `prices_daily`, `abnormal_returns`, `candidate_scores`. POST `/api/revalidate?path=/tracker`. | `/tracker` reflects today's prices |
| Weekly Sun 22:00 SGT | GitHub Actions | `pipelines/weekly_filings.py` | SGXNet scrape, dedupe, upsert into `filings_t1`. Postgres trigger fires Edge Function for email blast. | New filings on `/tracker`; registered users emailed |
| Monthly first Mon 06:00 SGT | GitHub Actions | `pipelines/monthly_full_run.py` | Full event-study + synthetic-control rebuild, upsert all gold tables, archive snapshot to Supabase Storage. POST `/api/revalidate-all`. | All static `/brief` charts refresh |
| On `filings_t1` insert | Edge Function (`pg_cron` trigger) | `email-blast` | Resend transactional email to all `user_profiles` opted in. | n/a (email side-effect) |
| On any pipeline failure | Edge Function | `pipeline-alert` | Email Palani; flip `pipeline_runs.status = 'failed'` so the web app shows a stale-data banner. | Yellow banner on `/tracker` if run age > 36 h |

### 7.4b Cloud runner options (alternatives, ranked)

You asked: where else can Python run on a schedule? Several places. All produce the same result — the Python pipeline writes to Supabase Postgres — so this is purely an ops choice.

| Option | Free-tier reality | Python feel | Verdict |
|---|---|---|---|
| **GitHub Actions** | Public repos: **unlimited** minutes. Private: 2,000 min/month. | YAML + checkout + setup-python + run. | ✅ **Default for `sg-eqdp-scanner`** because the repo is public, so cron minutes are free forever. Lives in the same place as the code. |
| **Modal** (`modal.com`) | $30/month free credit, ~30 hours of CPU. Schedules are first-class Python: `@modal.function(schedule=modal.Cron("30 10 * * *"))`. | Python-native; no YAML; functions live next to your code. | ✅ Best DX. Recommended *alternative* if you want to keep cron in Python and out of GitHub. Daily/weekly/monthly easily fits the free credit. |
| **Fly.io machines** | $5/month allowance for tiny machines; can run cron via `fly machine` schedules. | Containerised, full Python. | ⚙️ Works, but more ops than the above. |
| **Render Cron Jobs** | Used to be free; now requires the $7/month paid plan. | Containerised. | ❌ No longer free; skip. |
| **Railway** | $5/month minimum after trial. | Containerised. | ❌ Not free; skip unless you already use it. |
| **PythonAnywhere** | Free tier with one daily scheduled task; limited CPU seconds. | Native Python, web-based editor. | ⚙️ Works for daily but not for weekly+monthly without paying. |
| **AWS Lambda** | 1M requests/month + 400k GB-seconds free. 15-min hard cap per invocation. | Container or zip; needs IaC. | ⚙️ Cheap and reliable but heavy on setup; the 15-min cap is fine for our jobs. |
| **Self-hosted (laptop, Raspberry Pi, home server, $5 VPS)** | $0–5/month. cron + a `.env` file. | Just Python. | ⚙️ Maximum control, maximum ops. Good if you already keep a machine on. |
| **Cloudflare Workers / Supabase Edge Functions** | Free, but **Deno/TypeScript only** — cannot run pandas / statsmodels / yfinance. | n/a for our analytical stack. | ❌ Wrong tool for the heavy Python job. Used for glue (§7.1). |

**Recommendation:** start with **GitHub Actions** — it is free forever for `sg-eqdp-scanner` (public repo), shares secrets with the repo, and needs no extra account. If the YAML annoys you or you want one fewer tool to think about across the stack, **Modal** is the next pick. Both are equally good at the actual work; the choice is which UX you prefer.

A Modal version of the daily job for comparison, so the alternative is concrete:

```python
# pipelines/modal_app.py
import modal

app = modal.App("sg-eqdp-scanner")

image = (
    modal.Image.debian_slim()
    .pip_install_from_requirements("requirements.txt")
)

@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase")],
    schedule=modal.Cron("30 10 * * *"),  # 18:30 SGT
    timeout=600,
)
def daily_score():
    from pipelines.daily_score import run
    run()
```

Two `@app.function(...)` decorators for weekly and monthly are the only additions needed.

### 7.5 What a GitHub Actions workflow looks like

```yaml
# .github/workflows/daily.yml
name: daily-score
on:
  schedule:
    - cron: '30 10 * * *'  # 18:30 SGT = 10:30 UTC
  workflow_dispatch:
jobs:
  refresh:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -r requirements.txt
      - run: python -m pipelines.daily_score
        env:
          SUPABASE_URL:           ${{ secrets.SUPABASE_URL }}
          SUPABASE_SERVICE_KEY:   ${{ secrets.SUPABASE_SERVICE_KEY }}
          REVALIDATE_TOKEN:       ${{ secrets.REVALIDATE_TOKEN }}
```

Three secrets in the repo — Supabase URL, Supabase service-role key (write access), Vercel revalidate token. The Python code uses `supabase-py` to upsert rows. No git commit, no data churn in the repo.

### 7.6 Failure handling

- **yfinance throttling** → exponential backoff + retry, max 3 attempts. After 3 failures, write `pipeline_runs.status = 'partial'` so `/tracker` shows a yellow "data is stale" banner with the timestamp of the last successful run.
- **SGXNet HTML drift** → parser unit tests run on every PR, refuse merge if golden-file diff fails. A live structural-change check runs at the start of `weekly_filings.py` and short-circuits if the page layout has shifted, alerting Palani.
- **Edge Function failure** → Supabase logs + email alert; the `/api/revalidate-hook` is idempotent so retries are safe.
- **Vercel deploy failure** → Vercel email + Slack notification to Palani.
- **Stale data** → if `pipeline_runs.last_success_at` is more than 36 h old, `/tracker` and `/brief#findings-stock` show a yellow staleness banner with the exact timestamp.

### 7.7 Cost reality

- Daily price refresh: 200 tickers × 1 yfinance call, ~5 min, $0 (GitHub Actions free for public repos = unlimited minutes).
- Weekly SGXNet scrape: ~100 polite HTTP requests, ~15 min, $0.
- Monthly full rerun: ~20 min single-machine pandas, $0.
- Postgres storage: low single-digit millions of rows after a year, well within the 500 MB free tier.
- Supabase Storage (Parquet snapshots, archive): ~1 GB after 5 years, within the 1 GB free tier.
- Edge Function invocations: a few hundred per week — within the 500k/month free tier with vast headroom.
- Vercel hobby plan: free up to ~100 GB bandwidth and 6,000 build minutes/month.
- Resend: 3,000 emails/month free; we send one blast on each new filing, plus the magic-link emails.
- Domain: ~$12/year.

Total monthly run cost: **$0–5** for years, until either (a) traffic exceeds Vercel's bandwidth limit, (b) Postgres exceeds 500 MB, or (c) email volume exceeds Resend's 3k/month — all of which would be good problems to have.

---

## 8. Sequenced execution plan (the next 15 working days)

The pivot to a web app adds roughly five days of frontend / auth / deployment work on top of the analytical sprint. The two tracks run in parallel where possible.

### Track A — Python analytical core (Days 1–10)

| Day | Deliverable |
|----|---|
| 1 | This strategy approved; T1/T2/T3 universe lists drafted from existing 48-stock seed |
| 2 | `src/universe.py` + `src/data/prices.py` + unit tests; data flowing for full T2 (~150–200 names) |
| 3 | `src/returns.py` (CAPM AR) + `src/liquidity.py` (Amihud); regression-tested against Phase 1 baseline |
| 4 | `src/events.py` (event windows) + `src/matching.py` (matched-pair DiD); programme-level + per-stock CAR ready |
| 5 | `src/synthetic.py` for top 15 named beneficiaries; placebo run on non-event Wednesdays |
| 6 | `scrapers/sgxnet/` filing scraper; T1 universe live; manager-alias resolution table built |
| 7 | `src/score.py` decoupled candidate score; `src/export.py` writes JSON to `web/public/data/` |
| 8 | `pipelines/daily_score.py` + `pipelines/weekly_filings.py` + `pipelines/monthly_full_run.py` |
| 9 | Bootstrap CIs everywhere; robustness pass; verify every brief number ties to a code line |
| 10 | GitHub Actions wired for daily/weekly/monthly cadence; pipeline status JSON for stale-banner |

### Track B — Next.js web application (Days 6–13, overlaps Track A)

| Day | Deliverable |
|----|---|
| 6 | `web/` scaffold: Next.js 15 + Tailwind + shadcn/ui; Supabase project provisioned; Resend domain verified |
| 7 | `/`, `/about`, `/disclaimer`, footer disclaimer banner; copy in author's voice |
| 8 | Email gate: `/api/register`, magic-link via Supabase + Resend; `EmailGate` component; `admin/users` |
| 9 | `/brief` long-form layout with section anchors; static-content sections (programme, problem, methodology) |
| 10 | Static charts (event studies, treatment-vs-control bars, sector heatmap) using Recharts; reads from `web/public/data/*.json` |
| 11 | `/brief#findings-stock` interactive sortable table; per-stock synthetic-control fan charts (Plotly, lazy-loaded) |
| 12 | `/tracker` live page with ISR; tier-toggle, filings feed, stale-data banner |
| 13 | `/api/pdf` on-demand PDF export (puppeteer or @react-pdf/renderer); `/methodology` standalone page |

### Track C — Launch & QA (Days 14–15)

| Day | Deliverable |
|----|---|
| 14 | End-to-end QA: registration flow tested across browsers; every chart cross-checked against the underlying Parquet; analytics events firing; revalidation webhook proved; non-overlap check vs the 3rd-party PDF for phrasing |
| 15 | Domain pointed to Vercel; soft-launch to ~10 trusted readers; one-page launch announcement; archive baseline snapshot of every gold table |

---

## 9. Headline findings to expect (hypotheses, not foregone conclusions)

These are *predictions to test*, not claims to make:

1. **Programme-level CAR is positive for T1+T2 versus STI control**, but smaller than the +6.8 pp Phase 1 raw figure — much of that will be absorbed by CAPM β. Expected residual after CAPM: somewhere in +2 to +5 pp, with bootstrap CI straddling zero on the announcement date but tightening on the tranche dates.
2. **The strongest per-stock evidence will be in industrial small-caps with prior international research coverage** (Frencken, UMS, CSE Global) — managers prefer deployable liquidity and the names already had institutional infrastructure. Synthetic control divergence likely 10–20 % over 6 months.
3. **REITs benefit second-order**, mostly via index re-rating rather than direct EQDP buying. Effect detectable but smaller and noisier.
4. **Many T3-named stocks will fail to show T1 filings** because positions stayed under 5 % — visible only by inference, not confirmation. Honest reporting of this gap is a credibility win.
5. **Several star performers in the OpenClaw tracker (Hong Leong Asia, Food Empire) will not survive the abnormal-return test** — their moves are explained by company-specific stories, not EQDP. We say so.

If the data refuses any of these, we change the narrative. The point of the methodology is to be wrong cleanly.

---

## 10. What we are explicitly not doing (and why)

- **Not paying for an SGXNet API.** The scraper is sufficient. If volume grows beyond what daily polite scraping can handle, we revisit.
- **Not building intraday microstructure.** Phase Advanced Track A. Out of scope until the brief exists and someone asks for tick-level evidence.
- **Not publishing recommendations.** The brief is descriptive ("did EQDP work, and for whom"). Trade ideas are downstream and require disclosures we don't take on here.
- **Not migrating to Spark / Delta.** ~20 GB fits in pandas + DuckDB. Doing so would burn a week and improve nothing measurable.
- **Not asking the LLM to write conclusions before the regressions land.** Headlines come from the data, not the prompt.

---

## 11. Open decisions

Most have been resolved by the 2026-05-03 revision. What remains:

| # | Decision | Recommended default |
|---|----------|---------------------|
| 1 | **Domain name** | Reserve `eqdp-brief.com` and a personal vanity such as `palanichidambaram.com`; point the site to the former, link from the latter |
| 2 | **Should the brief name specific managers** (e.g. "BlackRock holds X") where filings exist | Yes — but only with filing-derived language and a clickable link to the SGXNet source URL on every claim |
| 3 | **Acceptable lag on T1 filing alerts** | Next-business-morning is fine for v1; same-day is a v2 perk |
| 4 | **GitHub user/org for the repo** (decided at Claude-Code CLI login) | Whatever Palani's preferred GitHub identity is; repo name fixed = `sg-eqdp-scanner` |

**Resolved (locked):**
- ✅ Format: Next.js web app, branded as the **EQDP Brief** (deliberately distinct from the third-party "dossier" terminology). PDF only as on-demand export.
- ✅ Audience: public — anyone may register
- ✅ Authorship: Palaniappan Chidambaram, personal research, explicitly **not** under Unison Group
- ✅ Disclaimer: present on every page (banner + footer + dedicated `/disclaimer` route)
- ✅ Codebase: Python first for analysis / signals / backtests; scrapers as a separate module
- ✅ Stack: **Next.js 15** + TypeScript + Tailwind + shadcn/ui, Recharts + Plotly, **Supabase** (Auth + Postgres + Storage + Edge Functions), Resend (email)
- ✅ Repository: **public GitHub monorepo** named **`sg-eqdp-scanner`** under MIT licence — analytical code, web app, edge functions, and pipeline configs all in one repository so any reader can clone, run, and verify the analysis themselves
- ✅ Hosting: **Vercel** (Next.js app) + **Supabase** (DB + auth + edge functions) — both free tiers
- ✅ Pipeline runner: **two phases**.
  - **Phase 0 backfill runs on laptop** — one-shot, ~30–60 min, writes initial 5 years of data into Supabase Postgres.
  - **Phase 1 incremental runs on GitHub Actions** — daily/weekly/monthly cron, free forever for the public repo, secrets shared natively with `sg-eqdp-scanner`. Modal is documented in §7.4b as a future fallback only; not used in v1.
  - **Supabase Edge Functions** handle short request-time TypeScript glue only (auth helpers, revalidate webhook, `pg_cron`-triggered email blasts). Edge Functions cannot be the analytical runner — Deno only, 150-second free-tier cap.
- ✅ Data storage: **Supabase Postgres** is the system of record for the gold layer. Schema is in §7.3. Daily snapshots stay in the database — no committed JSON in git, so the repo stays clean as historical depth grows.

---

## 12. Bottom line

We have three pieces in front of us:
- A strong but circular signal model (ChatGPT)
- A working but score-conflating tracker (KimiClaw / OpenClaw)
- A rigorous but slow four-phase plan (Claude)

The right move is a 15-day sprint, run as two parallel tracks:

1. **Python analytical core** (Days 1–10) — decouples the candidate detector from the impact estimator, applies Phase-2-grade methodology (CAPM AR, DiD, synthetic control, placebos) on the existing universe, and adds SGXNet ground truth in a separable scraper module.
2. **Next.js web application** (Days 6–13) — public, email-gated brief with interactive Recharts / Plotly visualisations, magic-link auth via Supabase + Resend, on-demand PDF export, and a live `/tracker` page that revalidates daily.
3. **Launch** (Days 14–15) — QA, domain, soft-launch to a small reader list.

Outcome: a permanent, refreshable, registration-tracked, public-facing research site under Palani's personal authorship, with disclaimers on every page, fully reproducible Python code behind every claim, and a continuous refresh cadence so the work stays current as the EQDP programme deploys further capital.

Status after this strategy: **decision document approved → execution begins.**

---

## 13. Disclaimer language (canonical text — re-used across the site)

The following text is the canonical disclaimer used on the site footer, the registration consent checkbox, the `/disclaimer` route, and the introduction of any downloadable PDF.

### 13.1 Banner (every page, top — sticky)

> **This is the personal research of Palaniappan Chidambaram. It is not investment advice, not affiliated with Unison Group, and may contain errors. Read the [full disclaimer](/disclaimer) before using any of this content.**

### 13.2 Registration consent (checkbox required to submit email)

> I have read and accept the [Disclaimer](/disclaimer). I understand this is the personal research of Palaniappan Chidambaram, that it is not investment advice, that the analysis is inferential because the MAS does not disclose specific holdings of EQDP-appointed managers, and that I am responsible for my own investment decisions. I consent to receiving email updates when the analysis refreshes; I can unsubscribe with one click.

### 13.3 Full disclaimer page (`/disclaimer`)

> **About this work**
>
> This site presents the personal research of Palaniappan Chidambaram. It is not affiliated with, endorsed by, or representative of Unison Group, the Monetary Authority of Singapore, the Singapore Exchange, or any of the asset managers mentioned. Views expressed are the author's own.
>
> **Not investment advice**
>
> Nothing on this site constitutes investment advice, an offer to buy or sell securities, or a recommendation of any kind. The author is not a licensed financial adviser. Information is provided for research and educational purposes only. Readers must conduct their own due diligence and, where appropriate, consult a licensed adviser before making any investment decision.
>
> **Inferential nature of the analysis**
>
> The MAS Equity Market Development Programme does not publicly disclose which specific Singapore-listed companies its appointed managers have purchased. Beneficiary identification on this site is *inferential* — it combines (a) eligibility criteria from public programme design, (b) public broker-research beneficiary lists, (c) market-microstructure changes around event dates, and (d) SGXNet substantial-shareholder filings (positions of 5 % or more). Sub-5 % positions are invisible to public filing; meaningful EQDP capital may be deployed in stocks that never appear in our T1 universe. Inference is not proof.
>
> **Data sources and accuracy**
>
> Price and volume data is sourced from Yahoo Finance via the `yfinance` library. Filing data is scraped from SGXNet. Programme-design and event-date information is drawn from public MAS press releases and accompanying media. While reasonable care is taken, no representation or warranty is made as to the accuracy, completeness, or timeliness of any information, and the author accepts no liability for any loss arising from reliance on it. Data may be delayed; cited timestamps reflect the most recent successful refresh.
>
> **Forward-looking statements**
>
> Any statement about future market behaviour or programme deployment is speculative and based on the author's interpretation of public information. Past performance does not indicate future results.
>
> **Conflicts of interest**
>
> The author may from time to time hold personal positions in securities discussed on this site. The author does not act on behalf of any client and receives no compensation from any party named in the analysis. Where a position is held, this will be disclosed in the relevant section.
>
> **Privacy and tracking**
>
> Registered users provide name and email to access full content. The site logs which sections each session views and when. Data is stored on Supabase infrastructure. The author will not share email addresses with third parties. One-click unsubscribe is available on every email and from the user profile page.
>
> **Contact**
>
> Questions, corrections, or take-down requests: [email address to be added on launch].

### 13.4 Footer (every page, bottom)

> © 2026 Palaniappan Chidambaram. Personal research — not investment advice — not affiliated with Unison Group. [Disclaimer](/disclaimer) · [About](/about) · [Privacy](/disclaimer#privacy)

These four blocks are versioned in the repo and updated together when the language changes.
