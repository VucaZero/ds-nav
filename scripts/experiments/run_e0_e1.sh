#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PY="/home/data/anaconda3/envs/vlnce38/bin/python"
CFG="vlnce_baselines/config/r2r_baselines/test_set_inference.yaml"

cd "$ROOT/programs/VLN-CE"

run_inference() {
  if [[ -z "${DISPLAY:-}" ]]; then
    xvfb-run -a -s "-screen 0 1280x1024x24" \
      "$PY" "$ROOT/scripts/run_official_vlnce_inference.py" "$@"
  else
    "$PY" "$ROOT/scripts/run_official_vlnce_inference.py" "$@"
  fi
}

# E0 smoke
run_inference \
  --exp-config "$CFG" \
  --method B0 \
  --split val_unseen \
  --max-episodes 5 \
  --output-dir "$ROOT/eval_results_official"

# E1 baseline full (val_unseen)
run_inference \
  --exp-config "$CFG" \
  --method B0 \
  --split val_unseen \
  --output-dir "$ROOT/eval_results_official"
