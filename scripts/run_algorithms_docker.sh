#!/usr/bin/env bash
set -euo pipefail

if ! command -v docker >/dev/null 2>&1; then
  echo "docker command not found in PATH" >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required to resolve dataset paths" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

HOST_CPLEX_STUDIO_DIR="${HOST_CPLEX_STUDIO_DIR:-}"
CONTAINER_CPLEX_STUDIO_DIR="${CONTAINER_CPLEX_STUDIO_DIR:-/opt/ibm/ILOG/CPLEX_Studio2211}"
declare -a DOCKER_SHARED_FLAGS=()

if [[ -z "${HOST_CPLEX_STUDIO_DIR}" ]]; then
  echo "HOST_CPLEX_STUDIO_DIR must point to the local IBM CPLEX Studio installation." >&2
  exit 1
fi

if [[ ! -d "${HOST_CPLEX_STUDIO_DIR}" ]]; then
  echo "HOST_CPLEX_STUDIO_DIR '${HOST_CPLEX_STUDIO_DIR}' does not exist." >&2
  exit 1
fi

if [[ ! -f "${HOST_CPLEX_STUDIO_DIR}/python/setup.py" ]]; then
  echo "CPLEX setup.py not found at ${HOST_CPLEX_STUDIO_DIR}/python/setup.py" >&2
  exit 1
fi

DOCKER_SHARED_FLAGS+=(-v "${HOST_CPLEX_STUDIO_DIR}:${CONTAINER_CPLEX_STUDIO_DIR}")
DOCKER_SHARED_FLAGS+=(-e "CPLEX_STUDIO_DIR2211=${CONTAINER_CPLEX_STUDIO_DIR}")

DATASETS=(deezer amazon1 amazon2)
QUERIES=(l1 l2 triangle rectangle)
SAMPLE_RATES=(4 8 16 32 64)
SAMPLE_RATE_ALGOS=(dp_s4s se_blackbox)
NO_SAMPLE_RATE_DEFAULT=(r2t)
ENABLE_R2T="${ENABLE_R2T:-1}"

declare -a NO_SAMPLE_RATE_ALGOS=()
if [[ "${ENABLE_R2T}" -ne 0 ]]; then
  NO_SAMPLE_RATE_ALGOS=("${NO_SAMPLE_RATE_DEFAULT[@]}")
else
  NO_SAMPLE_RATE_ALGOS=()
fi

declare -a BASE_HOST_PATHS=()
declare -a BASE_CONTAINER_PATHS=()
declare -a BASE_LABELS=()

for dataset in "${DATASETS[@]}"; do
  for query in "${QUERIES[@]}"; do
    rel_path="info/${dataset}/${query}.txt"
    host_path="${PROJECT_ROOT}/${rel_path}"
    if [[ ! -f "${host_path}" ]]; then
      echo "Warning: skipping missing input file ${host_path}" >&2
      continue
    fi
    BASE_HOST_PATHS+=("${host_path}")
    BASE_CONTAINER_PATHS+=("/app/${rel_path}")
    BASE_LABELS+=("${dataset}-${query}")
  done
done

if [[ "${#BASE_HOST_PATHS[@]}" -eq 0 ]]; then
  echo "No input files found. Populate ${PROJECT_ROOT}/info/<dataset>/<query>.txt before running." >&2
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

if [[ -z "${AVAILABLE_CPUS}" || "${AVAILABLE_CPUS}" -lt 1 ]]; then
  echo "Unable to determine available CPU cores." >&2
  exit 1
fi

if [[ -r /proc/meminfo ]]; then
  MEM_KB="$(awk '/MemAvailable:/ {print $2; exit}' /proc/meminfo)"
  if [[ -z "${MEM_KB}" ]]; then
    echo "Unable to read MemAvailable from /proc/meminfo." >&2
    exit 1
  fi
  AVAILABLE_MEMORY_BYTES=$(( MEM_KB * 1024 ))
else
  AVAILABLE_MEMORY_BYTES="$(python3 - <<'PY'\nimport os\ntry:\n    pages = os.sysconf('SC_AVPHYS_PAGES')\n    page_size = os.sysconf('SC_PAGE_SIZE')\n    if pages == -1 or page_size == -1:\n        raise ValueError\n    print(pages * page_size)\nexcept (ValueError, AttributeError, OSError):\n    print(0)\nPY\n)"
  if [[ -z "${AVAILABLE_MEMORY_BYTES}" || "${AVAILABLE_MEMORY_BYTES}" -le 0 ]]; then
    echo "Unable to determine available memory on this system." >&2
    exit 1
  fi
