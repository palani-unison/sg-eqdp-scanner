"""Day-4 tests — nearest-neighbour matching and DiD."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.matching import FeatureRow, did_panel, match_controls


def _features() -> tuple[list[FeatureRow], list[FeatureRow]]:
    treated = [
        FeatureRow("T1.SI", sector="Industrial", beta=1.2, amihud_60d=1e-7),
        FeatureRow("T2.SI", sector="REIT", beta=0.6, amihud_60d=2e-7),
    ]
    pool = [
        # Same-sector candidates close in feature space
        FeatureRow("CTRL_IND_NEAR.SI", sector="Industrial", beta=1.18, amihud_60d=1.05e-7),
        FeatureRow("CTRL_IND_FAR.SI", sector="Industrial", beta=2.5, amihud_60d=1e-6),
        FeatureRow("CTRL_REIT_NEAR.SI", sector="REIT", beta=0.62, amihud_60d=2.1e-7),
        FeatureRow("CTRL_REIT_FAR.SI", sector="REIT", beta=1.5, amihud_60d=8e-7),
    ]
    return treated, pool


def test_match_controls_picks_nearest_same_sector() -> None:
    treated, pool = _features()
    pairs = match_controls(treated, pool)
    assert pairs["T1.SI"] == "CTRL_IND_NEAR.SI"
    assert pairs["T2.SI"] == "CTRL_REIT_NEAR.SI"


def test_match_controls_falls_back_to_global_when_sector_missing() -> None:
    treated = [FeatureRow("ORPHAN.SI", sector="HealthcareSpecialty", beta=1.0, amihud_60d=1e-7)]
    pool = [
        FeatureRow("BANKS.SI", sector="Financials", beta=1.05, amihud_60d=1.1e-7),
        FeatureRow("REIT.SI", sector="REIT", beta=0.4, amihud_60d=5e-7),
    ]
    pairs = match_controls(treated, pool, require_same_sector=True)
    assert pairs["ORPHAN.SI"] == "BANKS.SI"  # closer in features


def test_match_controls_used_unique_avoids_reuse() -> None:
    treated = [
        FeatureRow("A.SI", sector="X", beta=1.0, amihud_60d=1e-7),
        FeatureRow("B.SI", sector="X", beta=1.01, amihud_60d=1.01e-7),
    ]
    pool = [
        FeatureRow("CTRL1.SI", sector="X", beta=1.0, amihud_60d=1e-7),
        FeatureRow("CTRL2.SI", sector="X", beta=1.5, amihud_60d=2e-7),
    ]
    pairs = match_controls(treated, pool, used_unique=True)
    assert set(pairs.values()) == {"CTRL1.SI", "CTRL2.SI"}


def test_match_controls_empty_treated_returns_empty() -> None:
    _, pool = _features()
    assert match_controls([], pool) == {}


def test_match_controls_rejects_empty_pool() -> None:
    treated, _ = _features()
    with pytest.raises(ValueError, match="control_pool is empty"):
        match_controls(treated, [])


def _toy_did_panel(delta: float = 0.005, n_per: int = 30) -> pd.DataFrame:
    """Construct a panel where treated stocks earn an extra δ in the post period."""
    rng = np.random.default_rng(0)
    rows = []
    treated = ["T1", "T2", "T3"]
    controls = ["C1", "C2", "C3"]
    for tk in treated + controls:
        for t in range(-n_per // 2, n_per // 2):
            base = rng.normal(0, 0.005)
            is_treated = tk in treated
            post_kick = delta if (is_treated and t >= 0) else 0.0
            rows.append({"ticker": tk, "t": t, "ret": base + post_kick})
    return pd.DataFrame(rows)


def test_did_panel_recovers_known_delta() -> None:
    panel = _toy_did_panel(delta=0.01, n_per=80)
    res = did_panel(
        panel,
        treated={"T1", "T2", "T3"},
        controls={"C1", "C2", "C3"},
        event_t0=0,
    )
    # With 80 days × 6 entities and σ=0.005, the estimator recovers δ=0.01
    # comfortably; we allow ±2σ slack.
    assert res.delta == pytest.approx(0.01, abs=3e-3)
    assert res.n_entities == 6
    assert "T1" in res.treated
    assert "C1" in res.controls


def test_did_panel_missing_outcome_raises() -> None:
    panel = pd.DataFrame({"ticker": ["A"], "t": [0]})  # no 'ret'
    with pytest.raises(KeyError, match="missing"):
        did_panel(panel, treated={"A"}, controls=set(), outcome="ret")
