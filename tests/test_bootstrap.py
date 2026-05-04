"""Day-9 tests — bootstrap estimators."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.bootstrap import (
    BootstrapCI,
    cluster_bootstrap_did,
    cluster_bootstrap_mean_car,
    stationary_bootstrap,
)


def _make_did_panel(
    delta: float = 0.01, n_treated: int = 8, n_controls: int = 8, n_per: int = 60
) -> pd.DataFrame:
    rng = np.random.default_rng(0)
    rows: list[dict[str, float | int | str]] = []
    treated_ids = [f"T{i}" for i in range(n_treated)]
    control_ids = [f"C{i}" for i in range(n_controls)]
    for tk in treated_ids + control_ids:
        for t in range(-n_per // 2, n_per // 2):
            ret = rng.normal(0, 0.005)
            if tk in treated_ids and t >= 0:
                ret += delta
            rows.append({"ticker": tk, "t": t, "ret": ret})
    return pd.DataFrame(rows)


def test_bootstrap_ci_has_required_fields() -> None:
    ci = BootstrapCI(
        metric="x", scope="y", point=0.5, lower=0.4, upper=0.6, n_replications=100
    )
    assert ci.metric == "x" and ci.scope == "y"
    assert 0.4 <= ci.point <= 0.6
    assert ci.lower_pct == 5.0 and ci.upper_pct == 95.0


def test_cluster_bootstrap_did_recovers_delta() -> None:
    panel = _make_did_panel(delta=0.01, n_treated=8, n_controls=8, n_per=80)
    res = cluster_bootstrap_did(
        panel,
        treated={f"T{i}" for i in range(8)},
        controls={f"C{i}" for i in range(8)},
        metric_name="did_delta",
        scope="toy",
        n_reps=200,  # small for unit test speed
        seed=42,
    )
    assert res.point == pytest.approx(0.01, abs=3e-3)
    # CI should contain the true δ at 5–95
    assert res.lower < 0.01 < res.upper


def test_cluster_bootstrap_did_ci_excludes_zero_when_signal_strong() -> None:
    panel = _make_did_panel(delta=0.02, n_treated=10, n_controls=10, n_per=100)
    res = cluster_bootstrap_did(
        panel,
        treated={f"T{i}" for i in range(10)},
        controls={f"C{i}" for i in range(10)},
        metric_name="did_delta",
        scope="toy_strong",
        n_reps=300,
        seed=0,
    )
    # δ=0.02 with σ=0.005 → strong signal, 5–95 CI should not cover 0
    assert res.lower > 0


def test_stationary_bootstrap_recovers_mean() -> None:
    rng = np.random.default_rng(123)
    x = rng.normal(loc=0.05, scale=0.01, size=300)
    res = stationary_bootstrap(
        pd.Series(x),
        fn=np.mean,
        metric_name="mean",
        scope="toy",
        n_reps=500,
        mean_block_len=5,
        seed=0,
    )
    assert res.point == pytest.approx(0.05, abs=2e-3)
    assert res.lower < 0.05 < res.upper


def test_stationary_bootstrap_rejects_too_short_series() -> None:
    with pytest.raises(ValueError, match="too short"):
        stationary_bootstrap(
            pd.Series([0.0]),
            fn=np.mean,
            metric_name="m",
            scope="s",
            n_reps=10,
            seed=0,
        )


def test_cluster_bootstrap_mean_car_point_equals_sample_mean() -> None:
    """Bootstrap point estimate is the sample mean by definition."""
    rng = np.random.default_rng(7)
    cars = pd.Series(rng.normal(loc=0.02, scale=0.05, size=300))
    res = cluster_bootstrap_mean_car(
        cars, metric_name="car", scope="t1", n_reps=500, seed=0
    )
    assert res.point == pytest.approx(float(cars.mean()), abs=1e-12)
    # CI brackets the point estimate
    assert res.lower < res.point < res.upper
    # CI width is on order of 2·SE(mean) ≈ 2·0.05/√300 ≈ 0.006 → 90% CI ~0.01
    assert 0.001 < (res.upper - res.lower) < 0.05


def test_cluster_bootstrap_mean_car_rejects_empty() -> None:
    with pytest.raises(ValueError, match="empty"):
        cluster_bootstrap_mean_car(
            pd.Series([np.nan, np.nan]),
            metric_name="m",
            scope="s",
            n_reps=10,
        )


def test_cluster_bootstrap_did_rejects_empty_sets() -> None:
    panel = _make_did_panel(delta=0.0, n_treated=4, n_controls=4, n_per=50)
    with pytest.raises(ValueError, match="empty"):
        cluster_bootstrap_did(
            panel,
            treated=set(),
            controls={f"C{i}" for i in range(4)},
            metric_name="m",
            scope="s",
            n_reps=10,
        )
