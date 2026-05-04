"""Ticker Analyzer — candlestick + volume + RSI/MACD/Bollinger.

This is the technical-analyst face of the app. The forensic narrative still
applies: vertical event lines, T1 filings annotated, Amihud overlay for
liquidity changes. Returns are *charted* here but never enter the candidate
score upstream.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.components import disclaimer_banner, empty_state, footer, page_header
from lib.supabase import load_filings, load_prices, load_tickers
from lib.ta import amihud, atr, bollinger, ema, macd, rsi, sma
from lib.theme import AMBER, BLUE, GREEN, GRID, INK, MUTED, RED, EVENT_DATES

st.set_page_config(page_title="Ticker Analyzer · EQDP", page_icon=":material/show_chart:", layout="wide")
disclaimer_banner()
page_header(
    "Ticker analyzer",
    subtitle=(
        "Forensic price-action view for any name in the universe. EQDP event "
        "lines and T1 filings are annotated directly on the chart so flow "
        "signals can be read against price."
    ),
    eyebrow="Technical view",
)

universe = load_tickers()
if universe.empty:
    empty_state("Universe is empty.", "Run `pipelines.backfill` to seed.")
    footer()
    st.stop()

# ---------------------------------------------------------------------------
# Controls
# ---------------------------------------------------------------------------
with st.sidebar:
    st.subheader("Selection")
    universe_sorted = universe.sort_values(
        ["t1_flag", "t2_flag", "t3_flag", "ticker"], ascending=[False, False, False, True]
    )
    options = universe_sorted["ticker"].tolist()
    default_idx = 0
    selected = st.selectbox(
        "Ticker",
        options=options,
        index=default_idx,
        format_func=lambda t: f"{t} — {universe.set_index('ticker').loc[t, 'name']}",
    )
    lookback = st.select_slider(
        "Lookback",
        options=["6M", "1Y", "2Y", "3Y", "5Y", "Max"],
        value="2Y",
    )
    st.markdown("---")
    st.subheader("Indicators")
    show_sma20 = st.checkbox("SMA-20", value=True)
    show_sma50 = st.checkbox("SMA-50", value=True)
    show_ema200 = st.checkbox("EMA-200", value=False)
    show_bb = st.checkbox("Bollinger (20, 2)", value=True)
    show_rsi = st.checkbox("RSI-14", value=True)
    show_macd = st.checkbox("MACD (12, 26, 9)", value=True)
    show_amihud = st.checkbox("Amihud illiquidity", value=False)
    show_filings = st.checkbox("Annotate T1 filings", value=True)

LOOKBACK_DAYS = {"6M": 180, "1Y": 365, "2Y": 730, "3Y": 1095, "5Y": 1825, "Max": 9999}
start_date = (
    pd.Timestamp.utcnow().tz_localize(None) - pd.Timedelta(days=LOOKBACK_DAYS[lookback])
).strftime("%Y-%m-%d")

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
prices = load_prices(selected, start=start_date if lookback != "Max" else None)
if prices.empty:
    empty_state(
        f"No prices for {selected}.",
        "Backfill prices_daily for this ticker.",
    )
    footer()
    st.stop()

prices = prices.set_index("trade_date").sort_index()
close = prices["adj_close"].fillna(prices["close"])

# ---------------------------------------------------------------------------
# Header KPIs
# ---------------------------------------------------------------------------
meta = universe.set_index("ticker").loc[selected]
last_close = float(close.iloc[-1])
prev_close = float(close.iloc[-2]) if len(close) >= 2 else last_close
day_chg = (last_close / prev_close - 1) if prev_close else 0.0
hi52 = float(close.tail(252).max()) if len(close) >= 5 else last_close
lo52 = float(close.tail(252).min()) if len(close) >= 5 else last_close
ret_period = (last_close / float(close.iloc[0]) - 1) if len(close) >= 2 else 0.0

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric(f"{selected}", f"S$ {last_close:,.3f}", f"{day_chg:+.2%}")
c2.metric(f"Period return ({lookback})", f"{ret_period:+.2%}")
c3.metric("52w high", f"S$ {hi52:,.3f}")
c4.metric("52w low", f"S$ {lo52:,.3f}")
c5.metric(
    "Tier",
    meta.get("headline_tier", "—"),
    f"{meta.get('sector') or ''} · {meta.get('market_cap_band') or ''}",
)

# ---------------------------------------------------------------------------
# Build chart
# ---------------------------------------------------------------------------
panels = 1 + (1 if show_rsi else 0) + (1 if show_macd else 0) + (1 if show_amihud else 0)
heights = [0.55] + [0.45 / max(panels - 1, 1)] * (panels - 1)
fig = make_subplots(
    rows=panels,
    cols=1,
    shared_xaxes=True,
    vertical_spacing=0.04,
    row_heights=heights,
)

# 1. Price + volume
fig.add_trace(
    go.Candlestick(
        x=prices.index,
        open=prices["open"],
        high=prices["high"],
        low=prices["low"],
        close=prices["close"],
        increasing_line_color=GREEN,
        decreasing_line_color=RED,
        increasing_fillcolor=GREEN,
        decreasing_fillcolor=RED,
        name=selected,
        showlegend=False,
    ),
    row=1,
    col=1,
)

if show_sma20:
    fig.add_trace(
        go.Scatter(
            x=prices.index,
            y=sma(close, 20),
            mode="lines",
            name="SMA-20",
            line=dict(color=BLUE, width=1.2),
        ),
        row=1,
        col=1,
    )
if show_sma50:
    fig.add_trace(
        go.Scatter(
            x=prices.index,
            y=sma(close, 50),
            mode="lines",
            name="SMA-50",
            line=dict(color=AMBER, width=1.2),
        ),
        row=1,
        col=1,
    )
if show_ema200:
    fig.add_trace(
        go.Scatter(
            x=prices.index,
            y=ema(close, 200),
            mode="lines",
            name="EMA-200",
            line=dict(color="#A78BFA", width=1.2),
        ),
        row=1,
        col=1,
    )
if show_bb:
    bb = bollinger(close, 20, 2.0)
    fig.add_trace(
        go.Scatter(
            x=prices.index,
            y=bb["upper"],
            mode="lines",
            line=dict(color=GRID, width=1),
            showlegend=False,
            hoverinfo="skip",
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=prices.index,
            y=bb["lower"],
            mode="lines",
            line=dict(color=GRID, width=1),
            fill="tonexty",
            fillcolor="rgba(127, 137, 166, 0.10)",
            name="BB-20·2",
            hoverinfo="skip",
        ),
        row=1,
        col=1,
    )

# Volume on the price subplot's secondary axis is messy in subplots; instead,
# overlay volume bars at the foot of the price panel as a thin band.
vol = prices["volume"].astype(float)
vol_scale = vol.max() if vol.max() > 0 else 1.0
y_lo = float(prices[["low", "open", "close"]].min().min())
y_hi = float(prices[["high", "open", "close"]].max().max())
band = (y_hi - y_lo) * 0.18
vol_y = y_lo - band + (vol / vol_scale) * band * 0.9
colors = np.where(prices["close"] >= prices["open"], GREEN, RED)
fig.add_trace(
    go.Bar(
        x=prices.index,
        y=vol_y - (y_lo - band),
        base=y_lo - band,
        marker_color=colors,
        opacity=0.45,
        name="volume",
        showlegend=False,
        hovertemplate="vol %{customdata:,.0f}<extra></extra>",
        customdata=vol,
    ),
    row=1,
    col=1,
)

next_row = 2

# 2. RSI
if show_rsi:
    rsi_vals = rsi(close, 14)
    fig.add_trace(
        go.Scatter(
            x=prices.index,
            y=rsi_vals,
            mode="lines",
            name="RSI-14",
            line=dict(color=BLUE, width=1.4),
            showlegend=False,
        ),
        row=next_row,
        col=1,
    )
    fig.add_hline(y=70, line=dict(color=RED, width=1, dash="dot"), row=next_row, col=1)
    fig.add_hline(y=30, line=dict(color=GREEN, width=1, dash="dot"), row=next_row, col=1)
    fig.update_yaxes(title_text="RSI", range=[0, 100], row=next_row, col=1)
    next_row += 1

# 3. MACD
if show_macd:
    md = macd(close, 12, 26, 9)
    hist_colors = np.where(md["hist"] >= 0, GREEN, RED)
    fig.add_trace(
        go.Bar(
            x=prices.index,
            y=md["hist"],
            marker_color=hist_colors,
            name="MACD hist",
            showlegend=False,
            opacity=0.55,
        ),
        row=next_row,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=prices.index,
            y=md["macd"],
            mode="lines",
            line=dict(color=BLUE, width=1.4),
            name="MACD",
            showlegend=False,
        ),
        row=next_row,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=prices.index,
            y=md["signal"],
            mode="lines",
            line=dict(color=AMBER, width=1.2),
            name="signal",
            showlegend=False,
        ),
        row=next_row,
        col=1,
    )
    fig.update_yaxes(title_text="MACD", row=next_row, col=1)
    next_row += 1

# 4. Amihud
if show_amihud:
    am = amihud(close, prices["volume"])
    fig.add_trace(
        go.Scatter(
            x=prices.index,
            y=am,
            mode="lines",
            line=dict(color="#A78BFA", width=1.4),
            name="Amihud (60d)",
            showlegend=False,
        ),
        row=next_row,
        col=1,
    )
    fig.update_yaxes(title_text="Amihud", row=next_row, col=1)
    next_row += 1

# Event lines on every subplot
for date_str in EVENT_DATES.values():
    fig.add_vline(
        x=date_str,
        line=dict(color=AMBER, width=1, dash="dot"),
        annotation_text=None,
    )

# T1-filing markers for this ticker
if show_filings:
    filings = load_filings(limit=None)
    if not filings.empty:
        my_filings = filings[filings["ticker"] == selected]
        for _, row in my_filings.iterrows():
            fig.add_vline(
                x=str(row["filing_date"]),
                line=dict(color=GREEN, width=1, dash="dash"),
                row=1,
                col=1,
            )

fig.update_xaxes(rangeslider_visible=False)
fig.update_layout(
    height=180 + 280 * panels // 2 + 220,
    showlegend=True,
    legend=dict(orientation="h", y=1.06, x=0),
    margin=dict(l=40, r=20, t=30, b=30),
)
st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})

# ---------------------------------------------------------------------------
# Side panels — current indicator readout + filings table
# ---------------------------------------------------------------------------
left, right = st.columns([1, 1])
with left:
    st.subheader("Indicator readout")
    rsi_now = float(rsi(close, 14).dropna().iloc[-1]) if len(close) > 14 else float("nan")
    md = macd(close, 12, 26, 9).iloc[-1] if len(close) > 35 else None
    atr_now = float(atr(prices["high"], prices["low"], close, 14).dropna().iloc[-1]) if len(close) > 14 else float("nan")
    bb_now = bollinger(close, 20, 2).iloc[-1] if len(close) > 20 else None
    rows: list[tuple[str, str]] = []
    rows.append(("RSI-14", f"{rsi_now:.1f}" if not np.isnan(rsi_now) else "—"))
    if md is not None:
        rows.append(("MACD", f"{md['macd']:.4f}"))
        rows.append(("MACD signal", f"{md['signal']:.4f}"))
        rows.append(("MACD hist", f"{md['hist']:+.4f}"))
    rows.append(("ATR-14", f"{atr_now:.4f}" if not np.isnan(atr_now) else "—"))
    if bb_now is not None:
        pct_b = (last_close - bb_now["lower"]) / (bb_now["upper"] - bb_now["lower"]) if bb_now["upper"] != bb_now["lower"] else float("nan")
        rows.append(("Bollinger %B", f"{pct_b:.2f}"))
    table = pd.DataFrame(rows, columns=["indicator", "value"])
    st.dataframe(table, use_container_width=True, hide_index=True)

with right:
    st.subheader("T1 filings on this name")
    filings = load_filings(limit=None)
    my_filings = (
        filings[filings["ticker"] == selected]
        if not filings.empty
        else pd.DataFrame()
    )
    if my_filings.empty:
        st.caption("No 5%+ filings on this name yet.")
    else:
        st.dataframe(
            my_filings[
                ["filing_date", "manager_id", "stake_pct", "direction", "source_url"]
            ].rename(
                columns={
                    "filing_date": "Filed",
                    "manager_id": "Manager",
                    "stake_pct": "Stake %",
                    "direction": "Direction",
                    "source_url": "Source",
                }
            ),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Stake %": st.column_config.NumberColumn(format="%.2f"),
                "Source": st.column_config.LinkColumn(display_text="SGXNet"),
            },
        )

footer()
