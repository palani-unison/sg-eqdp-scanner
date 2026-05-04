"""Shared Streamlit UI components — disclaimer banner, KPI cards, tier pill,
and a one-shot mobile-responsive CSS injection that every page picks up via
``disclaimer_banner()``.
"""

from __future__ import annotations

import streamlit as st

from .theme import TIER_COLORS

_DISCLAIMER_TEXT = (
    "**Not investment advice.** This is a technical study and analysis "
    "intended for discussion. See the [Disclaimer](Disclaimer) page."
)


# Tightens layout, shrinks heavy chart heights, compacts KPI metrics, and
# makes wide DataFrames horizontally scrollable on narrow viewports. Streamlit
# columns already stack on narrow viewports — this CSS just polishes the
# resulting vertical layout so it doesn't feel like a desktop site mashed
# onto a phone.
_MOBILE_CSS = """
<style>
/* ---------- universal padding tightening (phones + tablets) ---------- */
@media (max-width: 768px) {
  .main .block-container, [data-testid="stAppViewContainer"] .main .block-container {
    padding-top: 0.85rem !important;
    padding-bottom: 1rem !important;
    padding-left: 0.85rem !important;
    padding-right: 0.85rem !important;
  }
  /* Compact disclaimer banner */
  [data-testid="stAlert"] {
    padding: 0.5rem 0.75rem !important;
    font-size: 0.85rem !important;
  }
}

/* ---------- phone-only tweaks ---------- */
@media (max-width: 640px) {
  /* Page header / typography */
  h1 { font-size: 1.55rem !important; line-height: 1.2 !important; }
  h2 { font-size: 1.2rem !important; }
  h3 { font-size: 1.05rem !important; }
  /* Body / subtitle markdown */
  .stMarkdown p, .stMarkdown li { font-size: 0.95rem !important; line-height: 1.5 !important; }

  /* KPI metrics — keep them compact when stacked */
  [data-testid="stMetric"] {
    background: rgba(34, 211, 238, 0.04);
    border: 1px solid #1F2742;
    border-radius: 10px;
    padding: 0.55rem 0.8rem !important;
    margin-bottom: 0.4rem;
  }
  [data-testid="stMetricValue"] { font-size: 1.05rem !important; }
  [data-testid="stMetricLabel"] { font-size: 0.78rem !important; }
  [data-testid="stMetricDelta"] { font-size: 0.78rem !important; }

  /* DataFrames — let wide tables scroll horizontally instead of squashing */
  [data-testid="stDataFrame"] { overflow-x: auto !important; }

  /* Selectboxes / multiselects — readable text */
  .stSelectbox, .stMultiSelect, .stRadio { font-size: 0.95rem !important; }

  /* Sidebar — narrower so it doesn't dominate when opened */
  section[data-testid="stSidebar"] { width: 250px !important; min-width: 250px !important; }
}

/* ---------- always: cap Plotly chart vertical sprawl on narrow viewports --- */
@media (max-width: 640px) {
  .js-plotly-plot, .plot-container, [data-testid="stPlotlyChart"] iframe {
    max-height: 520px !important;
  }
}

/* Custom HTML cards (Investment Thesis types & phases) — wrap inner text */
@media (max-width: 640px) {
  div[style*="border-radius:14px"], div[style*="border-radius:16px"] {
    margin-bottom: 0.6rem;
  }
}
</style>
"""


def _inject_mobile_css() -> None:
    """Inject the responsive CSS once per session run. Streamlit deduplicates
    identical st.markdown calls implicitly across the same page render, so
    this is safe to call from every page."""
    st.markdown(_MOBILE_CSS, unsafe_allow_html=True)


def disclaimer_banner() -> None:
    _inject_mobile_css()
    st.info(_DISCLAIMER_TEXT, icon=":material/info:")


def page_header(title: str, subtitle: str | None = None, *, eyebrow: str | None = None) -> None:
    """Heavyweight typographic header — sets a forensic, editorial tone."""
    _inject_mobile_css()
    if eyebrow:
        st.markdown(
            f"<div style='color:#8A95B5;font-size:0.78rem;letter-spacing:0.18em;"
            f"text-transform:uppercase;margin-bottom:0.25rem'>{eyebrow}</div>",
            unsafe_allow_html=True,
        )
    st.markdown(
        f"<h1 style='margin:0 0 0.25rem 0;font-weight:700;letter-spacing:-0.02em'>{title}</h1>",
        unsafe_allow_html=True,
    )
    if subtitle:
        st.markdown(
            f"<div style='color:#8A95B5;font-size:1.02rem;max-width:62ch;"
            f"line-height:1.55;margin-bottom:1.25rem'>{subtitle}</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown("<div style='margin-bottom:1rem'></div>", unsafe_allow_html=True)


def kpi_row(metrics: list[tuple[str, str, str | None]]) -> None:
    """Row of KPI tiles: list of (label, value, delta-or-None)."""
    cols = st.columns(len(metrics))
    for col, (label, value, delta) in zip(cols, metrics):
        with col:
            st.metric(label=label, value=value, delta=delta)


def tier_pill(tier: str) -> str:
    color = TIER_COLORS.get(tier, "#3F4868")
    return (
        f"<span style='background:{color}22;color:{color};border:1px solid {color}55;"
        f"padding:2px 8px;border-radius:999px;font-size:0.78rem;font-weight:600;"
        f"letter-spacing:0.04em'>{tier.upper()}</span>"
    )


def footer() -> None:
    st.markdown(
        "<hr style='border:none;border-top:1px solid #252C4A;margin:2rem 0 0.75rem'/>"
        "<div style='color:#8A95B5;font-size:0.82rem;line-height:1.5'>"
        "© 2026 Palaniappan Chidambaram. Personal research — not investment advice. "
        "<a href='Disclaimer' target='_self' style='color:#8A95B5'>Disclaimer</a>"
        "</div>",
        unsafe_allow_html=True,
    )


def empty_state(message: str, hint: str | None = None) -> None:
    st.markdown(
        f"<div style='border:1px dashed #252C4A;border-radius:12px;padding:2.25rem 1.25rem;"
        f"text-align:center;color:#8A95B5'>"
        f"<div style='font-size:1.05rem;color:#F1F5FF;margin-bottom:0.35rem'>{message}</div>"
        f"{f'<div style=\"font-size:0.85rem\">{hint}</div>' if hint else ''}"
        f"</div>",
        unsafe_allow_html=True,
    )
