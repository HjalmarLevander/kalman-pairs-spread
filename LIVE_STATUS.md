# Live Paper-Trading Status

_Auto-updated by `scripts/alpaca_paper_trade.py` -- last run 2026-11-02._

**This is a status page, not a results page.** Per [PAPER_TRADING_PROTOCOL.md](PAPER_TRADING_PROTOCOL.md), a minimum 3-month evaluation window was pre-committed before any Sharpe/P&L number here would be statistically meaningful -- showing one earlier would just be noise dressed up as a result. This page shows the system is genuinely running against a live Alpaca paper account, nothing more, until that window closes.

- **Days into evaluation window**: 72 / 90 (18 remaining before a go/no-go is even eligible)
- **Account equity**: $97,771.99

## Open positions

| symbol | side | qty | market value |
|---|---|---|---|
| CSX | short | -97 | $-5,062.49 |
| JBLU | long | 1225.636363637 | $3,738.19 |
| KO | long | 56.466431849 | $5,338.90 |
| LUV | short | -152 | $-6,653.04 |
| MA | short | -15 | $-9,703.88 |
| PEP | short | -39 | $-5,419.44 |
| UNP | long | 16.647169494 | $5,077.39 |
| V | long | 23.419251671 | $9,799.90 |

## Per-pair status

| pair | position | z_entry | z_exit | realized P&L | unrealized P&L |
|---|---|---|---|---|---|
| V / MA | short spread | 1.0 | 0.5 | $79.89 | $-31.70 |
| KO / PEP | short spread | 1.0 | 0.25 | $395.91 | $-91.01 |
| UNP / CSX | flat | 1.5 | 0.5 | $228.00 | $48.58 |
| LUV / JBLU | long spread | 1.5 | 0.5 | $0.00 | $-2,497.75 |
