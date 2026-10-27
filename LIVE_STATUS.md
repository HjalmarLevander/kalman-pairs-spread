# Live Paper-Trading Status

_Auto-updated by `scripts/alpaca_paper_trade.py` -- last run 2026-10-27._

**This is a status page, not a results page.** Per [PAPER_TRADING_PROTOCOL.md](PAPER_TRADING_PROTOCOL.md), a minimum 3-month evaluation window was pre-committed before any Sharpe/P&L number here would be statistically meaningful -- showing one earlier would just be noise dressed up as a result. This page shows the system is genuinely running against a live Alpaca paper account, nothing more, until that window closes.

- **Days into evaluation window**: 66 / 90 (24 remaining before a go/no-go is even eligible)
- **Account equity**: $97,431.08

## Open positions

| symbol | side | qty | market value |
|---|---|---|---|
| CSX | short | -97 | $-4,974.16 |
| JBLU | long | 1225.636363637 | $3,229.55 |
| KO | long | 56.466431849 | $5,212.42 |
| LUV | short | -152 | $-6,495.72 |
| PEP | short | -39 | $-5,246.86 |
| UNP | long | 16.647169494 | $4,921.82 |

## Per-pair status

| pair | position | z_entry | z_exit | realized P&L | unrealized P&L |
|---|---|---|---|---|---|
| V / MA | flat | 1.0 | 0.5 | $79.89 | $0.00 |
| KO / PEP | short spread | 1.0 | 0.25 | $395.91 | $-44.92 |
| UNP / CSX | short spread | 1.5 | 0.5 | $123.37 | $-18.66 |
| LUV / JBLU | long spread | 1.5 | 0.5 | $0.00 | $-2,849.07 |