fi

CONTAINER_CPUS=4
CONTAINER_MEMORY_BYTES=$((16 * 1024 * 1024 * 1024))
if [[ "${AVAILABLE_MEMORY_BYTES}" -lt "${CONTAINER_MEMORY_BYTES}" ]]; then
  echo "Only $((AVAILABLE_MEMORY_BYTES / (1024 * 1024))) MiB memory available; at least 16 GiB is required to launch one container." >&2
  exit 1
fi

MAX_BY_CPU=$(( AVAILABLE_CPUS / CONTAINER_CPUS ))
MAX_BY_MEMORY=$(( AVAILABLE_MEMORY_BYTES / CONTAINER_MEMORY_BYTES ))
MAX_CONCURRENT="${MAX_BY_MEMORY}"
if [[ "${MAX_CONCURRENT}" -gt "${MAX_BY_CPU}" ]]; then
  MAX_CONCURRENT="${MAX_BY_CPU}"
fi

if [[ "${MAX_CONCURRENT}" -lt 1 ]]; then
  echo "Detected ${AVAILABLE_CPUS} CPUs and ${AVAILABLE_MEMORY_BYTES} bytes memory; cannot schedule containers." >&2
  exit 1
fi

if [[ -n "${MAX_DOCKER_CONCURRENCY:-}" ]]; then
  if ! [[ "${MAX_DOCKER_CONCURRENCY}" =~ ^[0-9]+$ ]]; then
    echo "MAX_DOCKER_CONCURRENCY must be a positive integer." >&2
    exit 1
  fi
  if [[ "${MAX_DOCKER_CONCURRENCY}" -lt 1 ]]; then
    echo "MAX_DOCKER_CONCURRENCY must be at least 1." >&2
    exit 1
  fi
  if [[ "${MAX_DOCKER_CONCURRENCY}" -lt "${MAX_CONCURRENT}" ]]; then
    MAX_CONCURRENT="${MAX_DOCKER_CONCURRENCY}"
  fi
fi

declare -a TASK_HOST_PATHS=()
declare -a TASK_CONTAINER_PATHS=()
declare -a TASK_BASE_LABELS=()
declare -a TASK_SAMPLE_RATES=()
declare -a TASK_ALGOS=()

for base_idx in "${!BASE_HOST_PATHS[@]}"; do
  host_path="${BASE_HOST_PATHS[base_idx]}"
  container_path="${BASE_CONTAINER_PATHS[base_idx]}"
  base_label="${BASE_LABELS[base_idx]}"

  for algo in "${NO_SAMPLE_RATE_ALGOS[@]}"; do
    TASK_HOST_PATHS+=("${host_path}")
    TASK_CONTAINER_PATHS+=("${container_path}")
    TASK_BASE_LABELS+=("${base_label}")
    TASK_SAMPLE_RATES+=("")
    TASK_ALGOS+=("${algo}")
  done

  for sample_rate in "${SAMPLE_RATES[@]}"; do
    for algo in "${SAMPLE_RATE_ALGOS[@]}"; do
      TASK_HOST_PATHS+=("${host_path}")
      TASK_CONTAINER_PATHS+=("${container_path}")
      TASK_BASE_LABELS+=("${base_label}")
      TASK_SAMPLE_RATES+=("${sample_rate}")
      TASK_ALGOS+=("${algo}")
    done
  done
done

