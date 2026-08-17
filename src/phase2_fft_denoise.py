"""Phase 2: frequency-domain denoising of the Kalman spread (see ../SPEC.md).

For each timestep t, take the trailing `window` samples of spread_t ending at
t (causal -- never touches t+1 or later), FFT it, zero out every frequency
bin whose power falls below the p-th percentile of that window's power
spectrum, inverse-FFT, and keep only the reconstructed value at t. This is a
rolling short-time FFT denoise rather than one FFT over the whole series,
because the spec calls the beta/spread relationship non-stationary over the
long run -- a single global FFT would let early-history frequency content
"denoise" a value decades later, which makes no economic sense and also
reintroduces a lookahead-adjacent leak (the whole-series FFT of a causal
signal is not causal itself).

`percentile` (p) is the free parameter Phase 3 sweeps -- this module exposes
the denoising primitive, not a chosen p.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

DEFAULT_WINDOW = 60


def fft_denoise_window(values: np.ndarray, percentile: float) -> float:
    """FFT-threshold-IFFT a single window, return only the reconstructed
    value at the window's last (most recent) index.
    """
    n = len(values)
    spectrum = np.fft.rfft(values)
    power = np.abs(spectrum) ** 2
    threshold = np.percentile(power, percentile)
    kept = np.where(power >= threshold, spectrum, 0)
    reconstructed = np.fft.irfft(kept, n=n)
    return float(reconstructed[-1])


def rolling_fft_denoise(spread: pd.Series, percentile: float, window: int = DEFAULT_WINDOW) -> pd.Series:
    """Causal rolling FFT denoise. The first `window - 1` points have no
    full trailing window and are left as NaN rather than padded/estimated
    from a partial window, since a partial-window FFT has a different
    effective frequency resolution and would not be comparable to the rest
    of the series.
    """
    values = spread.to_numpy()
    out = np.full(len(values), np.nan)
    for i in range(window - 1, len(values)):
        out[i] = fft_denoise_window(values[i - window + 1: i + 1], percentile)
    return pd.Series(out, index=spread.index, name="spread_denoised")


def variance_explained(spread: pd.Series, denoised: pd.Series) -> float:
    """1 - (residual variance / raw variance), over the overlapping,
    non-NaN portion of both series. Reported alongside the trading-side
    metrics in Phase 3a, not decided here.
    """
    aligned = pd.concat([spread, denoised], axis=1, join="inner").dropna()
    if aligned.empty:
        return float("nan")
    residual = aligned.iloc[:, 0] - aligned.iloc[:, 1]
    raw_var = aligned.iloc[:, 0].var()
    if raw_var == 0:
        return float("nan")
    return float(1 - residual.var() / raw_var)
