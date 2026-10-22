# Live Paper-Trading Status

_Auto-updated by `scripts/alpaca_paper_trade.py` -- last run 2026-10-22._

**This is a status page, not a results page.** Per [PAPER_TRADING_PROTOCOL.md](PAPER_TRADING_PROTOCOL.md), a minimum 3-month evaluation window was pre-committed before any Sharpe/P&L number here would be statistically meaningful -- showing one earlier would just be noise dressed up as a result. This page shows the system is genuinely running against a live Alpaca paper account, nothing more, until that window closes.

- **Days into evaluation window**: 61 / 90 (29 remaining before a go/no-go is even eligible)
- **Account equity**: $97,991.96

## Open positions

| symbol | side | qty | market value |
|---|---|---|---|
| JBLU | long | 1225.636363637 | $3,646.27 |
| KO | long | 56.466431849 | $5,345.39 |
| LUV | short | -152 | $-6,355.12 |
| PEP | short | -39 | $-5,393.90 |

## Per-pair status

| pair | position | z_entry | z_exit | realized P&L | unrealized P&L |
|---|---|---|---|---|---|
| V / MA | flat | 1.0 | 0.5 | $52.38 | $0.00 |
| KO / PEP | short spread | 1.0 | 0.25 | $395.91 | $-58.97 |
| UNP / CSX | flat | 1.5 | 0.5 | $123.37 | $0.00 |
| LUV / JBLU | long spread | 1.5 | 0.5 | $0.00 | $-2,291.75 |
