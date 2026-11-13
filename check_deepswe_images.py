"""Inspect public DeepSWE image metadata without downloading image layers."""
import concurrent.futures
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ACCEPT = ",".join([
    "application/vnd.oci.image.index.v1+json",
    "application/vnd.docker.distribution.manifest.list.v2+json",
    "application/vnd.oci.image.manifest.v1+json",
    "application/vnd.docker.distribution.manifest.v2+json",
])


def read_json(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=25) as response:
        return json.load(response)


def inspect(image):
    result = {"image": image}
    try:
        repo, tag = image.removeprefix("public.ecr.aws/").rsplit(":", 1)
        query = urllib.parse.urlencode({
            "service": "public.ecr.aws", "scope": f"repository:{repo}:pull"
        })
        token = read_json("https://public.ecr.aws/token/?" + query)["token"]
        headers = {"Authorization": "Bearer " + token, "Accept": ACCEPT}
        manifest = read_json(f"https://public.ecr.aws/v2/{repo}/manifests/{tag}", headers)
        result["media_type"] = manifest.get("mediaType")
        if "manifests" in manifest:
            result["platforms"] = [entry.get("platform", {}) for entry in manifest["manifests"]]
        else:
            digest = manifest["config"]["digest"]
            config = read_json(f"https://public.ecr.aws/v2/{repo}/blobs/{digest}", headers)
            result["platforms"] = [{"os": config.get("os"), "architecture": config.get("architecture")}]
            result["compressed_layer_bytes"] = sum(layer["size"] for layer in manifest.get("layers", []))
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


if __name__ == "__main__":
    images = {"public.ecr.aws/x8v8d7g8/mars-base:latest"}
    for path in (ROOT / "deep-swe/tasks").glob("*/task.toml"):
        images.update(re.findall(r'^docker_image = "([^"]+)"', path.read_text(), re.M))
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        for result in pool.map(inspect, sorted(images)):
            results.append(result)
            print(json.dumps(result), flush=True)
    (ROOT / "deepswe-image-platforms.json").write_text(json.dumps(results, indent=2) + "\n")
