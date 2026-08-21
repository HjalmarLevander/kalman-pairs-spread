"""Phase 0 EDA: empirical pair selection for the Kalman-filtered pairs-spread
strategy (see ../SPEC.md).

Screens a candidate universe of economically-linked pairs by (1) rolling
return correlation across multiple lookback windows, (2) Engle-Granger
cointegration on price levels, and (3) rolling-window OLS hedge-ratio
stability, then writes a ranked shortlist.

No-lookahead note: SELECTION_START/SELECTION_END bound every price fetch in
this module. Only data inside that window is ever touched, so the shortlist
this script produces can be validated later on a later, still-unseen window
without having leaked information from it during selection.

Multiple-comparison caveat: ~12 pairs x 4 correlation windows plus a
cointegration p-value each gives many chances for a spuriously "significant"
pair to surface, and autocorrelated financial returns make naive p-values
overconfident. No formal correction is applied here -- treat this shortlist
as a candidate list to confirm out-of-sample, not a proof.
"""
from __future__ import annotations

import csv
import os
from dataclasses import dataclass, asdict

import numpy as np
import pandas as pd
import yfinance as yf
from statsmodels.tsa.stattools import coint

CANDIDATE_PAIRS: list[tuple[str, str]] = [
    ("XOM", "CVX"),   # oil majors
    ("KO", "PEP"),    # beverages
    ("GS", "MS"),     # investment banks
    ("HD", "LOW"),    # home improvement retail
    ("UPS", "FDX"),   # logistics/parcel
    ("V", "MA"),      # payment networks
    ("SPY", "VOO"),   # near-identical S&P 500 ETFs
    ("GLD", "GDX"),   # gold price vs. gold miners
    ("USO", "XLE"),   # oil price ETF vs. energy sector ETF
    ("JPM", "BAC"),   # money-center banks
    ("PG", "CL"),     # household/personal-care staples
    ("MSFT", "GOOGL"),  # large-cap tech (weaker linkage, deliberate negative control)
    # widened universe -- more sectors, more dual-listed / near-substitute pairs
    ("WMT", "TGT"),   # big-box retail
    ("MCD", "YUM"),   # quick-service restaurants
    ("PFE", "MRK"),   # pharma majors
    ("JNJ", "ABT"),   # diversified healthcare
    ("T", "VZ"),      # telecom carriers
    ("CVS", "WBA"),   # pharmacy retail
    ("C", "WFC"),     # money-center banks (2nd tier)
    ("CAT", "DE"),    # heavy equipment
    ("UNP", "CSX"),   # rail freight
    ("COST", "WMT"),  # big-box / warehouse retail
    ("INTC", "AMD"),  # semiconductors (weaker linkage, competitive not complementary)
    ("SLB", "HAL"),   # oilfield services
    ("MET", "PRU"),   # life insurance
    ("EMR", "ITW"),   # industrial conglomerates
    ("KMB", "PG"),    # household paper/personal-care staples
    ("AEP", "DUK"),   # regulated utilities
    ("SO", "D"),      # regulated utilities (2nd pair)
    ("NEE", "AEP"),   # utilities, renewables-leaning vs. traditional
    # commodities & crypto -- no pure-play liquid US-listed tin or aluminum
    # ETF exists on yfinance; DBB (broad base metals) / CPER (copper) is the
    # closest honest proxy, not a real aluminum/tin pair
    ("GLD", "SLV"),      # gold vs. silver, the classic precious-metals pair
    ("GLD", "PPLT"),     # gold vs. platinum
    ("SLV", "PPLT"),     # silver vs. platinum
    ("PALL", "PPLT"),    # palladium vs. platinum (both auto-catalyst metals)
    ("DBB", "CPER"),     # broad base-metals ETF vs. copper (aluminum/tin proxy, not a true pair)
    ("BTC-USD", "ETH-USD"),  # crypto majors
    # second widening -- more sectors not yet covered, to find independent
    # candidates for the walk-forward bar rather than mine the same pool harder
    ("DAL", "UAL"),   # airlines
    ("DAL", "AAL"),   # airlines (2nd pair)
    ("LUV", "JBLU"),  # airlines (low-cost)
    ("AMAT", "LRCX"), # semiconductor equipment
    ("ALL", "PGR"),   # auto insurance
    ("TRV", "CB"),    # property & casualty insurance
    ("MO", "PM"),     # tobacco (same company pre/post 2008 spinoff)
    ("HON", "MMM"),   # diversified industrials
    ("TJX", "ROST"),  # off-price apparel retail
    ("BLK", "TROW"),  # asset managers
    ("COF", "DFS"),   # consumer credit/card issuers
    ("AXP", "COF"),   # consumer credit (2nd pair)
    ("DHI", "LEN"),   # homebuilders
    ("PHM", "LEN"),   # homebuilders (2nd pair)
    ("IP", "WY"),     # paper & forest products
    ("DD", "LYB"),    # chemicals
    ("LIN", "APD"),   # industrial gases
    ("DIS", "CMCSA"), # diversified media
    ("KR", "SYY"),    # food distribution/retail
    ("XLF", "KRE"),   # financials sector vs. regional banks
    ("XLI", "XLB"),   # industrials vs. materials sector ETFs
    ("IWM", "MDY"),   # small-cap vs. mid-cap index ETFs
    ("EFA", "VEA"),   # developed-markets ex-US ETFs (near-duplicate, same family as SPY/VOO)
]

