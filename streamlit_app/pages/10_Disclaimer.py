"""Disclaimer — full canonical text."""

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
    subtitle="The whole text. Read it before relying on anything on this site.",
    eyebrow="Legal & methodological",
)

DOC_PATH = Path(__file__).resolve().parents[2] / "docs" / "DISCLAIMER.md"
try:
    text = DOC_PATH.read_text(encoding="utf-8")
    st.markdown(text)
except FileNotFoundError:
    st.error(f"Disclaimer file not found at {DOC_PATH}.")

footer()
