"""One-off experiment (not a new numbered phase): reruns Phase 1 with the
half-life-floored noise-parameter fit, then Phase 2/3/4 on top, to test
whether constraining Kalman noise params away from the near-degenerate MLE
regime actually produces a profitable strategy -- rather than just
asserting it should in the writeup.
"""
import numpy as np
import pandas as pd

from src.mean_reversion import half_life
from src.phase0_pair_selection import SELECTION_END, SELECTION_START, load_prices
from src.phase1_kalman_hedge_ratio import fit_noise_params_with_half_life_floor, run_kalman_filter
from src.phase2_fft_denoise import rolling_fft_denoise, variance_explained
from src.phase4_backtest import backtest, regime_split_dates, split_metrics_by_regime
from statsmodels.tsa.stattools import adfuller

MIN_HALF_LIFE = 10.0
PERCENTILE_GRID = (0, 50, 70, 90)
Z_ENTRY_GRID = (1.0, 1.5, 2.0, 2.5)
Z_EXIT_GRID = (0.25, 0.5, 0.75)

pairs = {"V_MA": ("V", "MA"), "KO_PEP": ("KO", "PEP")}
tickers = sorted({t for p in pairs.values() for t in p})
prices = load_prices(tickers, SELECTION_START, SELECTION_END)

for label, (a, b) in pairs.items():
    x, y = prices[a], prices[b]
    delta, obs_cov, ll, hl = fit_noise_params_with_half_life_floor(x, y, min_half_life_days=MIN_HALF_LIFE)
    result = run_kalman_filter(label, x, y, delta, obs_cov)
    raw_spread = result.spread
    notional = (y + result.beta * x).abs().reindex(raw_spread.index)
    returns_proxy = raw_spread.diff().fillna(0)
    extreme_mask = regime_split_dates(returns_proxy)

    print(f"\n=== {label} (delta={delta:g}, obs_cov={obs_cov:g}, half_life={hl:.1f}d, "
          f"spread_std={raw_spread.std():.3f}) ===")

    best_overall = None
    for p in PERCENTILE_GRID:
        denoised = raw_spread if p == 0 else rolling_fft_denoise(raw_spread, percentile=p, window=60)
        ve = variance_explained(raw_spread, denoised)
        s = denoised.dropna()
        adf_p = float(adfuller(s)[1]) if len(s) >= 30 else float("nan")
        hl_denoised = half_life(denoised)

        best = None
        for z_entry in Z_ENTRY_GRID:
            for z_exit in Z_EXIT_GRID:
                if z_exit >= z_entry:
                    continue
                res = backtest(denoised, z_entry=z_entry, z_exit=z_exit, zscore_window=60, notional=notional)
                regime = split_metrics_by_regime(res.daily_pnl, extreme_mask)
                row = dict(z_entry=z_entry, z_exit=z_exit, sharpe=res.sharpe, max_dd=res.max_drawdown,
                           hit_rate=res.hit_rate, n_trades=res.n_trades, **regime)
                if best is None or (not np.isnan(res.sharpe) and (np.isnan(best["sharpe"]) or res.sharpe > best["sharpe"])):
                    best = row
        print(f"  p={p:3d} var_explained={ve:.3f} adf_p={adf_p:.4f} half_life={hl_denoised:.1f}d "
              f"| best sharpe={best['sharpe']:.2f} max_dd={best['max_dd']:.2f} hit_rate={best['hit_rate']:.2f} "
              f"n_trades={best['n_trades']} (z_entry={best['z_entry']}, z_exit={best['z_exit']}) "
              f"extreme_sharpe={best['extreme_sharpe']:.2f} normal_sharpe={best['normal_sharpe']:.2f}")
        if best_overall is None or (not np.isnan(best["sharpe"]) and (np.isnan(best_overall["sharpe"]) or best["sharpe"] > best_overall["sharpe"])):
            best_overall = dict(best, percentile=p)

    print(f"  -> best overall: p={best_overall['percentile']} sharpe={best_overall['sharpe']:.2f}")
