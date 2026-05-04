# References — sg-eqdp-scanner

Documents, URLs, and external resources consulted while building this project. Updated as work progresses.

## In-repo documents (canonical specs, read at every session start)

| File | Purpose |
|---|---|
| `CLAUDE.md` | Project guide for Claude Code; mission, architecture, non-negotiables |
| `docs/STRATEGY.md` | Forensic-research strategy, tier taxonomy, deliverable shape |
| `docs/PLAN.md` | 15-day execution plan with per-day acceptance criteria |
| `docs/METHODOLOGY.md` | Mathematical specification for every metric on the site |
| `docs/DATA_MODEL.md` | Data-model notes |
| `docs/DISCLAIMER.md` | Canonical disclaimer language reused across the site |
| `docs/TICKERS.md` | Starter universe (T3 named, STI-30 control) |
| `db/schema.sql` | Postgres schema — all 14 gold tables + RLS policies |
| `memory.md` | Living progress log; updated end of each session |

## External APIs / endpoints actually probed during this build

| URL | Result | Used for |
|---|---|---|
| `https://eodhd.com/api/exchanges-list/` | 200 — 73 exchanges, no Singapore | Decided EODHD doesn't cover SGX |
| `https://eodhd.com/api/eod/D05.SI` (and `.SG`, `.SGX`, `.SIN`) | 404 / empty | Confirmed no SGX equity coverage on EODHD |
| `https://eodhd.com/api/eod/AAPL.US` | 200 — full OHLCV | Token validity check |
| `https://eodhd.com/api/eod/0700.HK` | 200 — full OHLCV | Confirmed HK is on EODHD (just not catalogued) |
| `https://eodhd.com/api/eod/GSPC.INDX` | 200 — full S&P 500 history | INDX exchange works |
| `https://eodhd.com/api/eod/STI.INDX` | 200 with 0 rows | STI Index not in user's plan |
| `https://api.sgx.com/announcements/v1.1/categories` | 401 Missing Authentication Token | api.sgx.com is auth-gated |
| `https://api.sgx.com/announcements/v1.1/` (with date filters) | 401 Unauthorized | Confirmed gated |
| `https://api.sgx.com/disclosure-of-interests/v1.0` | 403 | Gated |
| `https://www.sgx.com/securities/company-announcements` | 200 — 6 KB JS-SPA shell | SPA, needs Playwright to render |
| `https://www.sgx.com/api/v1/announcements` | 200 but non-JSON | Likely SPA HTML, not data |
| `https://links.sgx.com/disclosure-of-interest` | 404 | Endpoint gone |
| `https://www.sgx.com/` | 200 | Homepage reachable |
| `https://supabase.com/dashboard/project/oojgkknpvkxdjcfcyfhr/sql` | (manual UI) | SQL Editor for schema apply |
| Yahoo Finance (yfinance over `query2.finance.yahoo.com`) | 200 with curl_cffi browser impersonation | Working OHLCV source for SGX |

## External tooling docs informing the build (not fetched in-session)

These are the canonical references that shaped how each library is used; they have been consulted via prior knowledge / prior reading rather than live-fetched in this session.

| Topic | Reference |
|---|---|
| yfinance + curl_cffi (anti-bot) | https://github.com/ranaroussi/yfinance, https://github.com/lexiforest/curl_cffi |
| Supabase Python client (REST) | https://supabase.com/docs/reference/python |
| Supabase SSR helpers (Next.js) | https://supabase.com/docs/guides/auth/server-side/nextjs |
| Supabase CLI (db push, link) | https://supabase.com/docs/reference/cli/introduction |
| supabase db query --linked (Management API) | `supabase db query --help` |
| linearmodels.PanelOLS | https://bashtage.github.io/linearmodels/panel/ |
| statsmodels OLS / sm.add_constant | https://www.statsmodels.org/stable/regression.html |
| Politis–Romano stationary bootstrap | Politis & Romano 1994, JASA |
| Cluster / pairs bootstrap for panel data | Cameron, Gelbach, Miller 2008 |
| CausalImpact (Bayesian SC) | https://github.com/google/CausalImpact (referenced for Day 5; deferred) |
| Next.js 15 App Router | https://nextjs.org/docs/app |
| @supabase/ssr cookies pattern | https://supabase.com/docs/guides/auth/server-side/creating-a-client |
| Tailwind CSS | https://tailwindcss.com/docs/installation |
| Vercel CLI deploy | https://vercel.com/docs/cli |
| Politis stationary block-bootstrap, mean block length 5 (per METHODOLOGY.md §10) | Politis–Romano 1994 |
| Supabase magic-link auth | https://supabase.com/docs/guides/auth/auth-magic-link |
| Vercel ISR (`revalidate`) | https://nextjs.org/docs/app/building-your-application/data-fetching/incremental-static-regeneration |

## Methodology — academic references (for /methodology page)

Listed here as a TODO bibliography to render on the public methodology page when /brief#methodology is built out.

- Brown & Warner 1985, *Using daily stock returns: The case of event studies*, JFE
- MacKinlay 1997, *Event studies in economics and finance*, JEL
- Amihud 2002, *Illiquidity and stock returns*, JFM (the Amihud ratio)
- Fama & French 1993, *Common risk factors in the returns on stocks and bonds*, JFE (FF3 factors)
- Abadie, Diamond, Hainmueller 2010, *Synthetic control methods for comparative case studies*, JASA
- Brodersen et al. 2015, *Inferring causal impact using Bayesian structural time-series models*, AOAS (CausalImpact)
- Cameron, Gelbach, Miller 2008, *Bootstrap-based improvements for inference with clustered errors*, RES
- Politis & Romano 1994, *The stationary bootstrap*, JASA

## Deferred / known-unread

- SGXNet substantial-shareholder filing form spec — needed to write the parser correctly; will be sourced from a real fixture once Playwright is wired.
- iEdge SG Next 50 constituents — needed for `IndexInclusion` signal in the score; currently 0 for all tickers. Will be hand-curated or scraped from SGX's index sheet.
- Pre-rotation values for the leaked secrets (DB password, EODHD token, Anthropic / Resend / Mistral / Datalab keys) — these are documented as needing rotation before any `git push`.

## Conventions

- Every fact on the website maps to a Postgres query (logged in `pipeline_runs.metrics_json`), a Python function in `src/`, and a test in `tests/`.
- Bi-temporal data has `effective_date` and `filing_date` separately.
- Returns appear only on the right-hand side of the impact regression; never an input to the candidate score (test enforces this in `tests/test_score.py`).
