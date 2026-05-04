"""Shared Streamlit UI components — disclaimer banner, KPI cards, tier pill."""

from __future__ import annotations

import streamlit as st

from .theme import TIER_COLORS

_DISCLAIMER_TEXT = (
    "**Not investment advice.** This is a technical study and analysis "
    "intended for discussion. See the [Disclaimer](Disclaimer) page."
)


def disclaimer_banner() -> None:
    st.info(_DISCLAIMER_TEXT, icon=":material/info:")


def page_header(title: str, subtitle: str | None = None, *, eyebrow: str | None = None) -> None:
    """Heavyweight typographic header — sets a forensic, editorial tone."""
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
        "© 2026 Palaniappan Chidambaram. Personal research — not investment advice — "
        "not affiliated with Unison Group. "
        "<a href='Disclaimer' target='_self' style='color:#8A95B5'>Disclaimer</a> · "
        "<a href='About' target='_self' style='color:#8A95B5'>About</a>"
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
