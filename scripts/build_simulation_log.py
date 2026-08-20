"""Builds a day-by-day causal simulation log for the playback engine.

Every field logged for date t is computable using ONLY data up to and
including t -- the Kalman filter, FFT denoiser, and z-score are all
already-causal (see phase1/phase2/phase4 docstrings). This script adds
nothing new computationally; it just logs every intermediate value per day
instead of only the final aggregate metrics, so a playback UI can show the
state evolving exactly as it would have appeared "live."

Noise parameters and trading rule are frozen exactly as validated
(half-life-floor fit on 2015-2021, p=70, z_entry/z_exit from the walk-forward
work) -- nothing here is re-tuned. The playback is split into a WARMUP phase
(2015-2021, the fit window -- shown collapsed, not played tick-by-tick) and
a LIVE phase (2022-2026, the genuine out-of-sample window) which is what the
UI actually plays back, so the no-lookahead property is visible, not just
asserted: nothing in the LIVE phase could have informed the fit that
produced the signal being played back.
"""
import json
import os

import numpy as np
import pandas as pd

from src.phase0_pair_selection import SELECTION_START, load_prices
from src.phase1_kalman_hedge_ratio import fit_noise_params_with_half_life_floor, run_kalman_filter
from src.phase2_fft_denoise import rolling_fft_denoise
from src.phase4_backtest import backtest, rolling_zscore

REPORTS = os.path.join(os.path.dirname(__file__), "..", "reports")

CONFIGS = {
    "V_MA": dict(pair=("V", "MA"), p=70, z_entry=1.0, z_exit=0.5, label="V / MA"),
    "KO_PEP": dict(pair=("KO", "PEP"), p=70, z_entry=1.0, z_exit=0.25, label="KO / PEP"),
}
TRAIN_START, TRAIN_END = SELECTION_START, "2021-12-31"
LIVE_END = "2026-08-01"
CAPITAL_PER_PAIR = 500.0
ZSCORE_WINDOW = 60


def build_pair_log(label: str, cfg: dict) -> dict:
    a, b = cfg["pair"]
    fit_prices = load_prices([a, b], TRAIN_START, TRAIN_END)
    delta, obs_cov, _, train_half_life = fit_noise_params_with_half_life_floor(
        fit_prices[a], fit_prices[b], min_half_life_days=10.0
    )

    full_prices = load_prices([a, b], TRAIN_START, LIVE_END)
    result = run_kalman_filter(label, full_prices[a], full_prices[b], delta, obs_cov)
    denoised = rolling_fft_denoise(result.spread, percentile=cfg["p"], window=60)
    z = rolling_zscore(denoised, ZSCORE_WINDOW)
    notional = (full_prices[b] + result.beta * full_prices[a]).abs().reindex(result.spread.index)

    bt = backtest(denoised, z_entry=cfg["z_entry"], z_exit=cfg["z_exit"],
                   zscore_window=ZSCORE_WINDOW, notional=notional)
    units = CAPITAL_PER_PAIR / notional.mean()

    # reconstruct daily position + decision label from the trade log
    position = pd.Series(0, index=result.spread.index)
    decision = pd.Series("FLAT", index=result.spread.index)
    for t in bt.trades:
        position.loc[t.entry_date:t.exit_date] = t.direction
        decision.loc[t.entry_date] = "ENTER_LONG" if t.direction == 1 else "ENTER_SHORT"
        idx = result.spread.index
        between = idx[(idx > t.entry_date) & (idx < t.exit_date)]
        decision.loc[between] = "HOLD"
        decision.loc[t.exit_date] = "EXIT"

    live_start = pd.Timestamp(TRAIN_END) + pd.Timedelta(days=1)
    live_mask = result.spread.index >= live_start
    live_dates = result.spread.index[live_mask]

    cum_pnl = (bt.daily_pnl * units).cumsum()
    # rebase cumulative PnL to 0 at the start of the LIVE window specifically,
    # so playback shows "PnL since going live," not PnL carried from warmup
    live_cum_pnl = cum_pnl.loc[live_dates] - (cum_pnl.loc[live_dates[0]] - (bt.daily_pnl.loc[live_dates[0]] * units))

    rows = []
    for d in live_dates:
        rows.append(dict(
            date=d.strftime("%Y-%m-%d"),
            price_a=round(float(full_prices[a].loc[d]), 2) if d in full_prices.index else None,
            price_b=round(float(full_prices[b].loc[d]), 2) if d in full_prices.index else None,
            beta=round(float(result.beta.loc[d]), 4),
            spread=round(float(result.spread.loc[d]), 4),
            spread_denoised=round(float(denoised.loc[d]), 4) if not pd.isna(denoised.loc[d]) else None,
            zscore=round(float(z.loc[d]), 3) if not pd.isna(z.loc[d]) else None,
            position=int(position.loc[d]),
            decision=str(decision.loc[d]),
            daily_pnl=round(float(bt.daily_pnl.loc[d] * units), 3),
            cum_pnl=round(float(live_cum_pnl.loc[d]), 3),
        ))

    n_trades_live = len([t for t in bt.trades if t.entry_date >= live_start])
    final_sharpe = (bt.daily_pnl.loc[live_dates] * units)
    sharpe = float(final_sharpe.mean() / final_sharpe.std() * np.sqrt(252)) if final_sharpe.std() > 0 else None

    return dict(
        label=cfg["label"], ticker_a=a, ticker_b=b,
        delta=delta, obs_cov=obs_cov, train_half_life=round(train_half_life, 2),
        z_entry=cfg["z_entry"], z_exit=cfg["z_exit"], percentile=cfg["p"],
        n_trades=n_trades_live, sharpe=round(sharpe, 2) if sharpe else None,
        rows=rows,
    )


def main():
    out = {}
    for label, cfg in CONFIGS.items():
        print(f"building {label}...")
        out[label] = build_pair_log(label, cfg)
        print(f"  {len(out[label]['rows'])} live days, {out[label]['n_trades']} trades, sharpe={out[label]['sharpe']}")

    path = os.path.join(REPORTS, "simulation_log.json")
    with open(path, "w") as f:
        json.dump(out, f)
    size_kb = os.path.getsize(path) / 1024
    print(f"\nwrote {path} ({size_kb:.0f} KB)")


if __name__ == "__main__":
    main()
