"""Daily paper-trading runner. See PAPER_TRADING_PROTOCOL.md for the rules
this operates under -- frozen parameters, no retuning, minimum 3-month
evaluation window.

Recomputes the full causal signal (Kalman filter -> FFT denoise -> z-score ->
entry/exit) from each pair's frozen fit window through today, using real
market data. Idempotent: safe to re-run any number of times, since it always
recomputes from scratch rather than mutating incremental state. Appends
today's snapshot to reports/paper_trading_ledger.json and prints a clear
"what would happen today" summary. No real orders are placed anywhere --
this only logs what the strategy would do.
"""
import json
import os
from datetime import date

import numpy as np
import pandas as pd

from src.phase0_pair_selection import load_prices
from src.phase1_kalman_hedge_ratio import fit_noise_params_with_half_life_floor, run_kalman_filter
from src.phase2_fft_denoise import rolling_fft_denoise
from src.phase4_backtest import backtest, rolling_zscore

REPORTS = os.path.join(os.path.dirname(__file__), "..", "reports")
LEDGER_PATH = os.path.join(REPORTS, "paper_trading_ledger.json")

CONFIGS = {
    "V_MA":    dict(pair=("V", "MA"),     fit_start="2015-01-01", fit_end="2021-12-31", p=70, z_entry=1.0, z_exit=0.5,  label="V / MA"),
    "KO_PEP":  dict(pair=("KO", "PEP"),   fit_start="2015-01-01", fit_end="2021-12-31", p=70, z_entry=1.0, z_exit=0.25, label="KO / PEP"),
    "UNP_CSX": dict(pair=("UNP", "CSX"),  fit_start="2019-01-01", fit_end="2023-12-31", p=70, z_entry=1.5, z_exit=0.5,  label="UNP / CSX"),
    "LUV_JBLU":dict(pair=("LUV", "JBLU"), fit_start="2019-01-01", fit_end="2023-12-31", p=70, z_entry=1.5, z_exit=0.5,  label="LUV / JBLU"),
}
CAPITAL_PER_PAIR = 250.0
PAPER_TRADING_START = "2026-08-22"  # frozen once, do not move


def build_pair_series(label, cfg, today):
    a, b = cfg["pair"]
    fit_prices = load_prices([a, b], cfg["fit_start"], cfg["fit_end"])
    delta, obs_cov, _, hl = fit_noise_params_with_half_life_floor(
        fit_prices[a], fit_prices[b], min_half_life_days=10.0
    )
    full_prices = load_prices([a, b], cfg["fit_start"], today)
    result = run_kalman_filter(label, full_prices[a], full_prices[b], delta, obs_cov)
    denoised = rolling_fft_denoise(result.spread, percentile=cfg["p"], window=60)
    z = rolling_zscore(denoised, 60)
    notional = (full_prices[b] + result.beta * full_prices[a]).abs().reindex(result.spread.index)
    bt = backtest(denoised, z_entry=cfg["z_entry"], z_exit=cfg["z_exit"], zscore_window=60, notional=notional)
    units = CAPITAL_PER_PAIR / notional.mean()

    position = pd.Series(0, index=result.spread.index)
    decision = pd.Series("FLAT", index=result.spread.index)
    for t in bt.trades:
        position.loc[t.entry_date:t.exit_date] = t.direction
        decision.loc[t.entry_date] = "ENTER_LONG" if t.direction == 1 else "ENTER_SHORT"
        idx = result.spread.index
        between = idx[(idx > t.entry_date) & (idx < t.exit_date)]
        decision.loc[between] = "HOLD"
        decision.loc[t.exit_date] = "EXIT"

    paper_mask = result.spread.index >= pd.Timestamp(PAPER_TRADING_START)
    paper_dates = result.spread.index[paper_mask]
    cum_pnl = (bt.daily_pnl * units).cumsum()
    baseline = cum_pnl.loc[paper_dates[0]] - (bt.daily_pnl.loc[paper_dates[0]] * units) if len(paper_dates) else 0.0

    rows = []
    for d in paper_dates:
        rows.append(dict(
            date=d.strftime("%Y-%m-%d"),
            price_a=round(float(full_prices[a].loc[d]), 2),
            price_b=round(float(full_prices[b].loc[d]), 2),
            beta=round(float(result.beta.loc[d]), 4),
            spread=round(float(result.spread.loc[d]), 4),
            spread_denoised=round(float(denoised.loc[d]), 4) if not pd.isna(denoised.loc[d]) else None,
            zscore=round(float(z.loc[d]), 3) if not pd.isna(z.loc[d]) else None,
            position=int(position.loc[d]),
            decision=str(decision.loc[d]),
            daily_pnl=round(float(bt.daily_pnl.loc[d] * units), 3),
            cum_pnl=round(float(cum_pnl.loc[d] - baseline), 3),
        ))
    return rows


def main():
    today = date.today().isoformat()
    ledger = {}
    print(f"Paper trading run: {today}  (evaluation started {PAPER_TRADING_START})\n")

    for label, cfg in CONFIGS.items():
        rows = build_pair_series(label, cfg, today)
        ledger[label] = dict(label=cfg["label"], config=cfg, rows=rows)

        if not rows:
            print(f"{cfg['label']}: no paper-trading days yet")
            continue
        latest = rows[-1]
        print(f"{cfg['label']:12s} {latest['date']}  z={latest['zscore']:>6}  "
              f"position={latest['position']:+d}  decision={latest['decision']:12s}  "
              f"daily_pnl=${latest['daily_pnl']:+.2f}  cum_pnl=${latest['cum_pnl']:+.2f}")

    combined_cum = sum(v["rows"][-1]["cum_pnl"] for v in ledger.values() if v["rows"])
    print(f"\nCombined paper P&L since {PAPER_TRADING_START}: ${combined_cum:+.2f} (on $1000)")

    with open(LEDGER_PATH, "w") as f:
        json.dump(ledger, f)
    print(f"\nwrote {LEDGER_PATH}")


if __name__ == "__main__":
    main()
