#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <data-file> [extra-args-for-main.py...]" >&2
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "docker command not found in PATH" >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required to resolve absolute paths" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DATA_PATH_INPUT="$1"
shift || true

DATA_ABS="$(python3 -c 'import os, sys; print(os.path.realpath(sys.argv[1]))' "${DATA_PATH_INPUT}")"

case "${DATA_ABS}" in
  "${PROJECT_ROOT}"/*)
    CONTAINER_DATA_PATH="/app${DATA_ABS#"${PROJECT_ROOT}"}"
    ;;
  *)
    echo "Data file must be inside the project directory (${PROJECT_ROOT})." >&2
    exit 1
    ;;
esac

if [[ ! -f "${DATA_ABS}" ]]; then
  echo "Data file '${DATA_ABS}' not found." >&2
  exit 1
fi

EXTRA_ARGS=("$@")

IMAGE_NAME="${IMAGE_NAME:-record-sampling}"

if ! docker image inspect "${IMAGE_NAME}" >/dev/null 2>&1; then
  echo "Docker image '${IMAGE_NAME}' not found. Building..."
  docker build -t "${IMAGE_NAME}" "${PROJECT_ROOT}"
fi

if command -v nproc >/dev/null 2>&1; then
  AVAILABLE_CPUS="$(nproc)"
else
  AVAILABLE_CPUS="$(sysctl -n hw.ncpu 2>/dev/null || echo 1)"
fi

ALGORITHMS=(r2t dp_s4s se_blackbox se_whitebox)

if [[ "${AVAILABLE_CPUS}" -lt "${#ALGORITHMS[@]}" ]]; then
  echo "At least ${#ALGORITHMS[@]} CPU cores are required; only ${AVAILABLE_CPUS} detected." >&2
  exit 1
fi

CONTAINER_PREFIX="record-sampling"
declare -a CONTAINER_NAMES=()
cleanup() {
  for name in "${CONTAINER_NAMES[@]}"; do
    docker rm -f "${name}" >/dev/null 2>&1 || true
  done
}
trap cleanup EXIT

pids=()

for idx in "${!ALGORITHMS[@]}"; do
  algo="${ALGORITHMS[idx]}"
  cpu="${idx}"
  container_name="${CONTAINER_PREFIX}-${algo}-$$"
  CONTAINER_NAMES+=("${container_name}")

  echo "Starting '${algo}' on CPU ${cpu} with 16G memory limit..."

  docker run --rm \
    --name "${container_name}" \
    --cpus=1 \
    --cpuset-cpus="${cpu}" \
    --memory=16g \
    --memory-swap=16g \
    --memory-swappiness=0 \
    -v "${PROJECT_ROOT}:/app" \
    -w /app \
    "${IMAGE_NAME}" \
    poetry run python src/main.py \
      -i "${CONTAINER_DATA_PATH}" \
      -a "${algo}" \
      "${EXTRA_ARGS[@]}" &

  pids+=("$!")
done

status=0
for pid in "${pids[@]}"; do
  if ! wait "${pid}"; then
    status=1
  fi
done

exit "${status}"
