# Working Memory — sg-eqdp-scanner

Living context for Claude Code. Update at the end of every session.

## Project mission (one paragraph)

Reverse-engineer the impact of the Singapore MAS Equity Market Development Programme (EQDP) — a S$6.5 billion programme deploying capital through asset managers into SGX-listed equities. Identify which Singapore-listed companies actually benefited (price appreciation, volume lift, liquidity improvement) versus which did not. Public-data forensic finance: MAS does not disclose specific holdings; we infer beneficiaries by combining eligibility filters, broker beneficiary lists, market microstructure, and SGXNet substantial-shareholder filings. Output is a public, email-gated **EQDP Brief** website.

## Key constants (canonical, do not change without research evidence)

```python
EVENTS = {
    "announcement": "2025-02-21",  # MAS launches S$5B EQDP
    "tranche_1":    "2025-07-21",  # S$1.1B → 3 managers
    "tranche_2":    "2025-11-19",  # S$2.85B → 6 managers
    "expansion":    "2026-02-12",  # Expanded to S$6.5B
}

EQDP_MANAGERS = [
    # First tranche (Jul 2025)
    "Avanda Investment Management",
    "Fullerton Fund Management",
    "JPMorgan Asset Management",
    # Second tranche (Nov 2025)
    "Amova Asset Management",  # formerly Nikko AM
    "AR Capital",
    "BlackRock",
    "Eastspring Investments",
    "Lion Global Investors",
    "Manulife Investment Management",
]

# Market identifiers
STI_TICKER = "^STI"
SGX_SUFFIX = ".SI"  # yfinance suffix for SGX equities
```

## Current state

- ✅ Strategy locked (see `docs/STRATEGY.md`)
- ✅ Repo scaffolded
- ✅ Day 1 — `src/constants.py`, `src/universe.py`, 15 tests green; T2=52, T3=27, control=20
- ✅ Day 2 — `src/data/prices.py` (yfinance + curl_cffi impersonation), `src/db.py`, `pipelines/backfill.py`, `scripts/db_push.py`. Schema applied via Supabase CLI. Phase 0 backfill: **109,465 rows × 69 tickers, 2020-01-02 → 2026-05-01**.
- ✅ Day 3 — `src/returns.py` (CAPM β + AR + CAR), `src/liquidity.py` (Amihud + 60d rolling), `pipelines/compute_metrics.py`. **69 betas, 101,466 liquidity rows, 1,589 STI factor returns**. Sector sanity passes: DBS β=1.35, OCBC β=1.16, UOB β=1.12; REITs β<1.0; semis low R² as expected. 43 tests pass.
- ✅ Day 4 — `src/events.py`, `src/matching.py` (Mahalanobis NN on sector + β + Amihud), `pipelines/compute_did.py`. **4,110 abnormal_returns rows × 4 events**. Per-event δ vs matched STI-30 controls (PanelOLS, entity+time FE):
   - announcement: δ = -0.63%/day, p = 0.004 ★ (signed away from treated — markets preferred large-caps at signal-only event)
   - tranche_1:   δ = -0.25%/day, p = 0.47 (CAR(treat) +5.7% vs CAR(ctrl) +1.2% but DiD null)
   - tranche_2:   δ = +0.72%/day, p = 0.016 ★ (only event with significant positive treatment effect — tracks deployment of S$2.85B)
   - expansion:   δ = +0.82%/day, p = 0.23 (insignificant)
