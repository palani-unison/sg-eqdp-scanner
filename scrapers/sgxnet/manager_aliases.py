"""EQDP-manager alias resolution.

Asset managers file substantial-shareholder notices under their full legal
entity name(s). The same firm can appear under several variants:

    "BlackRock Inc."
    "BlackRock Investment Management (Singapore) Pte. Ltd."
    "BlackRock Asset Management North Asia Limited"

We resolve any of these to the canonical ``manager_id`` used in
``eqdp_managers`` and ``filings_t1``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

from src.constants import EQDP_MANAGERS


# Canonical manager_id slugs (match what backfill.py upserts into eqdp_managers).
def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


CANONICAL_IDS: Final[dict[str, str]] = {name: _slug(name) for name in EQDP_MANAGERS}


@dataclass(frozen=True, slots=True)
class ManagerMatch:
    manager_id: str
    canonical_name: str
    matched_alias: str
    raw_text: str


# Alias patterns — substring match is checked case-insensitively against the
# raw text scraped from the SGX filing's "Notifying Person" / "Substantial
# Shareholder" field. Order: most specific → least specific so a more
# distinctive variant wins when multiple match.
_ALIAS_PATTERNS: Final[dict[str, tuple[str, ...]]] = {
    "Avanda Investment Management": (
        "avanda investment management",
        "avanda invt mgmt",
        "avanda",
    ),
    "Fullerton Fund Management": (
        "fullerton fund management",
        "fullerton fund mgmt",
        "fullerton fund",
        "fullerton",
    ),
    "JPMorgan Asset Management": (
        "jpmorgan asset management",
        "j.p. morgan asset management",
        "jpmorgan investment management",
        "jp morgan asset management",
        "jpmorgan",
        "j.p. morgan",
    ),
    "Amova Asset Management": (
        "amova asset management",
        "amova",
        # Pre-rebrand:
        "nikko asset management",
        "nikko am",
    ),
    "AR Capital": (
        "ar capital",
        "ar capital pte",
        "ar cap",
    ),
    "BlackRock": (
        "blackrock investment management",
        "blackrock asset management",
        "blackrock fund advisors",
        "blackrock institutional trust",
        "blackrock advisors",
        "blackrock",
    ),
    "Eastspring Investments": (
        "eastspring investments",
        "eastspring",
    ),
    "Lion Global Investors": (
        "lion global investors",
        "lion global",
    ),
    "Manulife Investment Management": (
        "manulife investment management",
        "manulife asset management",
        "manulife financial",
        "manulife",
    ),
}


_NORMALISE_RE = re.compile(r"\s+")


def _normalise(s: str) -> str:
    return _NORMALISE_RE.sub(" ", s).strip().lower()


def resolve_manager(raw_text: str) -> ManagerMatch | None:
    """Return the canonical EQDP manager match for an SGX filing notifier
    string, or ``None`` if no alias matches.

    Match is the first (longest-by-pattern-order) substring hit in
    ``_ALIAS_PATTERNS``. Whitespace and case are normalised.
    """
    if not raw_text:
        return None
    needle = _normalise(raw_text)
    for canonical, aliases in _ALIAS_PATTERNS.items():
        for alias in aliases:
            if alias in needle:
                return ManagerMatch(
                    manager_id=CANONICAL_IDS[canonical],
                    canonical_name=canonical,
                    matched_alias=alias,
                    raw_text=raw_text,
                )
    return None


def all_canonical_ids() -> dict[str, str]:
    """Return a copy of the canonical name → slug map."""
    return dict(CANONICAL_IDS)
