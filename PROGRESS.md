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

## 2026-08-19 — Widened universe (36 pairs incl. commodities/crypto), then walk-forward invalidated 2 of the 4 "new" pairs

**Widened candidate universe** (`src/phase0_pair_selection.py` CANDIDATE_PAIRS, now 36
pairs) to include more equity sectors plus commodities (GLD/SLV, GLD/PPLT, SLV/PPLT,
PALL/PPLT, DBB/CPER as an aluminum/tin proxy -- no liquid pure-play US-listed ETF
exists for either metal) and crypto (BTC-USD/ETH-USD). **None of the commodity or
crypto pairs cleared cointegration** on the 2015-2021 screen (best was BTC/ETH at
p=0.21, still far above 0.05) -- excluded, consistent with gold/silver's well-known
non-mean-reverting multi-year trending behavior and BTC/ETH's narrative-driven
decoupling. Not forced in.

Of the equity expansion, two borderline candidates (KMB/PG p=0.052, UNP/CSX p=0.068
on the static 2015-2021 screen) were fit and OOS-tested the same way as V/MA/KO-PEP
and looked strong: OOS Sharpe 1.77 and 1.95, even better than in-sample. A combined
4-pair book raised capital utilization from 57%->92% of days active and portfolio
Sharpe to ~3-4 (with idle-cash yield). This looked like a genuine improvement.

**Then ran actual walk-forward validation** (`scripts/walk_forward_validation.py`,
`reports/walk_forward_results.csv`) to directly test the concern that "best 2 of 36
candidates on one static window" is itself a selection-bias risk the single OOS
check doesn't rule out. Method: 3 non-overlapping folds with an expanding training
window (train always starts 2015-01-01; folds train through 2019/2021/2023, test
purely forward on the following ~2 years each), re-running the FULL pair screen
(correlation + cointegration + beta stability) from scratch on each fold's
training-only data -- not just refitting Kalman params on pairs chosen once.

**Result: KMB/PG and UNP/CSX do not survive this test.** Neither pair cleared the
cointegration screen in fold 1 (train through 2019) or fold 2 (train through 2021)
-- they only appear as "cointegrated" once the training window is extended through
2023. That means their apparent structural relationship is not stable across
independent historical windows; it's very plausibly a product of being the best 2 of
36 on one specific long window, exactly the risk flagged earlier. Their strong OOS
Sharpe from the single static-window test should now be treated as likely a
selection-bias artifact, not validated edge. **Do not include KMB/PG or UNP/CSX in
the tradeable book without further evidence** (e.g. surviving a 4th, later fold).

**V/MA and KO/PEP, by contrast, both cleared the cointegration screen independently
in fold 2 AND fold 3** (i.e. using only 2015-2021 training data, and again using only
2015-2023 training data) **and both had positive OOS Sharpe in both corresponding
test windows**: V/MA fold2=1.38/fold3=1.77, KO/PEP fold2=0.64/fold3=2.20. This is a
materially stronger validation than the single-split OOS check from 2026-08-17 --
these two pairs now have two independent, non-overlapping confirmations, not one.

**SPY/VOO is actively bad, not just "excluded on taste."** It has the tightest
cointegration (p=0.006-0.019, best in the whole universe) but strongly NEGATIVE OOS
Sharpe in both folds it appears in (-7.75, -5.96) with ~0% hit rate -- a reminder
that near-perfect cointegration (two index funds tracking the same thing) does not
imply a tradeable mean-reverting spread; the near-zero spread from near-identical
assets is dominated by costs and micro-noise, not signal. Good confirmation that the
original qualitative call to exclude it was right, now backed by a real backtest
number instead of intuition.

**BTC-USD/ETH-USD**, the one crypto pair to even marginally clear screening (fold 3
only, p=0.049), had OOS Sharpe -7.16 -- consistent with the earlier decision not to
force crypto into the book, and a reminder that a pair barely clearing a p<0.05 bar
in one fold, appearing in no other fold, is exactly the profile of a false positive.

**Also confirms the multiple-comparisons concern was real and appropriately sized**:
with 36 candidates tested per fold, the Bonferroni-corrected threshold is
p<0.00139; almost nothing survives it (only V/MA in fold 3, barely). Raw p<0.05
alone is not a reliable filter at this many candidates -- repeated appearance across
independent folds with consistent-sign OOS performance is doing the real work of
separating signal from noise here, not the p-value on its own.

**Updated conclusion**: the validated, tradeable book is back to **V/MA and KO/PEP
only** -- now with stronger (multi-fold) evidence than before, not weaker. The
4-pair, Sharpe-3-4 result from the prior session should be treated as retracted
pending KMB/PG and UNP/CSX surviving a genuine walk-forward fold, not as a real
improvement. The lesson generalizes: "screen many pairs, keep the winners, OOS-test
the winners once" is not sufficient -- the winners need to independently reappear
across multiple non-overlapping selection windows before they're trustworthy.

## 2026-08-21 — Widened universe to 59 pairs; expanding-window design hit a
## detection-power confound; fixed-window design resolves it and adds 2 pairs

