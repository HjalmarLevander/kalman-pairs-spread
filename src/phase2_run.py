"""Applies Phase 2 FFT denoising to the Phase 1 Kalman spreads and writes
denoised series + variance-explained summary for a small percentile grid.
Not the Phase 3 sweep itself (that's a separate, larger deliverable) -- this
is a quick look to confirm the denoiser behaves sensibly on real spreads
before Phase 3 is built.
"""
import os

import pandas as pd

from src.phase2_fft_denoise import rolling_fft_denoise, variance_explained

REPORT_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")
PREVIEW_PERCENTILES = (50, 70, 90)


def main() -> None:
    for pair in ("V_MA", "KO_PEP"):
        path = os.path.join(REPORT_DIR, f"phase1_kalman_{pair}.csv")
        df = pd.read_csv(path, index_col=0, parse_dates=True)
        spread = df["spread"]

        for p in PREVIEW_PERCENTILES:
            denoised = rolling_fft_denoise(spread, percentile=p, window=60)
            ve = variance_explained(spread, denoised)
            print(f"{pair} p={p}: variance_explained={ve:.4f} "
                  f"denoised_std={denoised.std():.5f} raw_std={spread.std():.5f}")


if __name__ == "__main__":
    main()
