"""What is EQDP — programme explainer for newcomers.

Sits as the first page after Home so anyone landing on the site can build
context before diving into the analytical pages.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.components import disclaimer_banner, footer, page_header

st.set_page_config(page_title="What is EQDP · EQDP Scanner", page_icon=":material/help:", layout="wide")
disclaimer_banner()
page_header(
    "What is EQDP?",
    subtitle=(
        "A government-backed liquidity and market-revival programme — MAS "
        "deploys capital via top fund managers to actively invest in SGX "
        "stocks, aiming to revive liquidity, valuation, and participation "
        "in Singapore's equity market."
    ),
    eyebrow="Programme primer",
)

# ---------------------------------------------------------------------------
# Headline KPIs (programme size + tranches)
# ---------------------------------------------------------------------------
c1, c2, c3, c4 = st.columns(4)
c1.metric("Programme size", "S$ 6.5B", "expanded 2026-02-12")
c2.metric("Tranche 1", "S$ 1.1B", "Jul 2025 · 3 managers")
c3.metric("Tranche 2", "S$ 2.85B", "Nov 2025 · 6 managers")
c4.metric("Mandate", "Active SGX equity", "small/mid-cap focus")

st.markdown("&nbsp;")

# ---------------------------------------------------------------------------
# Core objective
# ---------------------------------------------------------------------------
left, right = st.columns([1.4, 1])

with left:
    st.markdown(
        """
### Core objective

EQDP is straightforward in intent:

> **Bring more liquidity, participation, and investor interest back into Singapore's equity market — especially mid- and small-cap stocks.**

It is the **Equity Market Development Programme** of the Monetary Authority
of Singapore (MAS) — a government-backed allocation of capital to selected
asset managers, who deploy it actively into SGX-listed equities under
specific mandates.

### How it works

- MAS allocates capital — **S$1.1B** in Tranche 1 (July 2025), **S$2.85B**
  in Tranche 2 (November 2025), expanded to a **S$6.5B** total in
  February 2026.
- That capital is placed with selected asset managers — names like
  **BlackRock**, **JPMorgan Asset Management**, **Fullerton Fund Management**,
  **Eastspring**, **Lion Global**, **Manulife**, **Avanda**, **Amova**
  (formerly Nikko AM), and **AR Capital**.
- The managers are **mandated to invest in SGX-listed companies** under
  active strategies — not passive index tracking.
- The focus skews towards **undervalued and under-researched** Singapore
  small/mid-caps where liquidity has thinned and analyst coverage has
  retreated.

### Why MAS is doing this

Singapore's equity market has visibly struggled with:

- **Low trading volumes** — daily turnover well below historical norms.
- **Limited analyst coverage** — especially in mid- and small-cap names.
- **Fewer IPOs** and a long-running decline in retail participation.

EQDP is designed to:

- Improve **price discovery** in thinner names.
- Increase **trading liquidity** through real, active, repeated buying.
- Attract both **institutional and retail** investors back into SGX.
- Strengthen Singapore's position as a **regional capital-market hub**.

### One-line summary

> EQDP is **MAS deploying capital via top fund managers to actively invest
> in SGX stocks, aiming to revive liquidity, valuation, and participation
> in Singapore's equity market.**
"""
    )

with right:
    st.markdown(
        """
### Canonical sources

The MAS pages below are the authoritative reference for the programme.
This site triangulates *who is benefiting* from public-market evidence;
the *programme design itself* is documented at the source.
"""
    )
    st.link_button(
        "Programme overview · MAS",
        "https://www.mas.gov.sg/development/asset-management/equity-market-development-programme",
        use_container_width=True,
    )
    st.link_button(
        "First-batch manager appointments (Tranche 1)",
        "https://www.mas.gov.sg/news/media-releases/2025/mas-appoints-first-batch-of-eqdp-asset-managers",
        use_container_width=True,
    )
    st.link_button(
        "Equities Market Review · final report",
        "https://www.mas.gov.sg/news/media-releases/2025/review-group-completes-equities-market-review",
        use_container_width=True,
    )

    st.markdown("&nbsp;")
    st.markdown(
        """
### What this site adds

MAS does not disclose **specific holdings** of EQDP-appointed managers.
The Tracker, Event Studies, and Ticker Analyzer pages on this site
**infer** beneficiaries from:

1. Programmatic eligibility (T2),
2. Broker beneficiary lists — RHB-30, Maybank-18, Edge-69 (T3),
3. Public 5%+ SGXNet substantial-shareholder filings (T1).

The Methodology page lays out the formal stack.
"""
    )

st.markdown("&nbsp;")

# ---------------------------------------------------------------------------
# Programme timeline
# ---------------------------------------------------------------------------
st.subheader("Timeline")

timeline = [
    ("2025-02-21", "Announcement", "MAS publishes the Equity Market Review's final recommendations and announces a S$5B programme."),
    ("2025-07-21", "Tranche 1 deployment", "First batch of three managers appointed — Avanda, Fullerton, JPMorgan AM. S$1.1B allocated."),
    ("2025-11-19", "Tranche 2 deployment", "Six more managers appointed — Amova, AR Capital, BlackRock, Eastspring, Lion Global, Manulife. S$2.85B allocated."),
    ("2026-02-12", "Expansion", "Programme size expanded to S$6.5B."),
]

for date, label, desc in timeline:
    cols = st.columns([0.18, 0.18, 1])
    cols[0].markdown(
        f"<div style='color:#7E89A6;font-family:ui-monospace,monospace;font-size:0.92rem'>{date}</div>",
        unsafe_allow_html=True,
    )
    cols[1].markdown(
        f"<div style='color:#3DD68C;font-weight:600'>{label}</div>",
        unsafe_allow_html=True,
    )
    cols[2].markdown(
        f"<div style='color:#E5E9F2'>{desc}</div>",
        unsafe_allow_html=True,
    )

footer()
