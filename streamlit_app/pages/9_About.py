"""About — what this is, what it isn't, and how it's built."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.components import disclaimer_banner, footer, page_header

st.set_page_config(page_title="About · EQDP", page_icon=":material/info:", layout="wide")
disclaimer_banner()
page_header(
    "About",
    subtitle="A quantitative case study built for education and institutional-grade analysis.",
    eyebrow="Identity",
)

st.markdown(
    """
### About this work

This site is a **quantitative case study** intended for **education and
institutional-grade analysis**. The aim is the dull, careful, *forensic*
work — combine eligibility, broker coverage, market microstructure, and
5%+ filings — and report what the evidence actually supports. The
methodology, code, and underlying data file are all public so anyone
can reproduce the conclusions or disagree with specific steps.

### Scope

- **Universe:** SGX-listed equities, ~70 names across T1 / T2 / T3 / control.
- **Window:** 2020-01 to today, with 252-day β windows ending 30 days pre-event.
- **Refresh:** daily prices, weekly filings, monthly synthetic-control refits.

### Stack

- **Python** (pandas, numpy, scipy, statsmodels, linearmodels) for analytics.
- **DuckDB** as the gold layer — a single file at `data/eqdp.duckdb`, committed to the repo.
- **Streamlit Community Cloud** for the public site.
- **GitHub Actions** for the daily / weekly / monthly cron jobs.

### What this site does *not* do

- It does not give investment advice.
- It does not claim to know which exact stocks a given manager has bought.
- It does not predict future outperformance for any name.
- It does not benchmark against any specific portfolio strategy.
"""
)

footer()
