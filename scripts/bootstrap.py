#!/usr/bin/env python3
"""Restore pinned upstreams and project-local ARM tools; never change system services."""
import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import tarfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(*args, cwd=ROOT, **kwargs):
    return subprocess.run(args, cwd=cwd, check=True, **kwargs)


def ensure_source(name, spec, check):
    target = ROOT / name
    if not target.exists():
        if check:
            raise RuntimeError(f"Missing upstream: {name}; run bootstrap first")
        target.mkdir()
        run("git", "init", "--quiet", cwd=target)
        run("git", "remote", "add", "origin", spec["url"], cwd=target)
        run("git", "fetch", "--depth", "1", "origin", spec["commit"], cwd=target)
        run("git", "checkout", "--detach", "FETCH_HEAD", cwd=target)
    actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=target, text=True).strip()
    if actual != spec["commit"]:
        raise RuntimeError(f"{name} HEAD differs from lock; refusing to reset existing work")
    if spec.get("patch"):
        patch = str(ROOT / spec["patch"])
        reverse = subprocess.run(["git", "apply", "--reverse", "--check", patch], cwd=target, capture_output=True)
        if reverse.returncode != 0:
            if check:
                raise RuntimeError(f"Required patch not applied: {name}")
            run("git", "apply", "--check", patch, cwd=target)
            run("git", "apply", patch, cwd=target)
    print(f"Verified upstream: {name} @ {actual}", flush=True)


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(spec, directory):
    path = directory / spec["filename"]
    if not path.exists() or sha256(path) != spec["sha256"]:
        partial = path.with_name(path.name + ".part")
        print(f"Downloading {spec['filename']}", flush=True)
        with urllib.request.urlopen(spec["url"], timeout=60) as response, partial.open("wb") as output:
            shutil.copyfileobj(response, output)
        if sha256(partial) != spec["sha256"]:
            raise RuntimeError(f"Checksum mismatch: {partial.name}")
        partial.replace(path)
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check existing environment without downloads or writes")
    parser.add_argument("--upstreams-only", action="store_true", help="Restore sources and patch only; works on non-ARM hosts")
    args = parser.parse_args()
    lock = json.loads((ROOT / "config/versions.json").read_text())
    for name, spec in lock["upstreams"].items():
        ensure_source(name, spec, args.check)
    if args.upstreams_only:
        return
    if platform.system() != "Linux" or platform.machine() not in ("aarch64", "arm64"):
        raise RuntimeError("Runtime tools require Linux ARM64; use --upstreams-only for source inspection")
    runtime = ROOT / ".runtime"
    if args.check:
        run(str(runtime / "bin/docker"), "--version")
        run(str(ROOT / "scripts/with_arm_env.sh"), "docker", "compose", "version")
        run(str(ROOT / "pier/.venv/bin/python"), "-c", "import sys; from importlib.metadata import version; print(sys.version); print('Pier', version('datacurve-pier'))")
        print("Environment check passed; daemon connectivity and model inference are separate checks.")
        return
    uv = shutil.which("uv")
    if not uv:
        raise RuntimeError("uv is required; install it following https://docs.astral.sh/uv/getting-started/installation/")
    downloads = runtime / "downloads"
    binaries = runtime / "bin"
    plugins = runtime / "docker-config/cli-plugins"
    for directory in (downloads, binaries, plugins):
        directory.mkdir(parents=True, exist_ok=True)
    archive = download(lock["tools"]["docker_cli"], downloads)
    with tarfile.open(archive) as bundle:
        with bundle.extractfile("docker/docker") as source, (binaries / "docker").open("wb") as output:
            shutil.copyfileobj(source, output)
    compose = download(lock["tools"]["compose"], downloads)
    shutil.copy2(compose, plugins / "docker-compose")
    for executable in (binaries / "docker", plugins / "docker-compose"):
        executable.chmod(0o755)
    env = dict(os.environ, UV_CACHE_DIR=str(runtime / "uv-cache"), UV_PYTHON_INSTALL_DIR=str(runtime / "python"))
    run(uv, "sync", "--project", str(ROOT / "pier"), "--python", lock["python"], "--locked", env=env)
    (runtime / "base-image.txt").write_text(lock["base_image"] + "\n")
    print("Project tools ready. No task images built and no NPU service started.")
    print("Next: python3 scripts/prepare_arm_tasks.py --all --base-image '" + lock["base_image"] + "'")


if __name__ == "__main__":
    main()
