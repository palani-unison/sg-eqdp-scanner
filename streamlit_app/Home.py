"""sg-eqdp-scanner — Streamlit entry point.

Run locally:
    streamlit run streamlit_app/Home.py

Deploy on Streamlit Community Cloud:
    1. Push this repo to GitHub.
    2. New app → main file path = `streamlit_app/Home.py`.
    3. Paste secrets from `.streamlit/secrets.toml.example` into Settings → Secrets.
"""

from __future__ import annotations

import datetime as dt

import plotly.graph_objects as go
import streamlit as st

from lib.components import disclaimer_banner, empty_state, footer, kpi_row, page_header
from lib.store import (
    latest_pipeline_runs,
    load_did_forest,
    load_factor_returns,
    load_filings,
    load_latest_scores,
    load_tickers,
)
from lib.theme import EVENT_DATES, EVENT_LABELS, GREEN, MUTED, RED, event_annotations, event_shapes
from lib.ta import cumulative

st.set_page_config(
    page_title="EQDP Scanner — Singapore equity programme impact",
    page_icon=":material/finance_mode:",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Sidebar identity / disclaimer
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### EQDP Scanner")
    st.caption(
        "Forensic study of the MAS Equity Market Development Programme — "
        "who actually benefited, and by how much."
    )
    st.markdown("---")
    st.markdown(
        f"**Today:** {dt.date.today():%Y-%m-%d}  \n"
        "**Maintainer:** Palaniappan Chidambaram  \n"
        "**Status:** _personal research_"
    )
    st.markdown("---")
    st.caption(
        "Data refreshed daily from Supabase (gold layer). "
        "Pipelines run on GitHub Actions; the source of truth is Postgres."
    )

# ---------------------------------------------------------------------------
# Hero
# ---------------------------------------------------------------------------
disclaimer_banner()
page_header(
    "EQDP Brief",
    subtitle=(
        "S$6.5 billion has been allocated to nine asset managers under the MAS "
        "Equity Market Development Programme. MAS does not disclose specific "
        "holdings — so this site does the next-best thing: triangulate the "
        "beneficiaries from eligibility, broker coverage, market microstructure, "
        "and 5%+ filings, then measure the impact rigorously."
    ),
    eyebrow="Singapore · MAS EQDP · personal research",
)

# ---------------------------------------------------------------------------
# Pipeline status banner
# ---------------------------------------------------------------------------
runs = latest_pipeline_runs(limit=5)
if not runs.empty:
    last = runs.iloc[0]
    fresh = (dt.datetime.now(dt.timezone.utc) - last["started_at"].to_pydatetime()).days
    pill = "fresh" if fresh <= 2 else "stale"
    color = GREEN if pill == "fresh" else RED
    st.markdown(
        f"<div style='display:flex;align-items:center;gap:0.6rem;margin-bottom:0.5rem'>"
        f"<span style='width:8px;height:8px;border-radius:999px;background:{color};"
        f"box-shadow:0 0 0 4px {color}22'></span>"
        f"<span style='color:#7E89A6;font-size:0.88rem'>Last refresh: "
        f"<b style='color:#E5E9F2'>{last['started_at']:%Y-%m-%d %H:%M UTC}</b> · "
        f"job <b style='color:#E5E9F2'>{last['job_name']}</b> · "
        f"<span style='color:{color}'>{last['status']}</span></span>"
        f"</div>",
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Top-row KPIs
# ---------------------------------------------------------------------------
tickers_df = load_tickers()
filings_df = load_filings(limit=None)
scores_df = load_latest_scores(top_n=0)

if not tickers_df.empty:
    kpi_row(
        [
            ("Universe", f"{len(tickers_df):,}", None),
            ("T1 — confirmed", f"{int(tickers_df['t1_flag'].sum()):,}", None),
            ("T2 — eligible", f"{int(tickers_df['t2_flag'].sum()):,}", None),
            ("T3 — broker-named", f"{int(tickers_df['t3_flag'].sum()):,}", None),
            (
                "T1 filings",
                f"{len(filings_df):,}" if not filings_df.empty else "0",
                None,
            ),
        ]
    )
else:
    empty_state(
        "Universe table is empty.",
        "Run `python -m pipelines.backfill --start 2020-01-01 --end yesterday` to seed Supabase.",
    )

st.markdown("&nbsp;")

# ---------------------------------------------------------------------------
# Two-column layout: STI cumulative + DiD forest
# ---------------------------------------------------------------------------
left, right = st.columns([1.4, 1])

with left:
    st.subheader("STI cumulative return — with EQDP event lines")
    factor = load_factor_returns(start="2024-01-02")
    if factor.empty or "market" not in factor.columns:
        empty_state("No factor returns yet.", "factor_returns table is empty.")
    else:
        factor = factor.dropna(subset=["market"]).copy()
        factor["cum"] = cumulative(factor["market"])
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=factor["trade_date"],
                y=factor["cum"],
                mode="lines",
                name="STI",
                line=dict(color=GREEN, width=2),
                hovertemplate="%{x|%Y-%m-%d}<br>cum return %{y:.2%}<extra></extra>",
            )
        )
        fig.update_layout(
            height=380,
            yaxis_tickformat=".0%",
            xaxis_title=None,
            yaxis_title="cumulative return",
            shapes=event_shapes(),
            annotations=event_annotations(),
        )
        st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("DiD impact (treated − control) — 90% CI")
    forest = load_did_forest()
    if forest.empty:
        empty_state(
            "No bootstrap CIs yet.",
            "Run `python -m pipelines.compute_bootstrap` after the DiD pipeline.",
        )
    else:
        order = list(EVENT_DATES.keys())
        forest = forest.set_index("scope").reindex(order).dropna().reset_index()
        forest["label"] = forest["scope"].map(lambda s: EVENT_LABELS.get(s, s).split(" (")[0])
        fig = go.Figure()
        for _, row in forest.iterrows():
            sig = (row["lower_5"] > 0) or (row["upper_95"] < 0)
            color = GREEN if sig else MUTED
            fig.add_trace(
                go.Scatter(
                    x=[row["lower_5"], row["upper_95"]],
                    y=[row["label"], row["label"]],
                    mode="lines",
                    line=dict(color=color, width=4),
                    showlegend=False,
                    hoverinfo="skip",
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=[row["point_estimate"]],
                    y=[row["label"]],
                    mode="markers",
                    marker=dict(color=color, size=12, line=dict(color="#0B1020", width=2)),
                    showlegend=False,
                    hovertemplate=(
                        f"<b>{row['label']}</b><br>"
                        f"δ {row['point_estimate']:.2%}<br>"
                        f"CI [{row['lower_5']:.2%}, {row['upper_95']:.2%}]<extra></extra>"
                    ),
                )
            )
        fig.add_vline(x=0, line=dict(color=MUTED, width=1, dash="dot"))
        fig.update_layout(
            height=380,
            xaxis_tickformat=".1%",
            xaxis_title="treated − control (CAR)",
            yaxis_title=None,
            margin=dict(l=160, r=20, t=20, b=40),
        )
        st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# Latest top-of-screen
