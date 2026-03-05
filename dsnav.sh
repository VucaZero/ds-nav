#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -d "$ROOT_DIR/archive/legacy_scripts" ]]; then
  LEGACY_DIR="$ROOT_DIR/archive/legacy_scripts"
elif [[ -d "$ROOT_DIR/history/archive_legacy/legacy_scripts" ]]; then
  LEGACY_DIR="$ROOT_DIR/history/archive_legacy/legacy_scripts"
else
  LEGACY_DIR="$ROOT_DIR/archive/legacy_scripts"
fi

usage() {
  cat <<'USAGE'
Usage:
  bash dsnav.sh <command> [args]

Commands:
  help                   Show this help

  env-setup              Run legacy ENV_SETUP.sh
  env-setup-interactive  Run legacy ENV_SETUP_INTERACTIVE.sh
  install                Run legacy INSTALL_HABITAT_VLNCE.sh
  patch                  Run legacy PATCH_DEPENDENCIES.sh
  diagnose               Run legacy ENVIRONMENT_DIAGNOSTIC.sh

  data-prepare           Run legacy PREPARE_VLN_CE_DATA.sh
  data-verify            Run legacy VERIFY_DATA.sh

  run-b0                 Run legacy RUN_B0_BASELINE.sh
  run-ours               Run legacy RUN_OURS_R_INFERENCE.sh

  run-method             Run python run.py
  eval                   Run python eval_all_methods.py
  verify                 Run python verify_project.py
USAGE
}

run_legacy() {
  local script_name="$1"
  shift || true

  local script_path="$LEGACY_DIR/$script_name"
  if [[ ! -f "$script_path" ]]; then
    echo "Missing legacy script: $script_path" >&2
    exit 1
  fi

  bash "$script_path" "$@"
}

cmd="${1:-help}"
shift || true

case "$cmd" in
  help|-h|--help)
    usage
    ;;
  env-setup)
    run_legacy "ENV_SETUP.sh" "$@"
    ;;
  env-setup-interactive)
    run_legacy "ENV_SETUP_INTERACTIVE.sh" "$@"
    ;;
  install)
    run_legacy "INSTALL_HABITAT_VLNCE.sh" "$@"
    ;;
  patch)
    run_legacy "PATCH_DEPENDENCIES.sh" "$@"
    ;;
  diagnose)
    run_legacy "ENVIRONMENT_DIAGNOSTIC.sh" "$@"
    ;;
  data-prepare)
    run_legacy "PREPARE_VLN_CE_DATA.sh" "$@"
    ;;
  data-verify)
    run_legacy "VERIFY_DATA.sh" "$@"
    ;;
  run-b0)
    run_legacy "RUN_B0_BASELINE.sh" "$@"
    ;;
  run-ours)
    run_legacy "RUN_OURS_R_INFERENCE.sh" "$@"
    ;;
  run-method)
    python "$ROOT_DIR/run.py" "$@"
    ;;
  eval)
    python "$ROOT_DIR/eval_all_methods.py" "$@"
    ;;
  verify)
    python "$ROOT_DIR/verify_project.py" "$@"
    ;;
  *)
    echo "Unknown command: $cmd" >&2
    usage
    exit 1
    ;;
esac
