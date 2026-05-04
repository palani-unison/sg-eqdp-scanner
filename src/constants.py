"""Canonical constants for sg-eqdp-scanner.

Single source of truth referenced by analytical code, tests, and docs.
Bump deliberately, not accidentally — any change here invalidates downstream
results. Cross-referenced by `memory.md` and `docs/STRATEGY.md`.
"""

from __future__ import annotations

from typing import Final

import pandas as pd

# yfinance ticker convention
SGX_SUFFIX: Final[str] = ".SI"
STI_TICKER: Final[str] = "^STI"

# Programme events. Keys are stable IDs used in abnormal_returns.event_id.
EVENTS: Final[dict[str, str]] = {
    "announcement": "2025-02-21",
    "tranche_1": "2025-07-21",
    "tranche_2": "2025-11-19",
    "expansion": "2026-02-12",
}


def event_date(event_id: str) -> pd.Timestamp:
    """Return the canonical event date as a tz-naive Timestamp."""
    return pd.Timestamp(EVENTS[event_id]).tz_localize(None)


# The nine EQDP-appointed managers across both tranches.
EQDP_MANAGERS: Final[tuple[str, ...]] = (
    # Tranche 1 (Jul 2025)
    "Avanda Investment Management",
    "Fullerton Fund Management",
    "JPMorgan Asset Management",
    # Tranche 2 (Nov 2025)
    "Amova Asset Management",  # formerly Nikko AM
    "AR Capital",
    "BlackRock",
    "Eastspring Investments",
    "Lion Global Investors",
    "Manulife Investment Management",
)

EQDP_MANAGER_TRANCHE: Final[dict[str, int]] = {
    "Avanda Investment Management": 1,
    "Fullerton Fund Management": 1,
    "JPMorgan Asset Management": 1,
    "Amova Asset Management": 2,
    "AR Capital": 2,
    "BlackRock": 2,
    "Eastspring Investments": 2,
    "Lion Global Investors": 2,
    "Manulife Investment Management": 2,
}

# Candidate-score weights — see docs/METHODOLOGY.md §3. Must sum to 1.0.
SCORE_WEIGHTS: Final[dict[str, float]] = {
    "liquidity_rise": 0.30,
    "institutional_proxy": 0.20,
    "index_inclusion": 0.15,
    "broker_named": 0.15,
    "filing_present": 0.20,
}

# CAPM β estimation window — 252 trading days (≈1 year) ending 30 days before event.
CAPM_BETA_WINDOW_DAYS: Final[int] = 252
CAPM_GAP_DAYS: Final[int] = 30

# Default event windows (trading-day offsets relative to event date).
EVENT_WINDOWS: Final[dict[str, tuple[int, int]]] = {
    "announcement": (-5, 20),
    "tranche_1": (-1, 10),
    "tranche_2": (-1, 10),
    "expansion": (-1, 20),
}

# Benchmark options for abnormal-return computation.
BENCHMARK_CAPM: Final[str] = "capm"
BENCHMARK_FF3: Final[str] = "ff3"
BENCHMARK_MARKET: Final[str] = "market_adjusted"
BENCHMARKS: Final[tuple[str, ...]] = (BENCHMARK_CAPM, BENCHMARK_FF3, BENCHMARK_MARKET)

# Tier identifiers used everywhere in the codebase and DB.
TIER_T1: Final[str] = "T1"
TIER_T2: Final[str] = "T2"
TIER_T3: Final[str] = "T3"
TIER_CONTROL: Final[str] = "control"
TIER_NONE: Final[str] = "none"
TIERS: Final[tuple[str, ...]] = (TIER_T1, TIER_T2, TIER_T3, TIER_CONTROL, TIER_NONE)

# Bootstrap configuration — docs/METHODOLOGY.md §10.
BOOTSTRAP_REPLICATIONS: Final[int] = 5_000
BOOTSTRAP_BLOCK_LENGTH: Final[int] = 5
