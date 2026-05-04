"""Day-1 acceptance tests for src/universe.py."""

from __future__ import annotations

import pytest

from src.constants import (
    EQDP_MANAGERS,
    EVENTS,
    SCORE_WEIGHTS,
    SGX_SUFFIX,
    TIER_CONTROL,
    TIER_T2,
    TIER_T3,
)
from src.universe import (
    Ticker,
    all_tickers,
    find,
    get_control,
    get_t1,
    get_t2,
    get_t3,
)


def test_events_has_four_canonical_dates() -> None:
    assert set(EVENTS) == {"announcement", "tranche_1", "tranche_2", "expansion"}


def test_managers_count_is_nine() -> None:
    assert len(EQDP_MANAGERS) == 9


def test_score_weights_sum_to_one() -> None:
    assert sum(SCORE_WEIGHTS.values()) == pytest.approx(1.0)


def test_t1_starts_empty() -> None:
    # Populated by SGXNet scraper on Day 6; empty until then.
    assert get_t1() == []


def test_t3_count_matches_seed() -> None:
    assert len(get_t3()) == 27


def test_control_count_matches_seed() -> None:
    assert len(get_control()) == 20


def test_t2_meets_day1_acceptance_criterion() -> None:
    """PLAN.md Day 1: get_t2() returns ≥48 tickers."""
    assert len(get_t2()) >= 48


def test_all_tickers_use_sgx_suffix() -> None:
    for t in all_tickers():
        assert t.symbol.endswith(SGX_SUFFIX), t.symbol


def test_no_overlap_between_t3_and_control() -> None:
    t3_syms = {t.symbol for t in get_t3()}
    ctrl_syms = {t.symbol for t in get_control()}
    assert t3_syms.isdisjoint(ctrl_syms)


def test_t2_includes_all_t3_names() -> None:
    """T3 names are by construction eligible — must appear in T2."""
    t2_syms = {t.symbol for t in get_t2()}
    t3_syms = {t.symbol for t in get_t3()}
    assert t3_syms.issubset(t2_syms)


def test_t3_rows_in_t2_carry_both_flags() -> None:
    t3_syms = {t.symbol for t in get_t3()}
    t2_rows = [t for t in get_t2() if t.symbol in t3_syms]
    for t in t2_rows:
        assert t.in_t2 and t.in_t3, t.symbol


def test_headline_tier_priority() -> None:
    # control-only ticker → control
    ctrl = get_control()[0]
    assert ctrl.headline_tier == TIER_CONTROL
    # T3 row → T3 wins over T2
    t3 = next(t for t in get_t2() if t.in_t3)
    assert t3.headline_tier == TIER_T3
    # T2-only row → T2
    t2_only = next(t for t in get_t2() if t.in_t2 and not t.in_t3)
    assert t2_only.headline_tier == TIER_T2


def test_ticker_rejects_non_sgx_symbol() -> None:
    with pytest.raises(ValueError):
        Ticker(symbol="AAPL", name="Apple", sector="Tech", in_t2=True)


def test_find_round_trips_known_ticker() -> None:
    assert find("E28.SI") is not None
    assert find("E28.SI").name == "Frencken Group"  # type: ignore[union-attr]
    assert find("DOES.NOT.EXIST.SI") is None


def test_all_tickers_no_duplicates() -> None:
    syms = [t.symbol for t in all_tickers()]
    assert len(syms) == len(set(syms))
