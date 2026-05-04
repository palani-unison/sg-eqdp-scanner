"""Universe explorer — T1 / T2 / T3 / control breakdown."""

from __future__ import annotations

import sys
from pathlib import Path

import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.components import disclaimer_banner, empty_state, footer, page_header, tier_pill
from lib.supabase import load_managers, load_tickers
from lib.theme import TIER_COLORS

st.set_page_config(page_title="Universe · EQDP", page_icon=":material/dataset:", layout="wide")
disclaimer_banner()
page_header(
    "The three-tier universe",
    subtitle=(
        "**T1** stocks where ≥1 EQDP-appointed manager filed a 5%+ disclosure. "
        "**T2** stocks satisfying programmatic eligibility (small/mid-cap, "
        "Mainboard or Catalist, daily-traded, not STI-30, not restricted). "
        "**T3** stocks named by RHB-30, Maybank-18, Edge-69 broker notes. "
        "**Control** is STI-30 large caps."
    ),
    eyebrow="Population definition",
)

df = load_tickers()
if df.empty:
    empty_state("Universe is empty.", "Run `python -m pipelines.backfill` to seed.")
    footer()
    st.stop()

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total tickers", f"{len(df):,}")
c2.metric("T1 — confirmed", f"{int(df['t1_flag'].sum()):,}")
c3.metric("T2 — eligible", f"{int(df['t2_flag'].sum()):,}")
c4.metric("T3 — broker-named", f"{int(df['t3_flag'].sum()):,}")
c5.metric("Control (STI-30)", f"{int(df['in_sti30'].sum()):,}")

st.markdown("&nbsp;")

# --- Tier × Sector heatmap
left, right = st.columns([1.2, 1])
with left:
    st.subheader("Headline tier × sector")
    hm = (
        df.assign(tier=df["headline_tier"])
        .groupby(["sector", "tier"])
        .size()
        .reset_index(name="count")
    )
    if not hm.empty:
        fig = px.density_heatmap(
            hm,
            x="tier",
            y="sector",
            z="count",
            color_continuous_scale="Viridis",
        )
        fig.update_layout(
            height=460, xaxis_title=None, yaxis_title=None, coloraxis_colorbar=dict(title=None)
        )
        st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("EQDP-appointed managers")
    managers = load_managers()
    if managers.empty:
        empty_state("No managers loaded.", None)
    else:
        for _, m in managers.iterrows():
            tranche = m.get("tranche")
            badge = "T1·Jul-2025" if tranche == 1 else "T2·Nov-2025"
            st.markdown(
                f"<div style='border:1px solid #1F2742;border-radius:8px;"
                f"padding:0.6rem 0.85rem;margin-bottom:0.5rem'>"
                f"<div style='display:flex;justify-content:space-between;"
                f"align-items:center'>"
                f"<b>{m['canonical_name']}</b>"
                f"<span style='color:#7E89A6;font-size:0.78rem'>{badge}</span>"
                f"</div></div>",
                unsafe_allow_html=True,
            )

st.markdown("&nbsp;")

# --- Filterable list
st.subheader("Browse the universe")
with st.sidebar:
    st.subheader("Filters")
    tier_choice = st.multiselect(
        "Headline tier",
        options=["T1", "T2", "T3", "control", "none"],
        default=["T1", "T2", "T3"],
    )
    cap = st.multiselect(
        "Cap band",
        options=["large", "mid", "small", "micro"],
        default=["large", "mid", "small", "micro"],
    )
    sectors = sorted([s for s in df["sector"].dropna().unique().tolist()])
    sec = st.multiselect("Sector", options=sectors, default=sectors)

flt = df[
    df["headline_tier"].isin(tier_choice)
    & df["market_cap_band"].fillna("").isin(cap + [""])
    & df["sector"].fillna("").isin(sec + [""])
].copy()

show = flt[
    [
        "ticker",
        "name",
        "headline_tier",
        "sector",
        "market_cap_band",
        "listing_board",
        "broker_named_count",
        "in_sti30",
        "in_next50",
    ]
].rename(
    columns={
        "ticker": "Ticker",
        "name": "Name",
        "headline_tier": "Tier",
        "sector": "Sector",
        "market_cap_band": "Cap",
        "listing_board": "Board",
        "broker_named_count": "# Brokers",
        "in_sti30": "STI",
        "in_next50": "Next50",
    }
)
st.dataframe(show, use_container_width=True, hide_index=True)
st.caption(f"{len(flt):,} of {len(df):,} tickers in view")

footer()
