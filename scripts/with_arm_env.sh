#!/usr/bin/env bash
set -euo pipefail
task_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
export PATH="$task_root/.runtime/bin:$task_root/pier/.venv/bin:$PATH"
export DOCKER_CONFIG="$task_root/.runtime/docker-config"
# Use the existing Engine 18.09 daemon and its classic builder.
export DOCKER_BUILDKIT=0
export COMPOSE_DOCKER_CLI_BUILD=0
export LITELLM_LOCAL_MODEL_COST_MAP=True
exec "$@"
