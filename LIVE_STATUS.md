# Live Paper-Trading Status

_Auto-updated by `scripts/alpaca_paper_trade.py` -- last run 2026-11-04._

**This is a status page, not a results page.** Per [PAPER_TRADING_PROTOCOL.md](PAPER_TRADING_PROTOCOL.md), a minimum 3-month evaluation window was pre-committed before any Sharpe/P&L number here would be statistically meaningful -- showing one earlier would just be noise dressed up as a result. This page shows the system is genuinely running against a live Alpaca paper account, nothing more, until that window closes.

- **Days into evaluation window**: 74 / 90 (16 remaining before a go/no-go is even eligible)
- **Account equity**: $97,931.30

## Open positions

| symbol | side | qty | market value |
|---|---|---|---|
| JBLU | long | 1225.636363637 | $4,191.80 |
| KO | long | 56.466431849 | $5,376.73 |
| LUV | short | -152 | $-6,927.40 |
| MA | short | -15 | $-9,936.30 |
| PEP | short | -39 | $-5,483.79 |
| V | long | 23.419251671 | $10,033.63 |

## Per-pair status

| pair | position | z_entry | z_exit | realized P&L | unrealized P&L |
|---|---|---|---|---|---|
| V / MA | short spread | 1.0 | 0.5 | $79.89 | $-30.40 |
| KO / PEP | short spread | 1.0 | 0.25 | $395.91 | $-117.53 |
| UNP / CSX | long spread | 1.5 | 0.5 | $228.00 | $0.00 |
| LUV / JBLU | flat | 1.5 | 0.5 | $-556.78 | $-2,318.50 |
