#!/usr/bin/env bash
# Download the XAU/USD spot history (Hugging Face mirror of the Kaggle 2004-2025 dataset), then build processed data.
set -e
cd "$(dirname "$0")/.."
mkdir -p data/raw
for f in XAU_1h_data.jsonl XAU_15m_data.jsonl XAU_1d_data.jsonl; do
  [ -f "data/raw/$f" ] || curl -sL -o "data/raw/$f" "https://huggingface.co/datasets/ZombitX64/xauusd-gold-price-historical-data-2004-2025/resolve/main/$f"
done
.venv/bin/python -m goldbot.data
