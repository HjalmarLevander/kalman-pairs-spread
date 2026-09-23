# Kalman-Filtered Pairs Spread

A pairs-trading research project: model the spread between two cointegrated
assets as a dynamic, Kalman-filtered mean-reverting process, denoise it in
the frequency domain, and trade the denoised signal's deviation from its
mean — with every free parameter (pair choice, denoising threshold,
entry/exit rule, position size) empirically justified rather than guessed.

# Hypothesis / Intuition driving this project

If you take two cointegrated assets, we can assume they are mean reverting, 
or at least mean reverting w.r.t scaling. If we can break down the mean
reversion into wave patterns that can potentially be predictive. So we classify
our reversion by using a Kalman filter which maps out the spread between the two 
assets traded. Then on top of our filter, we perform a Fourier Transform. Further, 
to de-noise even more we only use the n-largest/most dominant waves. 

Now given cointegration, we can observe the magnitude of the spread, understand its
z-score compared to standard spread, and argue whether the gap will close or not.

If the z-score is unusually high (i.e. 1 - 2 sigma event) and the FFT suggest that it 
will close soon, we short the spread and vice versa.

Full methodology: [SPEC.md](SPEC.md). Full decision log, including every
dead end and rejected idea: [PROGRESS.md](PROGRESS.md).

# Results

Currently, this project is being tested through live paper trading; see LIVE_STATUS.md.

The backtest has shown a lot of potential. I tested the final strategy across four different pairs over a common out-of-sample period from January 2024 through August 2026. Over that period, the combined strategy generated roughly a 27% return.

What I found more interesting than the return itself was how differently the strategy behaved from the market. Over the same period, SPY returned about 66%, but the strategy's correlation with SPY was only -0.026. That is exactly what I would hope to see from a strategy built around relative movements between two assets rather than the direction of the market.

The combined portfolio also had a worryingly high Sharpe ratio of 3.83. Each of the four individual pairs produced a positive Sharpe as well. A backtest Sharpe this high makes me more suspicious, not less, which is a large part of why I moved the strategy into forward paper testing rather than treating the backtest as evidence that the strategy works.

Live paper trading has now been running for about five weeks on a $100,000 Alpaca paper account. Positions are dynamically sized at 10–20% of equity, with individual positions so far ranging from about $10.7k to $14.8k. Four closed trades have produced +$191.58 in realized P&L, while the four currently open positions are at approximately -$203 unrealized P&L. So far, correlation to SPY remains near zero at 0.107, while annualized volatility has been 0.88% compared with 9.3% for SPY.

Five weeks is obviously far too short to draw much from these numbers. The paper-trading protocol was set in advance with a minimum three-month evaluation window, so for now I am simply letting it run.

The full performance results, including the individual pairs, equity curves, and testing methodology, can be found below.

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
