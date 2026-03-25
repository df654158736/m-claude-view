#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [ -d ".venv" ] && [ -f ".venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

if [ -f ".env" ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

export LLM_BASE_URL="${LLM_BASE_URL:-https://dashscope.aliyuncs.com/compatible-mode/v1}"
export LLM_MODEL="${LLM_MODEL:-qwen-max}"
export LLM_MAX_ITERATIONS="${LLM_MAX_ITERATIONS:-20}"
export LLM_TEMPERATURE="${LLM_TEMPERATURE:-0.7}"

if [ -z "${LLM_API_KEY:-}" ]; then
  echo "LLM_API_KEY is required. Please set it in .env or environment."
  exit 1
fi

export PYTHONPATH=backend
python -m src.main --host 0.0.0.0 --port 8765 --config backend/config.yaml
