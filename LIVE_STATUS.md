# Live Paper-Trading Status

_Auto-updated by `scripts/alpaca_paper_trade.py` -- last run 2026-11-05._

**This is a status page, not a results page.** Per [PAPER_TRADING_PROTOCOL.md](PAPER_TRADING_PROTOCOL.md), a minimum 3-month evaluation window was pre-committed before any Sharpe/P&L number here would be statistically meaningful -- showing one earlier would just be noise dressed up as a result. This page shows the system is genuinely running against a live Alpaca paper account, nothing more, until that window closes.

- **Days into evaluation window**: 75 / 90 (15 remaining before a go/no-go is even eligible)
- **Account equity**: $97,987.49

## Open positions

| symbol | side | qty | market value |
|---|---|---|---|
| CSX | long | 123.068560235 | $6,437.10 |
| KO | long | 56.466431849 | $5,475.55 |
| MA | short | -15 | $-10,105.32 |
| PEP | short | -39 | $-5,639.40 |
| UNP | short | -21 | $-6,451.94 |
| V | long | 23.419251671 | $10,202.36 |

## Per-pair status

| pair | position | z_entry | z_exit | realized P&L | unrealized P&L |
|---|---|---|---|---|---|
| V / MA | short spread | 1.0 | 0.5 | $79.89 | $-30.69 |
| KO / PEP | short spread | 1.0 | 0.25 | $395.91 | $-174.32 |
| UNP / CSX | long spread | 1.5 | 0.5 | $228.00 | $119.31 |
| LUV / JBLU | flat | 1.5 | 0.5 | $-556.78 | $0.00 |
