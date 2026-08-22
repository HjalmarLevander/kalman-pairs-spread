"""Builds reports/strategy_explainer.html: a plain-English walkthrough of the
mechanism (spread -> FFT waves -> denoised pattern -> z-score -> decision),
worked win/loss examples pulled from real trade history, and the current
testing-data (out-of-sample) performance + market-correlation results.

Follows Robin Swarm's html_builder layout rules even though this was written
directly (no API credits this session): CSS grid/flexbox only, no
position:absolute for layout, no fixed heights on text containers,
box-sizing:border-box, overflow-wrap on variable text, overflow-x:auto on
wide content, single-column stacked-panel structure.

Pure string templating over precomputed JSON -- no LLM calls, re-runnable.
"""
import json
import os

import numpy as np

ROOT = os.path.join(os.path.dirname(__file__), "..")
REPORTS = os.path.join(ROOT, "reports")


def line_path(values, width=640, height=140, pad=8, y_range=None):
    vals = [v for v in values if v is not None]
    lo, hi = (y_range if y_range else (min(vals), max(vals)))
    span = (hi - lo) or 1.0
    n = len(values)
    pts = []
    for i, v in enumerate(values):
        if v is None:
            continue
        x = pad + (width - 2 * pad) * i / max(n - 1, 1)
        y = pad + (height - 2 * pad) * (1 - (v - lo) / span)
        pts.append(f"{x:.1f},{y:.1f}")
    zero_y = pad + (height - 2 * pad) * (1 - (0 - lo) / span) if lo <= 0 <= hi else None
    return " ".join(pts), zero_y, lo, hi


def marker(values, idx, width=640, height=140, pad=8, y_range=None):
    vals = [v for v in values if v is not None]
    lo, hi = (y_range if y_range else (min(vals), max(vals)))
    span = (hi - lo) or 1.0
    n = len(values)
    x = pad + (width - 2 * pad) * idx / max(n - 1, 1)
    y = pad + (height - 2 * pad) * (1 - (values[idx] - lo) / span)
    return x, y


def bar_chart_svg(powers, kept_mask, threshold, width=640, height=140, pad_l=8, pad_r=8, pad_t=8, pad_b=8):
    n = len(powers)
    max_p = max(powers) or 1.0
    bar_w = (width - pad_l - pad_r) / n * 0.7
    gap = (width - pad_l - pad_r) / n
    bars = []
    for i, p in enumerate(powers):
        h = (height - pad_t - pad_b) * (p / max_p)
        x = pad_l + i * gap
        y = height - pad_b - h
        color = "var(--series-denoised)" if kept_mask[i] else "var(--muted-text)"
        opacity = "0.95" if kept_mask[i] else "0.35"
        bars.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{h:.1f}" fill="{color}" opacity="{opacity}" rx="1.5"/>')
    thresh_y = height - pad_b - (height - pad_t - pad_b) * (threshold / max_p)
    bars.append(f'<line x1="{pad_l}" y1="{thresh_y:.1f}" x2="{width-pad_r}" y2="{thresh_y:.1f}" stroke="var(--warning)" stroke-width="1" stroke-dasharray="4,3"/>')
    return "".join(bars)


def fnum(v, d=2):
    return f"{v:.{d}f}" if v is not None else "—"


def trade_walkthrough_svg(slice_rows, entry_offset, exit_offset, direction_label, width=640, height=160):
    spreads = [r["spread_denoised"] for r in slice_rows]
    path, zero_y, lo, hi = line_path(spreads, width, height, y_range=None)
    ex, ey = marker(spreads, entry_offset, width, height)
    xx, xy = marker(spreads, exit_offset, width, height)
    entry_color = "var(--critical)" if direction_label == "SHORT" else "var(--good)"
    return dict(path=path, zero_y=zero_y, entry_x=ex, entry_y=ey, exit_x=xx, exit_y=xy, entry_color=entry_color, width=width, height=height)


