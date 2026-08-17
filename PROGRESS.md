# Progress Tracker

Drive each phase through `@robin` in VS Code (Planner → Draft → Engineer → Critic →
Runner). Check off phases as Robin lands verified, tested code for them. See
SPEC.md for full detail on each phase.

- [x] Phase 0 — Ticker/pair selection (correlation + cointegration + beta-stability screen)
- [x] Phase 1 — Kalman filter dynamic hedge ratio
- [ ] Phase 2 — FFT denoising pipeline
- [ ] Phase 3a — Signal-quality sweep across percentile p
- [ ] Phase 3b — Extreme-event sensitivity analysis
- [ ] Phase 3c — Trading-performance sweep across percentile p
- [ ] Phase 3d — Synthesis plot (signal quality vs. performance)
- [ ] Phase 4 — Trade signal + full backtest, parameter stability check

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
