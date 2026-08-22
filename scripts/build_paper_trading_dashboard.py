"""Builds reports/paper_trading_dashboard.html from reports/paper_trading_ledger.json.
Re-run this after every `python -m scripts.paper_trade` to refresh the page,
then republish the artifact. Shows v1 (frozen baseline) and v2 (proportional
sizing + compounding) side by side per PAPER_TRADING_PROTOCOL.md.
"""
import json
import os

ROOT = os.path.join(os.path.dirname(__file__), "..")
REPORTS = os.path.join(ROOT, "reports")
LEDGER_PATH = os.path.join(REPORTS, "paper_trading_ledger.json")
OUT_PATH = os.path.join(REPORTS, "paper_trading_dashboard.html")


def line_path(values, width=600, height=120, pad=8):
    vals = [v for v in values if v is not None]
    if not vals:
        return "", None
    lo, hi = min(vals), max(vals)
    if lo == hi:
        lo -= 1
        hi += 1
    span = hi - lo
    n = len(values)
    pts = []
    for i, v in enumerate(values):
        if v is None:
            continue
        x = pad + (width - 2 * pad) * i / max(n - 1, 1)
        y = pad + (height - 2 * pad) * (1 - (v - lo) / span)
        pts.append(f"{x:.1f},{y:.1f}")
    zero_y = pad + (height - 2 * pad) * (1 - (0 - lo) / span) if lo <= 0 <= hi else None
    return " ".join(pts), zero_y


