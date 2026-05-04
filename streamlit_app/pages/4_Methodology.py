"""Methodology — explainer with formulae."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.components import disclaimer_banner, footer, page_header

st.set_page_config(page_title="Methodology · EQDP", page_icon=":material/calculate:", layout="wide")
disclaimer_banner()
page_header(
    "Methodology",
    subtitle="The formal stack. Decoupled detector vs estimator vs confidence.",
    eyebrow="How the numbers are made",
)

st.markdown(
    """
## 0. Universe — iEdge SG Next 50

This study focuses on the **iEdge SG Next 50** — the small- and mid-cap
universe of SGX-listed equities ranked 31–80 by float-adjusted market
capitalisation. The Next 50 is the natural hunting ground for active
small/mid-cap mandates: large enough to be liquid, small enough to be
under-researched, and explicitly *outside* STI-30 (which the EQDP
programme de-emphasises).

A control set of **STI-30 large caps** sits alongside the Next 50.
They are not the target of the programme, so any divergence between
the Next 50 cohort and STI-30 is informative for inferring beneficiary
flow.

## 1. Detector — finding candidates BEFORE returns

Think of this as a **signal engine**. You are *not* predicting returns
directly — you are identifying conditions that usually *precede*
institutional buying.

The screen fires before any return is observed. Inputs:

- **Liquidity rise** — change in 60-day Amihud illiquidity ratio.
- **Institutional proxy** — share of close-vs-VWAP days favouring close.
- **Index inclusion** — dummy for iEdge SG Next 50 membership.
- **Broker-named** — count of T3 broker beneficiary lists.
- **Filing presence** — dummy for any T1 SGXNet 5%+ filing.

All five components are min-max scaled cross-sectionally per `score_date`,
then weighted (see `src/constants.py::SCORE_WEIGHTS`):

```
total_score = 0.30·liquidity_rise + 0.20·institutional_proxy
            + 0.15·index_inclusion + 0.15·broker_named + 0.20·filing_present
```

### Why min-max scaling?

The five components live in completely different units — a liquidity
*delta*, a fraction of trading days, a 0/1 dummy, a count of broker
mentions, another 0/1 dummy. Min-max scaling converts each one to a
comparable **0–1 signal** so the weighted sum is meaningful.

### Why the detector is flow-based, not price-based

Returns are **not** an input. The detector reads only flow signals:

- A stock that already **ran up** with no underlying flow change → may
  score zero.
- A **quiet accumulation** with rising liquidity, broker chatter, and a
  filing → may score high even before the price has moved.

That decoupling is deliberate. It avoids **chasing performance** —
the most common failure mode of naive screens that simply rank by
trailing return.

## 2. Estimator — did it actually outperform?

Once the detector has fired, the estimator asks the next question:

> **After the signal, did the stock beat what it should have returned?**

### Abnormal Return (AR)

We do *not* report raw return. Raw return mixes the stock's idiosyncratic
move with whatever the broader market did that day. Instead we compute
**abnormal return** — the difference between the realised return and a
fair benchmark expected return:

```
AR_t = R_t − E[R_t | benchmark]
```

Cumulative abnormal return: `CAR_{t} = Σ_{s≤t} AR_s`.

### Why three benchmarks?

A single benchmark is fragile. We compute the same AR three ways and
look for agreement across them:

- **CAPM** — simple baseline. β estimated on a 252-day pre-event window
  ending 30 trading days before the event, then
  `AR_t = R_t − (α + β·R_M,t)`.
- **Fama-French 3-factor** — adds **size (SMB)** and **value (HML)**
  effects on top of market exposure, so we don't mistake style drift
  for alpha.
- **Market-adjusted** — naïve `AR_t = R_t − R_M,t`. A sanity check
  that doesn't depend on a fitted β.

If all three benchmarks point the same direction, the result is robust.
If they diverge, the model choice was doing the work — and we say so.

## 3. Difference-in-differences (DiD) — causality testing

The estimator tells you whether *one* stock outperformed its benchmark.
DiD asks the harder, more honest question:

> **Did treated stocks outperform MORE than similar stocks that did
> *not* receive the signal?**

That subtraction strips out anything happening market-wide during the
event window — so what's left is closer to a *causal* effect of the
signal itself, not a coincidence with broader conditions.

### How matching works

We split the universe into:

- **Treated** — stocks where the EQDP signals fired (T1 ∪ T2 ∪ T3).
- **Control** — stocks *without* signals, picked to look as similar as
  possible to each treated name on:
  - **Sector**
  - **Market capitalisation**
  - **Beta**
  - **Liquidity** (pre-event Amihud)

A treated name and its matched control should look identical on the
day before the event. Any divergence after the event is the DiD δ.

For each event we compute the cross-sectional mean CAR for the treated
panel and the matched control panel, then take the difference and run a
PanelOLS with entity + time fixed effects to extract the δ coefficient.

## 4. Bayesian synthetic control *(deferred)*

DiD compares each treated stock to a **single matched** control. This
section makes that comparison more sophisticated.

Instead of comparing each treated stock to *one* nearest neighbour, we
build a **custom synthetic counterfactual** — a weighted blend of
similar names from a donor pool — that tracks the treated stock's
pre-event behaviour as closely as possible. After the event, the gap
between the actual stock and its synthetic version is the impact, with
a full posterior for uncertainty (Bayesian credible bands).

The model uses ≤5 donor-pool members per treated name. This step is
currently deferred — the package is not yet wired into the active
stack — but the schema and pipeline hooks are in place.

## 5. Placebo + bootstrap — confidence layer

How sure are we the DiD δ is real and not noise? Two safety nets:

- **Placebo** — re-run the entire DiD pipeline on non-event dates
  picked from the same year. If the method is sound, the distribution
  of placebo δ should be **centred on zero** with the bulk inside a
  small band. Any persistent positive or negative drift on placebos is
  a red flag.
- **Block bootstrap** — 5,000 replications, block length 5, on the
  panel of treated and control returns. Reported CI = 5/95 percentile
  of the bootstrap distribution. This handles the serial correlation
  in daily equity returns better than a vanilla i.i.d. bootstrap.

## 6. The three rules — why they matter a lot

These three are not stylistic — they're load-bearing. Violate any one
of them and the entire analysis collapses into something you can't
trust.

1. **No look-ahead bias.** At any given timestamp, the analysis only
   uses information that was *publicly available at that time*. Every
   filing has both an `effective_date` (when it happened) and a
   `filing_date` (when it became public). Index membership, broker
   initiations, programme announcements — all carry the same bi-temporal
   stamp. We never let the future leak into the past.
2. **Adjusted prices only.** Returns are computed from
   split-and-dividend-adjusted prices (`yfinance auto_adjust=True`,
   spot-checked against known events). Without this, a 2-for-1 split
   shows up as a -50% one-day return — and the entire abnormal-return
   chain becomes garbage.
3. **Detector ≠ Estimator.** The candidate score uses *only* flow
   signals — it never sees returns. The estimator measures returns
   but never feeds back into the score. This is a hard wall. Without
   it you end up with a circular model that ranks by past performance
   and then claims to have predicted it.
"""
)

footer()
