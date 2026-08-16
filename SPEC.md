# Strategy Spec: Kalman-Filtered Pairs Spread with Frequency-Domain Denoising

## Objective

Build and backtest a pairs-trading strategy where the spread between two correlated
assets is modeled as a dynamic (Kalman-filtered) mean-reverting process, denoised in
the frequency domain to separate genuine mean-reversion dynamics from noise, and
traded based on deviations of the denoised signal from its estimated mean. A key
deliverable is empirical justification (not a hardcoded guess) for every free
parameter: which tickers, which denoising threshold, which entry/exit rule.

---

## Phase 0: Ticker / Pair Selection (EDA)

Before any modeling, screen candidate pairs empirically rather than assuming a pair.

1. **Candidate universe**: define a pool of asset pairs with plausible economic
   linkage (same sector, supply chain relationship, ETF vs. constituent, commodity
   vs. producer, dual-listed shares, etc.).
2. **Correlation screen**: compute rolling correlation of returns over multiple
   lookback windows (e.g., 30/90/180/365 days). Flag pairs with consistently high
   correlation, not just high correlation in one lucky window.
3. **Cointegration screen**: for surviving pairs, run a formal cointegration test
   (e.g., Engle-Granger or Johansen) on price levels, not just a correlation-of-returns
   check — correlation and cointegration are different properties and both matter here.
4. **Stability of relationship**: check whether the static OLS hedge ratio drifts a
   lot over time (rolling-window beta estimate). Pairs with wildly unstable beta are
   *exactly* the case the Kalman filter is meant to handle, but extreme instability may
   indicate the relationship isn't structurally sound at all — distinguish "beta drifts
   smoothly" from "beta is essentially uncorrelated with itself over time."
5. **Output of this phase**: a ranked shortlist of pairs with correlation stats,
   cointegration test p-values, and a qualitative note on beta stability, to select the
   pair(s) taken into Phase 1.

---

## Phase 1: Dynamic Hedge Ratio via Kalman Filter

Model the relationship between assets X and Y as a state-space system:

- **State equation**: `beta_t = beta_{t-1} + w_t`  (beta follows a random walk; w_t ~ process noise)
- **Observation equation**: `Y_t = beta_t * X_t + v_t`  (v_t ~ observation noise)

Run a standard (or extended, if nonlinear terms are added later) Kalman filter to
produce a time-varying estimate `beta_t` at every timestep, along with the filter's
own uncertainty estimate for beta.

- **Output**: filtered `beta_t` series, and the raw spread `spread_t = Y_t - beta_t * X_t`.
- **Tunable**: process noise variance and observation noise variance (these control
  how fast beta is allowed to adapt vs. how much it's smoothed) — these should be fit
  or grid-searched, not guessed.

---

## Phase 2: Frequency-Domain Denoising

Treat `spread_t` as a noisy, quasi-periodic signal and denoise it via FFT-based
power thresholding.

1. Compute the FFT of `spread_t` (over a rolling window, since the relationship is
   non-stationary over the long run).
2. Compute the power spectrum: `power_f = |FFT_f|^2` for each frequency bin.
3. Choose a **percentile threshold** `p` on the power distribution; keep only
   frequency components with power above the p-th percentile, zero out the rest.
4. Inverse FFT the thresholded spectrum to reconstruct a denoised time-domain
   signal, `spread_denoised_t`.
5. **Note for later comparison**: this FFT approach assumes the retained components
   behave like stable sinusoids within the window. As an alternative/robustness check,
   the same denoising goal can be approached via Singular Spectrum Analysis (Hankel
   matrix embedding + SVD + diagonal averaging), which does not assume a fixed
   sinusoidal basis. Both should ultimately be compared empirically on this data
   rather than assumed equivalent.

---

## Phase 3: Percentile Threshold Selection — Signal Quality vs. Trading Performance

This is the core empirical question of the project: which percentile `p` is "best,"
and best by what criterion. Two different notions of "best" must be evaluated
separately, then compared, because they will not necessarily agree.

### 3a. Signal-quality sweep (independent of trading)

For a grid of percentiles (e.g., 50, 60, 70, 80, 90, 95):
- Compute variance explained / reconstruction error of `spread_denoised_t` vs. raw `spread_t`.
- Run a stationarity test (e.g., ADF) on the denoised spread — does higher `p` make
  the series more convincingly mean-reverting?
- Estimate mean-reversion half-life (e.g., via Ornstein-Uhlenbeck fit) of the
  denoised spread at each `p`.

### 3b. Extreme-event sensitivity

A sudden jump or regime break (earnings surprise, correlation breakdown, macro
shock) is broadband in frequency space — it shows up spread across many
frequencies, not concentrated in a few. As `p` increases:
- More of that broadband, transient content gets filtered out.
- The signal becomes smoother and more textbook-mean-reverting, but increasingly
  lags or misses genuine regime shifts.

To quantify this directly:
- Identify known large-move dates/windows for the selected tickers (earnings dates,
  known macro shocks, or statistically-flagged large-move days).
- Split history into "extreme" vs. "normal" regime windows.
- For each `p`, measure how much power is filtered out specifically *during* extreme
  windows vs. normal windows. A threshold that disproportionately strips power during
  extreme windows is removing information, not just noise.

### 3c. Trading-performance sweep

For the same grid of `p`, run the full backtest (Phase 4) and record:
- Sharpe ratio, max drawdown, hit rate, average trade duration, turnover
- Performance broken out separately for "extreme" vs. "normal" regime windows
  (from 3b), since a threshold that performs well overall may be doing so only in
  calm periods.

### 3d. Synthesis

Plot the 3a/3b signal-quality metrics and the 3c performance metrics together
against `p`. The percentile that maximizes signal smoothness/stationarity will not
necessarily maximize Sharpe — a signal too smooth reacts too slowly to real regime
changes. The point where the two curves diverge is the actionable output: it
indicates how much of the filtered "noise" was actually informative regime-shift
content worth trading around, rather than discarding.

---

## Phase 4: Trade Signal & Backtest

1. Compute a rolling z-score of `spread_denoised_t` relative to its own rolling
   mean/std (or relative to the Kalman filter's implied equilibrium).
2. Define entry rule (e.g., enter when |z| exceeds threshold `z_entry`) and exit
   rule (e.g., exit on reversion to `z_exit`, or after max holding period, or on
   stop-loss).
3. Account for transaction costs and realistic position sizing (e.g., dollar-neutral
   using the current `beta_t` for hedge ratio).
4. Backtest across the full history and across the extreme/normal regime split
   defined above.
5. Report standard performance metrics plus stability across different `p` and
   `(z_entry, z_exit)` combinations — avoid selecting a single overfit combination;
   look for a stable plateau of good performance across nearby parameter values.

---

## Deliverables

1. Ranked shortlist of candidate pairs with correlation/cointegration diagnostics (Phase 0).
2. Kalman filter implementation with fitted/tuned process & observation noise (Phase 1).
3. FFT denoising pipeline with percentile thresholding (Phase 2).
4. Signal-quality sweep results (3a/3b) and trading-performance sweep results (3c),
   plotted together (3d).
5. Final backtest report on the selected pair(s) and parameters, including
   regime-split performance and a parameter-stability check.
