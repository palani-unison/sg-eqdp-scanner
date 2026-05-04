"""Disclaimer — clean, simple, single source of truth."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.components import footer, page_header

st.set_page_config(page_title="Disclaimer · EQDP", page_icon=":material/gavel:", layout="wide")
page_header(
    "Disclaimer",
    subtitle="Read before relying on anything on this site.",
    eyebrow="Legal & methodological",
)

st.markdown(
    """
### Not investment advice

Nothing on this site is investment advice, an offer to buy or sell any
security, or a recommendation. The content is provided for **technical
study, education, and institutional-grade analysis** — for *discussion*,
not action. Readers must conduct their own due diligence and, where
appropriate, consult a licensed financial adviser before making any
investment decision.

### Inferential nature of the analysis

The beneficiary identification on this site is **inferential**. Specific
holdings of large institutional investors are not always publicly
disclosed; this study combines:

- Programmatic eligibility filters,
- Public broker-research beneficiary lists,
- Market-microstructure changes around event dates,
- Public 5%+ substantial-shareholder filings.

Smaller positions are invisible to public filing, and meaningful capital
may flow into stocks that never appear in our screen. **Inference is not
proof.**

### Data sources and accuracy

Price and volume data is sourced from public market data via the
`yfinance` library. Filing data is scraped from public exchange portals.
Programme-design and event-date information is drawn from public press
releases and accompanying media. While reasonable care is taken,
**no representation or warranty** is made as to the accuracy,
completeness, or timeliness of any information, and the author accepts
no liability for any loss arising from reliance on it.

### Forward-looking statements

Any statement about future market behaviour is speculative and based on
the author's interpretation of public information. **Past performance
does not indicate future results.**

### Reproducibility

The code, schema, and DuckDB data file behind this site are public.
Anyone can clone the repository, re-run the pipelines, and verify (or
challenge) the conclusions step by step.
"""
)

footer()
