#!/usr/bin/env bash
set -euo pipefail
task_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
task_name="${1:?Usage: smoke_arm_task.sh TASK_NAME [oracle|nop]}"
agent_name="${2:-oracle}"
case "$agent_name" in oracle|nop) ;; *) echo 'Only oracle or nop is supported by this smoke check' >&2; exit 2 ;; esac
job_name="${task_name}-${agent_name}-$(date -u +%Y%m%dT%H%M%SZ)"
exec "$task_root/scripts/with_arm_env.sh" pier run \
  --path "$task_root/arm/tasks/$task_name" --agent "$agent_name" \
  --env docker --n-concurrent 1 --max-retries 0 --no-delete \
  --jobs-dir "$task_root/arm/jobs" --job-name "$job_name"
