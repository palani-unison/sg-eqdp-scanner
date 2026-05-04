"""Event studies — CARs around the four EQDP events, treated vs control."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.components import disclaimer_banner, empty_state, footer, page_header
from lib.supabase import load_event_study, load_tickers
from lib.theme import BLUE, GREEN, MUTED, EVENT_LABELS

st.set_page_config(page_title="Event Studies · EQDP", page_icon=":material/timeline:", layout="wide")
disclaimer_banner()
page_header(
    "Event-study CARs",
    subtitle=(
        "Mean cumulative abnormal return (CAR) on each event date for treated "
        "(T1∪T2∪T3) versus control (STI-30). Benchmark choice — CAPM, FF3, "
        "or simple market-adjusted — toggleable below. The β estimation window "
        "ends 30 trading days before the event to avoid contamination."
    ),
    eyebrow="Methodology §1–2 · 252-day β window",
)

tickers = load_tickers()
if tickers.empty:
    empty_state("Universe is empty.", "Run pipelines.backfill first.")
    footer()
    st.stop()

tier_of: dict[str, str] = {}
for _, row in tickers.iterrows():
    if row.get("in_sti30"):
        tier_of[row["ticker"]] = "control"
    elif row.get("t1_flag") or row.get("t2_flag") or row.get("t3_flag"):
        tier_of[row["ticker"]] = "treated"

with st.sidebar:
    st.subheader("Controls")
    benchmark = st.radio(
        "Benchmark",
        options=["capm", "ff3", "market_adjusted"],
        format_func=lambda v: {"capm": "CAPM", "ff3": "Fama-French 3", "market_adjusted": "Market-adj."}[v],
        horizontal=False,
    )
    show_table = st.toggle("Show numeric table", value=False)


def _per_t_means(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["bucket"] = df["ticker"].map(tier_of)
    df = df.dropna(subset=["bucket", "car"])
    out = (
        df.groupby(["t", "bucket"])["car"]
        .agg(["mean", "std", "count"])
        .reset_index()
        .pivot(index="t", columns="bucket")
    )
    out.columns = [f"{a}_{b}" for a, b in out.columns]
    return out.sort_index()


tab_keys = list(EVENT_LABELS.keys())
tabs = st.tabs([EVENT_LABELS[k] for k in tab_keys])

for tab, event_id in zip(tabs, tab_keys):
    with tab:
        ar_df = load_event_study(event_id, benchmark=benchmark)
        if ar_df.empty:
            empty_state(
                f"No abnormal_returns rows for {event_id} / {benchmark}.",
                "Run `pipelines.compute_metrics` to populate.",
            )
            continue

        agg = _per_t_means(ar_df)
        if agg.empty:
            empty_state("No treated/control rows after filtering.", None)
            continue

        fig = go.Figure()
        if "mean_treated" in agg.columns:
            ci = (1.96 * agg["std_treated"] / agg["count_treated"].pow(0.5)).fillna(0)
            fig.add_trace(
                go.Scatter(
                    x=agg.index,
                    y=agg["mean_treated"] + ci,
                    mode="lines",
                    line=dict(width=0),
                    showlegend=False,
                    hoverinfo="skip",
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=agg.index,
                    y=agg["mean_treated"] - ci,
                    mode="lines",
                    line=dict(width=0),
                    fill="tonexty",
                    fillcolor="rgba(61, 214, 140, 0.18)",
                    showlegend=False,
                    hoverinfo="skip",
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=agg.index,
                    y=agg["mean_treated"],
                    mode="lines",
                    name="treated",
                    line=dict(color=GREEN, width=2.5),
                    hovertemplate="t=%{x}<br>CAR %{y:.2%}<extra>treated</extra>",
                )
            )
        if "mean_control" in agg.columns:
            fig.add_trace(
                go.Scatter(
                    x=agg.index,
                    y=agg["mean_control"],
                    mode="lines",
                    name="control (STI-30)",
                    line=dict(color=BLUE, width=2, dash="dash"),
                    hovertemplate="t=%{x}<br>CAR %{y:.2%}<extra>control</extra>",
                )
            )
        fig.add_vline(x=0, line=dict(color=MUTED, width=1, dash="dot"))
        fig.add_hline(y=0, line=dict(color=MUTED, width=1, dash="dot"))
        fig.update_layout(
            height=440,
            xaxis_title="event time (trading days)",
            yaxis_title="cumulative abnormal return",
            yaxis_tickformat=".1%",
            legend=dict(orientation="h", y=-0.18),
        )
        st.plotly_chart(fig, use_container_width=True)

        # KPI strip — terminal CAR + difference
        if "mean_treated" in agg.columns and "mean_control" in agg.columns:
            term_t = agg["mean_treated"].iloc[-1]
            term_c = agg["mean_control"].iloc[-1]
            n_t = int(agg["count_treated"].max() or 0)
            n_c = int(agg["count_control"].max() or 0)
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Terminal CAR — treated", f"{term_t:.2%}", f"n={n_t}")
            c2.metric("Terminal CAR — control", f"{term_c:.2%}", f"n={n_c}")
            c3.metric("Treated − control", f"{term_t - term_c:+.2%}")
            c4.metric("Window", f"{int(agg.index.min())} → {int(agg.index.max())}")

        if show_table:
            st.dataframe(
                agg.round(4),
                use_container_width=True,
            )

footer()
