import numpy as np
import pandas as pd
import pytest

from src.phase1_kalman_hedge_ratio import fit_noise_params, run_kalman_filter


@pytest.fixture
def rng():
    return np.random.default_rng(1)


def _static_beta_pair(rng, n=500, true_beta=1.5, obs_noise=0.5):
    """y = true_beta * x + noise, constant beta -- the filter should
    converge close to true_beta and stay there with low uncertainty."""
    idx = pd.date_range("2018-01-01", periods=n, freq="B")
    x = pd.Series(100 + np.cumsum(rng.normal(0, 1, n)), index=idx)
    y = pd.Series(true_beta * x.to_numpy() + rng.normal(0, obs_noise, n), index=idx)
    return x, y, true_beta


def _drifting_beta_pair(rng, n=500):
    """beta itself follows a slow random walk -- the filter's beta_t should
    track the drift rather than sit flat at one value."""
    idx = pd.date_range("2018-01-01", periods=n, freq="B")
    x = pd.Series(100 + np.cumsum(rng.normal(0, 1, n)), index=idx)
    true_beta = 1.0 + np.cumsum(rng.normal(0, 0.01, n))
    y = pd.Series(true_beta * x.to_numpy() + rng.normal(0, 0.3, n), index=idx)
    return x, y, true_beta


def test_filter_converges_near_true_static_beta(rng):
    x, y, true_beta = _static_beta_pair(rng)
    delta, obs_cov, ll = fit_noise_params(x, y)
    result = run_kalman_filter("X/Y", x, y, delta, obs_cov)
    tail_beta = result.beta.iloc[-50:].mean()
    assert tail_beta == pytest.approx(true_beta, abs=0.2)


def test_filter_uncertainty_converges_from_initial_guess(rng):
    """With nonzero process noise the filter's steady-state uncertainty
    doesn't keep shrinking forever (it settles), but it should still drop
    sharply from the initial, uninformed prior in the first few steps."""
    x, y, _ = _static_beta_pair(rng)
    delta, obs_cov, _ = fit_noise_params(x, y)
    result = run_kalman_filter("X/Y", x, y, delta, obs_cov)
    initial_std = result.beta_std.iloc[0]
    steady_state_std = result.beta_std.iloc[-30:].mean()
    assert steady_state_std < initial_std


def test_filter_tracks_drifting_beta(rng):
    x, y, true_beta = _drifting_beta_pair(rng)
    delta, obs_cov, _ = fit_noise_params(x, y)
    result = run_kalman_filter("X/Y", x, y, delta, obs_cov)
    # filtered beta should end up closer to the true final beta than the
    # naive assumption of "beta never moved from its start"
    err_tracking = abs(result.beta.iloc[-1] - true_beta[-1])
    err_static_assumption = abs(true_beta[0] - true_beta[-1])
    assert err_tracking < err_static_assumption


def test_spread_is_roughly_stationary_for_cointegrated_pair(rng):
    x, y, _ = _static_beta_pair(rng, obs_noise=0.3)
    delta, obs_cov, _ = fit_noise_params(x, y)
    result = run_kalman_filter("X/Y", x, y, delta, obs_cov)
    tail_spread = result.spread.iloc[100:]
    # a genuinely mean-reverting spread shouldn't drift on the same scale as
    # the underlying random-walk price level (~sqrt(n) growth)
    assert tail_spread.std() < x.std()


def test_fit_noise_params_returns_grid_members(rng):
    x, y, _ = _static_beta_pair(rng)
    delta, obs_cov, ll = fit_noise_params(x, y)
    from src.phase1_kalman_hedge_ratio import DELTA_GRID, OBS_COV_GRID
    assert delta in DELTA_GRID
    assert obs_cov in OBS_COV_GRID
    assert np.isfinite(ll)
