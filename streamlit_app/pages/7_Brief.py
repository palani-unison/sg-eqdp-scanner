"""EQDP Brief — narrative readout. Placeholder for now."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.components import disclaimer_banner, footer, page_header

st.set_page_config(page_title="Brief · EQDP", page_icon=":material/article:", layout="wide")
disclaimer_banner()
page_header(
    "EQDP Brief — narrative",
    subtitle=(
        "The forensic narrative — programme design, beneficiary identification, "
        "impact estimates, confidence layer — coming next. The data backbone is "
        "in place; the writing is what's left."
    ),
    eyebrow="Coming soon",
)

st.markdown(
    """
The Brief will be written into this page section by section, drawing on the
data already wired in:

1. **Programme design** — what S$6.5B actually buys, in what tranches, to whom.
2. **The nine managers** — who they are, what each tranche meant.
3. **The three-tier universe** — T1 confirmed via filings, T2 from eligibility,
   T3 from broker lists.
4. **Event studies** — CARs around announcement, Tranche 1, Tranche 2, expansion.
5. **DiD results** — treated minus control, with bootstrap CIs.
6. **Synthetic-control case studies** — the top named beneficiaries, one by one.
7. **What we still don't know** — sub-5% positions, programme runway,
   manager strategies.

Until the narrative lands, the live data lives in **Tracker**, **Event Studies**,
**Universe**, **Ticker Analyzer**, and **Filings**.
"""
)

footer()