def main():
    explainer = json.load(open(os.path.join(REPORTS, "explainer_data.json")))
    perf = json.load(open(os.path.join(REPORTS, "testing_performance.json")))

    # --- FFT demo charts ---
    fft = explainer["fft_demo"]
    raw_path, raw_zero, raw_lo, raw_hi = line_path(fft["raw_window"])
    den_path, den_zero, den_lo, den_hi = line_path(fft["denoised_window"], y_range=(raw_lo, raw_hi))
    kept_mask = [True] * fft["n_kept"] + [False] * (fft["n_total"] - fft["n_kept"])
    # power spectrum isn't sorted by kept/discarded in frequency order; rebuild mask aligned to actual bins
    powers = fft["power_spectrum"]
    kept_mask = [p >= fft["threshold"] for p in powers]
    bars_svg = bar_chart_svg(powers, kept_mask, fft["threshold"])

    # --- win/loss trade walkthroughs ---
    win = explainer["win_example"]
    loss = explainer["loss_example"]
    win_chart = trade_walkthrough_svg(win["slice"], win["entry_offset"], win["exit_offset"], "SHORT" if win["slice"][win["entry_offset"]]["decision"]=="ENTER_SHORT" else "LONG")
    loss_chart = trade_walkthrough_svg(loss["slice"], loss["entry_offset"], loss["exit_offset"], "SHORT" if loss["slice"][loss["entry_offset"]]["decision"]=="ENTER_SHORT" else "LONG")

    win_entry_row = win["slice"][win["entry_offset"]]
    win_exit_row = win["slice"][win["exit_offset"]]
    loss_entry_row = loss["slice"][loss["entry_offset"]]
    loss_exit_row = loss["slice"][loss["exit_offset"]]
    win_direction = "SHORT the spread (sell MA, buy V)" if win_entry_row["decision"] == "ENTER_SHORT" else "LONG the spread (buy MA, sell V)"
    loss_direction = "SHORT the spread (sell MA, buy V)" if loss_entry_row["decision"] == "ENTER_SHORT" else "LONG the spread (buy MA, sell V)"

    # --- equity curve: strategy vs SPY, common OOS window ---
    eq = perf["equity_chart"]
    strat_path, strat_zero, s_lo, s_hi = line_path(eq["strategy"], y_range=(min(eq["strategy"]+eq["spy"]), max(eq["strategy"]+eq["spy"])))
    spy_path, spy_zero, _, _ = line_path(eq["spy"], y_range=(min(eq["strategy"]+eq["spy"]), max(eq["strategy"]+eq["spy"])))

    pp = perf["per_pair_stats"]
    pc = perf["per_pair_corr"]

    html = f"""<title>Mean Reversion, Explained</title>
<style>
  :root {{
    --bg: #f9f9f7; --surface: #fcfcfb; --surface-2: #f0efec; --border: rgba(11,11,11,0.10);
    --text: #0b0b0b; --muted-text: #52514e; --axis: #898781; --grid: #e1e0d9;
    --series-a: #2a78d6; --series-b: #eb6834; --series-denoised: #1baf7a;
    --good: #0ca30c; --critical: #d03b3b; --warning: #eda100;
    --mono: "SF Mono", "Menlo", "Consolas", monospace; --sans: -apple-system, "Segoe UI", system-ui, sans-serif;
  }}
  @media (prefers-color-scheme: dark) {{
    :root:not([data-theme="light"]) {{
      --bg: #0d0d0d; --surface: #1a1a19; --surface-2: #232322; --border: rgba(255,255,255,0.10);
      --text: #ffffff; --muted-text: #c3c2b7; --axis: #898781; --grid: #2c2c2a;
      --series-a: #3987e5; --series-b: #d95926; --series-denoised: #199e70;
      --good: #0ca30c; --critical: #e66767; --warning: #c98500;
    }}
  }}
  :root[data-theme="dark"] {{
    --bg: #0d0d0d; --surface: #1a1a19; --surface-2: #232322; --border: rgba(255,255,255,0.10);
    --text: #ffffff; --muted-text: #c3c2b7; --axis: #898781; --grid: #2c2c2a;
    --series-a: #3987e5; --series-b: #d95926; --series-denoised: #199e70;
    --good: #0ca30c; --critical: #e66767; --warning: #c98500;
  }}

  * {{ box-sizing: border-box; }}
  html, body {{ margin: 0; padding: 0; background: var(--bg); color: var(--text); }}
  body {{ font-family: var(--sans); line-height: 1.6; }}
  main {{ max-width: 900px; margin: 0 auto; padding: 40px 24px 80px; display: flex; flex-direction: column; gap: 44px; }}

  h1, h2, h3 {{ text-wrap: balance; margin: 0; overflow-wrap: break-word; }}
  h1 {{ font-size: 1.7rem; font-weight: 700; }}
  h2 {{ font-size: 1.25rem; font-weight: 700; }}
  h3 {{ font-size: 1rem; font-weight: 700; color: var(--muted-text); }}
  p {{ margin: 0; overflow-wrap: break-word; }}
  .muted {{ color: var(--muted-text); }}
  code, .mono {{ font-family: var(--mono); font-variant-numeric: tabular-nums; }}

  header {{ display: flex; flex-direction: column; gap: 14px; border-bottom: 1px solid var(--border); padding-bottom: 32px; }}
  .eyebrow {{ font-family: var(--mono); font-size: 0.75rem; color: var(--muted-text); text-transform: uppercase; letter-spacing: 0.1em; }}
  header p.lede {{ max-width: 68ch; color: var(--muted-text); font-size: 1.02rem; }}

  .verdict {{
    display: flex; flex-wrap: wrap; gap: 10px; align-items: center;
    background: color-mix(in srgb, var(--good) 12%, var(--surface));
    border: 1px solid color-mix(in srgb, var(--good) 35%, var(--border));
    border-radius: 10px; padding: 14px 18px; font-family: var(--mono); font-size: 0.88rem; color: var(--good);
  }}
  .verdict .dot {{ width: 8px; height: 8px; border-radius: 50%; background: var(--good); flex: 0 0 auto; }}

  section {{ display: flex; flex-direction: column; gap: 16px; min-width: 0; }}
  .step-num {{ font-family: var(--mono); font-size: 0.75rem; color: var(--series-a); }}

  .step-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 14px; }}
  .step-card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 16px; display: flex; flex-direction: column; gap: 8px; min-width: 0; }}
  .step-card p {{ font-size: 0.85rem; color: var(--muted-text); }}

  .chart-card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 18px 20px; display: flex; flex-direction: column; gap: 10px; min-width: 0; }}
  .chart-card svg {{ width: 100%; height: auto; display: block; overflow-x: auto; }}
  .chart-legend {{ display: flex; gap: 16px; font-size: 0.76rem; color: var(--muted-text); flex-wrap: wrap; }}
  .chart-legend .swatch {{ display: inline-block; width: 10px; height: 2px; margin-right: 6px; vertical-align: middle; }}

  .trade-card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 20px; display: flex; flex-direction: column; gap: 14px; min-width: 0; }}
  .trade-card.win {{ border-color: color-mix(in srgb, var(--good) 40%, var(--border)); }}
  .trade-card.loss {{ border-color: color-mix(in srgb, var(--critical) 40%, var(--border)); }}
  .trade-header {{ display: flex; justify-content: space-between; align-items: baseline; flex-wrap: wrap; gap: 8px; }}
  .trade-pnl {{ font-family: var(--mono); font-size: 1.1rem; font-weight: 700; }}
  .trade-pnl.pos {{ color: var(--good); }}
  .trade-pnl.neg {{ color: var(--critical); }}
  .reasoning-list {{ display: flex; flex-direction: column; gap: 10px; margin: 0; padding: 0; list-style: none; }}
  .reasoning-list li {{ display: flex; gap: 10px; font-size: 0.88rem; }}
  .reasoning-list .tag {{
    font-family: var(--mono); font-size: 0.68rem; padding: 2px 8px; border-radius: 5px; height: fit-content;
    background: var(--surface-2); color: var(--muted-text); white-space: nowrap;
  }}

  .table-scroll {{ overflow-x: auto; border: 1px solid var(--border); border-radius: 10px; }}
  table {{ border-collapse: collapse; width: 100%; min-width: 480px; font-size: 0.85rem; }}
  thead th {{ background: var(--surface-2); color: var(--muted-text); text-align: left; padding: 9px 12px; border-bottom: 1px solid var(--border); white-space: nowrap; }}
  tbody td {{ padding: 8px 12px; border-bottom: 1px solid var(--border); white-space: nowrap; }}
  tbody tr:last-child td {{ border-bottom: none; }}
  .pos {{ color: var(--good); }}
  .neg {{ color: var(--critical); }}

  .callout {{ border-radius: 10px; padding: 16px 20px; display: flex; gap: 12px; border: 1px solid var(--border); background: var(--surface); }}
  .callout.warn {{ border-color: color-mix(in srgb, var(--warning) 45%, var(--border)); background: color-mix(in srgb, var(--warning) 8%, var(--surface)); }}
  .callout .body {{ font-size: 0.88rem; overflow-wrap: break-word; }}

  footer {{ border-top: 1px solid var(--border); padding-top: 20px; font-size: 0.78rem; color: var(--muted-text); display: flex; flex-direction: column; gap: 6px; }}
</style>

<main>

  <header>
    <span class="eyebrow">Kalman-Filtered Pairs Spread &middot; Plain-English Walkthrough</span>
    <h1>Betting that two related stocks snap back together, explained step by step</h1>
    <p class="lede">This strategy finds two economically-linked stocks, tracks the gap between their prices, and
    bets that when the gap gets unusually wide, it will shrink back to normal. Below: the mechanism in plain
    English, the actual math turned into pictures, a real trade that worked, a real trade that didn't, and how
    it's performed on data none of this was built or tuned on.</p>
    <div class="verdict">
      <span class="dot"></span>
      On testing data never used to fit the model ({perf['common_oos_start']} to {perf['today']}, {perf['n_days']} trading days):
      turned $1000 into ${perf['combined_final']:,.0f} (Sharpe {perf['combined_sharpe']}),
      with {perf['correlation_oos']:.3f} correlation to the S&amp;P 500 &mdash; essentially zero.
    </div>
  </header>

  <section>
    <h2>The five-step mechanism</h2>
    <div class="step-grid">
      <div class="step-card">
        <span class="step-num">STEP 1</span>
        <h3>Pick two linked stocks</h3>
        <p>Two companies whose businesses move together for real economic reasons &mdash; e.g. two payment
        networks, two beverage makers. Screened and statistically confirmed, not assumed.</p>
      </div>
      <div class="step-card">
        <span class="step-num">STEP 2</span>
        <h3>Track the gap between them</h3>
        <p>The "spread" = one stock's price minus a ratio (&beta;) of the other's. That ratio drifts over time,
        so it's re-estimated every day (a Kalman filter) rather than fixed once.</p>
      </div>
      <div class="step-card">
        <span class="step-num">STEP 3</span>
        <h3>Filter out the noise</h3>
        <p>The raw gap is jittery. Break it into frequency "waves" (FFT), keep only the strongest ones, discard
        the rest &mdash; leaving a cleaner picture of the real pattern.</p>
      </div>
      <div class="step-card">
        <span class="step-num">STEP 4</span>
        <h3>Wait for it to stretch far</h3>
        <p>Compare today's (cleaned) gap to its own recent normal range. When it's stretched unusually far in
        either direction, that's the signal.</p>
      </div>
      <div class="step-card">
        <span class="step-num">STEP 5</span>
        <h3>Bet on the snap-back</h3>
        <p>Buy the cheap side, sell the expensive side, in the exact ratio that makes the bet neutral to the
        overall market. Close the position once the gap normalizes.</p>
      </div>
    </div>
  </section>

  <section>
    <h2>Seeing the mean reversion</h2>
    <p class="muted">A real 60-day window of the raw V/MA spread &mdash; the actual gap between the two stocks'
    prices, scaled by the hedge ratio. Notice it wanders, but keeps being pulled back toward a central level
    rather than drifting off forever. That pull-back tendency is the entire trade.</p>
    <div class="chart-card">
      <svg viewBox="0 0 640 140" preserveAspectRatio="none">
        {f'<line x1="8" y1="{raw_zero:.1f}" x2="632" y2="{raw_zero:.1f}" stroke="var(--grid)" stroke-width="1" stroke-dasharray="3,3" />' if raw_zero else ''}
        <polyline points="{raw_path}" fill="none" stroke="var(--series-a)" stroke-width="1.8" />
      </svg>
      <div class="chart-legend"><span><span class="swatch" style="background:var(--series-a)"></span>raw spread (V/MA), 60 trading days</span></div>
    </div>
  </section>

  <section>
    <h2>Breaking it into waves</h2>
    <p class="muted">The same 60-day window, decomposed into its {fft['n_total']} underlying frequency
    components (a Fourier transform). Each bar is how much of the spread's total wiggle that frequency accounts
    for. Only the <span style="color:var(--series-denoised)">tallest {fft['n_kept']} bars</span> &mdash; above
    the dashed threshold &mdash; are kept; the rest are treated as noise and zeroed out.</p>
    <div class="chart-card">
      <svg viewBox="0 0 640 140" preserveAspectRatio="none">{bars_svg}</svg>
      <div class="chart-legend">
        <span><span class="swatch" style="background:var(--series-denoised)"></span>kept ({fft['n_kept']} of {fft['n_total']})</span>
        <span><span class="swatch" style="background:var(--muted-text);opacity:0.5"></span>discarded as noise</span>
      </div>
    </div>
  </section>

  <section>
    <h2>The simplified pattern</h2>
    <p class="muted">Reconstructing the spread from only the kept waves produces a cleaner version of the same
    60 days &mdash; the underlying pull-toward-center pattern, with the high-frequency jitter removed.</p>
    <div class="chart-card">
      <svg viewBox="0 0 640 140" preserveAspectRatio="none">
        <polyline points="{raw_path}" fill="none" stroke="var(--muted-text)" stroke-width="1" opacity="0.6" />
        <polyline points="{den_path}" fill="none" stroke="var(--series-denoised)" stroke-width="2" />
      </svg>
      <div class="chart-legend">
        <span><span class="swatch" style="background:var(--muted-text)"></span>raw</span>
        <span><span class="swatch" style="background:var(--series-denoised)"></span>denoised (kept waves only)</span>
      </div>
    </div>
  </section>

  <section>
    <h2>A real winning trade, step by step</h2>
    <div class="trade-card win">
      <div class="trade-header">
        <h3>V / MA &middot; {win_entry_row['date']} &rarr; {win_exit_row['date']} ({win['exit_offset']-win['entry_offset']} trading days)</h3>
        <span class="trade-pnl pos">+${win['pnl']:.2f} on $250 allocated</span>
      </div>
      <div class="chart-card" style="padding:12px 14px;">
        <svg viewBox="0 0 640 160" preserveAspectRatio="none">
          {f'<line x1="8" y1="{win_chart["zero_y"]:.1f}" x2="632" y2="{win_chart["zero_y"]:.1f}" stroke="var(--grid)" stroke-width="1" stroke-dasharray="3,3" />' if win_chart['zero_y'] else ''}
          <polyline points="{win_chart['path']}" fill="none" stroke="var(--series-a)" stroke-width="1.8" />
          <circle cx="{win_chart['entry_x']:.1f}" cy="{win_chart['entry_y']:.1f}" r="4.5" fill="{win_chart['entry_color']}" />
          <circle cx="{win_chart['exit_x']:.1f}" cy="{win_chart['exit_y']:.1f}" r="4.5" fill="var(--warning)" />
        </svg>
      </div>
      <ul class="reasoning-list">
        <li><span class="tag">ENTRY</span><span>On {win_entry_row['date']}, the denoised spread's z-score hit {win_entry_row['zscore']:.2f} &mdash;
        beyond the entry threshold. Decision: <strong>{win_direction}</strong>. V was priced at ${win_entry_row['price_a']}, MA at ${win_entry_row['price_b']}, hedge ratio &beta;={win_entry_row['beta']:.3f}.</span></li>
        <li><span class="tag">HOLD</span><span>Position held for {win['exit_offset']-win['entry_offset']} trading days while the spread moved back toward its recent average.</span></li>
        <li><span class="tag">EXIT</span><span>On {win_exit_row['date']}, z-score had fallen to {win_exit_row['zscore']:.2f} &mdash; inside the exit band.
        Position closed. Realized profit: <strong class="pos">+${win['pnl']:.2f}</strong> on the $250 allocated to this pair.</span></li>
      </ul>
    </div>
  </section>

  <section>
    <h2>A real losing trade &mdash; why it doesn't always work</h2>
    <p class="muted">Not every trade reverts on schedule. This is the actual mechanism failing, not a
    hypothetical: the spread kept drifting instead of snapping back, and the position was closed at a loss when
    the z-score itself unwound past our exit band on the wrong side, rather than reverting to the entry level.</p>
    <div class="trade-card loss">
      <div class="trade-header">
        <h3>V / MA &middot; {loss_entry_row['date']} &rarr; {loss_exit_row['date']} ({loss['exit_offset']-loss['entry_offset']} trading days)</h3>
        <span class="trade-pnl neg">${loss['pnl']:.2f} on $250 allocated</span>
      </div>
      <div class="chart-card" style="padding:12px 14px;">
        <svg viewBox="0 0 640 160" preserveAspectRatio="none">
          {f'<line x1="8" y1="{loss_chart["zero_y"]:.1f}" x2="632" y2="{loss_chart["zero_y"]:.1f}" stroke="var(--grid)" stroke-width="1" stroke-dasharray="3,3" />' if loss_chart['zero_y'] else ''}
          <polyline points="{loss_chart['path']}" fill="none" stroke="var(--series-a)" stroke-width="1.8" />
          <circle cx="{loss_chart['entry_x']:.1f}" cy="{loss_chart['entry_y']:.1f}" r="4.5" fill="{loss_chart['entry_color']}" />
          <circle cx="{loss_chart['exit_x']:.1f}" cy="{loss_chart['exit_y']:.1f}" r="4.5" fill="var(--warning)" />
        </svg>
      </div>
      <ul class="reasoning-list">
        <li><span class="tag">ENTRY</span><span>On {loss_entry_row['date']}, z-score was {loss_entry_row['zscore']:.2f}, past the entry threshold.
        Decision: <strong>{loss_direction}</strong>. V at ${loss_entry_row['price_a']}, MA at ${loss_entry_row['price_b']}, &beta;={loss_entry_row['beta']:.3f}.</span></li>
        <li><span class="tag">WHAT WENT WRONG</span><span>Rather than reverting toward the entry level, the spread continued moving and
        eventually crossed back the other way, past the exit band on the losing side &mdash; the relationship didn't behave the way its recent
        history suggested it would.</span></li>
        <li><span class="tag">EXIT</span><span>Closed on {loss_exit_row['date']} for <strong class="neg">${loss['pnl']:.2f}</strong>.
        This is the real, irreducible risk: mean reversion is a tendency estimated from history, not a guarantee for any single trade.</span></li>
      </ul>
    </div>
  </section>

  <section>
    <h2>Performance on testing data</h2>
    <p class="muted">"Testing data" here means data that came <em>after</em> each pair's parameters were frozen
    &mdash; none of it was used to choose the hedge ratio, the denoising threshold, or the entry/exit rules.
    Combined across all four validated pairs, $250 allocated to each:</p>
    <div class="chart-card">
      <svg viewBox="0 0 640 160" preserveAspectRatio="none">
        <polyline points="{spy_path}" fill="none" stroke="var(--series-b)" stroke-width="1.8" />
        <polyline points="{strat_path}" fill="none" stroke="var(--series-a)" stroke-width="2.2" />
      </svg>
      <div class="chart-legend">
        <span><span class="swatch" style="background:var(--series-a)"></span>this strategy ($1000 &rarr; ${perf['combined_final']:,.0f})</span>
        <span><span class="swatch" style="background:var(--series-b)"></span>SPY, same window ($1000 &rarr; ${perf['spy_final']:,.0f})</span>
      </div>
    </div>
    <div class="table-scroll">
      <table>
        <thead><tr><th>pair</th><th>P&amp;L on $250</th><th>Sharpe</th><th>half-life</th><th>correlation to SPY</th></tr></thead>
        <tbody>
        {"".join(f'''<tr><td>{s["label"]}</td><td class="{"pos" if s["total_pnl"]>=0 else "neg"}">{"+" if s["total_pnl"]>=0 else ""}${s["total_pnl"]:.2f}</td><td>{s["sharpe"]}</td><td>{s["half_life"]}d</td><td>{pc[k]:+.4f}</td></tr>''' for k, s in pp.items())}
        <tr style="font-weight:700"><td>Combined</td><td class="pos">+${perf['combined_total_pnl']:.2f}</td><td>{perf['combined_sharpe']}</td><td>&mdash;</td><td>{perf['correlation_oos']:+.4f}</td></tr>
        </tbody>
      </table>
    </div>
  </section>

  <section>
    <h2>Why near-zero correlation is the actual point</h2>
    <p>SPY earned far more in raw terms over this same window ({perf['spy_total_return_pct']}% vs.
    {perf['combined_total_pnl']/1000*100:.1f}%) &mdash; this was never going to out-earn a strong bull market, and
    it shouldn't be judged as if that were the goal. What it does instead: its daily returns have essentially no
    relationship to the market's (correlation {perf['correlation_oos']:.3f}), confirmed individually for every
    pair including the more cyclical airline pair (LUV/JBLU: {pc['LUV_JBLU']:+.4f}). A return stream this
    independent of market direction is valuable specifically as a diversifier &mdash; it doesn't need to beat
    the market to be worth holding alongside it.</p>
  </section>

  <div class="callout warn">
    <span class="body"><strong>Read alongside, not instead of, the full research log.</strong> This page is the
    plain-English walkthrough. The detailed methodology &mdash; walk-forward validation, the transaction-cost
    bug that was caught and fixed, leverage economics, bet-sizing analysis, and every retraction along the way
    &mdash; lives in the companion strategy report. Nothing here has been paper-traded or run with real money
    yet.</span>
  </div>

  <footer>
    <span>Generated from <code>reports/explainer_data.json</code> and <code>reports/testing_performance.json</code>
    by <code>scripts/build_explainer_report.py</code> &mdash; static HTML, no build step, following the same
    layout discipline as Robin Swarm's html_builder (grid/flexbox only, no fixed heights on text, box-sizing
    border-box) even though this was written directly rather than through the live pipeline (no API credits
    this session).</span>
  </footer>

</main>
"""
    out_path = os.path.join(REPORTS, "strategy_explainer.html")
    with open(out_path, "w") as f:
        f.write(html)
    print(f"wrote {out_path} ({len(html)/1024:.0f} KB)")


if __name__ == "__main__":
    main()
