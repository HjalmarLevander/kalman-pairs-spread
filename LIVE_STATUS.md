# Live Paper-Trading Status

_Auto-updated by `scripts/alpaca_paper_trade.py` -- last run 2026-10-28._

**This is a status page, not a results page.** Per [PAPER_TRADING_PROTOCOL.md](PAPER_TRADING_PROTOCOL.md), a minimum 3-month evaluation window was pre-committed before any Sharpe/P&L number here would be statistically meaningful -- showing one earlier would just be noise dressed up as a result. This page shows the system is genuinely running against a live Alpaca paper account, nothing more, until that window closes.

- **Days into evaluation window**: 67 / 90 (23 remaining before a go/no-go is even eligible)
- **Account equity**: $97,616.39

## Open positions

| symbol | side | qty | market value |
|---|---|---|---|
| CSX | short | -97 | $-5,049.34 |
| JBLU | long | 1225.636363637 | $3,474.68 |
| KO | long | 56.466431849 | $5,213.55 |
| LUV | short | -152 | $-6,625.68 |
| PEP | short | -39 | $-5,176.47 |
| UNP | long | 16.647169494 | $4,995.82 |

## Per-pair status

| pair | position | z_entry | z_exit | realized P&L | unrealized P&L |
|---|---|---|---|---|---|
| V / MA | flat | 1.0 | 0.5 | $79.89 | $0.00 |
| KO / PEP | short spread | 1.0 | 0.25 | $395.91 | $26.61 |
| UNP / CSX | short spread | 1.5 | 0.5 | $123.37 | $-19.84 |
| LUV / JBLU | long spread | 1.5 | 0.5 | $0.00 | $-2,733.90 |
