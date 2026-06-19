#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
VENV_DIR="${SCRIPT_DIR}/.venv"
PYTHON_BIN="${PYTHON_BIN:-python3}"
DB_PATH="${SCRIPT_DIR}/history_index.db"
PDF_PATH="${WORKSPACE_ROOT}/唐山市第一中学校史.pdf"
REBUILD_INDEX=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --rebuild)
      REBUILD_INDEX=1
      shift
      ;;
    *)
      PDF_PATH="$1"
      shift
      ;;
  esac
done

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "Python interpreter not found: ${PYTHON_BIN}" >&2
  exit 1
fi

"${PYTHON_BIN}" -m venv "${VENV_DIR}"
"${VENV_DIR}/bin/python" -m pip install --upgrade pip
"${VENV_DIR}/bin/pip" install -r "${SCRIPT_DIR}/requirements.txt"

if [[ "${REBUILD_INDEX}" -eq 1 ]]; then
  if [[ ! -f "${PDF_PATH}" ]]; then
    echo "PDF not found for rebuild: ${PDF_PATH}" >&2
    exit 1
  fi
  "${VENV_DIR}/bin/python" "${SCRIPT_DIR}/build_index.py" --pdf "${PDF_PATH}" --db "${DB_PATH}"
elif [[ -f "${DB_PATH}" ]]; then
  echo "Using bundled SQLite index: ${DB_PATH}"
else
  if [[ ! -f "${PDF_PATH}" ]]; then
    echo "Bundled index not found and PDF not found: ${PDF_PATH}" >&2
    exit 1
  fi
  "${VENV_DIR}/bin/python" "${SCRIPT_DIR}/build_index.py" --pdf "${PDF_PATH}" --db "${DB_PATH}"
fi

echo ""
echo "Install finished."
echo "Query command:"
echo "${VENV_DIR}/bin/python ${SCRIPT_DIR}/query_index.py \"唐山一中是什么时候建立的？\""