# ---------------------------------------------------------------------------
st.subheader("Latest candidate scores — top of screen")
top = load_latest_scores(top_n=15)
if top.empty:
    empty_state(
        "No candidate scores yet.",
        "Run `python -m pipelines.score_pipeline` after metrics are populated.",
    )
else:
    show = top[
        [
            "ticker",
            "eqdp_tier",
            "total_score",
            "liquidity_rise",
            "institutional_proxy",
            "index_inclusion",
            "broker_named",
            "filing_present",
            "score_date",
        ]
    ].copy()
    show.columns = [
        "Ticker",
        "Tier",
        "Score",
        "Liquidity Δ",
        "Inst. proxy",
        "Index incl.",
        "Broker named",
        "Filing",
        "As of",
    ]
    st.dataframe(
        show,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Score": st.column_config.ProgressColumn(
                "Score", min_value=0.0, max_value=1.0, format="%.2f"
            ),
            "Liquidity Δ": st.column_config.NumberColumn(format="%.2f"),
            "Inst. proxy": st.column_config.NumberColumn(format="%.2f"),
            "Broker named": st.column_config.NumberColumn(format="%.2f"),
        },
    )
    st.caption(
        "**Reminder:** the candidate score does not see returns. "
        "It uses only liquidity, institutional proxy, index inclusion, "
        "broker naming, and filing presence — see Methodology."
    )

footer()
