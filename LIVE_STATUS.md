# Live Paper-Trading Status

_Auto-updated by `scripts/alpaca_paper_trade.py` -- last run 2026-11-12._

**This is a status page, not a results page.** Per [PAPER_TRADING_PROTOCOL.md](PAPER_TRADING_PROTOCOL.md), a minimum 3-month evaluation window was pre-committed before any Sharpe/P&L number here would be statistically meaningful -- showing one earlier would just be noise dressed up as a result. This page shows the system is genuinely running against a live Alpaca paper account, nothing more, until that window closes.

- **Days into evaluation window**: 82 / 90 (8 remaining before a go/no-go is even eligible)
- **Account equity**: $97,993.38

## Open positions

| symbol | side | qty | market value |
|---|---|---|---|
| KO | long | 56.466431849 | $5,532.02 |
| MA | short | -15 | $-9,943.20 |
| PEP | short | -39 | $-5,601.96 |
| V | long | 23.419251671 | $10,010.79 |

## Per-pair status

| pair | position | z_entry | z_exit | realized P&L | unrealized P&L |
|---|---|---|---|---|---|
| V / MA | short spread | 1.0 | 0.5 | $79.89 | $-60.14 |
| KO / PEP | short spread | 1.0 | 0.25 | $395.91 | $-80.41 |
| UNP / CSX | flat | 1.5 | 0.5 | $304.54 | $0.00 |
| LUV / JBLU | flat | 1.5 | 0.5 | $-556.78 | $0.00 |
