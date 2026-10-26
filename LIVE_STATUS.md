# Live Paper-Trading Status

_Auto-updated by `scripts/alpaca_paper_trade.py` -- last run 2026-10-26._

**This is a status page, not a results page.** Per [PAPER_TRADING_PROTOCOL.md](PAPER_TRADING_PROTOCOL.md), a minimum 3-month evaluation window was pre-committed before any Sharpe/P&L number here would be statistically meaningful -- showing one earlier would just be noise dressed up as a result. This page shows the system is genuinely running against a live Alpaca paper account, nothing more, until that window closes.

- **Days into evaluation window**: 65 / 90 (25 remaining before a go/no-go is even eligible)
- **Account equity**: $97,061.83

## Open positions

| symbol | side | qty | market value |
|---|---|---|---|
| CSX | short | -97 | $-4,970.77 |
| JBLU | long | 1225.636363637 | $2,892.50 |
| KO | long | 56.466431849 | $5,219.19 |
| LUV | short | -152 | $-6,523.84 |
| MA | short | -15 | $-9,218.62 |
| PEP | short | -39 | $-5,272.80 |
| UNP | long | 16.647169494 | $4,926.98 |
| V | long | 23.719954401 | $9,588.67 |

## Per-pair status

| pair | position | z_entry | z_exit | realized P&L | unrealized P&L |
|---|---|---|---|---|---|
| V / MA | short spread | 1.0 | 0.5 | $52.38 | $8.00 |
| KO / PEP | short spread | 1.0 | 0.25 | $395.91 | $-64.08 |
| UNP / CSX | short spread | 1.5 | 0.5 | $123.37 | $-10.11 |
| LUV / JBLU | long spread | 1.5 | 0.5 | $0.00 | $-3,214.24 |
