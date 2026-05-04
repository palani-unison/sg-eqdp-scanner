"""Ticker Analyzer — candlestick + volume + RSI/MACD/Bollinger + Amihud.

All controls live in-page (not the sidebar) so the chart canvas owns the
full width. Event lines (4 EQDP dates) and any T1 filings are annotated
on the price panel only; indicator subplots stay clean.
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
from lib.store import load_filings, load_prices, load_tickers
from lib.ta import amihud, atr, bollinger, ema, macd, rsi, sma
from lib.theme import AMBER, BLUE, GREEN, GRID, INK, MUTED, PURPLE, RED, EVENT_DATES, EVENT_LABELS

st.set_page_config(page_title="Ticker Analyzer · EQDP", page_icon=":material/show_chart:", layout="wide")
disclaimer_banner()
page_header(
    "Ticker analyzer",
    subtitle=(
        "Forensic price-action view for any name in the universe. "
        "EQDP event lines overlay the price panel directly so flow signals "
        "can be read against price."
    ),
    eyebrow="Technical view",
)

universe = load_tickers()
if universe.empty:
    empty_state("Universe is empty.", "Run `pipelines.backfill` to seed.")
    footer()
    st.stop()

# ---------------------------------------------------------------------------
# In-page controls
# ---------------------------------------------------------------------------
LOOKBACK_DAYS = {"6M": 180, "1Y": 365, "2Y": 730, "3Y": 1095, "5Y": 1825, "Max": 9999}

universe_sorted = universe.sort_values(
    ["t1_flag", "t2_flag", "t3_flag", "ticker"], ascending=[False, False, False, True]
)
options = universe_sorted["ticker"].tolist()
ticker_label = lambda t: f"{t} — {universe.set_index('ticker').loc[t, 'name']}"

ctrl_left, ctrl_mid, ctrl_right = st.columns([1.6, 1, 2.2])
with ctrl_left:
    selected = st.selectbox(
        "Ticker",
        options=options,
        index=0,
        format_func=ticker_label,
        label_visibility="visible",
    )
with ctrl_mid:
    lookback = st.selectbox(
        "Lookback",
        options=list(LOOKBACK_DAYS.keys()),
        index=2,
        label_visibility="visible",
    )
with ctrl_right:
    indicator_choices = st.multiselect(
        "Indicators",
        options=["SMA-20", "SMA-50", "EMA-200", "Bollinger", "RSI", "MACD", "Amihud"],
        default=["SMA-20", "SMA-50", "Bollinger", "RSI", "MACD"],
        label_visibility="visible",
    )
selected_set = set(indicator_choices)

start_date = (
    pd.Timestamp.utcnow().tz_localize(None) - pd.Timedelta(days=LOOKBACK_DAYS[lookback])
).strftime("%Y-%m-%d")

# ---------------------------------------------------------------------------
# Load + sanitize data
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
# adj_close should be primary; fall back to close on rows where adj is null.
prices["adj_close"] = pd.to_numeric(prices["adj_close"], errors="coerce")
prices["close"] = pd.to_numeric(prices["close"], errors="coerce")
close = prices["adj_close"].where(prices["adj_close"].notna(), prices["close"])
close = close.dropna()
if close.empty:
    empty_state(f"No usable close prices for {selected}.", None)
    footer()
    st.stop()

prices_chart = prices.loc[close.index].copy()

# ---------------------------------------------------------------------------
# Header KPI strip
# ---------------------------------------------------------------------------
meta = universe.set_index("ticker").loc[selected]
last_close = float(close.iloc[-1])
prev_close = float(close.iloc[-2]) if len(close) >= 2 else last_close
day_chg = (last_close / prev_close - 1) if prev_close else 0.0
window_252 = close.tail(252)
hi52 = float(window_252.max())
lo52 = float(window_252.min())
ret_period = (last_close / float(close.iloc[0]) - 1) if len(close) >= 2 else 0.0

kc1, kc2, kc3, kc4, kc5 = st.columns(5)
kc1.metric(f"{selected}", f"S$ {last_close:,.3f}", f"{day_chg:+.2%}")
kc2.metric(f"Period return ({lookback})", f"{ret_period:+.2%}")
kc3.metric("52w high", f"S$ {hi52:,.3f}")
kc4.metric("52w low", f"S$ {lo52:,.3f}")
kc5.metric(
    "Tier",
    str(meta.get("headline_tier", "—")),
    f"{(meta.get('sector') or '').strip()} · {(meta.get('market_cap_band') or '').strip()}",
)

# ---------------------------------------------------------------------------
# Build the figure
# ---------------------------------------------------------------------------
show_rsi = "RSI" in selected_set
show_macd = "MACD" in selected_set
show_amihud = "Amihud" in selected_set
show_bb = "Bollinger" in selected_set

panels = 1 + (1 if show_rsi else 0) + (1 if show_macd else 0) + (1 if show_amihud else 0)
if panels == 1:
    row_heights = [1.0]
else:
    extra = 0.45 / (panels - 1)
    row_heights = [0.55] + [extra] * (panels - 1)

fig = make_subplots(
    rows=panels,
    cols=1,
    shared_xaxes=True,
    vertical_spacing=0.045,
    row_heights=row_heights,
)

# Price panel — candlestick
fig.add_trace(
    go.Candlestick(
        x=prices_chart.index,
        open=prices_chart["open"],
        high=prices_chart["high"],
        low=prices_chart["low"],
        close=prices_chart["close"],
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

# Overlays on price panel
if "SMA-20" in selected_set:
    fig.add_trace(
        go.Scatter(
            x=close.index, y=sma(close, 20), mode="lines", name="SMA-20",
            line=dict(color=BLUE, width=1.3),
        ),
        row=1, col=1,
    )
if "SMA-50" in selected_set:
    fig.add_trace(
        go.Scatter(
            x=close.index, y=sma(close, 50), mode="lines", name="SMA-50",
            line=dict(color=AMBER, width=1.3),
        ),
        row=1, col=1,
    )
if "EMA-200" in selected_set:
    fig.add_trace(
        go.Scatter(
            x=close.index, y=ema(close, 200), mode="lines", name="EMA-200",
            line=dict(color=PURPLE, width=1.3),
        ),
        row=1, col=1,
    )
if show_bb:
    bb = bollinger(close, 20, 2.0)
    fig.add_trace(
        go.Scatter(
            x=bb.index, y=bb["upper"], mode="lines",
            line=dict(color="rgba(34,211,238,0.0)", width=0),
            showlegend=False, hoverinfo="skip",
        ),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=bb.index, y=bb["lower"], mode="lines",
            line=dict(color="rgba(34,211,238,0.0)", width=0),
            fill="tonexty", fillcolor="rgba(34,211,238,0.10)",
            name="BB-20·2", hoverinfo="skip",
        ),
        row=1, col=1,
    )

# Volume strip at the foot of the price panel.
vol = prices_chart["volume"].astype(float).fillna(0)
vol_max = float(vol.max()) if vol.max() > 0 else 1.0
y_lo = float(prices_chart[["low", "open", "close"]].min().min())
y_hi = float(prices_chart[["high", "open", "close"]].max().max())
band = (y_hi - y_lo) * 0.18 if y_hi > y_lo else 1.0
vol_y = (vol / vol_max) * band * 0.9
green_red = np.where(prices_chart["close"] >= prices_chart["open"], GREEN, RED)
fig.add_trace(
    go.Bar(
        x=prices_chart.index,
        y=vol_y,
        base=y_lo - band,
        marker_color=green_red,
        opacity=0.45,
        name="volume",
        showlegend=False,
        hovertemplate="vol %{customdata:,.0f}<extra></extra>",
        customdata=vol,
    ),
    row=1, col=1,
)

next_row = 2
if show_rsi:
    rsi_vals = rsi(close, 14)
    fig.add_trace(
        go.Scatter(
            x=rsi_vals.index, y=rsi_vals, mode="lines", name="RSI-14",
            line=dict(color=BLUE, width=1.4), showlegend=False,
        ),
        row=next_row, col=1,
    )
    fig.add_hline(y=70, line=dict(color=RED, width=1, dash="dot"), row=next_row, col=1)
    fig.add_hline(y=30, line=dict(color=GREEN, width=1, dash="dot"), row=next_row, col=1)
    fig.update_yaxes(title_text="RSI", range=[0, 100], row=next_row, col=1)
    next_row += 1

if show_macd:
    md = macd(close, 12, 26, 9)
    hist_colors = np.where(md["hist"] >= 0, GREEN, RED)
    fig.add_trace(
        go.Bar(x=md.index, y=md["hist"], marker_color=hist_colors, opacity=0.55,
               name="MACD hist", showlegend=False),
        row=next_row, col=1,
    )
    fig.add_trace(
        go.Scatter(x=md.index, y=md["macd"], mode="lines",
                   line=dict(color=BLUE, width=1.4), name="MACD", showlegend=False),
        row=next_row, col=1,
    )
    fig.add_trace(
        go.Scatter(x=md.index, y=md["signal"], mode="lines",
                   line=dict(color=AMBER, width=1.2), name="signal", showlegend=False),
        row=next_row, col=1,
    )
    fig.update_yaxes(title_text="MACD", row=next_row, col=1)
    next_row += 1

if show_amihud:
    am = amihud(close, prices_chart["volume"])
    fig.add_trace(
        go.Scatter(x=am.index, y=am, mode="lines",
                   line=dict(color=PURPLE, width=1.4), name="Amihud (60d)", showlegend=False),
        row=next_row, col=1,
    )
    fig.update_yaxes(title_text="Amihud", row=next_row, col=1)
    next_row += 1

# Event lines on the price panel ONLY (avoid the row=1, col=1 + multi-axis bug
# in plotly where add_vline tries to compute axis bounds across all rows).
chart_min, chart_max = prices_chart.index.min(), prices_chart.index.max()
for date_str, label in zip(EVENT_DATES.values(), EVENT_LABELS.values()):
    d = pd.Timestamp(date_str)
    if not (chart_min <= d <= chart_max):
        continue
    # Use a scatter with vertical line markers — bypasses add_vline's axis-merging quirk.
    fig.add_trace(
        go.Scatter(
            x=[d, d],
            y=[y_lo - band, y_hi],
            mode="lines",
            line=dict(color=AMBER, width=1.2, dash="dot"),
            name=label.split(" (")[0],
            hoverinfo="skip",
            showlegend=False,
        ),
        row=1, col=1,
    )
    fig.add_annotation(
        x=d, y=y_hi, xref=f"x", yref=f"y",
        text=label.split(" (")[0],
        showarrow=False, yanchor="bottom",
        font=dict(color=AMBER, size=10),
        row=1, col=1,
    )

# T1 filings on the price panel (if any for this ticker).
filings = load_filings(limit=None)
if not filings.empty:
    my_filings = filings[filings["ticker"] == selected]
    for _, row in my_filings.iterrows():
        d = pd.Timestamp(row["filing_date"])
        if not (chart_min <= d <= chart_max):
            continue
        fig.add_trace(
            go.Scatter(
                x=[d, d], y=[y_lo - band, y_hi],
                mode="lines",
                line=dict(color=GREEN, width=1.2, dash="dash"),
                showlegend=False, hoverinfo="skip",
            ),
            row=1, col=1,
        )

fig.update_xaxes(rangeslider_visible=False)
fig.update_layout(
    height=240 + 200 * (panels - 1) + 220,
    showlegend=True,
    legend=dict(orientation="h", y=1.06, x=0, bgcolor="rgba(0,0,0,0)"),
    margin=dict(l=40, r=20, t=30, b=30),
    bargap=0.05,
)
st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})

# ---------------------------------------------------------------------------
# Below-chart panels — indicator readout + filings
# ---------------------------------------------------------------------------
left, right = st.columns([1, 1])
with left:
    st.subheader("Current readout")
    rsi_now = float(rsi(close, 14).dropna().iloc[-1]) if len(close) > 14 else float("nan")
    md_last = macd(close, 12, 26, 9).iloc[-1] if len(close) > 35 else None
    atr_now = (
        float(atr(prices_chart["high"], prices_chart["low"], close, 14).dropna().iloc[-1])
        if len(close) > 14
        else float("nan")
    )
    bb_last = bollinger(close, 20, 2).iloc[-1] if len(close) > 20 else None
    rows: list[tuple[str, str]] = []
    rows.append(("RSI-14", f"{rsi_now:.1f}" if not np.isnan(rsi_now) else "—"))
    if md_last is not None:
        rows.append(("MACD", f"{md_last['macd']:.4f}"))
        rows.append(("MACD signal", f"{md_last['signal']:.4f}"))
        rows.append(("MACD hist", f"{md_last['hist']:+.4f}"))
    rows.append(("ATR-14", f"{atr_now:.4f}" if not np.isnan(atr_now) else "—"))
    if bb_last is not None and bb_last["upper"] != bb_last["lower"]:
        pct_b = (last_close - bb_last["lower"]) / (bb_last["upper"] - bb_last["lower"])
        rows.append(("Bollinger %B", f"{pct_b:.2f}"))
    table = pd.DataFrame(rows, columns=["indicator", "value"])
    st.dataframe(table, use_container_width=True, hide_index=True)

with right:
    st.subheader("T1 filings on this name")
    if filings.empty or selected not in set(filings["ticker"].astype(str)):
        st.caption("No 5%+ filings on this name yet.")
    else:
        sub = filings[filings["ticker"] == selected][
            ["filing_date", "manager_id", "stake_pct", "direction", "source_url"]
        ].rename(
            columns={
                "filing_date": "Filed",
                "manager_id": "Manager",
                "stake_pct": "Stake %",
                "direction": "Direction",
                "source_url": "Source",
            }
        )
        st.dataframe(
            sub,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Stake %": st.column_config.NumberColumn(format="%.2f"),
                "Source": st.column_config.LinkColumn(display_text="Open"),
            },
        )

footer()
