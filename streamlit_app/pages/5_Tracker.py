"""Tracker — full candidate-score table with filtering and tier breakdown."""

from __future__ import annotations

import sys
from pathlib import Path

import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.components import disclaimer_banner, empty_state, footer, page_header
from lib.store import load_latest_scores, load_tickers
from lib.theme import TIER_COLORS

st.set_page_config(page_title="Tracker · EQDP Scanner", page_icon=":material/leaderboard:", layout="wide")
disclaimer_banner()
page_header(
    "Candidate-score tracker",
    subtitle=(
        "The screen that fires before any return is observed. Inputs: liquidity rise, "
        "institutional proxy, index inclusion, broker naming, filing presence. "
        "**Returns are deliberately excluded** — see Methodology §3."
    ),
    eyebrow="Daily snapshot · screen, not signal",
)

scores = load_latest_scores(top_n=0)
tickers = load_tickers()

if scores.empty or tickers.empty:
    empty_state("No data yet.", "Run the pipeline once and refresh.")
    footer()
    st.stop()

merged = scores.merge(
    tickers[["ticker", "name", "sector", "market_cap_band", "listing_board"]],
    on="ticker",
    how="left",
)

with st.sidebar:
    st.subheader("Filters")
    tiers = sorted(merged["eqdp_tier"].dropna().unique().tolist())
    sel_tiers = st.multiselect("Tier", tiers, default=tiers)
    sectors = sorted([s for s in merged["sector"].dropna().unique().tolist()])
    sel_sectors = st.multiselect("Sector", sectors, default=sectors)
    min_score = st.slider("Min score", 0.0, 1.0, 0.0, 0.05)
    boards = sorted(merged["listing_board"].dropna().unique().tolist())
    sel_boards = st.multiselect("Board", boards, default=boards)

flt = merged[
    merged["eqdp_tier"].isin(sel_tiers)
    & merged["sector"].fillna("").isin(sel_sectors + [""])
    & (merged["total_score"].fillna(0) >= min_score)
    & merged["listing_board"].fillna("").isin(sel_boards + [""])
].copy()

# KPI strip
c1, c2, c3, c4 = st.columns(4)
c1.metric("In view", f"{len(flt):,}", f"{len(flt)/max(len(merged),1):.0%} of universe")
c2.metric("Median score", f"{flt['total_score'].median():.2f}" if len(flt) else "—")
c3.metric(
    "Top score",
    f"{flt['total_score'].max():.2f}" if len(flt) else "—",
    flt.iloc[0]["ticker"] if len(flt) else None,
)
c4.metric(
    "As of",
    f"{flt['score_date'].max()}" if len(flt) else "—",
)

st.markdown("&nbsp;")

left, right = st.columns([1, 1])
with left:
    st.subheader("Score distribution")
    if not flt.empty:
        fig = px.histogram(
            flt,
            x="total_score",
            color="eqdp_tier",
            nbins=24,
            color_discrete_map=TIER_COLORS,
            barmode="stack",
        )
        fig.update_layout(
            height=320,
            xaxis_title="total score",
            yaxis_title="count",
            legend_title=None,
        )
        st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Tier composition")
    if not flt.empty:
        tier_counts = (
            flt["eqdp_tier"].value_counts().rename_axis("tier").reset_index(name="count")
        )
        fig = px.bar(
            tier_counts,
            x="tier",
            y="count",
            color="tier",
            color_discrete_map=TIER_COLORS,
            text="count",
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(height=320, showlegend=False, xaxis_title=None, yaxis_title=None)
        st.plotly_chart(fig, use_container_width=True)

st.subheader("Ranked screen")
display_cols = [
    "ticker",
    "name",
    "eqdp_tier",
    "total_score",
    "liquidity_rise",
    "institutional_proxy",
    "index_inclusion",
    "broker_named",
    "filing_present",
    "sector",
    "market_cap_band",
]
show = flt[display_cols].rename(
    columns={
        "ticker": "Ticker",
        "name": "Name",
        "eqdp_tier": "Tier",
        "total_score": "Score",
        "liquidity_rise": "Liq Δ",
        "institutional_proxy": "Inst. proxy",
        "index_inclusion": "Index",
        "broker_named": "Broker",
        "filing_present": "Filing",
        "sector": "Sector",
        "market_cap_band": "Cap",
    }
)
st.dataframe(
    show,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Score": st.column_config.ProgressColumn(
            "Score", min_value=0.0, max_value=1.0, format="%.2f"
        ),
        "Liq Δ": st.column_config.NumberColumn(format="%.2f"),
        "Inst. proxy": st.column_config.NumberColumn(format="%.2f"),
        "Broker": st.column_config.NumberColumn(format="%.2f"),
    },
)

st.download_button(
    "Download CSV",
    show.to_csv(index=False).encode("utf-8"),
    file_name=f"eqdp-tracker-{flt['score_date'].max()}.csv",
    mime="text/csv",
    use_container_width=False,
)

footer()
