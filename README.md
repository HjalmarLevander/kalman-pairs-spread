# Kalman-Filtered Pairs Spread

A pairs-trading research project: model the spread between two cointegrated
assets as a dynamic, Kalman-filtered mean-reverting process, denoise it in
the frequency domain, and trade the denoised signal's deviation from its
mean — with every free parameter (pair choice, denoising threshold,
entry/exit rule, position size) empirically justified rather than guessed.

Full methodology: [SPEC.md](SPEC.md). Full decision log, including every
dead end and rejected idea: [PROGRESS.md](PROGRESS.md).

## Status: paper trading, in progress (started 2026-08-22)

**Live status (auto-updated daily): [LIVE_STATUS.md](LIVE_STATUS.md)**

This is **not** a finished, validated, profitable strategy yet — it's an
active research project currently in its paper-trading evaluation phase,
running on a real (simulated-money) Alpaca paper broker. Numbers below are
backtest/walk-forward results; live paper-trading results are too early
(days, not months) to draw conclusions from and are deliberately not
reported here as a track record. See
[PAPER_TRADING_PROTOCOL.md](PAPER_TRADING_PROTOCOL.md) for the pre-committed
evaluation criteria and minimum 3-month window before any go/no-go decision
on real capital.

## What it does

1. **Pair selection** (`src/phase0_pair_selection.py`) — screens candidate
   pairs by rolling correlation, cointegration (Engle-Granger), and
   hedge-ratio stability. Re-validated via walk-forward testing across
   independent, non-overlapping time windows — not just a single best-fit
   window — to guard against selection bias. **Validated book: V/MA,
   KO/PEP, UNP/CSX, LUV/JBLU.**
2. **Dynamic hedge ratio** (`src/phase1_kalman_hedge_ratio.py`) — a Kalman
   filter (not smoother — smoothing would leak future data) tracks the
   time-varying hedge ratio between each pair. Noise parameters are
   grid-searched by log-likelihood, constrained away from a near-degenerate
   regime that maximizes fit but produces an untradeable, too-fast-reverting
   residual (a real bug caught and fixed mid-project — see PROGRESS.md).
3. **Frequency-domain denoising** (`src/phase2_fft_denoise.py`) — a rolling,
   strictly causal short-time FFT separates genuine mean-reversion dynamics
   from noise in the spread.
4. **Backtest + trading rule** (`src/phase4_backtest.py`) — z-score
   entry/exit on the denoised spread, transaction costs charged against real
   traded notional (not the spread's own numeric scale — an early version of
   this bug inflated Sharpe ~1000x before being caught).
5. **Live paper execution** (`scripts/alpaca_paper_trade.py`) — runs the
   full causal pipeline daily against real market data and places real
   orders on an Alpaca paper account, sized at 10-20% of account equity per
   trade scaled by entry conviction (z-score magnitude).

## What didn't work (kept, not hidden)

- **Stop-loss exits**: tested, made the worst trades *larger*, not smaller
  (repeated whipsaw re-entry during trending, non-reverting stretches).
  Rejected.
- **ML confidence-based position sizing**: trained a random forest on
  entry-time features to predict trade win/loss, sized positions by
  predicted confidence. Out-of-sample AUC 0.473 — worse than a coin flip.
  An apparent P&L improvement from confidence-weighting turned out to be the
  model mostly detecting *which pair* a trade belonged to, not real
  per-trade skill (confirmed via a within-pair permutation null test).
  Rejected — not enough trade history yet for this approach to have a shot.
- **Two pairs (KMB/PG, UNP/CSX on an earlier universe) that looked great on
  a single validation split**: didn't survive walk-forward testing across
  independent time windows. Treated as a selection-bias artifact, not
  edge, and dropped.

## Results (backtest / walk-forward, not live)

| pair | OOS Sharpe (2 independent folds) | avg trade duration |
|---|---|---|
| V/MA | 1.38 / 1.77 | ~9 days |
| KO/PEP | 0.64 / 2.20 | ~9 days |
| UNP/CSX | 1.97 / 2.57 | ~9 days |
| LUV/JBLU | 0.97 / 1.92 | ~10 days |

Full write-up with methodology, worked examples, and charts:
`reports/strategy_explainer.html` / `reports/strategy_report.html` (open
locally — not hosted).

## Running it

```sh
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest tests/                          # 29+ tests across all phases
python -m scripts.paper_trade          # log-only "what would happen" v1 baseline
python -m scripts.alpaca_paper_trade   # live paper-broker execution, v2 track (needs .env with Alpaca keys)
```
