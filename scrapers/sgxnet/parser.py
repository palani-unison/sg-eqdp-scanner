"""SGXNet substantial-shareholder filing parser.

The SGX disclosure-of-interest form has a stable field set across filings.
This module parses one HTML filing into a typed ``Filing`` record. The fetch
layer (``fetcher.py``) is the part that needs Playwright/SPA rendering — the
parser itself takes raw HTML so it's deterministic and unit-testable.

Bi-temporal columns (per CLAUDE.md):
    effective_date  — when the stake actually crossed the 5% threshold
    filing_date     — when the public learned (notice date)

Structural-change detector:
    ``page_fingerprint(html)`` returns a stable hash of the form's structural
    skeleton (tag names + class hooks). The pipeline fingerprints a known-good
    sample and compares; if SGX changes their layout, the comparison flags
    and short-circuits the run.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from bs4 import BeautifulSoup, Tag


@dataclass(frozen=True, slots=True)
class Filing:
    """One substantial-shareholder filing parsed from SGXNet."""

    filing_id: str
    ticker: str
    notifier_raw: str  # raw "Notifying Person" / "Substantial Shareholder" text
    effective_date: str  # ISO date
    filing_date: str  # ISO date
    stake_pct: float | None  # post-transaction stake; None if unparseable
    direction: str  # acquired | disposed | crossed_up | crossed_down
    source_url: str
    parser_version: str = "v0.1"


_DATE_RE = re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b")
_PCT_RE = re.compile(r"(\d{1,3}(?:\.\d{1,4})?)\s*%")


class ParseError(ValueError):
    """Raised when the filing HTML cannot be reduced to a Filing."""


def parse_filing(html: str, *, source_url: str) -> Filing:
    """Parse one SGX substantial-shareholder filing's HTML.

    ``html`` is the form's HTML body (whatever the fetch layer obtained,
    typically Playwright's ``page.content()``).

    The matching is keyword-anchored rather than DOM-path-anchored so it
    survives small markup churn within the form sections.
    """
    soup = BeautifulSoup(html, "lxml")
    text = " ".join(soup.get_text(separator=" ", strip=True).split())

    filing_id = _extract_field(text, ("filing id", "submission id", "reference"))
    ticker = _extract_ticker(soup, text)
    notifier = _extract_field(
        text,
        (
            "name of substantial shareholder",
            "name of substantial unitholder",
            "name of director",
            "notifying person",
        ),
    )
    effective = _extract_date_after(text, ("date of change", "date of acquisition", "effective date"))
    filing = _extract_date_after(text, ("date of notice", "date of submission", "filing date"))
    stake = _extract_pct_after(text, ("after the change", "post-transaction", "current shareholding"))
    direction = _classify_direction(text)

    if not (ticker and notifier and effective and filing):
        missing = [
            label
            for label, val in (
                ("ticker", ticker),
                ("notifier", notifier),
                ("effective_date", effective),
                ("filing_date", filing),
            )
            if not val
        ]
        raise ParseError(f"missing required fields: {missing}")

    return Filing(
        filing_id=filing_id or _synth_filing_id(source_url, filing, ticker),
        ticker=ticker,
        notifier_raw=notifier,
        effective_date=effective,
        filing_date=filing,
        stake_pct=stake,
        direction=direction,
        source_url=source_url,
    )


def page_fingerprint(html: str) -> str:
    """Stable hash of the page's structural skeleton.

    Strips text content; keeps tag tree + class names. Used by the
    structural-change detector at the start of the weekly pipeline.
    """
    soup = BeautifulSoup(html, "lxml")
    skeleton: list[str] = []
    for el in soup.find_all(True):
        if not isinstance(el, Tag):
            continue
        cls = ".".join(sorted(el.get("class") or []))
        skeleton.append(f"{el.name}#{cls}")
    return hashlib.sha256("|".join(skeleton).encode("utf-8")).hexdigest()


# ---------- Helpers ----------


def _synth_filing_id(source_url: str, filing_date: str, ticker: str) -> str:
    """Stable surrogate filing_id when SGX doesn't expose one in the page."""
    return f"sgx_{ticker}_{filing_date}_{hashlib.sha1(source_url.encode()).hexdigest()[:8]}"


def _extract_field(text: str, labels: tuple[str, ...]) -> str:
    """Find a labeled field's value: returns the chunk between the label
    and the next ALL-CAPS or label-like word."""
    for label in labels:
        m = re.search(rf"{re.escape(label)}\s*[:\-]?\s*(.+?)(?=  [A-Z][^a-z]{{2,}}|$)", text, re.IGNORECASE)
        if m:
            val = m.group(1).strip(" :-")
            if 1 <= len(val) <= 200:
                return val
    return ""


def _extract_ticker(soup: BeautifulSoup, text: str) -> str:
    """Find the SGX ticker. Prefer DOM hooks; fall back to regex."""
    # DOM hook: any tag whose text matches the canonical SGX-code pattern
    for el in soup.find_all(True):
        if not isinstance(el, Tag):
            continue
        s = el.get_text(strip=True)
        if re.fullmatch(r"[A-Z0-9]{2,5}", s):
            return f"{s}.SI"
    # Regex on the full text near a "Stock code" label
    m = re.search(r"stock\s*code[:\s]+([A-Z0-9]{2,5})", text, re.IGNORECASE)
    if m:
        return f"{m.group(1).upper()}.SI"
    return ""


def _extract_date_after(text: str, anchors: tuple[str, ...]) -> str:
    for anchor in anchors:
        idx = text.lower().find(anchor)
        if idx == -1:
            continue
        m = _DATE_RE.search(text, idx)
        if m:
            return m.group(1)
    return ""


def _extract_pct_after(text: str, anchors: tuple[str, ...]) -> float | None:
    for anchor in anchors:
        idx = text.lower().find(anchor)
        if idx == -1:
            continue
        m = _PCT_RE.search(text, idx)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                return None
    return None


def _classify_direction(text: str) -> str:
    t = text.lower()
    if "acquisition" in t or "acquired" in t:
        return "acquired"
    if "disposal" in t or "disposed" in t or "sold" in t:
        return "disposed"
    if "ceased" in t or "fell below" in t or "below 5" in t:
        return "crossed_down"
    if "crossed" in t or "above 5" in t or "exceeds 5" in t:
        return "crossed_up"
    return "acquired"  # default for unsigned 5%-threshold notices
