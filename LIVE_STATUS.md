# Live Paper-Trading Status

_Auto-updated by `scripts/alpaca_paper_trade.py` -- last run 2026-09-04._

**This is a status page, not a results page.** Per [PAPER_TRADING_PROTOCOL.md](PAPER_TRADING_PROTOCOL.md), a minimum 3-month evaluation window was pre-committed before any Sharpe/P&L number here would be statistically meaningful -- showing one earlier would just be noise dressed up as a result. This page shows the system is genuinely running against a live Alpaca paper account, nothing more, until that window closes.

- **Days into evaluation window**: 13 / 90 (77 remaining before a go/no-go is even eligible)
- **Account equity**: $100,077.33

## Open positions

| symbol | side | qty | market value |
|---|---|---|---|
| KO | long | 82.328068996 | $7,300.44 |
| MA | long | 9.279674126 | $5,394.27 |
| PEP | short | -51 | $-7,026.27 |
| V | short | -14 | $-5,257.28 |

## Per-pair status

| pair | position | z_entry | z_exit |
|---|---|---|---|
| V / MA | long spread | 1.0 | 0.5 |
| KO / PEP | short spread | 1.0 | 0.25 |
| UNP / CSX | flat | 1.5 | 0.5 |
| LUV / JBLU | flat | 1.5 | 0.5 |
