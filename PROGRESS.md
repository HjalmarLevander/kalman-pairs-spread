# Progress Tracker

Drive each phase through `@robin` in VS Code (Planner → Draft → Engineer → Critic →
Runner). Check off phases as Robin lands verified, tested code for them. See
SPEC.md for full detail on each phase.

- [x] Phase 0 — Ticker/pair selection (correlation + cointegration + beta-stability screen)
- [x] Phase 1 — Kalman filter dynamic hedge ratio
- [x] Phase 2 — FFT denoising pipeline
- [x] Phase 3a — Signal-quality sweep across percentile p
- [x] Phase 3b — Extreme-event sensitivity analysis (regime-split Sharpe folded into the 3c sweep)
- [x] Phase 3c — Trading-performance sweep across percentile p
- [x] Phase 3d — Synthesis (see HTML report)
- [x] Phase 4 — Trade signal + full backtest, parameter stability check

## Notes / decisions log

(Append dated notes here as decisions get made — e.g. which pair was selected in
Phase 0 and why, which noise-variance values Phase 1 converged on, etc. Keep this
file as the running source of truth; don't let context live only in chat history.)

## 2026-08-17 — Phase 0 run

Robin's backend hit `credit balance too low` on the Anthropic account behind `ant
auth`, so Phase 0 was implemented directly (not through the `@robin` pipeline) using
Robin's already-approved plan/draft as the design guide: `src/phase0_pair_selection.py`
+ `tests/test_phase0.py`, all local compute, no LLM calls. Robin's Engineer
`max_tokens` cap was also bumped 16000→24000 in `~/AgenticCoding/backend/agents/engineer.py`
for when credits are restored and later phases run through `@robin` again.

SELECTION_START/END = 2015-01-01 to 2021-12-31 (no-lookahead boundary — do not widen
without treating it as a new, separate out-of-sample rerun).

Shortlist (`reports/phase0_pair_shortlist.csv`), ranked best-first:
1. **SPY/VOO** — corr ~0.999 across all windows, coint p=0.006, beta_cv=0.002 (near-perfectly
   stable ~0.92 hedge ratio). Almost too clean — these are two S&P 500 index funds, so this
   is closer to a tracking-error trade than a genuine economically-linked pairs trade. Good
   sanity-check pair, maybe not the most interesting one to build the strategy around.
2. **V/MA** — corr ~0.85-0.89, coint p=0.007, beta_cv=0.35 (moderate drift, autocorr 0.999 —
   drifts smoothly, doesn't look like noise). Good Kalman-filter candidate: real economic
   linkage (duopoly payment networks) with an actually-drifting hedge ratio.
3. **KO/PEP** — corr ~0.71-0.73, coint p=0.025, beta_cv=0.59. Classic textbook pairs-trade
   pair; more drift in beta than V/MA but still smooth (autocorr 0.999), not noisy.
4-12. GS/MS, GLD/GDX, HD/LOW, PG/CL, JPM/BAC, USO/XLE, MSFT/GOOGL, XOM/CVX, UPS/FDX — coint
   p-value > 0.14, several > 0.5 (XOM/CVX, UPS/FDX not cointegrated in this window despite
   decent correlation — correlation without cointegration, exactly the distinction the spec
   called out to check for).

**Recommendation for Phase 1**: take V/MA and KO/PEP forward (SPY/VOO as a trivial
sanity-check baseline, not a real trading candidate). Not yet validated on a later
out-of-sample window — do that before committing to a final pair.

## 2026-08-17 — Phase 1 run

Also implemented directly (still no Robin/API — pending credit top-up), following
the same design pattern: `src/phase1_kalman_hedge_ratio.py` + `tests/test_phase1.py`
(5/5 pass). Filters (not smooths) beta_t so the signal never uses future
observations — smoothing would itself be a lookahead leak at trade time.

`(delta, obs_cov)` grid-searched by maximizing `KalmanFilter.loglikelihood` on
DELTA_GRID x OBS_COV_GRID (5x5), same SELECTION_START/END boundary as Phase 0.

Results on real data (`reports/phase1_kalman_{V_MA,KO_PEP}.csv`):
- **V/MA**: delta=1e-4, obs_cov=0.01, beta ranges 1.17-1.77 over the window, spread
  std=0.01.
- **KO/PEP**: delta=1e-3, obs_cov=**0.001 (grid's lower boundary)**, beta ranges
  2.19-3.12, spread std=0.001.

**Flag for Phase 2/3**: KO/PEP's log-likelihood-optimal obs_cov sits at the grid's
edge, and both spreads have very small std relative to price levels — the filter is
trusting observations heavily enough that beta re-fits almost every timestep,
leaving little residual to actually trade. Pure log-likelihood MLE is known to favor
this near-degenerate regime (it rewards a tight fit, not a *useful, tradeable*
residual). Don't take these noise parameters as final: Phase 3's signal-quality vs.
trading-performance sweep should treat (delta, obs_cov) as still-open, not locked in
by Phase 1's MLE alone — worth widening OBS_COV_GRID downward to confirm it's a
genuine likelihood peak and not just hitting a boundary, and cross-checking against
spread half-life/ADF stationarity rather than trusting log-likelihood in isolation.

## 2026-08-17 — Phase 2 run

Still direct implementation, no Robin/API. `src/phase2_fft_denoise.py` +
`tests/test_phase2.py` (5/5 pass, including a causality test that confirms the
denoised value at time t is bit-identical whether or not later observations exist
yet -- a rolling *causal* short-time FFT, not one FFT over the whole series, since
a whole-series FFT of a non-stationary signal both makes little economic sense and
is itself a lookahead-adjacent leak).

`src/phase2_run.py` is a quick preview (not the full Phase 3 sweep) applying
p=50/70/90 to both Phase 1 spreads. Sanity check passed: variance_explained falls
monotonically as p increases for both pairs (V/MA: 0.85→0.66→0.38, KO/PEP:
0.86→0.66→0.36), i.e. the mechanism behaves as designed before building the larger
Phase 3 sweep + trading-performance comparison on top of it.

SSA (Phase 2's flagged robustness alternative) not yet implemented — still open,
noted in SPEC.md as a later comparison, not required to unblock Phase 3.

## 2026-08-17 — Phase 3 + Phase 4 run (real results, negative)

`src/phase4_backtest.py` (z-score entry/exit, regime split) + `src/phase3_sweep.py`
(percentile grid x (z_entry, z_exit) grid, both pairs) + tests (26/26 pass total,
across all phases). Still direct implementation, no Robin/API.

**Bug caught and fixed before trusting results**: the first backtest pass priced
transaction costs off the spread's own numeric scale (`cost_frac * abs(spread)`,
spread ~ $0.01-0.001) instead of real traded notional (Y_t + beta_t*X_t, ~$100s).
That undercharged costs by roughly 1000x and produced implausible Sharpe ~5-7 with
100% hit rates — caught by eyeballing the numbers, not by a test. Fixed by passing a
real `notional` series into `backtest()`, computed from actual prices + beta.

**Honest result after the fix: the strategy is unprofitable at every percentile and
(z_entry, z_exit) tried.** Best Sharpe at any percentile is still negative for both
V/MA and KO/PEP (roughly -1.4 to -3.2 depending on p), 0% hit rate, and both
extreme- and normal-regime Sharpe are negative. Full grid in
`reports/phase3_sweep_{V_MA,KO_PEP}.csv`.

**Why**: this traces straight back to the Phase 1 flag. The Kalman filter's
likelihood-optimal noise parameters make beta re-fit almost every timestep, so the
spread is close to a small, fast-mean-reverting residual (half-life <1 day at every
percentile). A signal that reverts in under a day, traded on daily bars with a
realistic ~5bps-per-leg cost against real notional, cannot outrun costs — there
isn't enough magnitude or persistence in the residual to pay for a round trip.
Higher percentile denoising shrinks losses (fewer trades) but never flips the sign.

**Implication for next steps**: don't tune (z_entry, z_exit, p) further on this
Kalman fit — that's polishing a signal that's structurally too fast and too small to
trade profitably. Revisit Phase 1: constrain the noise-parameter search away from the
near-degenerate regime (e.g. widen OBS_COV_GRID and penalize very short implied
half-life, not just raw log-likelihood) so the spread retains a slower, larger-
amplitude mean-reverting component worth paying transaction costs for.

Full write-up with tables and an equity-curve chart: see the published HTML report
(link given to the user in chat).

## 2026-08-17 — Follow-up: half-life floor fixes it, and it holds out-of-sample

Tested the fix proposed above rather than just asserting it. Added
`fit_noise_params_with_half_life_floor()` to `src/phase1_kalman_hedge_ratio.py`
(same grid, but restricted to (delta, obs_cov) pairs whose resulting spread has OU
half-life >= a floor, e.g. 10 days; falls back to the longest achievable half-life
if nothing clears it). Test added confirming it never returns a shorter half-life
than the unconstrained MLE fit.

**Effect on the fit** (`scripts/rerun_with_half_life_floor.py`): half-life jumps
from <1 day to 7.3d (V/MA) and 11.6d (KO/PEP); spread std jumps ~400-6000x (V/MA:
0.01 -> 4.02, KO/PEP: 0.0006 -> 2.42). The MLE was picking a near-degenerate fit
that produced a residual too small and fast to trade; constraining it away from
that regime produces a residual with real, tradeable magnitude.

**Effect on the backtest, same realistic notional-based costs**: Sharpe flips
positive at every percentile tried for both pairs. Best: **V/MA Sharpe 1.35 at
p=70** (86-102 trades, 88-90% hit rate across p), **KO/PEP Sharpe 1.30 at p=70**
(72-76 trades, 83-88% hit rate). Positive Sharpe held across the whole percentile
grid (0/50/70/90) for both pairs, not just one lucky point -- the parameter-
stability plateau the spec asked for.

**Out-of-sample validation** (`scripts/out_of_sample_check.py`) -- the test that
actually matters: froze (delta, obs_cov, p, z_entry, z_exit) exactly as fit/chosen
on 2015-2021, then ran the whole pipeline unchanged on 2022-2026 data neither this
fit nor any earlier sweep had ever touched.

| pair | in-sample half-life | OOS half-life | OOS Sharpe | OOS hit rate | OOS trades |
|---|---|---|---|---|---|
| V/MA | 7.3d | 8.0d | **1.35** | 0.93 | 55 |
| KO/PEP | 11.6d | 14.3d | **1.38** | 0.90 | 48 |

Sharpe held (slightly improved) and half-life stayed close to the in-sample value
on genuinely unseen data. This is the strongest evidence in the project so far that
the effect is real rather than a sweep artifact.

**Caveats before calling this done**:
- The OOS Kalman filter was cold-started (initial_state_mean=0) at 2022-01-01 rather
  than carrying forward filter state from the fitted window, which is what a live
  system would do -- introduces a short burn-in transient not present in a true
  live deployment, biasing the OOS number slightly conservative if anything.
- z_entry/z_exit and p were chosen by best-Sharpe on the *same* in-sample window as
  the half-life floor, so there's still one layer of in-sample selection this OOS
  check doesn't fully wash out (the floor and the noise-param choice were the part
  actually tested against a true holdout; the trading-rule grid was not
  independently re-validated OOS).
- 5bps/leg is a reasonable but assumed cost; not fit or validated against real
  broker/exchange data for these tickers.
- Regime-split Sharpe (extreme > normal in most rows) deserves a closer look before
  trusting it -- could be genuine (bigger dislocations = bigger reversion trades) or
  an artifact of how `regime_split_dates` flags days using the spread's own moves.

Not yet done: SSA denoising comparison (Phase 2's flagged alternative), Johansen/
multi-asset extension, position sizing beyond one unit of spread notional, and a
second, independent OOS window (e.g. holding out 2022-2023 to validate on 2024-2026
so the current OOS window isn't itself reused for further tuning).
