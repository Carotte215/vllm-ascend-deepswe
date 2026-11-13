#!/usr/bin/env bash
set -euo pipefail
task_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
task_name="${1:?Usage: build_arm_task.sh TASK_NAME}"
task_dir="$task_root/arm/tasks/$task_name"
image_name="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["task_image"])' "$task_dir/arm-adaptation.json")"
mkdir -p "$task_root/arm/build-logs"
"$task_root/scripts/with_arm_env.sh" docker build --platform linux/arm64 --network host \
  --cpu-period 100000 --cpu-quota 200000 --memory 8g \
  --build-arg http_proxy --build-arg https_proxy \
  --build-arg HTTP_PROXY --build-arg HTTPS_PROXY \
  --build-arg ALL_PROXY --build-arg all_proxy \
  -t "$image_name" "$task_dir/environment" 2>&1 | tee "$task_root/arm/build-logs/$task_name.log"
image_arch="$("$task_root/scripts/with_arm_env.sh" docker image inspect --format '{{.Architecture}}' "$image_name")"
test "$image_arch" = arm64
printf 'Built ARM image: %s\n' "$image_name"
