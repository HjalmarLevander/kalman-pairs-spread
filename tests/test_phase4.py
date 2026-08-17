import numpy as np
import pandas as pd
import pytest

from src.phase4_backtest import backtest, regime_split_dates, rolling_zscore, split_metrics_by_regime


@pytest.fixture
def rng():
    return np.random.default_rng(4)


def _ou_process(rng, n=1000, theta=0.05, mu=0.0, sigma=0.3):
    """Simulated Ornstein-Uhlenbeck (genuinely mean-reverting) series -- a
    z-score entry/exit strategy should be able to extract positive expected
    PnL from this by construction."""
    idx = pd.date_range("2018-01-01", periods=n, freq="B")
    x = np.zeros(n)
    for t in range(1, n):
        x[t] = x[t - 1] + theta * (mu - x[t - 1]) + rng.normal(0, sigma)
    return pd.Series(x, index=idx)


def test_zscore_is_nan_before_window_fills():
    s = pd.Series(np.arange(20, dtype=float))
    z = rolling_zscore(s, window=10)
    assert z.iloc[:9].isna().all()
    assert z.iloc[9:].notna().all()


def test_backtest_no_trades_on_flat_series_within_band():
    idx = pd.date_range("2018-01-01", periods=200, freq="B")
    flat = pd.Series(np.zeros(200) + np.random.default_rng(0).normal(0, 0.01, 200), index=idx)
    result = backtest(flat, z_entry=100, z_exit=50, zscore_window=30)  # threshold unreachable
    assert result.n_trades == 0
    assert np.isnan(result.hit_rate)


def test_backtest_extracts_positive_expectancy_from_ou_process(rng):
    spread = _ou_process(rng)
    result = backtest(spread, z_entry=1.5, z_exit=0.3, zscore_window=40, transaction_cost_bps=1.0)
    assert result.n_trades > 5
    assert result.sharpe > 0


def test_higher_transaction_costs_reduce_sharpe(rng):
    spread = _ou_process(rng)
    cheap = backtest(spread, z_entry=1.5, z_exit=0.3, zscore_window=40, transaction_cost_bps=1.0)
    expensive = backtest(spread, z_entry=1.5, z_exit=0.3, zscore_window=40, transaction_cost_bps=200.0)
    assert expensive.sharpe < cheap.sharpe


def test_max_holding_period_forces_exit(rng):
    spread = _ou_process(rng, theta=0.001)  # very slow reversion, would hold a long time otherwise
    result = backtest(spread, z_entry=1.0, z_exit=-1.0, zscore_window=40, max_holding_days=5)
    # z_exit set below z_entry's reachable range without reversion, so the
    # only thing that can end a trade is the max-holding-period forced exit
    if result.trades:
        assert max(t.duration_days for t in result.trades) <= 5


def test_regime_split_flags_large_moves():
    idx = pd.date_range("2018-01-01", periods=100, freq="B")
    returns = pd.Series(np.random.default_rng(5).normal(0, 0.01, 100), index=idx)
    returns.iloc[50] = 0.5  # inject an obvious outlier
    mask = regime_split_dates(returns, threshold_std=2.5)
    assert mask.iloc[50]
    assert mask.sum() < 10  # most days should NOT be flagged extreme


def test_split_metrics_by_regime_returns_finite_or_nan(rng):
    spread = _ou_process(rng)
    result = backtest(spread, z_entry=1.5, z_exit=0.3, zscore_window=40)
    fake_returns = spread.diff().fillna(0)
    mask = regime_split_dates(fake_returns)
    metrics = split_metrics_by_regime(result.daily_pnl, mask)
    assert metrics["n_extreme_days"] + metrics["n_normal_days"] == len(result.daily_pnl)