def main():
    ledger = json.load(open(LEDGER_PATH))
    any_rows = any(v["rows"] for v in ledger.values())

    n_days = max((len(v["rows"]) for v in ledger.values()), default=0)
    last_date = None
    for v in ledger.values():
        if v["rows"]:
            last_date = v["rows"][-1]["date"]

    v1_combined_series = []
    if any_rows:
        max_len = max(len(v["rows"]) for v in ledger.values())
        for i in range(max_len):
            total = sum(v["rows"][i]["cum_pnl"] for v in ledger.values() if len(v["rows"]) > i)
            v1_combined_series.append(1000 + total)
    v2_combined_capital = sum(v["v2"]["current_capital"] for v in ledger.values())
    v1_combined_final = 1000 + sum(v["rows"][-1]["cum_pnl"] for v in ledger.values() if v["rows"]) if any_rows else 1000

    pair_rows_html = ""
    for key, v in ledger.items():
        rows = v["rows"]
        v2 = v["v2"]
        if rows:
            latest = rows[-1]
            status = f"""
              <div class="stat-row"><span class="k">Latest</span><span class="v">{latest['date']}</span></div>
              <div class="stat-row"><span class="k">z-score</span><span class="v">{latest['zscore']}</span></div>
              <div class="stat-row"><span class="k">Position</span><span class="v">{latest['position']:+d}</span></div>
              <div class="stat-row"><span class="k">Decision</span><span class="v">{latest['decision']}</span></div>
              <div class="stat-row"><span class="k">v1 cum P&amp;L</span><span class="v {'pos' if latest['cum_pnl']>=0 else 'neg'}">${latest['cum_pnl']:+.2f}</span></div>
            """
        else:
            status = '<p class="muted" style="font-size:0.85rem">No trading day logged yet &mdash; awaiting next market close.</p>'
        pair_rows_html += f"""
        <div class="card">
          <span class="kicker">{v['label']}</span>
          {status}
          <div class="stat-row"><span class="k">v2 capital</span><span class="v">${v2['current_capital']:.2f} ({v2['n_trades']} trades)</span></div>
        </div>"""

    v1_path, v1_zero = line_path(v1_combined_series) if v1_combined_series else ("", None)

    html = f"""<title>Paper Trading Dashboard</title>
<style>
  :root {{
    --bg: #f9f9f7; --surface: #fcfcfb; --surface-2: #f0efec; --border: rgba(11,11,11,0.10);
    --text: #0b0b0b; --muted-text: #52514e; --good: #0ca30c; --critical: #d03b3b; --accent: #2a78d6;
    --mono: "SF Mono", "Menlo", "Consolas", monospace; --sans: -apple-system, "Segoe UI", system-ui, sans-serif;
  }}
  @media (prefers-color-scheme: dark) {{
    :root:not([data-theme="light"]) {{
      --bg: #0d0d0d; --surface: #1a1a19; --surface-2: #232322; --border: rgba(255,255,255,0.10);
      --text: #ffffff; --muted-text: #c3c2b7; --good: #0ca30c; --critical: #e66767; --accent: #3987e5;
    }}
  }}
  :root[data-theme="dark"] {{
    --bg: #0d0d0d; --surface: #1a1a19; --surface-2: #232322; --border: rgba(255,255,255,0.10);
    --text: #ffffff; --muted-text: #c3c2b7; --good: #0ca30c; --critical: #e66767; --accent: #3987e5;
  }}
  * {{ box-sizing: border-box; }}
  html, body {{ margin: 0; padding: 0; background: var(--bg); color: var(--text); }}
  body {{ font-family: var(--sans); line-height: 1.5; }}
  main {{ max-width: 900px; margin: 0 auto; padding: 32px 20px 60px; display: flex; flex-direction: column; gap: 28px; }}
  h1 {{ font-size: 1.4rem; margin: 0; }}
  p {{ margin: 0; overflow-wrap: break-word; }}
  .muted {{ color: var(--muted-text); }}
  .mono {{ font-family: var(--mono); font-variant-numeric: tabular-nums; }}
  header {{ display: flex; flex-direction: column; gap: 10px; border-bottom: 1px solid var(--border); padding-bottom: 20px; }}
  .status-banner {{ background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 14px 18px; font-family: var(--mono); font-size: 0.85rem; }}
  .card-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; }}
  .card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 16px; display: flex; flex-direction: column; gap: 6px; min-width: 0; }}
  .kicker {{ font-size: 0.72rem; color: var(--muted-text); text-transform: uppercase; letter-spacing: 0.05em; }}
  .stat-row {{ display: flex; justify-content: space-between; font-size: 0.82rem; gap: 8px; }}
  .stat-row .k {{ color: var(--muted-text); }}
  .stat-row .v {{ font-family: var(--mono); }}
  .pos {{ color: var(--good); }}
  .neg {{ color: var(--critical); }}
  .chart-card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 16px 18px; display: flex; flex-direction: column; gap: 8px; }}
  .chart-card svg {{ width: 100%; height: auto; display: block; }}
  footer {{ border-top: 1px solid var(--border); padding-top: 14px; font-size: 0.72rem; color: var(--muted-text); }}
</style>
<main>
  <header>
    <h1>Paper Trading &mdash; v1 (frozen) vs v2 (proportional sizing + compounding)</h1>
    <p class="muted">Started 2026-08-22. See PAPER_TRADING_PROTOCOL.md for the rules. No real money, no broker
    &mdash; a daily computed signal on real market data, logged forward.</p>
  </header>

  <div class="status-banner">
    {"Trading days logged: " + str(n_days) + " &middot; last update: " + str(last_date) if any_rows else "No trading days logged yet &mdash; markets closed since evaluation start. Run `python -m scripts.paper_trade` after the next market close."}
  </div>

  <section>
    <div class="card-grid">
      {pair_rows_html}
    </div>
  </section>

  {"" if not v1_combined_series else f'''
  <section class="chart-card">
    <span class="kicker">v1 combined capital ($1000 start)</span>
    <svg viewBox="0 0 600 120" preserveAspectRatio="none">
      {f'<line x1="8" y1="{v1_zero:.1f}" x2="592" y2="{v1_zero:.1f}" stroke="var(--border)" stroke-width="1" stroke-dasharray="3,3" />' if v1_zero else ''}
      <polyline points="{v1_path}" fill="none" stroke="var(--accent)" stroke-width="2" />
    </svg>
    <p class="muted" style="font-size:0.8rem">Current: ${v1_combined_final:,.2f}</p>
  </section>
  '''}

  <section class="chart-card">
    <span class="kicker">v2 combined capital</span>
    <p class="mono" style="font-size:1.3rem; margin:0;">${v2_combined_capital:,.2f}</p>
    <p class="muted" style="font-size:0.8rem">Started at $1000. Compounds per-pair as trades close.</p>
  </section>

  <footer>Generated from reports/paper_trading_ledger.json by scripts/build_paper_trading_dashboard.py. Re-run
  both after each day's `python -m scripts.paper_trade` to refresh.</footer>
</main>
"""
    with open(OUT_PATH, "w") as f:
        f.write(html)
    print(f"wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
