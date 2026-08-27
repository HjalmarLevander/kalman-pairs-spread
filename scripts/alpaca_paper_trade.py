"""Live paper-trading execution via Alpaca's paper API, v2 (proportional-
sizing + compounding) track only -- see PAPER_TRADING_PROTOCOL.md.

v1 (frozen baseline) deliberately stays a log-only simulation in
paper_trade.py / reports/paper_trading_ledger.json, per user decision: v2 is
the track actually being tested with a real (paper) broker execution layer.

Run manually (not scheduled) with:
    source .venv/bin/activate
    python -m scripts.alpaca_paper_trade

Idempotent per day: reports/alpaca_live_state.json records the last date
each pair was processed, so re-running the same day is a no-op rather than
double-submitting orders.
"""
import json
import os

import pandas as pd
from dotenv import load_dotenv

from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.trading.requests import MarketOrderRequest

from scripts.paper_trade import CONFIGS, V2_SIZE_CAP
from src.phase0_pair_selection import load_prices
from src.phase1_kalman_hedge_ratio import fit_noise_params_with_half_life_floor, run_kalman_filter
from src.phase2_fft_denoise import rolling_fft_denoise
from src.phase4_backtest import DEFAULT_MAX_HOLDING_DAYS, DEFAULT_TRANSACTION_COST_BPS, rolling_zscore

load_dotenv()

REPORTS = os.path.join(os.path.dirname(__file__), "..", "reports")
STATE_PATH = os.path.join(REPORTS, "alpaca_live_state.json")
SIGNAL_LOG_PATH = os.path.join(REPORTS, "alpaca_signal_log.csv")

# Position sizing: percent of live Alpaca account equity at entry time,
# scaled linearly by the same z-score-conviction multiplier v2 already uses
# (min conviction at z_entry -> MIN_EQUITY_FRACTION, max conviction at
# V2_SIZE_CAP -> MAX_EQUITY_FRACTION). Replaces the earlier fixed $/pair
# allocation per user decision. Incidentally also clears the whole-share
# short-sale minimum (Alpaca requires whole shares to short) for every pair
# without a per-pair override, since 10-20% of a $100k paper account is far
# above the ~$612 UNP/CSX needed to clear 1 share on its small-beta leg.
# Up to 4 pairs can signal simultaneously -> worst case ~4x20%=80% of equity
# deployed at once, a real aggregation-risk increase versus the old fixed
# small-dollar allocation that was never itself backtested at this scale.
MIN_EQUITY_FRACTION = 0.10
MAX_EQUITY_FRACTION = 0.20


def log_signal_row(label: str, cfg: dict, sig: dict, decision: str) -> None:
    """Append today's full signal snapshot (prices, beta, spread, z-score,
    decision) to a CSV so the numbers behind every decision are visible and
    auditable, not just the trade events.
    """
    z_value = sig["zscore"]
    row = dict(
        run_at=pd.Timestamp.now().isoformat(timespec="seconds"),
        date=sig["today"], pair=label,
        price_a=sig["price_a"], price_b=sig["price_b"], beta=round(sig["beta"], 4),
        spread=round(sig["spread"], 4),
        spread_denoised=round(sig["spread_denoised"], 4) if sig["spread_denoised"] is not None else None,
        zscore=round(z_value, 3) if z_value == z_value else None,  # NaN check
        z_entry=cfg["z_entry"], z_exit=cfg["z_exit"],
        entry_notional=round(sig["entry_notional"], 2) if sig["entry_notional"] else None,
        size_mult=round(sig["size_mult"], 3), decision=decision,
    )
    file_exists = os.path.exists(SIGNAL_LOG_PATH)
    df_row = pd.DataFrame([row])
    df_row.to_csv(SIGNAL_LOG_PATH, mode="a", header=not file_exists, index=False)


def get_client() -> TradingClient:
    key = os.environ["ALPACA_API_KEY"]
    secret = os.environ["ALPACA_SECRET_KEY"]
    return TradingClient(key, secret, paper=True)


def load_state() -> dict:
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH) as f:
            return json.load(f)
    return {}


def save_state(state: dict) -> None:
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)


