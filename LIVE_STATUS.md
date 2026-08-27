# Live Paper-Trading Status

_Auto-updated by `scripts/alpaca_paper_trade.py` -- last run 2026-08-27._

**This is a status page, not a results page.** Per [PAPER_TRADING_PROTOCOL.md](PAPER_TRADING_PROTOCOL.md), a minimum 3-month evaluation window was pre-committed before any Sharpe/P&L number here would be statistically meaningful -- showing one earlier would just be noise dressed up as a result. This page shows the system is genuinely running against a live Alpaca paper account, nothing more, until that window closes.

- **Days into evaluation window**: 5 / 90 (85 remaining before a go/no-go is even eligible)
- **Account equity**: $100,031.57

## Open positions

| symbol | side | qty | market value |
|---|---|---|---|
| CSX | long | 7.25982575 | $373.77 |
| KO | long | 82.328068996 | $7,381.12 |
| PEP | short | -51 | $-7,157.34 |
| UNP | short | -1 | $-308.13 |

## Per-pair status

| pair | position | z_entry | z_exit |
|---|---|---|---|
| V / MA | flat | 1.0 | 0.5 |
| KO / PEP | short spread | 1.0 | 0.25 |
| UNP / CSX | long spread | 1.5 | 0.5 |
| LUV / JBLU | flat | 1.5 | 0.5 |
