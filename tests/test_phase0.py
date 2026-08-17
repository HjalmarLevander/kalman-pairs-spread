import numpy as np
import pandas as pd
import pytest

from src.phase0_pair_selection import (
    build_shortlist,
    cointegration_test,
    rolling_correlation,
    rolling_hedge_ratio_stability,
)


@pytest.fixture
def rng():
    return np.random.default_rng(0)


def _cointegrated_pair(rng, n=800):
    """x is a random walk; y = 2*x + stationary noise -- cointegrated by construction."""
    idx = pd.date_range("2018-01-01", periods=n, freq="B")
    x = pd.Series(100 + np.cumsum(rng.normal(0, 1, n)), index=idx)
    noise = pd.Series(rng.normal(0, 1, n), index=idx)
    y = 2 * x + noise
    return x, y


def _independent_pair(rng, n=800):
    """Two independent random walks -- not cointegrated, no stable relationship."""
    idx = pd.date_range("2018-01-01", periods=n, freq="B")
    x = pd.Series(100 + np.cumsum(rng.normal(0, 1, n)), index=idx)
    y = pd.Series(50 + np.cumsum(rng.normal(0, 1, n)), index=idx)
    return x, y


def test_cointegration_flags_known_cointegrated_pair(rng):
    x, y = _cointegrated_pair(rng)
    pvalue = cointegration_test(x, y)
    assert pvalue < 0.05


def test_cointegration_does_not_flag_independent_walks(rng):
    x, y = _independent_pair(rng)
    pvalue = cointegration_test(x, y)
    assert pvalue > 0.05


def test_rolling_correlation_high_for_scaled_series(rng):
    x, y = _cointegrated_pair(rng)
    corr = rolling_correlation(x, y, windows=(30, 90))
    assert corr[30] > 0.5
    assert corr[90] > 0.5


def test_rolling_correlation_low_for_independent_walks(rng):
    x, y = _independent_pair(rng)
    corr = rolling_correlation(x, y, windows=(30, 90))
    for v in corr.values():
        assert abs(v) < 0.9  # not perfectly correlated; loose bound, random walks can drift


def test_hedge_ratio_stable_for_cointegrated_pair(rng):
    x, y = _cointegrated_pair(rng)
    beta_mean, beta_cv, _ = rolling_hedge_ratio_stability(x, y, window=90)
    assert beta_mean == pytest.approx(2.0, abs=0.3)
    assert beta_cv < 0.3  # low coefficient of variation -> smoothly stable, not noise


def test_hedge_ratio_unstable_for_independent_walks(rng):
    x, y = _independent_pair(rng)
    beta_mean, beta_cv, _ = rolling_hedge_ratio_stability(x, y, window=90)
    # independent walks can still produce a spurious rolling beta, but it
    # should not look anywhere near as stable as the true cointegrated case
    assert np.isnan(beta_cv) or beta_cv > 0.3 or abs(beta_mean) < 0.05


def test_hedge_ratio_handles_zero_variance_window():
    idx = pd.date_range("2018-01-01", periods=50, freq="B")
    x = pd.Series([100.0] * 50, index=idx)  # zero variance -> guards div-by-zero
    y = pd.Series(np.arange(50, dtype=float), index=idx)
    beta_mean, beta_cv, beta_autocorr = rolling_hedge_ratio_stability(x, y, window=20)
    assert np.isnan(beta_mean) or beta_mean == 0


def test_build_shortlist_empty_when_all_tickers_missing():
    empty_prices = pd.DataFrame()
    rows = build_shortlist([("AAA", "BBB"), ("CCC", "DDD")], empty_prices)
    assert len(rows) == 2
    assert all(r.note == "missing price data" for r in rows)
    assert all(r.corr_consistent is False for r in rows)


def test_build_shortlist_skips_pair_with_one_missing_ticker(rng):
    x, _ = _cointegrated_pair(rng)
    prices = pd.DataFrame({"AAA": x})
    rows = build_shortlist([("AAA", "ZZZ")], prices)
    assert rows[0].note == "missing price data"
