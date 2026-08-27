"""Phase 5 (exploratory): can a model trained on entry-time features predict
which trades win, well enough to use as a size-confidence multiplier?

Every feature here is deliberately restricted to information available AT
TRADE ENTRY -- the same causal discipline as every earlier phase. Nothing
here is allowed to see the trade's own outcome, duration, or exit price.

Honesty constraint: with ~70-90 trades per pair (~300 total across the book),
a random forest can trivially memorize noise. This module trains on an
EARLY time slice and evaluates OUT-OF-SAMPLE on a LATER time slice per pair
(not a random shuffle-split, which would leak adjacent-in-time trades that
share market regime between train and test). If the model has no real skill
on the held-out slice, that is the honest answer, not a reason to keep
tuning until it does.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score

from scripts.paper_trade import CONFIGS
from src.phase0_pair_selection import load_prices
from src.phase1_kalman_hedge_ratio import fit_noise_params_with_half_life_floor, run_kalman_filter
from src.phase2_fft_denoise import rolling_fft_denoise
from src.phase4_backtest import DEFAULT_MAX_HOLDING_DAYS, DEFAULT_TRANSACTION_COST_BPS, rolling_zscore

FEATURE_COLUMNS = [
    "abs_entry_z", "spread_std", "beta", "beta_std_norm", "entry_notional", "half_life",
]


def build_trade_dataset(end_date: str = "2026-08-24") -> pd.DataFrame:
    """Replays each pair's full history and records one row per trade with
    entry-time-only features plus the eventual outcome (win/loss, pnl) --
    outcome columns are for labeling/evaluation only, never fed to the model
    as a feature.
    """
    rows = []
    for label, cfg in CONFIGS.items():
        a, b = cfg["pair"]
        fit_prices = load_prices([a, b], cfg["fit_start"], cfg["fit_end"])
        delta, obs_cov, _, half_life = fit_noise_params_with_half_life_floor(
            fit_prices[a], fit_prices[b], min_half_life_days=10.0
        )
        full_prices = load_prices([a, b], cfg["fit_start"], end_date)
        result = run_kalman_filter(label, full_prices[a], full_prices[b], delta, obs_cov)
        denoised = rolling_fft_denoise(result.spread, percentile=cfg["p"], window=60)
        z = rolling_zscore(denoised, 60)
        spread_std = denoised.rolling(60).std()
        notional = (full_prices[b] + result.beta * full_prices[a]).abs().reindex(result.spread.index)
        beta_std_norm = (result.beta_std / result.beta.abs()).reindex(result.spread.index)

        cost_frac = DEFAULT_TRANSACTION_COST_BPS / 10_000.0
        position = 0
        entry_i = entry_date = entry_spread = entry_price = entry_z = None
        entry_features = None

        dates = denoised.index
        for i in range(1, len(dates)):
            today, yesterday = dates[i], dates[i - 1]
            if pd.isna(z.loc[today]) or pd.isna(denoised.loc[today]) or pd.isna(denoised.loc[yesterday]):
                continue
            zt = z.loc[today]
            held_days = (i - entry_i) if entry_i is not None else 0

            if position != 0:
                should_exit = (
                    abs(zt) <= cfg["z_exit"] or np.sign(zt) == position or held_days >= DEFAULT_MAX_HOLDING_DAYS
                )
                if should_exit:
                    exit_notional = notional.loc[today] if not pd.isna(notional.loc[today]) else abs(denoised.loc[today])
                    entry_cost = cost_frac * entry_features["entry_notional"]
                    exit_cost = cost_frac * exit_notional
                    trade_pnl = position * (denoised.loc[today] - entry_price) - entry_cost - exit_cost
                    rows.append(dict(
                        pair=label, entry_date=entry_date, exit_date=today,
                        duration_days=i - entry_i, direction=position,
                        pnl=trade_pnl, win=int(trade_pnl > 0),
                        **entry_features,
                    ))
                    position = 0
                    entry_i = entry_date = entry_spread = entry_price = entry_z = entry_features = None

            elif abs(zt) >= cfg["z_entry"]:
                position = -1 if zt > 0 else 1
                entry_i, entry_date, entry_price, entry_z = i, today, denoised.loc[today], zt
                entry_features = dict(
                    abs_entry_z=abs(zt),
                    spread_std=float(spread_std.loc[today]) if not pd.isna(spread_std.loc[today]) else np.nan,
                    beta=float(result.beta.loc[today]),
                    beta_std_norm=float(beta_std_norm.loc[today]) if today in beta_std_norm.index and not pd.isna(beta_std_norm.loc[today]) else np.nan,
                    entry_notional=float(notional.loc[today]) if not pd.isna(notional.loc[today]) else np.nan,
                    half_life=half_life,
                )

    return pd.DataFrame(rows).dropna()


def time_based_split(df: pd.DataFrame, train_frac: float = 0.7):
    """Per-pair time split (not a global date cutoff -- pairs have different
    fit windows) so train is strictly earlier than test within each pair,
    avoiding the leakage a random shuffle-split would introduce between
    trades that share a market regime.
    """
    train_parts, test_parts = [], []
    for pair, g in df.groupby("pair"):
        g = g.sort_values("entry_date")
        cut = int(len(g) * train_frac)
        train_parts.append(g.iloc[:cut])
        test_parts.append(g.iloc[cut:])
    return pd.concat(train_parts), pd.concat(test_parts)


def evaluate_confidence_model(df: pd.DataFrame) -> dict:
    train, test = time_based_split(df)
    X_train, y_train = train[FEATURE_COLUMNS], train["win"]
    X_test, y_test = test[FEATURE_COLUMNS], test["win"]

    clf = RandomForestClassifier(n_estimators=300, max_depth=4, min_samples_leaf=5,
                                  random_state=42, class_weight="balanced")
    clf.fit(X_train, y_train)
    proba_test = clf.predict_proba(X_test)[:, 1]

    baseline_rate = y_train.mean()  # naive "always predict train hit rate" baseline
    try:
        auc = roc_auc_score(y_test, proba_test)
    except ValueError:
        auc = float("nan")  # only one class present in test slice

    # Does using predicted confidence as a size multiplier actually raise
    # total pnl vs. flat 1x sizing, on the SAME held-out trades?
    conf_mult = 0.5 + 1.5 * proba_test  # map [0,1] -> [0.5x, 2x], same cap philosophy as v2
    pnl_flat = test["pnl"].sum()
    pnl_confidence_weighted = (test["pnl"] * conf_mult).sum()

    return dict(
        n_train=len(train), n_test=len(test),
        train_hit_rate=round(baseline_rate, 3), test_hit_rate=round(y_test.mean(), 3),
        test_auc=round(auc, 3) if auc == auc else None,
        feature_importance=dict(zip(FEATURE_COLUMNS, np.round(clf.feature_importances_, 3))),
        pnl_flat_sizing=round(pnl_flat, 2), pnl_confidence_weighted=round(pnl_confidence_weighted, 2),
        improvement=round(pnl_confidence_weighted - pnl_flat, 2),
    )


if __name__ == "__main__":
    df = build_trade_dataset()
    print(f"Total trades across book: {len(df)}  (per pair: {df.groupby('pair').size().to_dict()})\n")
    result = evaluate_confidence_model(df)
    for k, v in result.items():
        print(f"{k}: {v}")
