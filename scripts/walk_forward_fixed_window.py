"""Fixed-length rolling-window walk-forward, as a follow-up to
walk_forward_validation.py's expanding-window design.

Motivation: the expanding-window folds showed several candidates (DAL/UAL,
TRV/CB, DHI/LEN, GS/MS, KMB/PG, UNP/CSX, T/VZ, PG/CL) with cointegration
p-values falling steadily as the training window lengthened (5y -> 7y -> 9y),
only crossing p<0.05 in the longest window. That's ambiguous: it's consistent
with a real-but-weak relationship that needs more data to detect (Engle-Granger
has low power on slow, long-half-life relationships), but equally consistent
with broad market-wide correlation drift (the passive-investing era pushing
most same-sector pairs' correlations up over time) mechanically inflating
cointegration test power for many pairs at once, independent of true
pair-specific structure.

A FIXED window length, rolled forward through time, separates these: if a
relationship is genuinely stable, it should be detectable with the same
~5 years of data regardless of which 5-year slice of history it's given, not
only once the sample has grown large enough. If it only ever appears with a
long window, that's evidence for the low-power (or drift) explanation, not a
truly pair-specific stable relationship at a scale a retail account trades at.
"""
import numpy as np
import pandas as pd

from src.phase0_pair_selection import CANDIDATE_PAIRS
from scripts.walk_forward_validation import screen_pairs, fold_test, N_CANDIDATES, BONFERRONI_ALPHA

FOLDS = [
    ("2015-01-01", "2019-12-31", "2021-12-31"),
    ("2017-01-01", "2021-12-31", "2023-12-31"),
    ("2019-01-01", "2023-12-31", "2026-08-01"),
]


def main():
    all_results = []
    for fold_i, (train_start, train_end, test_end) in enumerate(FOLDS, start=1):
        print(f"\n{'='*70}\nFOLD {fold_i}: train=[{train_start}, {train_end}] (5y fixed)  test=({train_end}, {test_end}]")
        candidates = screen_pairs(train_start, train_end)
        bonferroni_survivors = [c for c in candidates if c[2] < BONFERRONI_ALPHA]
        print(f"  {len(candidates)}/{N_CANDIDATES} pairs pass raw p<0.05 screen; {len(bonferroni_survivors)} survive Bonferroni (p<{BONFERRONI_ALPHA:.5f})")
        for a, b, p in candidates:
            print(f"    {a}/{b}: coint_p={p:.4f}")
            r = fold_test(train_start, train_end, test_end, (a, b))
            if r is None:
                continue
            r["fold"] = fold_i
            r["coint_pvalue_train"] = p
            all_results.append(r)
            print(f"      -> OOS test_sharpe={r['test_sharpe']:.2f} trades={r['test_n_trades']} hit_rate={r['test_hit_rate']:.2f}")

    df = pd.DataFrame(all_results)
    df.to_csv("reports/walk_forward_fixed_window_results.csv", index=False)

    print(f"\n{'='*70}\nPairs appearing in >1 fold (fixed 5y window, rolled forward):")
    for pair, g in df.groupby("pair"):
        if len(g) > 1:
            sharpes = ", ".join(f"fold{int(f)}={s:.2f}" for f, s in zip(g["fold"], g["test_sharpe"]))
            print(f"  {pair}: {sharpes}")

    print("\nPairs appearing in only 1 fold:")
    for pair, g in df.groupby("pair"):
        if len(g) == 1:
            row = g.iloc[0]
            print(f"  {pair}: fold{int(row['fold'])} only, test_sharpe={row['test_sharpe']:.2f}")


if __name__ == "__main__":
    main()
