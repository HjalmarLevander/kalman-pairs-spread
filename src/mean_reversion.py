"""Shared mean-reversion diagnostics used by Phase 1 (noise-parameter
selection) and Phase 3 (signal-quality sweep), so both use the same
definition of half-life rather than two subtly different ones.
"""
import numpy as np
import pandas as pd


def half_life(spread: pd.Series) -> float:
    """OU mean-reversion half-life via AR(1) fit: spread_t - spread_{t-1} =
    -lambda*(spread_{t-1} - mean) + eps, fit by OLS. ln(2)/lambda in days.
    Returns inf if the fit implies no reversion (lambda <= 0).
    """
    s = spread.dropna()
    if len(s) < 30:
        return float("nan")
    lagged = s.shift(1).dropna()
    delta = (s - s.shift(1)).dropna()
    lagged = lagged.loc[delta.index]
    x = lagged.to_numpy() - lagged.mean()
    y = delta.to_numpy()
    if x.var() == 0:
        return float("nan")
    lam = -np.polyfit(x, y, 1)[0]
    if lam <= 0:
        return float("inf")
    return float(np.log(2) / lam)