def compute_today_signal(label: str, cfg: dict, today: str, pair_state: dict):
    """Same causal pipeline as paper_trade.py's v2 track: Kalman -> FFT
    denoise -> z-score. Decides today's action (ENTER/EXIT/HOLD/FLAT) by
    replicating backtest()'s own per-day entry/exit conditions directly
    against our tracked position state, rather than reading bt.trades --
    backtest() only appends a trade to that list once a position CLOSES, so
    an entry signal on the most recent day (still open, nothing to close it
    yet) never appears there. Relying on bt.trades for "did we enter today"
    silently misses every live entry.
    """
    a, b = cfg["pair"]
    fit_prices = load_prices([a, b], cfg["fit_start"], cfg["fit_end"])
    delta, obs_cov, _, _ = fit_noise_params_with_half_life_floor(
        fit_prices[a], fit_prices[b], min_half_life_days=10.0
    )
    full_prices = load_prices([a, b], cfg["fit_start"], today)
    result = run_kalman_filter(label, full_prices[a], full_prices[b], delta, obs_cov)
    denoised = rolling_fft_denoise(result.spread, percentile=cfg["p"], window=60)
    z = rolling_zscore(denoised, 60)
    notional = (full_prices[b] + result.beta * full_prices[a]).abs().reindex(result.spread.index)
    size_mult_series = (z.abs() / cfg["z_entry"]).clip(lower=1.0, upper=V2_SIZE_CAP)

    today_ts = result.spread.index[-1]
    price_a = float(full_prices[a].iloc[-1])
    price_b = float(full_prices[b].iloc[-1])
    beta_today = float(result.beta.iloc[-1])
    z_today = float(z.loc[today_ts]) if today_ts in z.index else float("nan")
    spread_today = float(result.spread.loc[today_ts])
    denoised_today = float(denoised.loc[today_ts]) if today_ts in denoised.index and not pd.isna(denoised.loc[today_ts]) else None
    entry_notional = float(notional.loc[today_ts]) if today_ts in notional.index else None
    size_mult = float(size_mult_series.loc[today_ts]) if today_ts in size_mult_series.index else 1.0

    position = pair_state["position"]
    action = "FLAT"
    direction = 0
    if not pd.isna(z_today):
        if position != 0:
            entry_date = pair_state.get("entry_date")
            held_days = (pd.Timestamp(today_ts) - pd.Timestamp(entry_date)).days if entry_date else 0
            should_exit = (
                abs(z_today) <= cfg["z_exit"]
                or (z_today > 0) == (position > 0)  # z crossed through zero past our entry side
                or held_days >= DEFAULT_MAX_HOLDING_DAYS
            )
            action = "EXIT" if should_exit else "HOLD"
        elif abs(z_today) >= cfg["z_entry"]:
            direction = -1 if z_today > 0 else 1  # spread too high -> short it; too low -> long it
            action = "ENTER"

    return dict(
        today=today_ts.strftime("%Y-%m-%d"), symbol_a=a, symbol_b=b,
        price_a=price_a, price_b=price_b, beta=beta_today,
        spread=spread_today, spread_denoised=denoised_today, zscore=z_today,
        action=action, direction=direction,
        entry_notional=entry_notional, size_mult=size_mult,
    )


