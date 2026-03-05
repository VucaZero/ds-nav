#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VLNCE="$ROOT/programs/VLN-CE"
HABLAB="$ROOT/programs/habitat-lab"
RAW_DIR="$ROOT/assets/raw"
WS_DIR="$ROOT/experiment_workspace"

echo "[1/6] ensure official asset directories"
mkdir -p "$VLNCE/data/scene_datasets/mp3d"
mkdir -p "$VLNCE/data/datasets/R2R_VLNCE_v1-3_preprocessed"
mkdir -p "$VLNCE/data/checkpoints"

if [[ -d "$HABLAB" ]]; then
  mkdir -p "$HABLAB/data/scene_datasets"
fi

echo "[2/6] place scene dataset config"
SCENE_CFG=""
if [[ -f "$ROOT/mp3d.scene_dataset_config.json" ]]; then
  SCENE_CFG="$ROOT/mp3d.scene_dataset_config.json"
elif [[ -f "$WS_DIR/configs/mp3d.scene_dataset_config.json" ]]; then
  SCENE_CFG="$WS_DIR/configs/mp3d.scene_dataset_config.json"
fi

if [[ -n "$SCENE_CFG" ]]; then
  cp -f "$SCENE_CFG" "$VLNCE/data/scene_datasets/mp3d.scene_dataset_config.json"
  # 当 mp3d 是外部软链接时，不向场景目录写入，避免跨项目权限与污染问题
  if [[ -d "$VLNCE/data/scene_datasets/mp3d" ]] && [[ ! -L "$VLNCE/data/scene_datasets/mp3d" ]]; then
    cp -f "$SCENE_CFG" "$VLNCE/data/scene_datasets/mp3d/mp3d.scene_dataset_config.json"
  fi

  if [[ -d "$HABLAB" ]]; then
    cp -f "$SCENE_CFG" "$HABLAB/data/scene_datasets/mp3d.scene_dataset_config.json"
  fi
fi

echo "[3/6] normalize R2R preprocessed dataset"
R2R_ZIP=""
if [[ -f "$ROOT/R2R_VLNCE_v1-2_preprocessed.zip" ]]; then
  R2R_ZIP="$ROOT/R2R_VLNCE_v1-2_preprocessed.zip"
elif [[ -f "$RAW_DIR/R2R_VLNCE_v1-2_preprocessed.zip" ]]; then
  R2R_ZIP="$RAW_DIR/R2R_VLNCE_v1-2_preprocessed.zip"
elif [[ -f "$WS_DIR/data/raw/R2R_VLNCE_v1-2_preprocessed.zip" ]]; then
  R2R_ZIP="$WS_DIR/data/raw/R2R_VLNCE_v1-2_preprocessed.zip"
fi

if [[ -n "$R2R_ZIP" ]]; then
  TMP_DIR="/tmp/r2r_unpack_layout"
  rm -rf "$TMP_DIR"
  mkdir -p "$TMP_DIR"
  unzip -q "$R2R_ZIP" -d "$TMP_DIR"

  if [[ -d "$TMP_DIR/R2R_VLNCE_v1-2_preprocessed" ]]; then
    rsync -a "$TMP_DIR/R2R_VLNCE_v1-2_preprocessed/" "$VLNCE/data/datasets/R2R_VLNCE_v1-3_preprocessed/"
  fi
fi

echo "[4/6] normalize checkpoint"
if [[ -f "$ROOT/CMA_PM_DA_Aug.pth" ]] && [[ ! -f "$VLNCE/data/checkpoints/CMA_PM_DA_Aug.pth" ]]; then
  cp -f "$ROOT/CMA_PM_DA_Aug.pth" "$VLNCE/data/checkpoints/CMA_PM_DA_Aug.pth"
elif [[ -f "$WS_DIR/models/CMA_PM_DA_Aug.pth" ]] && [[ ! -f "$VLNCE/data/checkpoints/CMA_PM_DA_Aug.pth" ]]; then
  cp -f "$WS_DIR/models/CMA_PM_DA_Aug.pth" "$VLNCE/data/checkpoints/CMA_PM_DA_Aug.pth"
fi

echo "[5/6] write asset manifest"
cat > "$ROOT/reports/asset_manifest_current.txt" <<MANIFEST
VLNCE_ROOT=$VLNCE
R2R_DIR=$VLNCE/data/datasets/R2R_VLNCE_v1-3_preprocessed
MP3D_DIR=$VLNCE/data/scene_datasets/mp3d
CKPT_FILE=$VLNCE/data/checkpoints/CMA_PM_DA_Aug.pth
MANIFEST

echo "[6/6] summarize"
echo "R2R files:  $(find "$VLNCE/data/datasets/R2R_VLNCE_v1-3_preprocessed" -type f 2>/dev/null | wc -l)"
echo "MP3D files: $(find -L "$VLNCE/data/scene_datasets/mp3d" -type f 2>/dev/null | wc -l)"
echo "CKPT file:  $(if [[ -f "$VLNCE/data/checkpoints/CMA_PM_DA_Aug.pth" ]]; then echo yes; else echo no; fi)"