- ✅ Day 7 — `src/score.py` (decoupled candidate score, returns-invariance test passes), `pipelines/score_pipeline.py`. **72 candidate_scores rows** for 2026-05-03 snapshot. Top-3: E28.SI (Frencken, T3, 0.488), 5DD.SI (Innotek, T2, 0.486 — non-broker-named lifted purely by flow signals — methodology working), AWX.SI (AEM, T3, 0.478). Tier averages: T3 0.323 > control 0.228 > T2 0.186. IndexInclusion=0 (no Next 50 list yet) and FilingPresent=0 (no SGXNet scrape yet) for everyone.
- ✅ Day 9 — `src/bootstrap.py` (cluster bootstrap on entities for DiD; cluster bootstrap on per-ticker CARs), `pipelines/compute_bootstrap.py`. **12 bootstrap_cis rows × 5,000 reps each**. Headline DiD δ with 5–95% CIs: announcement [-0.0099, -0.0030] (negative-sig ★), tranche_1 [-0.0077, +0.0030] (null), tranche_2 [+0.0025, +0.0118] (positive-sig ★ — confirmed), expansion [-0.0018, +0.0198] (null). CAR(treat) tranche_1 = +5.67% [+3.19%, +8.56%] — significant raw outperformance that DiD absorbs once entity+time FE applied.
- ✅ Web app — Next.js 15 scaffold complete and built (`npm run build` green, 12 routes, 102 kB shared JS). `/`, `/about`, `/disclaimer`, `/register`, `/login` (magic-link + admin-password dual mode), `/admin` (gated, dashboard with run + count stats), `/admin/users` (registration list), `/brief` (gated, reads top-15 from candidate_scores), `/tracker` (gated, ISR 6h, stale-data banner). Middleware enforces ADMIN_EMAIL == pachidam@outlook.com on `/admin/*`. Admin user created in Supabase Auth (id=47399ba3-4846-4f3a-96ab-c197dd88147c). Deploy guide at `web/DEPLOY.md`.
- ✅ Day 6 (scaffolded) — `scrapers/sgxnet/{manager_aliases,parser,ratelimit,fetcher}.py`, `pipelines/weekly_filings.py`, 27 SGXNet tests. Manager alias resolution covers all 9 EQDP managers (incl. Nikko AM → Amova rebrand). Parser uses keyword-anchored extraction + structural-change fingerprint hash. **Live SGX fetch deferred** — `www.sgx.com/securities/company-announcements` is a JS-SPA shell on plain GET (6 KB, no listings); the public `api.sgx.com/announcements` endpoints are auth-gated (401/403). Documented in `scrapers/sgxnet/fetcher.py`. Pipeline runs in fixture mode (`--fixtures-dir`) until Playwright is wired.
- ✅ Web app — McKinsey-style redesign deployed to **eqdp-screener.vercel.app**. 16 routes (10 public, 4 gated, 2 auth). Sidebar navigation grouped by Read/Brief/About. Editorial typography (Source Serif headings + Inter body), navy ink, electric-blue accent, warm off-white page. New public pages: `/programme`, `/managers`, `/methodology`, `/market`, `/risks`, `/about`, `/disclaimer`.
- ✅ `/brief` charts — DiD δ forest plot with bootstrap CIs, cumulative returns line (treatment vs control vs STI), beneficiary scatter (CAR vs volume lift), 4-panel event-study CAR grid. Each chart + the candidate-scores table has a CSV export button.
- ✅ Two new derived tables: `ticker_summaries` (72 rows) and `cohort_timeseries` (587 rows), populated by `pipelines/compute_summaries.py`. Drive the brief charts.
- ⏳ Day 5 — synthetic control (deferred — `tfcausalimpact` may not have Py 3.14 wheels)
- ⏳ Live SGXNet — Playwright integration needed (see `scrapers/sgxnet/fetcher.py:fetch_live` docstring)
- 111 Python tests pass; mypy strict + ruff clean across 38 Python files; web app builds clean (Next 15 + TS strict, 12 routes).
- Reference index at `docs/REFERENCES.md`: in-repo specs, external endpoints probed, deferred-unread items, methodology bibliography.
- Data processing reference at `docs/data_processing.md`: every table, what it stores, which pipeline produces it, how the website maps to it. **Read this before changing any pipeline.**
- Local export at `scripts/export_data.py` → `data/exports/<table>.csv` for every analytical table (217,534 rows, ~14 MB; gitignored).

## Live deployment

- ✅ **Vercel project `eqdp-screener`** (team `pachidamoutlookcoms-projects`) deployed and serving at **https://eqdp-screener.vercel.app**.
- All 8 env vars pushed to all 3 environments (production / preview / development). Verified live: `/`, `/disclaimer`, `/login` → 200; `/admin`, `/brief` → 307 → `/login` (middleware enforcing).
- Admin login: `pachidam@outlook.com` / password `Eqdp2026!` via the "Password (admin)" tab on `/login`. **Password is in chat transcript — rotate after first login.**

## Pending / documented blockers

- **GitHub push** — paused mid-flight at user's request. `.git/` initialised, 93 files staged after gitignore audit + secret scan (0 known patterns leaked). Ready to commit + `gh repo create sg-eqdp-scanner --public` + `vercel git connect` whenever user says go. `.env.example` rewritten as pure placeholders.
- **SGX live scrape (Day 6) — fully Akamai-blocked.** Plain GET, Playwright (headless), and Playwright + `playwright-stealth` all return `403 Access Denied` (Akamai reference `18.d0a4c117…`). Bypassing this needs (a) residential proxy, (b) pre-authenticated session cookies, or (c) paid Akamai-bypass tooling. Documented in `docs/REFERENCES.md`. Pipeline runs in fixture mode for now.
- **Day 5 synthetic control** — `tfcausalimpact` may not have Py 3.14 wheels; fallback path = hand-rolled Abadie-style constrained least squares. Deferred.
- **iEdge SG Next 50 list** — needed to make `IndexInclusion` signal real (currently 0 for all). Manual hand-curate or scrape SGX index sheet.
- **3 dead Yahoo tickers** (`C61U.SI`, `F1E.SI`, `J91U.SI`) — likely renamed; needs hand-correction (e.g., `C61U.SI` → `AU8U.SI` for CapitaLand China Trust).

