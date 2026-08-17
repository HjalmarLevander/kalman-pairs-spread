"""Phase 1: dynamic hedge ratio via Kalman filter (see ../SPEC.md).

State-space model, per pair (X, Y):
    beta_t = beta_{t-1} + w_t          w_t ~ N(0, transition_covariance)
    Y_t    = beta_t * X_t + v_t        v_t ~ N(0, observation_covariance)

transition_covariance and observation_covariance are NOT guessed: they're
grid-searched by maximizing the Kalman filter's own log-likelihood on the
selection-window data (same no-lookahead boundary as Phase 0 --
SELECTION_START/END are imported from phase0, not redefined).

Output per pair: filtered beta_t, its uncertainty (state covariance), and
the resulting spread_t = Y_t - beta_t * X_t, written to reports/.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

import numpy as np
import pandas as pd
from pykalman import KalmanFilter

from src.phase0_pair_selection import SELECTION_END, SELECTION_START, load_prices

# Grid search ranges for the two free noise variances. delta controls how
# fast beta is allowed to adapt (small delta -> transition_covariance near
# zero -> beta barely moves -> static OLS-like); obs_cov controls how much
# weight the filter puts on each new observation vs. its prior belief.
DELTA_GRID = (1e-6, 1e-5, 1e-4, 1e-3, 1e-2)
OBS_COV_GRID = (1e-3, 1e-2, 1e-1, 1.0, 10.0)

REPORT_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")


@dataclass
class KalmanFitResult:
    pair: str
    delta: float
    obs_cov: float
    loglikelihood: float
    beta: pd.Series
    beta_std: pd.Series
    spread: pd.Series


def _build_filter(x: np.ndarray, delta: float, obs_cov: float) -> KalmanFilter:
    """delta -> transition_covariance via the standard delta/(1-delta) scaling
    used in Kalman pairs-trading (Ernest Chan's convention): keeps the
    process-noise magnitude on a comparable, boundable [0, inf) scale as
    delta ranges over (0, 1) instead of grid-searching a raw covariance
    whose sensible range depends on the data's own scale.
    """
    trans_cov = delta / (1 - delta)
    obs_matrices = x.reshape(-1, 1, 1)
    return KalmanFilter(
        transition_matrices=np.array([[1.0]]),
        observation_matrices=obs_matrices,
        transition_covariance=np.array([[trans_cov]]),
        observation_covariance=np.array([[obs_cov]]),
        initial_state_mean=np.array([0.0]),
        initial_state_covariance=np.array([[1.0]]),
    )


def fit_noise_params(x: pd.Series, y: pd.Series) -> tuple[float, float, float]:
    """Grid-search (delta, obs_cov) maximizing filter log-likelihood on
    (x, y). Returns (best_delta, best_obs_cov, best_loglikelihood).
    """
    aligned = pd.concat([x, y], axis=1, join="inner").dropna()
    x_arr, y_arr = aligned.iloc[:, 0].to_numpy(), aligned.iloc[:, 1].to_numpy()

    best = (DELTA_GRID[0], OBS_COV_GRID[0], -np.inf)
    for delta in DELTA_GRID:
        for obs_cov in OBS_COV_GRID:
            kf = _build_filter(x_arr, delta, obs_cov)
            ll = kf.loglikelihood(y_arr.reshape(-1, 1))
            if ll > best[2]:
                best = (delta, obs_cov, ll)
    return best


def run_kalman_filter(pair_label: str, x: pd.Series, y: pd.Series, delta: float, obs_cov: float) -> KalmanFitResult:
    """Filter (not smooth) beta_t and its uncertainty -- filtering, not
    smoothing, is what a live trading signal must use: smoothing would use
    future observations to estimate beta_t, which is unavailable at trade
    time and would itself be a form of lookahead bias.
    """
    aligned = pd.concat([x, y], axis=1, join="inner").dropna()
    x_arr, y_arr = aligned.iloc[:, 0].to_numpy(), aligned.iloc[:, 1].to_numpy()

    kf = _build_filter(x_arr, delta, obs_cov)
    state_means, state_covs = kf.filter(y_arr.reshape(-1, 1))

    beta = pd.Series(state_means[:, 0], index=aligned.index, name="beta")
    beta_std = pd.Series(np.sqrt(state_covs[:, 0, 0]), index=aligned.index, name="beta_std")
    spread = pd.Series(aligned.iloc[:, 1].to_numpy() - beta.to_numpy() * aligned.iloc[:, 0].to_numpy(),
                        index=aligned.index, name="spread")

    ll = kf.loglikelihood(y_arr.reshape(-1, 1))
    return KalmanFitResult(pair_label, delta, obs_cov, ll, beta, beta_std, spread)


def process_pair(pair_label: str, prices: pd.DataFrame) -> KalmanFitResult:
    a, b = pair_label.split("/")
    x, y = prices[a], prices[b]
    delta, obs_cov, ll = fit_noise_params(x, y)
    return run_kalman_filter(pair_label, x, y, delta, obs_cov)


def write_result(result: KalmanFitResult, out_dir: str = REPORT_DIR) -> str:
    os.makedirs(out_dir, exist_ok=True)
    safe_name = result.pair.replace("/", "_")
    path = os.path.join(out_dir, f"phase1_kalman_{safe_name}.csv")
    df = pd.DataFrame({
        "beta": result.beta,
        "beta_std": result.beta_std,
        "spread": result.spread,
    })
    df.to_csv(path, index_label="date")
    return path


def main() -> None:
    pairs = ["V/MA", "KO/PEP"]
    tickers = sorted({t for p in pairs for t in p.split("/")})
    prices = load_prices(tickers, SELECTION_START, SELECTION_END)

    for pair_label in pairs:
        result = process_pair(pair_label, prices)
        path = write_result(result)
        print(
            f"{pair_label}: delta={result.delta:g} obs_cov={result.obs_cov:g} "
            f"loglik={result.loglikelihood:.1f} beta[final]={result.beta.iloc[-1]:.4f} "
            f"-> {path}"
        )


if __name__ == "__main__":
    main()
