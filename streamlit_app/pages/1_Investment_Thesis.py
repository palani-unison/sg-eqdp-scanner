"""Investment Thesis — the manager's hunting-ground logic + 3-phase impact."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.components import disclaimer_banner, footer, page_header

st.set_page_config(page_title="Investment Thesis · EQDP", page_icon=":material/insights:", layout="wide")
disclaimer_banner()
page_header(
    "The investment thesis behind EQDP",
    subtitle=(
        "EQDP is **directed capital with constraints + incentives** — "
        "active alpha-seeking money, not stimulus. That mandate creates a "
        "specific hunting ground and a specific way price action plays out "
        "around manager activity."
    ),
    eyebrow="How managers actually think",
)

# ---------------------------------------------------------------------------
# Lead — re-anchor the framing
# ---------------------------------------------------------------------------
st.markdown(
    """
Think like a fund manager receiving MAS money. You have an **active**
mandate, a finite window, and a benchmark to beat. You will not buy what
everyone already owns. You will hunt for **mispriced edges** in places
mainstream capital has stopped looking. That filter — not the
programme's headline size — is what shapes who actually benefits.
"""
)

st.markdown("&nbsp;")

# ---------------------------------------------------------------------------
# Five hunting grounds
# ---------------------------------------------------------------------------
st.subheader("Five types of stocks managers hunt for")

types = [
    (
        "Type 1",
        "“Ignored but fundamentally OK”",
        "Low coverage · alpha seeker",
        "Solid balance sheets, steady earnings, but abandoned by analysts. "
        "The work has already been done by the company — the gap is *visibility*. "
        "Re-rating happens when the visibility gap closes.",
        "#3DD68C",
    ),
    (
        "Type 2",
        "Illiquid mid/small caps",
        "Liquidity itself is the catalyst",
        "Names where bid/ask is wide and average daily turnover is thin. "
        "Active capital deployment doesn't just *react* to fundamentals — it "
        "*creates* a tighter market, which on its own can re-rate the equity.",
        "#4FA3FF",
    ),
    (
        "Type 3",
        "Stocks with a “narrative gap”",
        "Capital + narrative = re-rating",
        "Operationally improving, but the story isn't told yet. When real "
        "money shows up, journalists and sell-side build the narrative around "
        "it. Capital is the trigger; the narrative is the multiplier.",
        "#A78BFA",
    ),
    (
        "Type 4",
        "Companies at an inflection point",
        "Asymmetric bet",
        "Turnaround stories, post-restructure, capacity coming online, "
        "regulatory tailwind. The downside is broadly priced in; the upside "
        "is contingent. EQDP-style active capital is built to back these.",
        "#F5A623",
    ),
    (
        "Type 5",
        "Under-owned domestic plays",
        "Ignored by foreign fund houses",
        "Singapore-domestic businesses too small for the global fund "
        "screens. EQDP managers, mandated to invest *here*, see them. "
        "Foreign capital arrives only after the local managers have done "
        "the work.",
        "#22D3EE",
    ),
]

cols = st.columns(len(types))
for col, (tag, title, sub, body, color) in zip(cols, types):
    with col:
        st.markdown(
            f"""
<div style='border:1px solid #1F2742;border-radius:12px;
            padding:1.1rem 0.95rem;height:100%;
            background:linear-gradient(180deg, {color}10 0%, transparent 60%)'>
  <div style='color:{color};font-size:0.72rem;letter-spacing:0.18em;
              text-transform:uppercase;font-weight:600;margin-bottom:0.3rem'>
    {tag}
  </div>
  <div style='color:#E5E9F2;font-size:1.0rem;font-weight:600;
              line-height:1.3;margin-bottom:0.2rem'>
    {title}
  </div>
  <div style='color:{color};font-size:0.78rem;font-weight:500;
              margin-bottom:0.65rem'>
    {sub}
  </div>
  <div style='color:#B7BFD2;font-size:0.88rem;line-height:1.5'>
    {body}
  </div>
</div>
""",
            unsafe_allow_html=True,
        )

st.markdown("&nbsp;")
st.markdown(
    """
> The five types are **not mutually exclusive** — a single name (UMS Integration,
> say) can sit at the intersection of "ignored but OK", "narrative gap",
> and "under-owned domestic". Stacked filters compound the asymmetry.
"""
)

st.markdown("&nbsp;")

# ---------------------------------------------------------------------------
# 3-phase impact pattern
# ---------------------------------------------------------------------------
st.subheader("How the impact unfolds — three phases")

phases = [
    (
        "1",
        "Accumulation",
        "Quiet buying",
        [
            "Fund managers build positions via VWAP / TWAP execution.",
            "Bid stays patient; iceberg orders absorb selling.",
            "Price barely moves — liquidity is *consumed*, not chased.",
            "Volume profile shifts subtly; close-vs-VWAP starts to favour close.",
        ],
        "#3DD68C",
    ),
    (
        "2",
        "Discovery",
        "Volume increases",
        [
            "Daily turnover crosses prior-regime upper band.",
            "Sell-side analysts notice the change in microstructure.",
            "First initiation reports / reactivations published.",
            "A small re-rating begins — multiple expands ~10–20%.",
        ],
        "#4FA3FF",
    ),
    (
        "3",
        "Participation",
        "Other funds + retail enter",
        [
            "Other institutional managers start their own due diligence.",
            "Retail flow follows once charts break out.",
            "Momentum and valuation expand together — the visible phase.",
            "By the time most observers notice, smart money is already trimming.",
        ],
        "#A78BFA",
    ),
]

cols = st.columns(len(phases))
for col, (n, title, sub, bullets, color) in zip(cols, phases):
    with col:
        bullet_html = "".join(
            f"<li style='color:#B7BFD2;margin-bottom:0.35rem;line-height:1.45'>{b}</li>"
            for b in bullets
        )
        st.markdown(
            f"""
<div style='border:1px solid #1F2742;border-radius:14px;
            padding:1.25rem;height:100%'>
  <div style='display:flex;align-items:baseline;gap:0.6rem;
              margin-bottom:0.45rem'>
    <span style='font-size:2.2rem;font-weight:800;line-height:1;color:{color}'>
      {n}
    </span>
    <span style='font-size:1.05rem;font-weight:600;color:#E5E9F2'>{title}</span>
  </div>
  <div style='color:{color};font-size:0.82rem;font-weight:500;
              text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.85rem'>
    {sub}
  </div>
  <ul style='margin:0;padding-left:1.1rem;font-size:0.9rem'>{bullet_html}</ul>
</div>
""",
            unsafe_allow_html=True,
        )

st.markdown("&nbsp;")

# ---------------------------------------------------------------------------
# The implication
# ---------------------------------------------------------------------------
st.markdown(
    """
### Where this site sits in the cycle

By the time a name flashes on the **Tracker** as a high-score candidate, the
underlying flow signals — Amihud compression, close-vs-VWAP shift, broker
naming, T1 filing — are firing. That places it somewhere between **late
Phase 1 and early Phase 2**: accumulation has happened, discovery is
getting underway, but the visible re-rating hasn't fully unfolded yet.

The Event Studies page measures whether Phase 2 / Phase 3 are *statistically
detectable* across the cohort, by event date, with treated-vs-control
DiD plus bootstrap CIs.

### The closing thesis

> EQDP rewards **under-owned, under-researched, improving businesses** —
> not stocks that are already popular. The screen on this site is built
> with that premise wired in: the candidate score uses only flow inputs,
> never returns, so a 245% rally does not win you a high score on its own.
"""
)

footer()