# No-lookahead boundary. Every fetch in this module is clipped to this
# window; bump SELECTION_END later for an out-of-sample rerun on fresh data.
SELECTION_START = "2015-01-01"
SELECTION_END = "2021-12-31"

CORRELATION_WINDOWS = (30, 90, 180, 365)
CORRELATION_CONSISTENCY_MIN = 0.5  # min rolling corr required across all windows to flag "consistent"
HEDGE_RATIO_WINDOW = 90

REPORT_PATH = os.path.join(os.path.dirname(__file__), "..", "reports", "phase0_pair_shortlist.csv")


@dataclass
class PairMetrics:
    pair: str
    corr_30d_mean: float
    corr_90d_mean: float
    corr_180d_mean: float
    corr_365d_mean: float
    corr_min_across_windows: float
    corr_consistent: bool
    coint_pvalue: float
    beta_mean: float
    beta_cv: float
    beta_autocorr: float
    note: str


def load_prices(tickers: list[str], start: str = SELECTION_START, end: str = SELECTION_END) -> pd.DataFrame:
    """Adjusted close prices for `tickers`, strictly within [start, end].

    Enforces the no-lookahead constraint in one place: any caller asking for
    dates outside [SELECTION_START, SELECTION_END] is a bug, not a feature,
    so this is the only function in the module allowed to call yfinance.
    """
    raw = yf.download(tickers, start=start, end=end, auto_adjust=True, progress=False)
    if raw.empty:
        return pd.DataFrame()
    close = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw[["Close"]].rename(columns={"Close": tickers[0]})
    return close.dropna(how="all")


def rolling_correlation(x: pd.Series, y: pd.Series, windows: tuple[int, ...] = CORRELATION_WINDOWS) -> dict[int, float]:
    """Mean rolling return-correlation per window length.

    A single high correlation in one window is not evidence of a durable
    relationship -- this returns one number per window so callers can check
    consistency across all of them rather than cherry-picking the best one.
    """
    rx, ry = x.pct_change().dropna(), y.pct_change().dropna()
    aligned = pd.concat([rx, ry], axis=1, join="inner")
    aligned.columns = ["x", "y"]
    out: dict[int, float] = {}
    for w in windows:
        if len(aligned) < w:
            out[w] = float("nan")
            continue
        roll = aligned["x"].rolling(w).corr(aligned["y"]).dropna()
        out[w] = float(roll.mean()) if len(roll) else float("nan")
    return out


def cointegration_test(x: pd.Series, y: pd.Series) -> float:
    """Engle-Granger cointegration p-value on price levels (statsmodels.coint).

    Bivariate pairs only need Engle-Granger, not Johansen -- Johansen earns
    its complexity with 3+ series.
    """
    aligned = pd.concat([x, y], axis=1, join="inner").dropna()
    if len(aligned) < 30:
        return float("nan")
    _, pvalue, _ = coint(aligned.iloc[:, 0], aligned.iloc[:, 1])
    return float(pvalue)


def rolling_hedge_ratio_stability(x: pd.Series, y: pd.Series, window: int = HEDGE_RATIO_WINDOW) -> tuple[float, float, float]:
    """Rolling-window OLS beta (y ~ beta * x) and two stability metrics.

    coefficient of variation (std/mean of beta) separates "beta drifts
    smoothly" (low CV, worth a Kalman filter) from "beta is essentially
    noise" (high CV / near-zero mean, not a structurally sound pair).
    Lag-1 autocorrelation of beta is a second, independent stability check:
    a smoothly drifting series is highly autocorrelated; pure noise is not.
    """
    aligned = pd.concat([x, y], axis=1, join="inner").dropna()
    aligned.columns = ["x", "y"]
    if len(aligned) < window + 2:
        return float("nan"), float("nan"), float("nan")

    betas = []
    for i in range(window, len(aligned) + 1):
        chunk = aligned.iloc[i - window:i]
        var_x = chunk["x"].var()
        if var_x == 0 or np.isnan(var_x):
            betas.append(np.nan)
            continue
        cov_xy = chunk["x"].cov(chunk["y"])
        betas.append(cov_xy / var_x)

    beta_series = pd.Series(betas).dropna()
    if len(beta_series) < 3:
        return float("nan"), float("nan"), float("nan")

    beta_mean = float(beta_series.mean())
    beta_cv = float(beta_series.std() / beta_mean) if beta_mean != 0 else float("nan")
    beta_autocorr = float(beta_series.autocorr(lag=1))
    return beta_mean, beta_cv, beta_autocorr


