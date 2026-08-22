# Paper Trading Protocol

Started: 2026-08-22. This document is written and frozen *before* live results
come in, specifically so evaluation criteria can't quietly shift once we see
how it's going — the same discipline the walk-forward validation depended on.

## Frozen configuration (do not retune during the evaluation period)

| Pair | Fit window | delta | obs_cov | FFT percentile | z_entry | z_exit | Capital |
|---|---|---|---|---|---|---|---|
| V / MA | 2015-01-01 to 2021-12-31 | 1e-6 | 10 | 70 | 1.0 | 0.5 | $250 |
| KO / PEP | 2015-01-01 to 2021-12-31 | 1e-5 | 10 | 70 | 1.0 | 0.25 | $250 |
| UNP / CSX | 2019-01-01 to 2023-12-31 | (fixed-window fit) | 10 | 70 | 1.5 | 0.5 | $250 |
| LUV / JBLU | 2019-01-01 to 2023-12-31 | (fixed-window fit) | 10 | 70 | 1.5 | 0.5 | $250 |

Total paper capital: $1000 ($250/pair, fixed allocation, not compounded).
zscore_window = 60 days for all pairs. Transaction cost model: 5bps/leg against
real notional (Y + beta*X), same as every backtest in this project.

**KO/PEP carries weaker statistical validation** than the other three (only
detected in expanding-window tests, not the fixed 5-year rolling window) —
watch it specifically, don't average its performance into the others without
noting this.

## What "paper trading" means here

Each day, `scripts/paper_trade.py` recomputes the full causal signal (Kalman
filter -> FFT denoise -> z-score -> entry/exit rule) from each pair's frozen fit
window through today, using real market data. Nothing here uses information
from after the current date — this is the same causal discipline as every
other phase of this project, just running forward in real time instead of
replayed against history. No real money or real brokerage orders are involved;
this logs what the strategy *would* do.

## Rules for the evaluation period (pre-committed)

1. **Do not change delta, obs_cov, percentile, z_entry, or z_exit for any pair
   during the evaluation window.** If a pair looks bad, that's data, not a
   reason to retune it mid-stream — retuning after seeing results is exactly
   the overfitting risk the walk-forward test was built to catch.
2. **Minimum evaluation period: 3 months** before drawing any conclusion.
   Shorter than that, daily noise dominates (see the Monte Carlo section of the
   strategy report — ~26% chance of a 1-month paper loss even if the strategy
   is working exactly as expected).
3. **Log every day it runs**, win or lose, to `reports/paper_trading_ledger.json`
   — no discarding bad stretches.
4. **Red flags to watch for** (would justify stopping early, not retuning):
   - Correlation to SPY drifting meaningfully away from ~0 over a sustained
     stretch (would mean the market-neutral property itself is breaking down)
   - A pair's hit rate or Sharpe collapsing to a level statistically
     inconsistent with its backtest distribution (check against the Monte
     Carlo bands in the strategy report before reacting to any single bad
     stretch)
   - Any single pair's cumulative paper loss exceeding roughly 2x its
     backtested max drawdown for a comparable period
5. **Go/no-go at 3 months**: compare realized Sharpe and correlation-to-SPY
   against the backtested ranges. If broadly consistent, continue paper
   trading toward a longer track record before considering real capital. If
   not, treat this as the paper-trading phase doing its job — catching a
   backtest/live gap before money was ever at risk.

## Running it

```sh
source .venv/bin/activate
python -m scripts.paper_trade
```

Safe to re-run any number of times per day (idempotent — recomputes fresh each
time rather than mutating incremental state, so there's no drift or corruption
risk from re-running). Intended cadence: once per day, after market close.
