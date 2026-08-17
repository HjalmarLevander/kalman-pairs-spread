import numpy as np
import pandas as pd
import pytest

from src.phase2_fft_denoise import fft_denoise_window, rolling_fft_denoise, variance_explained


@pytest.fixture
def rng():
    return np.random.default_rng(2)


def _noisy_sine(rng, n=400, freq=1 / 20, noise_std=0.5):
    idx = pd.date_range("2018-01-01", periods=n, freq="B")
    t = np.arange(n)
    true_signal = np.sin(2 * np.pi * freq * t)
    noisy = true_signal + rng.normal(0, noise_std, n)
    return pd.Series(noisy, index=idx), true_signal


def test_denoise_window_is_identity_at_percentile_zero():
    """Keeping every frequency component (threshold at the 0th percentile)
    should reconstruct the input almost exactly."""
    rng = np.random.default_rng(3)
    values = rng.normal(0, 1, 32)
    out = fft_denoise_window(values, percentile=0)
    assert out == pytest.approx(values[-1], abs=1e-9)


def test_denoise_reduces_distance_to_true_signal(rng):
    """A moderate percentile threshold should pull the noisy series closer
    to the underlying clean sine than the raw noisy series is."""
    noisy, true_signal = _noisy_sine(rng)
    denoised = rolling_fft_denoise(noisy, percentile=70, window=40)
    valid = denoised.dropna().index
    idx_pos = noisy.index.get_indexer(valid)

    raw_err = np.mean((noisy.loc[valid].to_numpy() - true_signal[idx_pos]) ** 2)
    denoised_err = np.mean((denoised.loc[valid].to_numpy() - true_signal[idx_pos]) ** 2)
    assert denoised_err < raw_err


def test_causal_denoise_unaffected_by_future_values(rng):
    """The denoised value at time t must be identical whether or not later
    observations exist yet -- otherwise the pipeline has a lookahead leak."""
    noisy, _ = _noisy_sine(rng, n=200)
    window = 40
    cutoff = 150

    full = rolling_fft_denoise(noisy, percentile=60, window=window)
    truncated = rolling_fft_denoise(noisy.iloc[:cutoff], percentile=60, window=window)

    check_at = cutoff - 1
    assert full.iloc[check_at] == pytest.approx(truncated.iloc[check_at], abs=1e-9)


def test_first_window_minus_one_points_are_nan(rng):
    noisy, _ = _noisy_sine(rng, n=100)
    window = 30
    denoised = rolling_fft_denoise(noisy, percentile=50, window=window)
    assert denoised.iloc[: window - 1].isna().all()
    assert denoised.iloc[window - 1 :].notna().all()


def test_higher_percentile_does_not_increase_variance_explained_monotonically_violation(rng):
    """Not a strict monotonicity claim (percentile vs. Sharpe famously
    diverge per the spec) -- just a sanity check that variance explained is
    a valid, bounded quantity and that keeping fewer components (higher p)
    does not somehow explain *more* raw variance than keeping all of them."""
    noisy, _ = _noisy_sine(rng)
    low_p = rolling_fft_denoise(noisy, percentile=10, window=40)
    high_p = rolling_fft_denoise(noisy, percentile=90, window=40)
    ve_low = variance_explained(noisy, low_p)
    ve_high = variance_explained(noisy, high_p)
    assert ve_low <= 1.0 + 1e-9
    assert ve_high <= ve_low + 1e-9
