"""SGXNet 5%+ filings tracker."""

from __future__ import annotations

import sys
from pathlib import Path

import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.components import disclaimer_banner, empty_state, footer, page_header
from lib.supabase import load_filings, load_managers

st.set_page_config(page_title="Filings · EQDP", page_icon=":material/inventory_2:", layout="wide")
disclaimer_banner()
page_header(
    "T1 — substantial-shareholder filings",
    subtitle=(
        "Every SGXNet 5%+ filing on or after 2025-07-21 from one of the nine "
        "EQDP-appointed managers, with the manager's tranche tagged. This is "
        "the only *direct* evidence of beneficiary identity — the rest of the "
        "site is inference around it."
    ),
    eyebrow="The ground truth",
)

filings = load_filings(limit=None)
managers = load_managers()

if filings.empty:
    empty_state(
        "No filings ingested yet.",
        "Run `python -m pipelines.weekly_filings` after configuring the SGXNet scraper.",
    )
    footer()
    st.stop()

if not managers.empty:
    filings = filings.merge(
        managers[["manager_id", "canonical_name", "tranche"]],
        on="manager_id",
        how="left",
    )
else:
    filings["canonical_name"] = filings["manager_id"]
    filings["tranche"] = None

c1, c2, c3, c4 = st.columns(4)
c1.metric("Filings", f"{len(filings):,}")
c2.metric("Unique tickers", f"{filings['ticker'].nunique():,}")
c3.metric("Unique managers", f"{filings['manager_id'].nunique():,}")
c4.metric(
    "Most recent",
    f"{filings['filing_date'].max():%Y-%m-%d}" if not filings.empty else "—",
)

st.markdown("&nbsp;")

# Activity timeline
st.subheader("Filings cadence")
cadence = (
    filings.assign(month=filings["filing_date"].astype("datetime64[ns]").dt.to_period("M").dt.to_timestamp())
    .groupby("month")
    .size()
    .reset_index(name="count")
)
fig = px.bar(cadence, x="month", y="count")
fig.update_traces(marker_color="#3DD68C", opacity=0.85)
fig.update_layout(height=260, xaxis_title=None, yaxis_title="filings", bargap=0.1)
st.plotly_chart(fig, use_container_width=True)

st.subheader("All filings")
show = filings[
    [
        "filing_date",
        "effective_date",
        "ticker",
        "canonical_name",
        "tranche",
        "stake_pct",
        "direction",
        "source_url",
    ]
].rename(
    columns={
        "filing_date": "Filed",
        "effective_date": "Effective",
        "ticker": "Ticker",
        "canonical_name": "Manager",
        "tranche": "Tranche",
        "stake_pct": "Stake %",
        "direction": "Direction",
        "source_url": "Source",
    }
)
st.dataframe(
    show,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Stake %": st.column_config.NumberColumn(format="%.2f"),
        "Tranche": st.column_config.NumberColumn(format="%d"),
        "Source": st.column_config.LinkColumn(display_text="SGXNet"),
    },
)

footer()
