"""Walk-forward validation: re-run PAIR SELECTION (not just parameter
fitting) using only data available at each point in time, then test purely
forward on data that selection never touched. Repeated across multiple
non-overlapping folds.

This directly targets the concern raised after the 4-pair result: KMB/PG and
UNP/CSX were picked as the best 2 of 36 candidates screened on one static
2015-2021 window, then OOS-tested on 2022-2026 with frozen params. That's
real, but the *selection* itself was made by picking winners from a large
pool on a single window -- a second, separate source of overfitting risk
that a single OOS test doesn't fully rule out. Walk-forward re-selection on
independent folds is the actual test of whether "screen many pairs, keep
the winners" generalizes, or whether it's a one-time lucky draw.

No-leakage discipline, explicit:
  - Pair screening (correlation, cointegration, beta stability) for fold N
    uses ONLY data in [start, train_end_N].
  - Kalman noise-parameter fitting (half-life floor) for fold N uses ONLY
    data in [start, train_end_N] -- same window as screening, never the
    fold's test window.
  - The Kalman filter / FFT denoiser / z-score DO run continuously across
    [start, test_end_N] when producing the tradeable signal (that's not
    leakage -- both are strictly causal, using only past-up-to-t prices,
    and prices before test_start already existed in the real world by
    test_start; the boundary that matters is that no TEST-period price
    informed pair selection or parameter fitting, which it doesn't here).
    This also removes the "cold start" artifact flagged as a limitation in
    the original OOS check.
  - Trading-performance metrics for fold N are computed ONLY over
    [test_start_N, test_end_N] daily PnL, even though the running signal
    was computed over the longer window.
"""
import warnings

import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import coint

warnings.filterwarnings("ignore", category=DeprecationWarning)

from src.phase0_pair_selection import (
    CANDIDATE_PAIRS,
    cointegration_test,
    load_prices,
    rolling_correlation,
    rolling_hedge_ratio_stability,
    CORRELATION_CONSISTENCY_MIN,
)
from src.phase1_kalman_hedge_ratio import fit_noise_params_with_half_life_floor, run_kalman_filter
from src.phase2_fft_denoise import rolling_fft_denoise
from src.phase4_backtest import backtest
from src.mean_reversion import half_life

UNIVERSE_START = "2015-01-01"
FOLDS = [
    # (train_end, test_end) -- train always starts at UNIVERSE_START (expanding window)
    ("2019-12-31", "2021-12-31"),
    ("2021-12-31", "2023-12-31"),
    ("2023-12-31", "2026-08-01"),
]
N_CANDIDATES = len(CANDIDATE_PAIRS)
BONFERRONI_ALPHA = 0.05 / N_CANDIDATES
RAW_ALPHA = 0.05


def screen_pairs(train_start: str, train_end: str) -> list[tuple[str, str, float]]:
    """Returns (a, b, coint_pvalue) for every candidate pair that clears
    correlation consistency + raw cointegration p < 0.05 on [train_start,
    train_end] only. This is the exact same logic as Phase 0, re-run fresh
    per fold on a training-only window.
    """
    tickers = sorted({t for pair in CANDIDATE_PAIRS for t in pair})
    prices = load_prices(tickers, train_start, train_end)

    passed = []
    for a, b in CANDIDATE_PAIRS:
        if a not in prices.columns or b not in prices.columns:
            continue
        x, y = prices[a].dropna(), prices[b].dropna()
        if len(x) < 100 or len(y) < 100:
            continue
        corr = rolling_correlation(x, y)
        corr_vals = [v for v in corr.values() if not np.isnan(v)]
        consistent = bool(corr_vals) and all(v >= CORRELATION_CONSISTENCY_MIN for v in corr_vals)
        if not consistent:
            continue
        pvalue = cointegration_test(x, y)
        if np.isnan(pvalue) or pvalue >= RAW_ALPHA:
            continue
        _, beta_cv, _ = rolling_hedge_ratio_stability(x, y)
        if not np.isnan(beta_cv) and beta_cv > 1.0:
            continue  # unstable beta, looks like noise not structure
        passed.append((a, b, pvalue))
    return sorted(passed, key=lambda r: r[2])