## Day-3 gotchas worth remembering

- **PostgREST `max_rows = 1000` server-side**, even with `.limit(10000)`. Pagination via `.range(offset, offset + page - 1)` is mandatory for any per-ticker historical scan. See `_load_ticker_prices` in `pipelines/compute_metrics.py`.
- **statsmodels 0.14.4 is incompatible with scipy 1.17** (removed `_lazywhere`). Need `statsmodels >= 0.14.5`. requirements.txt pins are stale; will update on Day 10.
- `^STI` index returns OK via yfinance + curl_cffi, same path as equities.

## Day-2 gotchas worth remembering

- yfinance 0.2.x is broken against Yahoo's new bot-detection. Pinned to **yfinance 1.3.0 + curl_cffi (Chrome impersonation)** — both required, the upgrade alone is not enough.
- Supabase direct DB host (`db.<proj>.supabase.co:5432`) is **IPv6-only**. The local network has no IPv6, so direct psycopg2 fails. Workaround: schema/migrations via **`supabase` CLI + `supabase db push`** (CLI uses Management API path); ad-hoc reads via supabase-py REST. PostgREST default cap is 1000 rows — use `supabase db query --linked` for analytical aggregates.
- Three hand-curated T2 seeds have NO yfinance data and need replacement: `C61U.SI`, `F1E.SI`, `J91U.SI`. Likely renamed/delisted; left in `tickers` table as TODO markers.
- `.env.example` accidentally received live credentials in this session — security flagged to user; needs rotation of DB password + Resend/Anthropic/Mistral/Datalab API keys before any `git push`.

## Decisions log

| Date | Decision | Rationale |
|---|---|---|
| 2026-05-03 | Web app, not PDF | Live data + registration tracking + visualisations |
| 2026-05-03 | Repo `sg-eqdp-scanner`, public, MIT | Reproducibility credibility |
| 2026-05-03 | Hybrid runner: GitHub Actions for Python, Edge Functions for glue | Edge Functions are Deno-only; can't run statsmodels |
| 2026-05-03 | Supabase Postgres = system of record (**reversed 2026-05-04**) | Avoid git data churn; queryable historical depth |
| 2026-05-03 | Phase 0 backfill on laptop, Phase 1 increments in cloud | Backfill is one-shot heavy, increments are tiny |
| 2026-05-03 | Brand = "EQDP Brief" (not "dossier") | Distinguish from third-party reference PDF |
| 2026-05-04 | **Web layer flipped Next.js → Streamlit** | Free Streamlit Cloud, data-science / TA aesthetic, no auth complexity |
| 2026-05-04 | **Data store flipped Supabase → DuckDB-in-repo** (`data/eqdp.duckdb`) | One-file analytics DB, no managed service, dashboard self-contained |
| 2026-05-04 | **Registration / email gate dropped** | Public read-only; Streamlit Cloud handles deploy without auth |
| 2026-05-04 | `src/store.py` shim mimics supabase-py chain so pipelines didn't need rewrites | Smallest diff to swap data layers |

## Open questions

- Domain — defaulting to `eqdp-brief.com` until Palani confirms registration
- Vercel deploy URL — Palani will share once first deploy lands
- GitHub username/org for the repo — provided at Claude Code CLI login

## Definitions / shorthand decoder

- **EQDP** = Equity Market Development Programme (MAS)
- **MAS** = Monetary Authority of Singapore
- **SGX** = Singapore Exchange
- **SGXNet** = SGX's filing portal where 5%+ substantial-shareholder disclosures land
- **STI** = Straits Times Index (top 30 SGX names)
- **iEdge SG Next 50** = SGX index of names ranked 31–80 by float-adjusted market cap
- **CAR** = Cumulative Abnormal Return
- **AR** = Abnormal Return (single day)
- **DiD** = Difference-in-Differences
- **FF3** = Fama-French 3-factor (market, SMB size, HML value)
- **T1 / T2 / T3** = Three-tier beneficiary universe (Confirmed / Eligible / Named)

## End-of-session checklist

- [ ] Updated "Current state" section above
- [ ] Logged any new decisions in the table
- [ ] Closed or rephrased any answered open questions
- [ ] Committed code with a clear message
- [ ] No analytical data committed to git (gold tables → Supabase only)
