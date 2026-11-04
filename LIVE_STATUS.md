# Live Paper-Trading Status

_Auto-updated by `scripts/alpaca_paper_trade.py` -- last run 2026-11-04._

**This is a status page, not a results page.** Per [PAPER_TRADING_PROTOCOL.md](PAPER_TRADING_PROTOCOL.md), a minimum 3-month evaluation window was pre-committed before any Sharpe/P&L number here would be statistically meaningful -- showing one earlier would just be noise dressed up as a result. This page shows the system is genuinely running against a live Alpaca paper account, nothing more, until that window closes.

- **Days into evaluation window**: 74 / 90 (16 remaining before a go/no-go is even eligible)
- **Account equity**: $97,891.00

## Open positions

| symbol | side | qty | market value |
|---|---|---|---|
| CSX | long | 123.068560235 | $6,309.11 |
| KO | long | 56.466431849 | $5,428.12 |
| MA | short | -15 | $-10,047.30 |
| PEP | short | -39 | $-5,592.99 |
| UNP | short | -21 | $-6,414.66 |
| V | long | 23.419251671 | $10,139.37 |

## Per-pair status

| pair | position | z_entry | z_exit | realized P&L | unrealized P&L |
|---|---|---|---|---|---|
| V / MA | short spread | 1.0 | 0.5 | $79.89 | $-35.66 |
| KO / PEP | short spread | 1.0 | 0.25 | $395.91 | $-175.34 |
| UNP / CSX | long spread | 1.5 | 0.5 | $228.00 | $28.59 |
| LUV / JBLU | flat | 1.5 | 0.5 | $-556.78 | $0.00 |