def fold_test(train_start, train_end, test_end, pair):
    a, b = pair
    fit_prices = load_prices([a, b], train_start, train_end)
    if a not in fit_prices.columns or b not in fit_prices.columns:
        return None
    delta, obs_cov, _, hl_train = fit_noise_params_with_half_life_floor(
        fit_prices[a], fit_prices[b], min_half_life_days=10.0
    )

    full_prices = load_prices([a, b], train_start, test_end)
    if a not in full_prices.columns or b not in full_prices.columns:
        return None
    label = f"{a}_{b}"
    result = run_kalman_filter(label, full_prices[a], full_prices[b], delta, obs_cov)
    denoised = rolling_fft_denoise(result.spread, percentile=70, window=60)
    notional = (full_prices[b] + result.beta * full_prices[a]).abs().reindex(result.spread.index)

    bt = backtest(denoised, z_entry=1.5, z_exit=0.5, zscore_window=60, notional=notional)

    test_start = pd.Timestamp(train_end) + pd.Timedelta(days=1)
    test_pnl = bt.daily_pnl.loc[test_start:test_end]
    if test_pnl.std() and test_pnl.std() > 0 and len(test_pnl.dropna()) > 20:
        test_sharpe = float(test_pnl.mean() / test_pnl.std() * np.sqrt(252))
    else:
        test_sharpe = float("nan")

    test_trades = [t for t in bt.trades if t.entry_date >= test_start]
    hit_rate = float(np.mean([t.pnl > 0 for t in test_trades])) if test_trades else float("nan")

    return dict(
        pair=f"{a}/{b}", train_half_life=hl_train, delta=delta, obs_cov=obs_cov,
        test_sharpe=test_sharpe, test_n_trades=len(test_trades), test_hit_rate=hit_rate,
        test_max_dd=float(test_pnl.cumsum().min()) if len(test_pnl.dropna()) else float("nan"),
    )


def main():
    all_results = []
    for fold_i, (train_end, test_end) in enumerate(FOLDS, start=1):
        print(f"\n{'='*70}\nFOLD {fold_i}: train=[{UNIVERSE_START}, {train_end}]  test=({train_end}, {test_end}]")
        candidates = screen_pairs(UNIVERSE_START, train_end)
        bonferroni_survivors = [c for c in candidates if c[2] < BONFERRONI_ALPHA]
        print(f"  {len(candidates)}/{N_CANDIDATES} pairs pass raw p<0.05 cointegration + correlation + beta-stability screen")
        print(f"  {len(bonferroni_survivors)}/{N_CANDIDATES} survive Bonferroni correction (p<{BONFERRONI_ALPHA:.5f})")
        for a, b, p in candidates:
            tag = "BONFERRONI-SURVIVOR" if p < BONFERRONI_ALPHA else ""
            print(f"    {a}/{b}: coint_p={p:.4f} {tag}")

        for a, b, p in candidates:
            r = fold_test(UNIVERSE_START, train_end, test_end, (a, b))
            if r is None:
                continue
            r["fold"] = fold_i
            r["coint_pvalue_train"] = p
            r["bonferroni_survivor"] = p < BONFERRONI_ALPHA
            all_results.append(r)
            print(f"    -> OOS test_sharpe={r['test_sharpe']:.2f} trades={r['test_n_trades']} hit_rate={r['test_hit_rate']:.2f}")

    df = pd.DataFrame(all_results)
    df.to_csv("reports/walk_forward_results.csv", index=False)
    print(f"\n{'='*70}\nSaved {len(df)} fold-pair results to reports/walk_forward_results.csv")

    print("\nPairs appearing in >1 fold, with per-fold Sharpe:")
    for pair, g in df.groupby("pair"):
        if len(g) > 1:
            sharpes = ", ".join(f"fold{int(f)}={s:.2f}" for f, s in zip(g["fold"], g["test_sharpe"]))
            print(f"  {pair}: {sharpes}")

    print("\nPairs appearing in only 1 fold (survived screening once, not repeatedly):")
    for pair, g in df.groupby("pair"):
        if len(g) == 1:
            row = g.iloc[0]
            print(f"  {pair}: fold{int(row['fold'])} only, test_sharpe={row['test_sharpe']:.2f}")


if __name__ == "__main__":
    main()
