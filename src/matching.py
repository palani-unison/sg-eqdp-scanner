"""Matched-pair DiD — closest control by Mahalanobis distance.

Per docs/METHODOLOGY.md §7. For each treatment stock, find the closest control
in the donor pool by ``(sector, β, amihud_60d)``. Distance is Mahalanobis on
standardised continuous features; the categorical ``sector`` filter is applied
first (only same-sector controls are eligible). If no same-sector control
exists, falls back to nearest-by-features irrespective of sector and emits a
warning column.

Then ``did_panel`` builds a long Treated × Post panel and runs
``linearmodels.PanelOLS`` with entity + time fixed effects:

    R_{i,t} = α_i + γ_t + δ · (Treated_i · Post_t) + ε_{i,t}

δ is the EQDP effect after the matched control absorbs everything we can
match on.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd
from linearmodels.panel import PanelOLS


@dataclass(frozen=True, slots=True)
class FeatureRow:
    """Per-ticker feature row used for matching."""

    ticker: str
    sector: str
    beta: float
    amihud_60d: float


@dataclass(frozen=True, slots=True)
class DiDResult:
    """Output of did_panel. ``delta`` is the Treated×Post coefficient."""

    delta: float
    std_error: float
    t_stat: float
    p_value: float
    n_obs: int
    n_entities: int
    treated: tuple[str, ...]
    controls: tuple[str, ...]


def _standardise(feat: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """z-score the listed columns (ddof=0). Constant columns return zeros."""
    out = feat.copy()
    for c in cols:
        sigma = out[c].std(ddof=0)
        mu = out[c].mean()
        out[c] = (out[c] - mu) / sigma if sigma > 0 else 0.0
    return out


def match_controls(
    treated: list[FeatureRow],
    control_pool: list[FeatureRow],
    *,
    cont_cols: tuple[str, ...] = ("beta", "amihud_60d"),
    require_same_sector: bool = True,
    used_unique: bool = False,
) -> dict[str, str]:
    """Return a mapping of treated ticker → matched control ticker.

    With ``require_same_sector=True``, the donor pool for each treated stock
    is filtered to its own sector; falls back to global pool if empty.

    With ``used_unique=True``, no control is reused across treated units —
    pick greedily in input order.
    """
    if not treated:
        return {}
    if not control_pool:
        raise ValueError("control_pool is empty")

    full = pd.DataFrame([asdict(t) for t in treated + control_pool])
    full = _standardise(full, list(cont_cols))
    # Force the numeric columns to float to keep np.linalg happy (mixed-dtype
    # rows from .iterrows() yield object arrays otherwise).
    for c in cont_cols:
        full[c] = full[c].astype("float64")
    is_treated = pd.Series(
        [True] * len(treated) + [False] * len(control_pool), index=full.index
    )

    treated_df = full[is_treated]
    pool_df = full[~is_treated]
    used: set[str] = set()
    out: dict[str, str] = {}

    for _, t in treated_df.iterrows():
        candidates = pool_df
        if require_same_sector:
            same = pool_df[pool_df["sector"] == t["sector"]]
            candidates = same if not same.empty else pool_df
        if used_unique:
            candidates = candidates[~candidates["ticker"].isin(used)]
            if candidates.empty:
                continue
        # Euclidean on z-scored features (post-standardisation cov ≈ I, so
        # Euclidean ≡ Mahalanobis and avoids singular-cov edge cases).
        target = np.asarray(
            [float(t[c]) for c in cont_cols], dtype="float64"
        )
        cand_pts = candidates[list(cont_cols)].to_numpy(dtype="float64")
        diff = cand_pts - target
        dist = np.linalg.norm(diff, axis=1)
        best_idx = int(np.argmin(dist))
        chosen = str(candidates.iloc[best_idx]["ticker"])
        out[str(t["ticker"])] = chosen
        used.add(chosen)
    return out


def did_panel(
    panel: pd.DataFrame,
    treated: set[str],
    controls: set[str],
    *,
    event_t0: int = 0,
    outcome: str = "ret",
) -> DiDResult:
    """Run a Treated × Post DiD on the long panel.

    The panel must have columns ``ticker``, ``t``, and ``outcome``. Rows where
    ticker is neither treated nor a control are dropped. Post = (t >= event_t0).

    Returns the δ coefficient, its t-stat, and the per-entity sample.
    """
    needed = {"ticker", "t", outcome}
    missing = needed - set(panel.columns)
    if missing:
        raise KeyError(f"panel missing columns: {sorted(missing)}")

    universe = treated | controls
    df = panel[panel["ticker"].isin(universe)].copy()
    df = df.dropna(subset=[outcome])
    if df.empty:
        raise ValueError("no rows match treated ∪ controls in panel")

    df["treated"] = df["ticker"].isin(treated).astype(int)
    df["post"] = (df["t"] >= event_t0).astype(int)
    df["interact"] = df["treated"] * df["post"]

    df = df.set_index(["ticker", "t"])
    df = df.sort_index()

    # PanelOLS with entity + time fixed effects.
    mod = PanelOLS(
        dependent=df[[outcome]],
        exog=df[["interact"]],
        entity_effects=True,
        time_effects=True,
    )
    res = mod.fit(cov_type="clustered", cluster_entity=True)
    delta = float(res.params["interact"])
    se = float(res.std_errors["interact"])
    tstat = float(res.tstats["interact"])
    pval = float(res.pvalues["interact"])
    return DiDResult(
        delta=delta,
        std_error=se,
        t_stat=tstat,
        p_value=pval,
        n_obs=int(res.nobs),
        n_entities=df.index.get_level_values("ticker").nunique(),
        treated=tuple(sorted(treated)),
        controls=tuple(sorted(controls)),
    )
