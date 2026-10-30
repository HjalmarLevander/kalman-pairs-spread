# Live Paper-Trading Status

_Auto-updated by `scripts/alpaca_paper_trade.py` -- last run 2026-10-30._

**This is a status page, not a results page.** Per [PAPER_TRADING_PROTOCOL.md](PAPER_TRADING_PROTOCOL.md), a minimum 3-month evaluation window was pre-committed before any Sharpe/P&L number here would be statistically meaningful -- showing one earlier would just be noise dressed up as a result. This page shows the system is genuinely running against a live Alpaca paper account, nothing more, until that window closes.

- **Days into evaluation window**: 69 / 90 (21 remaining before a go/no-go is even eligible)
- **Account equity**: $97,924.90

## Open positions

| symbol | side | qty | market value |
|---|---|---|---|
| CSX | short | -97 | $-4,995.02 |
| JBLU | long | 1225.636363637 | $3,560.47 |
| KO | long | 56.466431849 | $5,328.74 |
| LUV | short | -152 | $-6,424.28 |
| MA | short | -15 | $-9,564.75 |
| PEP | short | -39 | $-5,361.91 |
| UNP | long | 16.647169494 | $5,033.02 |
| V | long | 23.419251671 | $9,692.53 |

## Per-pair status

| pair | position | z_entry | z_exit | realized P&L | unrealized P&L |
|---|---|---|---|---|---|
| V / MA | short spread | 1.0 | 0.5 | $79.89 | $0.05 |
| KO / PEP | short spread | 1.0 | 0.25 | $395.91 | $-43.65 |
| UNP / CSX | short spread | 1.5 | 0.5 | $123.37 | $71.69 |
| LUV / JBLU | long spread | 1.5 | 0.5 | $0.00 | $-2,446.71 |
