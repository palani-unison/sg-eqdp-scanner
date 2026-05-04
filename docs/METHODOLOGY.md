# METHODOLOGY.md

The forensic backbone of the EQDP Brief. Every claim on the website maps to one of the methods below. This document is referenced from `/methodology` on the site and from §4 of `STRATEGY.md`.

---

## Mental model

We separate three concerns that should not be confused:

1. **Candidate detection** — *who plausibly got bought.* No return inputs. (§3 below.)
2. **Impact estimation** — *did those names actually outperform, after stripping market / size / value.* (§4–§7 below.)
3. **Confidence** — *how much do we trust the impact estimate.* (§8–§9 below.)

Every output from the pipeline ties to one of these three.

---

## 1. The Three-Tier Universe

| Tier | Definition | Source | Approx size |
|---|---|---|---|
| T1 — Confirmed | ≥1 EQDP-appointed manager has filed a 5%+ substantial-shareholder disclosure on/after 2025-07-21 | SGXNet | grows weekly |
| T2 — Eligible | Programmatic eligibility filter (small/mid-cap, SGX Mainboard or Catalist, daily traded, not in STI-30, not restricted sector) | SGX listing data | ~150–200 |
| T3 — Named | Stock named by RHB-30 / Maybank-18 / Edge-69 broker beneficiary lists | Broker notes | ~120 unique |
| Control | STI-30 large caps (de-emphasised by EQDP) | Index constituents | 30 |

A stock can sit in multiple tiers. The interesting empirical question is the **overlap and disagreement** between tiers.

---

## 2. Bi-temporal data model

Every fact with publication lag carries two dates:

- `effective_date` — when the event actually occurred (e.g. "BlackRock crossed 5% on 2025-09-12")
- `filing_date` — when the public learned about it (e.g. "filed 2025-09-15")

A backtest dated 2025-09-13 must use `filing_date <= 2025-09-13`. Using `effective_date` would peek into the future. Postgres makes this enforceable with predicates on every read.

---

## 3. The decoupled candidate score

> Score = w₁·LiquidityRise + w₂·InstitutionalProxy + w₃·IndexInclusion + w₄·BrokerNamed + w₅·FilingPresent

Weights default to (0.30, 0.20, 0.15, 0.15, 0.20).

| Signal | Definition |
|---|---|
| LiquidityRise | 60-day rolling Amihud illiquidity, change vs 60-day rolling 6-months-ago. Lower Amihud = better; we score the improvement. |
| InstitutionalProxy | Fraction of last 30 trading days where close > 30-day VWAP. Sustained-accumulation proxy. |
| IndexInclusion | Dummy: 1 if currently in iEdge SG Next 50 or other mid-cap index, else 0. |
| BrokerNamed | Count of T3 lists naming the stock, normalised to [0,1]. |
| FilingPresent | Dummy: 1 if any T1 filing within 12 months, else 0. |

**Returns are not an input.** A unit test enforces this: vary the price series of a stock, the score must not move.

---

## 4. CAPM-adjusted abnormal returns

For each stock *i* we estimate (α, β) on a clean 252-trading-day window ending 30 days before the announcement date 2025-02-21:

> R_i,t = α_i + β_i · R_market,t + ε_i,t

where R_market is the daily return on the STI ETF (proxy for the SGX market portfolio).

The abnormal return on day *t* is then:

> AR_i,t = R_i,t − (α_i + β_i · R_market,t)

Cumulative abnormal return over event window [t1, t2]:

> CAR_i = Σ AR_i,t for t in [t1, t2]

Default windows:

- [-5, +20] for the announcement
- [-1, +10] for each tranche
- [-1, +20] for the expansion

---

## 5. Fama-French 3-factor (robustness)

> R_i,t − R_f = α_i + β_M·(R_M − R_f) + β_S·SMB + β_V·HML + ε_i,t

We construct SMB (Small-Minus-Big) and HML (High-Minus-Low) factors from our SGX universe rather than borrowing US factors:

- Sort all SGX stocks each month by market cap. SMB = bottom-quintile mean return − top-quintile mean return.
- Sort by P/B. HML = highest-P/B-quintile mean return − lowest-quintile (inverse P/B used for HML convention).

If the EQDP effect survives FF3 adjustment, it is not just a small-cap rotation story.

---

## 6. Liquidity — Amihud illiquidity ratio

For each stock-day:

> Amihud_i,t = |R_i,t| / DollarVolume_i,t

Lower is better — the same return is achieved on more volume. Compute the change in 60-day rolling mean from pre-event to post-event windows. This is the cleanest liquidity signal achievable from daily OHLCV.

We also report **turnover velocity** (volume / shares-outstanding) as a sanity comparator.

---

## 7. Matched-pair difference-in-differences

For each treatment stock, find the closest control by (sector, market-cap quintile, pre-event β, pre-event Amihud). Distance is Mahalanobis on the standardised features.

The DiD coefficient comes from:

> R_i,t = α_i + γ_t + δ · (Treated_i × Post_t) + ε_i,t

estimated as a panel regression with entity and time fixed effects (`linearmodels.PanelOLS`). δ is the EQDP effect after partialling out everything the matched control absorbs.

---

## 8. Bayesian synthetic control

For the top 10–15 named beneficiaries, we build a synthetic counterfactual price path from a weighted basket of non-EQDP stocks fit to the pre-event period — implemented via `tfcausalimpact`.

For each treatment stock and each event date:

1. Pre-event window: 180 trading days ending 30 days before the event.
2. Donor pool: STI-30 + non-named small/mid-caps not in T1 or T3.
3. Fit a Bayesian structural time-series model on the pre-period.
4. Project the counterfactual into the post-event window.
5. Report the posterior mean divergence and 95% credible interval.

The output for each (stock, event) is a fan chart with observed-vs-counterfactual bands.

---

## 9. Placebo tests

We run the entire impact pipeline on **dates where nothing happened** — 20 random Wednesdays in 2024 chosen out of weeks with no MAS press release, no major broker initiation, and no index rebalance.

- The distribution of "effects" on placebo dates is the empirical null.
- A real EQDP date should sit in the right tail of this null.
- Placebo p-value ≈ uniform → method is unbiased.
- Placebo p-value distribution skewed → method has hidden bias (we investigate before publishing).

---

## 10. Block-bootstrap confidence intervals

Analytic CIs are unreliable for small panels with fat tails. We use:

- **Stationary bootstrap** with mean block length 5 trading days.
- 5,000 replications per metric.
- 5–95 percentile CI reported on every headline number on the website.

For per-stock synthetic control, we use the posterior credible intervals from `tfcausalimpact` directly — those are already Bayesian.

---

## 11. What this methodology cannot answer

- Sub-5% positions — invisible to public filings, undetectable from daily data alone.
- Intraday microstructure (bid-ask spreads, order-book depth) — out of scope until we ingest tick data.
- Why a manager bought any specific stock — we observe the buy, not the thesis.
- Whether T3-named stocks that don't show T1 filings were considered and rejected vs simply held below 5%.

These limits are documented on the site at `/brief#limitations` and again at `/disclaimer`.

---

## 12. Reproducibility checklist

Every chart on the website maps to:
- A specific Postgres query (logged in `pipeline_runs.metrics_json`).
- A specific Python function in `src/`.
- A specific test in `tests/` that pins behaviour against a fixed historical snapshot.

A reader can clone the repo, run `pipelines/backfill.py`, and produce identical charts. That is the credibility floor.
