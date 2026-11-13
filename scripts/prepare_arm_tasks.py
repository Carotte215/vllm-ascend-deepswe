#!/usr/bin/env python3
"""Generate ARM task copies while preserving upstream prompts and grading files."""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM_BASE = "public.ecr.aws/x8v8d7g8/mars-base:latest"


def hashes(directory):
    return {
        str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(directory.rglob("*")) if path.is_file()
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", action="append")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--base-image", required=True, help="Prefer an immutable ARM image digest")
    args = parser.parse_args()
    source = ROOT / "deep-swe"
    revision = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
    names = sorted(p.parent.name for p in (source / "tasks").glob("*/task.toml")) if args.all else args.task
    if not names:
        parser.error("Specify --task or --all")
    manifest = []
    for name in names:
        original = source / "tasks" / name
        if original.parent != source / "tasks" or not (original / "task.toml").is_file():
            raise ValueError(f"Unknown task: {name}")
        dest = ROOT / "arm/tasks" / name
        if dest.exists():
            raise FileExistsError(f"Refusing to replace existing adapted task: {dest}")
        shutil.copytree(original, dest)
        image = f"deepswe-arm64/{name}:{revision[:12]}"
        task_path = dest / "task.toml"
        text, count = re.subn(r'^docker_image = "[^"]+"$', f'docker_image = "{image}"', task_path.read_text(), count=1, flags=re.M)
        if count != 1:
            raise ValueError(f"Expected one agent image reference in {task_path}")
        task_path.write_text(text)
        dockerfile = dest / "environment/Dockerfile"
        text = dockerfile.read_text()
        if f"FROM {UPSTREAM_BASE}\n" not in text:
            raise ValueError(f"Unexpected base image in {dockerfile}")
        text = text.replace(f"FROM {UPSTREAM_BASE}\n", f"FROM {args.base_image}\n", 1)
        changes = ["task.toml", "environment/Dockerfile", "tests/Dockerfile"]
        if name == "cliffy-config-file-parsing":
            text = text.replace("deno-x86_64-unknown-linux-gnu.zip", "deno-aarch64-unknown-linux-gnu.zip")
        # nextest's /linux endpoint is explicitly x86_64, not auto-detected.
        text = text.replace('https://get.nexte.st/${NEXTEST_VERSION}/linux"', 'https://get.nexte.st/${NEXTEST_VERSION}/linux-arm"')
        if name == "pest-character-class-coalescing":
            # The unbounded bootstrap dependency now resolves to 2.9.6, whose
            # generated parser calls APIs absent in this task's 2.8.6 runtime.
            text = text.replace(
                "RUN cargo fetch && cargo build --package pest_bootstrap",
                "RUN cargo fetch && "
                "cargo update -p pest_generator@2.9.6 --precise 2.8.6 && "
                "cargo update -p pest_meta@2.9.6 --precise 2.8.6 && "
                "cargo update -p pest@2.9.6 --precise 2.8.6 && "
                "cargo build --package pest_bootstrap",
            )
        dockerfile.write_text(text)
        verifier = dest / "tests/Dockerfile"
        text, count = re.subn(r"^FROM .+$", f"FROM {image}", verifier.read_text(), count=1, flags=re.M)
        if count != 1:
            raise ValueError(f"Expected one verifier base in {verifier}")
        verifier.write_text(text)
        before, after = hashes(original), hashes(dest)
        modified = sorted(path for path in before if before[path] != after[path])
        if set(modified) - set(changes) or before.keys() != after.keys():
            raise AssertionError(f"Unexpected modifications: {modified}")
        entry = {
            "task": name, "source_commit": revision, "platform": "linux/arm64",
            "base_image": args.base_image, "task_image": image,
            "modified_files": modified,
            "unchanged_file_sha256": {path: value for path, value in before.items() if path not in modified},
            "validation_report": "arm/validation.json",
        }
        (dest / "arm-adaptation.json").write_text(json.dumps(entry, indent=2) + "\n")
        manifest.append(entry)
        print(f"Prepared {name}: {image}")
    output = ROOT / "arm/manifests"
    output.mkdir(parents=True, exist_ok=True)
    (output / ("all-tasks.json" if args.all else "selected-tasks.json")).write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
