"""The real test: apply the half-life-floored Kalman params and best (p,
z_entry, z_exit) found on the 2015-2021 SELECTION window -- frozen, not
refit -- to 2022 onward, which this pipeline has never touched. This is
what tells us whether the positive Sharpe from rerun_with_half_life_floor.py
is real or an artifact of fitting and sweeping on the same window.
"""
import numpy as np
import pandas as pd

from src.mean_reversion import half_life
from src.phase0_pair_selection import SELECTION_END, SELECTION_START, load_prices
from src.phase1_kalman_hedge_ratio import fit_noise_params_with_half_life_floor, run_kalman_filter
from src.phase2_fft_denoise import rolling_fft_denoise
from src.phase4_backtest import backtest, regime_split_dates, split_metrics_by_regime

OOS_START = "2022-01-01"
OOS_END = "2026-08-01"

configs = {
    "V_MA": dict(pair=("V", "MA"), p=70, z_entry=1.0, z_exit=0.5),
    "KO_PEP": dict(pair=("KO", "PEP"), p=70, z_entry=1.0, z_exit=0.25),
}

for label, cfg in configs.items():
    a, b = cfg["pair"]

    # Fit noise params on the SAME selection window as before (frozen choice)
    fit_prices = load_prices([a, b], SELECTION_START, SELECTION_END)
    delta, obs_cov, ll, hl = fit_noise_params_with_half_life_floor(fit_prices[a], fit_prices[b], min_half_life_days=10.0)

    # Apply that frozen (delta, obs_cov) to fresh, never-seen data
    oos_prices = load_prices([a, b], OOS_START, OOS_END)
    result = run_kalman_filter(label, oos_prices[a], oos_prices[b], delta, obs_cov)
    denoised = rolling_fft_denoise(result.spread, percentile=cfg["p"], window=60)
    notional = (oos_prices[b] + result.beta * oos_prices[a]).abs().reindex(result.spread.index)

    bt = backtest(denoised, z_entry=cfg["z_entry"], z_exit=cfg["z_exit"], zscore_window=60, notional=notional)
    hl_oos = half_life(denoised)

    print(f"{label}: OOS 2022-2026, frozen params (delta={delta:g}, obs_cov={obs_cov:g}, p={cfg['p']}, "
          f"z_entry={cfg['z_entry']}, z_exit={cfg['z_exit']})")
    print(f"  in-sample half_life was {hl:.1f}d -> OOS half_life={hl_oos:.1f}d, spread_std={denoised.std():.3f}")
    print(f"  OOS sharpe={bt.sharpe:.2f} max_dd={bt.max_drawdown:.2f} hit_rate={bt.hit_rate:.2f} n_trades={bt.n_trades}\n")
