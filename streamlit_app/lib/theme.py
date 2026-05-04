"""Plotly + colour tokens for the Streamlit app.

The `forensic` plotly template is registered on import so any chart that does
not pass `template=` will still inherit the dark, ink-on-graph paper feel.
"""

from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio

INK = "#F1F5FF"
MUTED = "#8A95B5"
GRID = "#252C4A"
PAPER = "#0A0E1F"
PANEL = "#141A33"

GREEN = "#3DD68C"
RED = "#FF6B6B"
AMBER = "#F5A623"
BLUE = "#22D3EE"
PURPLE = "#A78BFA"
PINK = "#F472B6"

TIER_COLORS = {
    "T1": "#3DD68C",
    "T2": "#22D3EE",
    "T3": "#A78BFA",
    "control": "#8A95B5",
    "none": "#3F4868",
}

EVENT_LABELS = {
    "announcement": "Announcement (2025-02-21)",
    "tranche_1": "Tranche 1 (2025-07-21)",
    "tranche_2": "Tranche 2 (2025-11-19)",
    "expansion": "Expansion (2026-02-12)",
}

EVENT_DATES = {
    "announcement": "2025-02-21",
    "tranche_1": "2025-07-21",
    "tranche_2": "2025-11-19",
    "expansion": "2026-02-12",
}


def _register_template() -> None:
    tmpl = go.layout.Template()
    tmpl.layout.paper_bgcolor = PAPER
    tmpl.layout.plot_bgcolor = PAPER
    tmpl.layout.font = dict(color=INK, family="Inter, system-ui, sans-serif", size=12)
    tmpl.layout.colorway = [GREEN, BLUE, AMBER, PURPLE, PINK, RED, "#FBBF24"]
    tmpl.layout.xaxis = dict(
        gridcolor=GRID, zerolinecolor=GRID, linecolor=GRID, ticks="outside", tickcolor=GRID
    )
    tmpl.layout.yaxis = dict(
        gridcolor=GRID, zerolinecolor=GRID, linecolor=GRID, ticks="outside", tickcolor=GRID
    )
    tmpl.layout.legend = dict(bgcolor="rgba(0,0,0,0)", bordercolor=GRID, borderwidth=0)
    tmpl.layout.margin = dict(l=40, r=20, t=40, b=40)
    tmpl.layout.hoverlabel = dict(bgcolor=PANEL, bordercolor=GRID, font=dict(color=INK))
    pio.templates["forensic"] = tmpl
    pio.templates.default = "forensic"


_register_template()


def event_shapes(x_axis: str = "x") -> list[dict]:
    """Vertical dotted lines at the four EQDP event dates — drop into fig.update_layout(shapes=...)."""
    return [
        dict(
            type="line",
            xref=x_axis,
            yref="paper",
            x0=date,
            x1=date,
            y0=0,
            y1=1,
            line=dict(color=AMBER, width=1, dash="dot"),
        )
        for date in EVENT_DATES.values()
    ]


def event_annotations() -> list[dict]:
    return [
        dict(
            x=date,
            y=1.02,
            xref="x",
            yref="paper",
            text=label.split(" (")[0],
            showarrow=False,
            font=dict(color=MUTED, size=10),
            xanchor="left",
        )
        for date, label in zip(EVENT_DATES.values(), EVENT_LABELS.values())
    ]
