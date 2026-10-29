# Live Paper-Trading Status

_Auto-updated by `scripts/alpaca_paper_trade.py` -- last run 2026-10-29._

**This is a status page, not a results page.** Per [PAPER_TRADING_PROTOCOL.md](PAPER_TRADING_PROTOCOL.md), a minimum 3-month evaluation window was pre-committed before any Sharpe/P&L number here would be statistically meaningful -- showing one earlier would just be noise dressed up as a result. This page shows the system is genuinely running against a live Alpaca paper account, nothing more, until that window closes.

- **Days into evaluation window**: 68 / 90 (22 remaining before a go/no-go is even eligible)
- **Account equity**: $97,593.72

## Open positions

| symbol | side | qty | market value |
|---|---|---|---|
| CSX | short | -97 | $-5,122.57 |
| JBLU | long | 1225.636363637 | $3,603.49 |
| KO | long | 56.466431849 | $5,240.08 |
| LUV | short | -152 | $-6,725.24 |
| PEP | short | -39 | $-5,227.56 |
| UNP | long | 16.647169494 | $5,041.68 |

## Per-pair status

| pair | position | z_entry | z_exit | realized P&L | unrealized P&L |
|---|---|---|---|---|---|
| V / MA | flat | 1.0 | 0.5 | $79.89 | $0.00 |
| KO / PEP | short spread | 1.0 | 0.25 | $395.91 | $2.05 |
| UNP / CSX | short spread | 1.5 | 0.5 | $123.37 | $-47.21 |
| LUV / JBLU | long spread | 1.5 | 0.5 | $0.00 | $-2,704.65 |
