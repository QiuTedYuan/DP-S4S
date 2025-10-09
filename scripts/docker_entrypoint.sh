#!/usr/bin/env bash
set -euo pipefail

install_cplex() {
  local setup_py="${CPLEX_STUDIO_DIR2211}/python/setup.py"

  if [[ ! -f "${setup_py}" ]]; then
    echo "CPLEX setup.py not found at ${setup_py}" >&2
    exit 1
  fi

  if poetry run python -c "import cplex" >/dev/null 2>&1; then
    return
  fi

  echo "Installing CPLEX from ${setup_py}..."
  poetry run python "${setup_py}" install
}

if [[ -n "${CPLEX_STUDIO_DIR2211:-}" ]]; then
  install_cplex
else
  echo "CPLEX_STUDIO_DIR2211 not set; skipping CPLEX install." >&2
fi

exec "$@"
