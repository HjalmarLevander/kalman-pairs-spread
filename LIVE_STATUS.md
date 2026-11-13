# Live Paper-Trading Status

_Auto-updated by `scripts/alpaca_paper_trade.py` -- last run 2026-11-13._

**This is a status page, not a results page.** Per [PAPER_TRADING_PROTOCOL.md](PAPER_TRADING_PROTOCOL.md), a minimum 3-month evaluation window was pre-committed before any Sharpe/P&L number here would be statistically meaningful -- showing one earlier would just be noise dressed up as a result. This page shows the system is genuinely running against a live Alpaca paper account, nothing more, until that window closes.

- **Days into evaluation window**: 83 / 90 (7 remaining before a go/no-go is even eligible)
- **Account equity**: $98,006.43

## Open positions

| symbol | side | qty | market value |
|---|---|---|---|
| KO | long | 56.466431849 | $5,569.85 |
| MA | short | -15 | $-9,898.05 |
| PEP | short | -39 | $-5,618.15 |
| V | long | 23.419251671 | $9,957.05 |

## Per-pair status

| pair | position | z_entry | z_exit | realized P&L | unrealized P&L |
|---|---|---|---|---|---|
| V / MA | short spread | 1.0 | 0.5 | $79.89 | $-68.73 |
| KO / PEP | short spread | 1.0 | 0.25 | $395.91 | $-58.77 |
| UNP / CSX | flat | 1.5 | 0.5 | $304.54 | $0.00 |
| LUV / JBLU | flat | 1.5 | 0.5 | $-556.78 | $0.00 |