User wanted more trades -> more pairs. Widened CANDIDATE_PAIRS from 36 to 59
(added airlines, insurers, homebuilders, chemicals, asset managers, more sector
ETFs). Re-ran the same expanding-window walk-forward
(`scripts/walk_forward_validation.py`): still only V/MA and KO/PEP repeat across
folds. Every new candidate (DAL/UAL, TRV/CB, DHI/LEN, GS/MS, IWM/MDY, etc.)
appeared in exactly one fold, the same pattern that got KMB/PG and UNP/CSX
retracted last session.

**But a diagnostic check on the near-misses revealed a confound in the expanding-
window design itself**: for most of these candidates, cointegration p-value fell
steadily as the training window lengthened (5y -> 7y -> 9y), only crossing p<0.05
in the longest (fold 3) window -- e.g. UNP/CSX: 0.572 -> 0.068 -> 0.023. That
pattern is ambiguous by construction: consistent with a real-but-weak relationship
needing more data to detect (cointegration tests have low power on slow,
long-half-life relationships), equally consistent with market-wide correlation
drift (the passive-investing era) mechanically inflating cointegration power for
many same-sector pairs at once as the sample grows, independent of true
pair-specific structure. An expanding window can't distinguish these.

**Built `scripts/walk_forward_fixed_window.py`**: same screen + fit + OOS test
logic, but 3 folds with a FIXED 5-year training window rolled forward in time
(2015-2019 -> 2021, 2017-2021 -> 2023, 2019-2023 -> 2026) instead of an expanding
one. A genuinely stable relationship should be detectable with a constant amount
of data at different points in history, not only once cumulative history grows
long enough.

**Result: two new pairs pass this harder, apples-to-apples bar.**
- **UNP/CSX**: coint_p=0.0196 (2017-2021 train) and 0.0053 (2019-2023 train), OOS
  Sharpe 1.97 and 2.57. Failed only in the earliest window (2015-2019, p=0.572) --
  plausibly a real regime shift (CSX had activist-investor-driven leadership/
  strategy changes starting ~2017), not noise.
- **LUV/JBLU**: coint_p=0.0012 and 0.0157, OOS Sharpe 0.97 and 1.92. Never
  appeared in the expanding-window screen at all -- only visible once the earliest,
  weakest-relationship years are excluded from the training sample.

**KO/PEP does not appear in the fixed-window screen at all**, in any of the 3
folds. Its earlier validation came from expanding windows of 7 and 9 years --
consistent with it being a real but statistically weak/slow relationship that
needs more cumulative data for the test to have power (its measured half-life,
11-14 days, is on the slower end), OR a fold-count coincidence. Keeping it in the
book given its multiple prior independent confirmations (original OOS check,
expanding-window fold 2 and 3), but flagging this as a softer form of evidence
than V/MA, UNP/CSX, or LUV/JBLU, which all clear the fixed-window bar directly.

**SPY/VOO and EFA/VEA** (both near-duplicate-ETF-family pairs) again show strong
cointegration but strongly negative OOS Sharpe (-7.83 and -0.77) under the
fixed-window test too -- reconfirms near-perfect cointegration between
functionally-identical instruments is not tradeable, this isn't a fluke of one
design.

**Updated validated book: V/MA, KO/PEP, UNP/CSX, LUV/JBLU** -- 4 pairs, roughly
doubling trade frequency/capital utilization versus the 2-pair book, via genuine
multi-fold (not single-window) confirmation this time. GS/MS, KMB/PG, MO/PM,
DHI/LEN, GLD/GDX, XOM/CVX remain single-fold-only under the fixed-window design
and are NOT included -- same standard applied consistently.

## 2026-08-22 — Paper trading started; stop-loss tested and rejected;
## proportional sizing + compounding added as a parallel v2 track

Paper trading began today (`PAPER_TRADING_PROTOCOL.md`, `scripts/paper_trade.py`)
on the frozen 4-pair book: $250/pair, fixed, non-compounded, exact configs from
the walk-forward work. Minimum 3-month evaluation window, no retuning during it,
red flags pre-committed.

Immediately tested two "make it more profitable" ideas empirically on the real
2024-2026 OOS window rather than assuming either would help:

- **Stop-loss: rejected.** Added `stop_loss_z` to `backtest()` (exit if z moves
  further adverse than entry by a set amount). Made the worst trades *larger*,
  not smaller (LUV/JBLU: -$4.89 -> -$23.67) -- an early exit often still leaves
  z past the entry threshold, so the strategy immediately re-enters the same
  losing bet and gets whipsawed repeatedly during genuine trends. Real,
  useful negative result; not used anywhere.
- **Signal-proportional sizing + compounding: works, added as v2 only.** Added
  `size_multiplier` to `backtest()` (per-trade size scaled by conviction, i.e.
  how far past entry threshold the z-score is, capped at 2x). Total P&L up
  19-45% across all 4 pairs on the OOS window, Sharpe roughly flat. Not folded
  into the frozen v1 protocol -- only tested on the same window used to
  evaluate everything else, no independent confirmation yet. Instead runs as a
  parallel "v2" track in `scripts/paper_trade.py` from the same 2026-08-22
  start date, same $1000 capital, so paper trading itself becomes v2's fresh
  out-of-sample test. v1 (frozen baseline) remains the primary evaluation
  subject; v2 is a tracked candidate, not a replacement.

Both `stop_loss_z` and `size_multiplier` are optional params on `backtest()`,
default `None`/no-op -- every existing test and prior result is unaffected
(29/29 tests pass, up from 27 with 2 new tests covering both mechanisms).