def _submit_leg(client: TradingClient, symbol: str, dollars: float, side: OrderSide, price: float):
    """Alpaca rejects fractional/notional orders that open or increase a
    short position ("fractional orders cannot be sold short") -- only whole-
    share quantities are allowed to sell short. Long (BUY) legs can stay
    notional (fractional), but any SELL-to-open leg must be a whole-share
    qty order, floored down from the target dollar amount.
    """
    if side == OrderSide.SELL:
        qty = int(dollars // price)
        if qty < 1:
            raise ValueError(f"{symbol}: target short size ${dollars:.2f} < 1 share at ${price:.2f}, cannot short")
        return client.submit_order(MarketOrderRequest(
            symbol=symbol, qty=qty, side=side, time_in_force=TimeInForce.DAY))
    return client.submit_order(MarketOrderRequest(
        symbol=symbol, notional=round(dollars, 2), side=side, time_in_force=TimeInForce.DAY))


def target_equity_fraction(size_mult: float) -> float:
    """Linear map from the [1, V2_SIZE_CAP] conviction multiplier to
    [MIN_EQUITY_FRACTION, MAX_EQUITY_FRACTION] of total account equity.
    """
    span = V2_SIZE_CAP - 1.0
    t = (size_mult - 1.0) / span if span > 0 else 1.0
    t = min(max(t, 0.0), 1.0)
    return MIN_EQUITY_FRACTION + t * (MAX_EQUITY_FRACTION - MIN_EQUITY_FRACTION)


def place_entry(client: TradingClient, sig: dict) -> dict:
    a, b, direction = sig["symbol_a"], sig["symbol_b"], sig["direction"]

    equity = float(client.get_account().equity)
    fraction = target_equity_fraction(sig["size_mult"])
    trade_dollars = equity * fraction
    units = trade_dollars / sig["entry_notional"]
    dollar_b = units * sig["price_b"]
    dollar_a = units * sig["beta"] * sig["price_a"]

    # direction +1 = long spread = long b, short beta*a. direction -1 = short spread = short b, long a.
    side_b = OrderSide.BUY if direction == 1 else OrderSide.SELL
    side_a = OrderSide.SELL if direction == 1 else OrderSide.BUY

    order_b = _submit_leg(client, b, dollar_b, side_b, sig["price_b"])
    try:
        order_a = _submit_leg(client, a, dollar_a, side_a, sig["price_a"])
    except Exception:
        # second leg failed -- roll back the first leg rather than leave an
        # unhedged, naked single-leg position sitting on the account.
        client.close_position(b)
        raise

    return dict(order_b_id=str(order_b.id), order_a_id=str(order_a.id),
                dollar_b=round(dollar_b, 2), dollar_a=round(dollar_a, 2), direction=direction,
                equity_at_entry=round(equity, 2), equity_fraction=round(fraction, 3), units=units)


def place_exit(client: TradingClient, sig: dict) -> dict:
    a, b = sig["symbol_a"], sig["symbol_b"]
    results = {}
    for sym in (a, b):
        try:
            client.close_position(sym)
            results[sym] = "closed"
        except Exception as e:
            results[sym] = f"error: {e}"
    return results


def main():
    client = get_client()
    state = load_state()
    today_iso = pd.Timestamp.today().strftime("%Y-%m-%d")

    print(f"Alpaca paper live run (v2 track only): {today_iso}\n")

    for label, cfg in CONFIGS.items():
        pair_state = state.get(label, dict(position=0, cumulative_realized_pnl=0.0,
                                             last_processed_date=None, trade_log=[]))
        for k, v in dict(entry_date=None, entry_spread=None,
                          entry_notional_used=None, units_used=None,
                          cumulative_realized_pnl=0.0).items():
            pair_state.setdefault(k, v)

        sig = compute_today_signal(label, cfg, today_iso, pair_state)

        z_str = f"{sig['zscore']:+.3f}" if sig["zscore"] == sig["zscore"] else "nan"
        print(f"{cfg['label']:12s} {sig['today']}  {sig['symbol_a']}=${sig['price_a']:.2f} "
              f"{sig['symbol_b']}=${sig['price_b']:.2f}  beta={sig['beta']:.4f}  "
              f"spread={sig['spread']:+.4f}  denoised={sig['spread_denoised']}  "
              f"z={z_str}  (entry={cfg['z_entry']}, exit={cfg['z_exit']})  action={sig['action']}")

        if pair_state["last_processed_date"] == sig["today"]:
            print(f"{'':12s} already processed for {sig['today']}, skipping\n")
            log_signal_row(label, cfg, sig, "SKIP_ALREADY_PROCESSED")
            state[label] = pair_state
            continue

        if sig["action"] == "EXIT":
            result = place_exit(client, sig)
            units = pair_state["units_used"]
            # spread pnl per unit = position * (exit_spread - entry_spread), same convention as backtest();
            # also charge the same entry+exit transaction cost convention (5bps/leg against real notional).
            spread_pnl = pair_state["position"] * (sig["spread"] - pair_state["entry_spread"])
            cost_frac = DEFAULT_TRANSACTION_COST_BPS / 10_000.0
            exit_cost = cost_frac * (sig["entry_notional"] or pair_state["entry_notional_used"])
            entry_cost = cost_frac * pair_state["entry_notional_used"]
            pnl_dollars = (spread_pnl - entry_cost - exit_cost) * units
            pair_state["cumulative_realized_pnl"] += pnl_dollars
            pair_state["position"] = 0
            pair_state["entry_date"] = None
            pair_state["trade_log"].append(dict(
                exit_date=sig["today"], pnl_dollars=round(pnl_dollars, 2),
                cumulative_realized_pnl=round(pair_state["cumulative_realized_pnl"], 2), alpaca=result))
            print(f"{'':12s} -> EXIT   pnl=${pnl_dollars:+.2f}  "
                  f"cumulative=${pair_state['cumulative_realized_pnl']:.2f}  {result}\n")
            log_signal_row(label, cfg, sig, "EXIT")

        elif sig["action"] == "ENTER":
            try:
                result = place_entry(client, sig)
            except Exception as e:
                print(f"{'':12s} -> ENTER FAILED (rolled back): {e}\n")
                log_signal_row(label, cfg, sig, "ENTER_FAILED")
                pair_state["last_processed_date"] = sig["today"]
                state[label] = pair_state
                continue
            pair_state["position"] = sig["direction"]
            pair_state["entry_date"] = sig["today"]
            pair_state["entry_spread"] = sig["spread"]
            pair_state["entry_notional_used"] = sig["entry_notional"]
            pair_state["units_used"] = result["units"]
            pair_state["trade_log"].append(dict(entry_date=sig["today"], **result))
            print(f"{'':12s} -> ENTER dir={sig['direction']:+d}  equity=${result['equity_at_entry']:.2f}  "
                  f"fraction={result['equity_fraction']:.1%}  "
                  f"${result['dollar_b']:.2f} {sig['symbol_b']} / ${result['dollar_a']:.2f} {sig['symbol_a']}\n")
            log_signal_row(label, cfg, sig, f"ENTER_{'LONG' if sig['direction'] == 1 else 'SHORT'}")

        else:
            print(f"{'':12s} -> {sig['action']} (position={pair_state['position']})\n")
            log_signal_row(label, cfg, sig, sig["action"])

        pair_state["last_processed_date"] = sig["today"]
        state[label] = pair_state

    save_state(state)
    print(f"\nwrote {STATE_PATH}")


if __name__ == "__main__":
    main()