def build_shortlist(pairs: list[tuple[str, str]], prices: pd.DataFrame) -> list[PairMetrics]:
    """Combine correlation/cointegration/stability results per pair.

    Gracefully skips pairs whose tickers didn't come back from load_prices
    (missing data, delisting, rate limit) instead of crashing -- an
    all-missing universe should produce an empty shortlist, not a traceback.
    """
    rows: list[PairMetrics] = []
    for a, b in pairs:
        pair_label = f"{a}/{b}"
        if a not in prices.columns or b not in prices.columns:
            rows.append(PairMetrics(
                pair=pair_label,
                corr_30d_mean=float("nan"),
                corr_90d_mean=float("nan"),
                corr_180d_mean=float("nan"),
                corr_365d_mean=float("nan"),
                corr_min_across_windows=float("nan"),
                corr_consistent=False,
                coint_pvalue=float("nan"),
                beta_mean=float("nan"),
                beta_cv=float("nan"),
                beta_autocorr=float("nan"),
                note="missing price data",
            ))
            continue

        x, y = prices[a].dropna(), prices[b].dropna()
        corr = rolling_correlation(x, y)
        corr_vals = [v for v in corr.values() if not np.isnan(v)]
        corr_min = min(corr_vals) if corr_vals else float("nan")
        consistent = bool(corr_vals) and all(v >= CORRELATION_CONSISTENCY_MIN for v in corr_vals)

        pvalue = cointegration_test(x, y)
        beta_mean, beta_cv, beta_autocorr = rolling_hedge_ratio_stability(x, y)

        note = ""
        if not np.isnan(beta_cv) and beta_cv > 1.0:
            note = "beta unstable -- looks like noise, not a structural relationship"
        elif not np.isnan(pvalue) and pvalue < 0.05 and consistent:
            note = "cointegrated + consistently correlated"

        rows.append(PairMetrics(
            pair=pair_label,
            corr_30d_mean=corr.get(30, float("nan")),
            corr_90d_mean=corr.get(90, float("nan")),
            corr_180d_mean=corr.get(180, float("nan")),
            corr_365d_mean=corr.get(365, float("nan")),
            corr_min_across_windows=corr_min,
            corr_consistent=consistent,
            coint_pvalue=pvalue,
            beta_mean=beta_mean,
            beta_cv=beta_cv,
            beta_autocorr=beta_autocorr,
            note=note,
        ))
    return rows


def rank(rows: list[PairMetrics]) -> list[PairMetrics]:
    """Best-first: cointegrated + consistent first, then by p-value, then by
    correlation stability. NaN cointegration (missing data) always sorts last.
    """
    def key(r: PairMetrics):
        pvalue = r.coint_pvalue if not np.isnan(r.coint_pvalue) else 1.0
        return (not r.corr_consistent, pvalue, -1 * (r.corr_min_across_windows if not np.isnan(r.corr_min_across_windows) else -1))
    return sorted(rows, key=key)


def write_shortlist(rows: list[PairMetrics], path: str = REPORT_PATH) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fieldnames = list(asdict(rows[0]).keys()) if rows else [f.name for f in PairMetrics.__dataclass_fields__.values()]
    with open(path, "w", newline="") as f:
        f.write(
            "# Phase 0 candidate shortlist. NOT a proof: ~12 pairs x 4 correlation "
            "windows + a cointegration p-value each is a multiple-comparisons setup, "
            "no correction applied. Confirm any selection out-of-sample before trading it.\n"
        )
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(asdict(r))


def main() -> None:
    tickers = sorted({t for pair in CANDIDATE_PAIRS for t in pair})
    prices = load_prices(tickers)
    rows = build_shortlist(CANDIDATE_PAIRS, prices)
    ranked = rank(rows)
    write_shortlist(ranked)
    print(f"wrote {len(ranked)} pairs to {REPORT_PATH}")


if __name__ == "__main__":
    main()