BASE_COMBINATIONS="${#BASE_HOST_PATHS[@]}"
SAMPLE_RATE_TASKS=$(( BASE_COMBINATIONS * ${#SAMPLE_RATE_ALGOS[@]} * ${#SAMPLE_RATES[@]} ))
NO_SAMPLE_RATE_TASKS=$(( BASE_COMBINATIONS * ${#NO_SAMPLE_RATE_ALGOS[@]} ))
TOTAL_CONTAINERS="${#TASK_ALGOS[@]}"

if [[ "${ENABLE_R2T}" -eq 0 ]]; then
  echo "ENABLE_R2T=0 -> skipping algorithms without sample rate (${NO_SAMPLE_RATE_DEFAULT[*]})."
fi

echo "Planning to launch ${TOTAL_CONTAINERS} containers (${NO_SAMPLE_RATE_TASKS} without sample rate + ${SAMPLE_RATE_TASKS} with sample rates)."

AVAILABLE_MEMORY_GB=$(awk -v b="${AVAILABLE_MEMORY_BYTES}" 'BEGIN {printf "%.2f", b/1024/1024/1024}')
echo "Detected ${AVAILABLE_CPUS} CPU cores and approximately ${AVAILABLE_MEMORY_GB} GiB of available memory."
echo "Running up to ${MAX_CONCURRENT} containers in parallel (16 GiB per container)."

CPU_INDICES=($(seq 0 $(( AVAILABLE_CPUS - 1 ))))

CONTAINER_PREFIX="record-sampling"
declare -a CONTAINER_NAMES=()
cleanup() {
  for name in "${CONTAINER_NAMES[@]}"; do
    docker rm -f "${name}" >/dev/null 2>&1 || true
  done
}
trap cleanup EXIT

overall_status=0
task_count="${#TASK_ALGOS[@]}"
offset=0

while [[ "${offset}" -lt "${task_count}" ]]; do
  remaining=$(( task_count - offset ))
  if [[ "${remaining}" -lt "${MAX_CONCURRENT}" ]]; then
    batch_size="${remaining}"
  else
    batch_size="${MAX_CONCURRENT}"
  fi

  batch_end=$(( offset + batch_size - 1 ))
  last_task_index=$(( task_count - 1 ))
  echo "--- Launching batch of ${batch_size} container(s) (${offset}-${batch_end} of ${last_task_index}) ---"

  pids=()
  for ((i=0; i<batch_size; i++)); do
    idx=$(( offset + i ))
    host_path="${TASK_HOST_PATHS[idx]}"
    container_path="${TASK_CONTAINER_PATHS[idx]}"
    base_label="${TASK_BASE_LABELS[idx]}"
    sample_rate="${TASK_SAMPLE_RATES[idx]}"
    algo="${TASK_ALGOS[idx]}"
    cpu_idx="$(( i * CONTAINER_CPUS))"
    cpu="${CPU_INDICES[cpu_idx]}"

    if [[ -n "${sample_rate}" ]]; then
      label="${base_label}-s${sample_rate}"
    else
      label="${base_label}"
    fi

    input_tag="$(echo "${label}" | tr '/.' '-')"
    container_name="${CONTAINER_PREFIX}-${algo}-${input_tag}-$$-${idx}"
    CONTAINER_NAMES+=("${container_name}")

    if [[ -n "${sample_rate}" ]]; then
      echo "Starting '${algo}' with input ${base_label} (sample_rate=${sample_rate}) on CPU ${cpu}-${cpu+CONTAINER_CPUS}..."
    else
      echo "Starting '${algo}' with input ${base_label} (default sample rate) on CPU ${cpu}-${cpu+CONTAINER_CPUS}..."
    fi

    cmd=(poetry run python src/main.py -i "${container_path}" -a "${algo}")
    if [[ -n "${sample_rate}" ]]; then
      cmd+=(-s "${sample_rate}")
    fi
    cmd+=("${EXTRA_ARGS[@]}")

    docker run --rm \
      --name "${container_name}" \
      --cpus=${CONTAINER_CPUS} \
      --cpuset-cpus="${cpu}-${cpu+CONTAINER_CPUS}" \
      --memory=16g \
      --memory-swap=16g \
      --memory-swappiness=0 \
      "${DOCKER_SHARED_FLAGS[@]}" \
      -v "${PROJECT_ROOT}:/app" \
      -w /app \
      "${IMAGE_NAME}" \
      "${cmd[@]}" &

    pids+=("$!")
  done

  batch_status=0
  for pid in "${pids[@]}"; do
    if ! wait "${pid}"; then
      batch_status=1
    fi
  done

  if [[ "${batch_status}" -ne 0 ]]; then
    echo "Batch ${offset}-${batch_end} encountered failures." >&2
    overall_status=1
  fi

  offset=$(( offset + batch_size ))
done

exit "${overall_status}"
