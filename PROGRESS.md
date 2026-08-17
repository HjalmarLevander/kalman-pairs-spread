# Progress Tracker

Drive each phase through `@robin` in VS Code (Planner → Draft → Engineer → Critic →
Runner). Check off phases as Robin lands verified, tested code for them. See
SPEC.md for full detail on each phase.

- [x] Phase 0 — Ticker/pair selection (correlation + cointegration + beta-stability screen)
- [ ] Phase 1 — Kalman filter dynamic hedge ratio
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
