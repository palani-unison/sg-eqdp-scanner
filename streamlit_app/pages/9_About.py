"""About — author, scope, contact."""

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
    subtitle="Who is doing this work, why, and what it is — and is not.",
    eyebrow="Identity",
)

st.markdown(
    """
This is the **personal research of Palaniappan Chidambaram**. It is *not* the
work product of Unison Group, MAS, SGX, or any of the nine EQDP-appointed
managers. Views are the author's own.

The site exists because MAS does not disclose the specific Singapore-listed
companies its appointed managers have purchased. That informational gap means
public discussion of "who is benefiting from the programme" is mostly noise.
The aim here is to do the dull, careful, *forensic* work — combine eligibility,
broker coverage, market microstructure, and 5%+ filings — and report what
the evidence actually supports.

### Scope

- Universe: SGX-listed equities, ~200 names across T1 / T2 / T3 / control.
- Window: 2024-01 to today, with 252-day β windows ending 30 days pre-event.
- Refresh: daily prices, weekly filings, monthly synth-control refits.

### Stack

- Python (pandas, statsmodels, tfcausalimpact) for analytics.
- Supabase Postgres as the gold layer.
- Streamlit Community Cloud for the public site.
- GitHub Actions for the cron jobs.

### Contact

Questions, corrections, take-down requests — `palani@unisongroup.com`.
"""
)

footer()
