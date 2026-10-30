# Live Paper-Trading Status

_Auto-updated by `scripts/alpaca_paper_trade.py` -- last run 2026-10-30._

**This is a status page, not a results page.** Per [PAPER_TRADING_PROTOCOL.md](PAPER_TRADING_PROTOCOL.md), a minimum 3-month evaluation window was pre-committed before any Sharpe/P&L number here would be statistically meaningful -- showing one earlier would just be noise dressed up as a result. This page shows the system is genuinely running against a live Alpaca paper account, nothing more, until that window closes.

- **Days into evaluation window**: 69 / 90 (21 remaining before a go/no-go is even eligible)
- **Account equity**: $97,990.57

## Open positions

| symbol | side | qty | market value |
|---|---|---|---|
| CSX | short | -97 | $-5,008.11 |
| JBLU | long | 1225.636363637 | $3,707.55 |
| KO | long | 56.466431849 | $5,351.89 |
| LUV | short | -152 | $-6,560.32 |
| MA | short | -15 | $-9,612.08 |
| PEP | short | -39 | $-5,339.30 |
| UNP | long | 16.647169494 | $5,072.56 |
| V | long | 23.419251671 | $9,722.27 |

## Per-pair status

| pair | position | z_entry | z_exit | realized P&L | unrealized P&L |
|---|---|---|---|---|---|
| V / MA | short spread | 1.0 | 0.5 | $79.89 | $-17.54 |
| KO / PEP | short spread | 1.0 | 0.25 | $395.91 | $2.12 |
| UNP / CSX | short spread | 1.5 | 0.5 | $123.37 | $98.13 |
| LUV / JBLU | long spread | 1.5 | 0.5 | $0.00 | $-2,435.67 |
