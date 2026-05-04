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
## 1. Detector — the candidate score

The screen fires *before* any return is observed. Inputs:

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

Returns are **not** an input. A 245% rally with no flow signal scores zero.

## 2. Estimator — abnormal returns

For each ticker × event we compute three benchmarks:

- **CAPM** — β estimated on a 252-day pre-event window ending 30 trading
  days before the event, then `AR_t = R_t − (α + β·R_M,t)`.
- **Fama-French 3-factor** — robustness check.
- **Market-adjusted** — naïve `AR_t = R_t − R_M,t`.

Cumulative abnormal return: `CAR_{t} = Σ_{s≤t} AR_s`.

## 3. Difference-in-differences

For each event, we compute the cross-sectional mean CAR for treated
(T1∪T2∪T3) and matched control sets, then take the difference. Matching
is on sector, market-cap band, β, and pre-event Amihud.

## 4. Bayesian synthetic control

For the top 10–15 named beneficiaries, we fit a Bayesian synthetic-control
model (`tfcausalimpact`) using ≤5 donor pool members per name. Counterfactual
deviations come with 95% credible bands.

## 5. Placebo + bootstrap

- **Placebo** — re-run the DiD at non-event dates. The distribution of
  placebo δ should be centred on zero.
- **Block bootstrap** — 5,000 replications, block length 5, on the panel
  of treated and control returns. Reported CI = 5/95 percentile of the
  bootstrap distribution.

## 6. The three rules we will not violate

1. **No look-ahead.** Every fact has both `effective_date` and `filing_date`.
2. **Adjusted prices only.** yfinance `auto_adjust=True`; spot-checked.
3. **Decoupled detector / estimator.** Score does not see returns.
"""
)

footer()
