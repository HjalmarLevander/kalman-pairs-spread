"""Phase 3: percentile-threshold sweep -- signal quality (3a) vs. trading
performance (3c), synthesized (3d). Extreme-event sensitivity (3b) is folded
into the same sweep via regime-split Sharpe from Phase 4's backtest.

Runs entirely on the Phase 1 Kalman spreads already on disk
(reports/phase1_kalman_*.csv) -- no network, no LLM calls.
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller

from src.phase0_pair_selection import SELECTION_END, SELECTION_START, load_prices
from src.phase2_fft_denoise import rolling_fft_denoise, variance_explained
from src.phase4_backtest import backtest, regime_split_dates, split_metrics_by_regime

REPORT_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")
PERCENTILE_GRID = (0, 50, 60, 70, 80, 90, 95)
Z_ENTRY_GRID = (1.0, 1.5, 2.0, 2.5)
Z_EXIT_GRID = (0.25, 0.5, 0.75)
FFT_WINDOW = 60
ZSCORE_WINDOW = 60


def half_life(spread: pd.Series) -> float:
    """OU mean-reversion half-life via AR(1) fit on the spread: ln(2)/-ln(phi)
    from spread_t - spread_{t-1} = -lambda*(spread_{t-1} - mean) + eps,
    fit by OLS. Returns inf if the fit implies no reversion (lambda <= 0).
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


def adf_pvalue(spread: pd.Series) -> float:
    s = spread.dropna()
    if len(s) < 30:
        return float("nan")
    return float(adfuller(s)[1])


def sweep_pair(pair: str) -> pd.DataFrame:
    path = os.path.join(REPORT_DIR, f"phase1_kalman_{pair}.csv")
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    raw_spread = df["spread"]
    returns_proxy = raw_spread.diff().fillna(0)
    extreme_mask = regime_split_dates(returns_proxy)

    # Real dollar notional of a one-unit spread position (Y_t + beta_t*X_t),
    # used to size transaction costs realistically -- charging bps against
    # the spread's own tiny numeric scale instead badly understates real
    # trading costs and was verified to inflate Sharpe to implausible levels.
    a, b = pair.split("_")
    prices = load_prices([a, b], SELECTION_START, SELECTION_END)
    notional = (prices[b] + df["beta"].reindex(prices.index) * prices[a]).abs()
    notional = notional.reindex(raw_spread.index)

    rows = []
    for p in PERCENTILE_GRID:
        denoised = raw_spread if p == 0 else rolling_fft_denoise(raw_spread, percentile=p, window=FFT_WINDOW)

        # 3a: signal quality
        ve = variance_explained(raw_spread, denoised)
        adf_p = adf_pvalue(denoised)
        hl = half_life(denoised)

        # 3c: trading performance -- best (z_entry, z_exit) at this p by Sharpe,
        # plus the full grid so 3d/parameter-stability can see the plateau
        best = None
        grid_results = []
        for z_entry in Z_ENTRY_GRID:
            for z_exit in Z_EXIT_GRID:
                if z_exit >= z_entry:
                    continue
                result = backtest(denoised, z_entry=z_entry, z_exit=z_exit, zscore_window=ZSCORE_WINDOW, notional=notional)
                regime = split_metrics_by_regime(result.daily_pnl, extreme_mask)
                row = dict(
                    percentile=p, z_entry=z_entry, z_exit=z_exit,
                    sharpe=result.sharpe, max_drawdown=result.max_drawdown,
                    hit_rate=result.hit_rate, n_trades=result.n_trades,
                    avg_duration=result.avg_trade_duration, turnover=result.turnover,
                    **regime,
                )
                grid_results.append(row)
                if best is None or (not np.isnan(result.sharpe) and (np.isnan(best["sharpe"]) or result.sharpe > best["sharpe"])):
                    best = row

        rows.append(dict(
            pair=pair, percentile=p,
            variance_explained=ve, adf_pvalue=adf_p, half_life_days=hl,
            best_z_entry=best["z_entry"], best_z_exit=best["z_exit"],
            best_sharpe=best["sharpe"], best_max_drawdown=best["max_drawdown"],
            best_hit_rate=best["hit_rate"], best_n_trades=best["n_trades"],
            best_turnover=best["turnover"],
            best_extreme_sharpe=best["extreme_sharpe"], best_normal_sharpe=best["normal_sharpe"],
            grid_sharpe_std=float(np.nanstd([r["sharpe"] for r in grid_results])),
        ))

    return pd.DataFrame(rows)


def main() -> None:
    all_rows = []
    for pair in ("V_MA", "KO_PEP"):
        summary = sweep_pair(pair)
        summary.to_csv(os.path.join(REPORT_DIR, f"phase3_sweep_{pair}.csv"), index=False)
        all_rows.append(summary)
        print(f"\n=== {pair} ===")
        print(summary.to_string(index=False))
    pd.concat(all_rows).to_csv(os.path.join(REPORT_DIR, "phase3_sweep_all.csv"), index=False)


if __name__ == "__main__":
    main()
