"""What would $1000 actually do: converts the strategy's realized daily PnL
(per unit of spread notional) into dollar terms for a fixed starting capital,
then block-bootstraps the historical daily-return series to project a
distribution of outcomes at several horizons.

Uses the FULL 2015-2026 history (in-sample fit window + out-of-sample
validation window) under the single frozen half-life-floored config from the
follow-up experiment -- not a new fit, not re-tuned on this longer window.
More history gives the bootstrap more raw material; the strategy parameters
themselves were already validated OOS separately (see PROGRESS.md).

Capital model (explicit, not hidden): $1000 total, split $500/$500 across
V/MA and KO/PEP. Position size per pair is fixed at (500 / average notional
for that pair) units of spread -- NOT compounded (units don't grow as
capital grows). This is a deliberately simple, conservative model; a real
allocator would resize positions as capital compounds, which would fatten
the right tail of these distributions, not the left.
"""
import json
import os

import numpy as np
import pandas as pd

from src.phase0_pair_selection import SELECTION_END, SELECTION_START, load_prices
from src.phase1_kalman_hedge_ratio import fit_noise_params_with_half_life_floor, run_kalman_filter
from src.phase2_fft_denoise import rolling_fft_denoise
from src.phase4_backtest import backtest

REPORTS = os.path.join(os.path.dirname(__file__), "..", "reports")

CONFIGS = {
    "V_MA": dict(pair=("V", "MA"), p=70, z_entry=1.0, z_exit=0.5),
    "KO_PEP": dict(pair=("KO", "PEP"), p=70, z_entry=1.0, z_exit=0.25),
}
FULL_START, FULL_END = SELECTION_START, "2026-08-01"
CAPITAL_PER_PAIR = 500.0
BLOCK_SIZE = 10  # trading days per bootstrap block, preserves short-run autocorrelation from trade clustering
N_SIMS = 10_000
HORIZONS_DAYS = {"1 month": 21, "3 months": 63, "6 months": 126, "1 year": 252, "2 years": 504, "3 years": 756}
SEED = 42


def dollar_daily_pnl(label: str, cfg: dict) -> pd.Series:
    a, b = cfg["pair"]
    fit_prices = load_prices([a, b], SELECTION_START, SELECTION_END)
    delta, obs_cov, _, _ = fit_noise_params_with_half_life_floor(fit_prices[a], fit_prices[b], min_half_life_days=10.0)

    full_prices = load_prices([a, b], FULL_START, FULL_END)
    result = run_kalman_filter(label, full_prices[a], full_prices[b], delta, obs_cov)
    denoised = rolling_fft_denoise(result.spread, percentile=cfg["p"], window=60)
    notional = (full_prices[b] + result.beta * full_prices[a]).abs().reindex(result.spread.index)

    bt = backtest(denoised, z_entry=cfg["z_entry"], z_exit=cfg["z_exit"], zscore_window=60, notional=notional)

    units = CAPITAL_PER_PAIR / notional.mean()
    return (bt.daily_pnl * units).rename(label)


def block_bootstrap_paths(daily_returns: np.ndarray, horizon_days: int, n_sims: int, block_size: int, rng: np.random.Generator) -> np.ndarray:
    n_obs = len(daily_returns)
    n_blocks_needed = int(np.ceil(horizon_days / block_size))
    starts = rng.integers(0, n_obs - block_size, size=(n_sims, n_blocks_needed))
    paths = np.empty((n_sims, n_blocks_needed * block_size))
    for i in range(n_blocks_needed):
        idx = starts[:, i][:, None] + np.arange(block_size)[None, :]
        paths[:, i * block_size:(i + 1) * block_size] = daily_returns[idx]
    return paths[:, :horizon_days]


def main():
    rng = np.random.default_rng(SEED)

    series = [dollar_daily_pnl(label, cfg) for label, cfg in CONFIGS.items()]
    combined = pd.concat(series, axis=1).fillna(0.0).sum(axis=1)
    daily_returns = combined.to_numpy()

    print(f"combined daily pnl: n={len(daily_returns)}, mean=${daily_returns.mean():.3f}, "
          f"std=${daily_returns.std():.3f}, annualized Sharpe={daily_returns.mean()/daily_returns.std()*np.sqrt(252):.2f}")

    results = {}
    for name, h in HORIZONS_DAYS.items():
        paths = block_bootstrap_paths(daily_returns, h, N_SIMS, BLOCK_SIZE, rng)
        cumulative = 1000.0 + paths.sum(axis=1)
        running_min = 1000.0 + np.minimum.accumulate(paths.cumsum(axis=1), axis=1)
        max_drawdown_dollars = (running_min - 1000.0)  # will be <= 0; worst point of each path (not path-max, just illustrative)
        pct = np.percentile(cumulative, [5, 25, 50, 75, 95])
        results[name] = {
            "horizon_days": h,
            "p5": round(float(pct[0]), 2),
            "p25": round(float(pct[1]), 2),
            "p50": round(float(pct[2]), 2),
            "p75": round(float(pct[3]), 2),
            "p95": round(float(pct[4]), 2),
            "prob_loss": round(float((cumulative < 1000.0).mean()), 4),
            "prob_below_800": round(float((cumulative < 800.0).mean()), 4),
            "worst_1pct": round(float(np.percentile(cumulative, 1)), 2),
        }
        print(f"{name:>9}: p5=${pct[0]:.0f} p50=${pct[2]:.0f} p95=${pct[4]:.0f} "
              f"P(loss)={results[name]['prob_loss']:.1%} P(<$800)={results[name]['prob_below_800']:.1%}")

    # sample fan-chart paths for the longest horizon, for visualization
    longest = max(HORIZONS_DAYS.values())
    fan_paths = block_bootstrap_paths(daily_returns, longest, 400, BLOCK_SIZE, rng)
    fan_cumulative = 1000.0 + np.cumsum(fan_paths, axis=1)
    # percentile band across time, plus a handful of individual sample paths
    band = {
        "days": list(range(0, longest, 10)),
        "p5": [round(float(x), 1) for x in np.percentile(fan_cumulative, 5, axis=0)[::10]],
        "p25": [round(float(x), 1) for x in np.percentile(fan_cumulative, 25, axis=0)[::10]],
        "p50": [round(float(x), 1) for x in np.percentile(fan_cumulative, 50, axis=0)[::10]],
        "p75": [round(float(x), 1) for x in np.percentile(fan_cumulative, 75, axis=0)[::10]],
        "p95": [round(float(x), 1) for x in np.percentile(fan_cumulative, 95, axis=0)[::10]],
        "sample_paths": [[round(float(v), 1) for v in fan_cumulative[i, ::10]] for i in range(8)],
    }

    out = {"horizons": results, "fan_chart": band, "n_sims": N_SIMS, "block_size": BLOCK_SIZE,
           "capital_per_pair": CAPITAL_PER_PAIR, "history_days": len(daily_returns)}
    with open(os.path.join(REPORTS, "monte_carlo.json"), "w") as f:
        json.dump(out, f)
    print(f"\nwrote {os.path.join(REPORTS, 'monte_carlo.json')}")


if __name__ == "__main__":
    main()
