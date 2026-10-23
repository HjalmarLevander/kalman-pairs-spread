# Live Paper-Trading Status

_Auto-updated by `scripts/alpaca_paper_trade.py` -- last run 2026-10-23._

**This is a status page, not a results page.** Per [PAPER_TRADING_PROTOCOL.md](PAPER_TRADING_PROTOCOL.md), a minimum 3-month evaluation window was pre-committed before any Sharpe/P&L number here would be statistically meaningful -- showing one earlier would just be noise dressed up as a result. This page shows the system is genuinely running against a live Alpaca paper account, nothing more, until that window closes.

- **Days into evaluation window**: 62 / 90 (28 remaining before a go/no-go is even eligible)
- **Account equity**: $97,653.38

## Open positions

| symbol | side | qty | market value |
|---|---|---|---|
| JBLU | long | 1225.636363637 | $3,143.76 |
| KO | long | 56.466431849 | $5,342.85 |
| LUV | short | -152 | $-6,184.88 |
| MA | short | -15 | $-9,428.33 |
| PEP | short | -39 | $-5,379.07 |
| V | long | 23.719954401 | $9,771.91 |

## Per-pair status

| pair | position | z_entry | z_exit | realized P&L | unrealized P&L |
|---|---|---|---|---|---|
| V / MA | short spread | 1.0 | 0.5 | $52.38 | $-18.47 |
| KO / PEP | short spread | 1.0 | 0.25 | $395.91 | $-46.69 |
| UNP / CSX | short spread | 1.5 | 0.5 | $123.37 | $0.00 |
| LUV / JBLU | long spread | 1.5 | 0.5 | $0.00 | $-2,624.02 |
