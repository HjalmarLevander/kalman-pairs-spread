#!/usr/bin/env bash
# Populates style_vault/ with reference repos for Robin's Engineer/Critic RAG
# grounding on this project (Kalman filtering, cointegration testing, spectral
# analysis, backtesting). style_vault/ is gitignored -- run once after clone.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."
mkdir -p style_vault
cd style_vault

clone_shallow() {
  local url="$1" dir="$2"
  if [ -d "$dir" ]; then
    echo "skip $dir (already present)"
  else
    git clone --depth 1 "$url" "$dir"
    rm -rf "$dir/.git"
  fi
}

clone_shallow https://github.com/pykalman/pykalman pykalman
clone_shallow https://github.com/statsmodels/statsmodels statsmodels
clone_shallow https://github.com/quantopian/pyfolio pyfolio
clone_shallow https://github.com/mementum/backtrader backtrader

echo
echo "Done. Run ingest() in the Robin backend (or restart the server) to embed."
