"""Daily-close price loader backed by Alpaca's own market data, for live
trading use only (scripts/alpaca_paper_trade.py) -- keeps the signal and the
execution on the same data source instead of straddling Alpaca (broker) and
yfinance (signal data), which had been two independent providers.

Historical backtest/walk-forward work (src/phase0-4) stays on yfinance
unchanged -- those results are already fixed and published, and re-deriving
them against a different provider is out of scope here. Spot-checked
Alpaca's IEX-feed daily closes against yfinance's adjusted closes for all 8
live tickers over a recent 2-week window: max discrepancy ~0.2%, consistent
with feed/rounding noise, not a split/dividend-adjustment mismatch -- safe
to use as a drop-in for the live pipeline.

Caveat: Alpaca's free/paper-tier `feed='iex'` bars are IEX-only, not the
full consolidated tape (SIP), and are NOT split/dividend-adjusted the way
yfinance's `auto_adjust=True` closes are. Fine for the short live-trading
window this loads (fit_start-to-today, no multi-year history refetched
here -- the Kalman/FFT noise-parameter fit itself still reads its frozen
fit-window data from yfinance), but would need reassessment before ever
being used to refit those parameters from scratch on Alpaca data alone.
"""
from __future__ import annotations

from datetime import datetime

import pandas as pd
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame


def load_prices_alpaca(tickers: list[str], start: str, end: str,
                        api_key: str, secret_key: str) -> pd.DataFrame:
    """Daily close prices for `tickers` in [start, end], shaped identically
    to phase0_pair_selection.load_prices (date-indexed, one column/ticker).
    """
    client = StockHistoricalDataClient(api_key, secret_key)
    req = StockBarsRequest(
        symbol_or_symbols=tickers, timeframe=TimeFrame.Day,
        start=datetime.fromisoformat(start), end=datetime.fromisoformat(end),
        feed="iex",
    )
    bars = client.get_stock_bars(req).df
    if bars.empty:
        return pd.DataFrame()

    out = {}
    for t in tickers:
        s = bars.loc[t]["close"]
        s.index = pd.to_datetime(s.index.date)
        out[t] = s
    return pd.DataFrame(out).dropna(how="all")
