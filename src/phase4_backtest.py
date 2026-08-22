"""Phase 4: trade signal + backtest on the (Kalman-filtered, FFT-denoised)
spread (see ../SPEC.md).

Signal: rolling z-score of spread_denoised_t against its own trailing
mean/std (causal -- same rolling-window discipline as Phase 2, no lookahead).

Position: dollar-neutral in "spread units" -- long the spread means long Y /
short beta*X, sized using the hedge ratio in effect at trade entry (not
re-hedged tick-by-tick mid-trade, which is standard pairs-trading practice
and avoids attributing beta-drift noise to trading PnL).

Costs: a flat per-leg transaction cost in basis points of notional, charged
on entry and on exit.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

DEFAULT_ZSCORE_WINDOW = 60
DEFAULT_TRANSACTION_COST_BPS = 5.0
DEFAULT_MAX_HOLDING_DAYS = 60


def rolling_zscore(series: pd.Series, window: int = DEFAULT_ZSCORE_WINDOW) -> pd.Series:
    mean = series.rolling(window).mean()
    std = series.rolling(window).std()
    z = (series - mean) / std
    return z.replace([np.inf, -np.inf], np.nan)


@dataclass
class Trade:
    entry_date: pd.Timestamp
    exit_date: pd.Timestamp
    direction: int  # +1 = long spread, -1 = short spread
    pnl: float
    duration_days: int


@dataclass
class BacktestResult:
    equity_curve: pd.Series
    daily_pnl: pd.Series
    trades: list[Trade] = field(default_factory=list)
    sharpe: float = float("nan")
    max_drawdown: float = float("nan")
    hit_rate: float = float("nan")
    avg_trade_duration: float = float("nan")
    turnover: float = float("nan")
    n_trades: int = 0


def _max_drawdown(equity: pd.Series) -> float:
    if equity.empty:
        return float("nan")
    running_max = equity.cummax()
    drawdown = (equity - running_max) / running_max.replace(0, np.nan)
    return float(drawdown.min()) if drawdown.notna().any() else float("nan")


def backtest(
    spread_denoised: pd.Series,
    z_entry: float = 2.0,
    z_exit: float = 0.5,
    zscore_window: int = DEFAULT_ZSCORE_WINDOW,
    transaction_cost_bps: float = DEFAULT_TRANSACTION_COST_BPS,
    max_holding_days: int = DEFAULT_MAX_HOLDING_DAYS,
    notional: pd.Series | None = None,
    stop_loss_z: float | None = None,
    size_multiplier: pd.Series | None = None,
) -> BacktestResult:
    """Z-score entry/exit backtest, one unit of spread notional per trade
    (position sizing in real dollars belongs to a portfolio layer above
    this, out of scope for the strategy-level backtest the spec asks for).

    `notional` is the real dollar exposure of a one-unit spread position
    (e.g. Y_t + beta_t * X_t from the underlying prices), used to size
    transaction costs. Costs computed off the spread's own numeric scale
    instead (the default when notional is omitted) will badly understate
    real costs, since spread_t = Y_t - beta_t*X_t is a small residual, not
    a traded amount -- charging bps against it prices trading at
    ~1000x cheaper than reality and inflates Sharpe accordingly.

    `stop_loss_z` (optional): force an exit if the z-score moves this many
    additional units past the entry z-score in the adverse direction (i.e.
    the position keeps getting worse instead of reverting). None disables it
    -- the default behavior relies only on max_holding_days as a time-based
    stop, with no price-based cut.

    `size_multiplier` (optional): per-day multiplier on daily PnL and cost,
    keyed by date. Used to test signal-proportional sizing (bet size scaled
    by entry conviction) without changing the entry/exit logic itself. None
    means constant 1x sizing throughout, matching every earlier backtest.
    """
    z = rolling_zscore(spread_denoised, zscore_window)
    spread = spread_denoised
    if notional is None:
        notional = spread.abs()

    position = 0  # -1, 0, +1
    entry_price = None
    entry_date = None
    entry_day_idx = None
    entry_cost = 0.0
    entry_z = None
    size_mult = 1.0

    daily_pnl = pd.Series(0.0, index=spread.index)
    trades: list[Trade] = []
    cost_frac = transaction_cost_bps / 10_000.0

    valid_idx = z.dropna().index
    if len(valid_idx) < 2:
        return BacktestResult(equity_curve=pd.Series(dtype=float), daily_pnl=daily_pnl)

    dates = spread.index
    for i in range(1, len(dates)):
        today, yesterday = dates[i], dates[i - 1]
        if pd.isna(z.loc[today]) or pd.isna(spread.loc[today]) or pd.isna(spread.loc[yesterday]):
            continue

        if position != 0:
            daily_pnl.loc[today] = size_mult * position * (spread.loc[today] - spread.loc[yesterday])

        zt = z.loc[today]
        held_days = (i - entry_day_idx) if entry_day_idx is not None else 0

        # stopped_out: position=-1 (short, entered because z was high) gets
        # worse if z rises further past entry_z + stop_loss_z; position=+1
        # (long) gets worse if z falls further past entry_z - stop_loss_z.
        stopped_out = (
            stop_loss_z is not None and position != 0 and entry_z is not None and (
                (position == -1 and zt >= entry_z + stop_loss_z)
                or (position == 1 and zt <= entry_z - stop_loss_z)
            )
        )

        should_exit = position != 0 and (
            abs(zt) <= z_exit
            or np.sign(zt) == position  # z crossed through zero past our entry side
            or held_days >= max_holding_days
            or stopped_out
        )
        if should_exit:
            exit_notional = notional.loc[today] if today in notional.index and not pd.isna(notional.loc[today]) else abs(spread.loc[today])
            cost = size_mult * cost_frac * exit_notional
            daily_pnl.loc[today] -= cost
            trade_pnl = size_mult * position * (spread.loc[today] - entry_price) - entry_cost - cost
            trades.append(Trade(entry_date, today, position, float(trade_pnl), i - entry_day_idx))
            position = 0
            entry_price = None
            entry_date = None
            entry_day_idx = None
            entry_cost = 0.0
            entry_z = None
            size_mult = 1.0

        elif position == 0 and abs(zt) >= z_entry:
            position = -1 if zt > 0 else 1  # spread too high -> short it; too low -> long it
            entry_price = spread.loc[today]
            entry_date = today
            entry_day_idx = i
            entry_z = zt
            size_mult = float(size_multiplier.loc[today]) if size_multiplier is not None and today in size_multiplier.index else 1.0
            entry_notional = notional.loc[today] if today in notional.index and not pd.isna(notional.loc[today]) else abs(entry_price)
            entry_cost = size_mult * cost_frac * entry_notional
            daily_pnl.loc[today] -= entry_cost

    equity_curve = daily_pnl.cumsum() + 1.0  # start at 1.0 "unit" of capital

    result = BacktestResult(equity_curve=equity_curve, daily_pnl=daily_pnl, trades=trades, n_trades=len(trades))
    if daily_pnl.std() and daily_pnl.std() > 0:
        result.sharpe = float(daily_pnl.mean() / daily_pnl.std() * np.sqrt(252))
    result.max_drawdown = _max_drawdown(equity_curve)
    if trades:
        result.hit_rate = float(np.mean([t.pnl > 0 for t in trades]))
        result.avg_trade_duration = float(np.mean([t.duration_days for t in trades]))
    result.turnover = len(trades) / max(len(dates), 1)
    return result


def regime_split_dates(returns: pd.Series, threshold_std: float = 2.5) -> pd.Series:
    """Boolean series, True on days flagged 'extreme' (|return| beyond
    threshold_std standard deviations of the full-window return
    distribution). Used to break out backtest performance by regime.
    """
    std = returns.std()
    return (returns.abs() > threshold_std * std).reindex(returns.index, fill_value=False)


def split_metrics_by_regime(daily_pnl: pd.Series, extreme_mask: pd.Series) -> dict[str, float]:
    aligned_mask = extreme_mask.reindex(daily_pnl.index, fill_value=False)
    extreme_pnl = daily_pnl[aligned_mask]
    normal_pnl = daily_pnl[~aligned_mask]

    def sharpe(pnl: pd.Series) -> float:
        if pnl.std() and pnl.std() > 0:
            return float(pnl.mean() / pnl.std() * np.sqrt(252))
        return float("nan")

    return {
        "extreme_sharpe": sharpe(extreme_pnl),
        "normal_sharpe": sharpe(normal_pnl),
        "extreme_mean_pnl": float(extreme_pnl.mean()) if len(extreme_pnl) else float("nan"),
        "normal_mean_pnl": float(normal_pnl.mean()) if len(normal_pnl) else float("nan"),
        "n_extreme_days": int(aligned_mask.sum()),
        "n_normal_days": int((~aligned_mask).sum()),
    }
