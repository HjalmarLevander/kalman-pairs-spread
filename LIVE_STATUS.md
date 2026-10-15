# Live Paper-Trading Status

_Auto-updated by `scripts/alpaca_paper_trade.py` -- last run 2026-10-15._

**This is a status page, not a results page.** Per [PAPER_TRADING_PROTOCOL.md](PAPER_TRADING_PROTOCOL.md), a minimum 3-month evaluation window was pre-committed before any Sharpe/P&L number here would be statistically meaningful -- showing one earlier would just be noise dressed up as a result. This page shows the system is genuinely running against a live Alpaca paper account, nothing more, until that window closes.

- **Days into evaluation window**: 54 / 90 (36 remaining before a go/no-go is even eligible)
- **Account equity**: $98,349.10

## Open positions

| symbol | side | qty | market value |
|---|---|---|---|
| JBLU | long | 1225.636363637 | $3,719.81 |
| KO | short | -74 | $-6,932.69 |
| LUV | short | -152 | $-5,990.32 |
| PEP | long | 50.496842105 | $6,662.05 |

## Per-pair status

| pair | position | z_entry | z_exit | realized P&L | unrealized P&L |
|---|---|---|---|---|---|
| V / MA | flat | 1.0 | 0.5 | $9.62 | $0.00 |
| KO / PEP | long spread | 1.0 | 0.25 | $241.84 | $-1.29 |
| UNP / CSX | flat | 1.5 | 0.5 | $123.37 | $0.00 |
| LUV / JBLU | long spread | 1.5 | 0.5 | $0.00 | $-1,853.41 |
