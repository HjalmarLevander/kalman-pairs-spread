# Live Paper-Trading Status

_Auto-updated by `scripts/alpaca_paper_trade.py` -- last run 2026-11-17._

**This is a status page, not a results page.** Per [PAPER_TRADING_PROTOCOL.md](PAPER_TRADING_PROTOCOL.md), a minimum 3-month evaluation window was pre-committed before any Sharpe/P&L number here would be statistically meaningful -- showing one earlier would just be noise dressed up as a result. This page shows the system is genuinely running against a live Alpaca paper account, nothing more, until that window closes.

- **Days into evaluation window**: 87 / 90 (3 remaining before a go/no-go is even eligible)
- **Account equity**: $98,128.00

## Open positions

| symbol | side | qty | market value |
|---|---|---|---|
| KO | long | 56.466431849 | $5,615.02 |
| MA | short | -15 | $-9,737.55 |
| PEP | short | -39 | $-5,588.31 |
| V | long | 23.419251671 | $9,843.11 |

## Per-pair status

| pair | position | z_entry | z_exit | realized P&L | unrealized P&L |
|---|---|---|---|---|---|
| V / MA | short spread | 1.0 | 0.5 | $79.89 | $-22.17 |
| KO / PEP | short spread | 1.0 | 0.25 | $395.91 | $16.24 |
| UNP / CSX | flat | 1.5 | 0.5 | $304.54 | $0.00 |
| LUV / JBLU | flat | 1.5 | 0.5 | $-556.78 | $0.00 |
