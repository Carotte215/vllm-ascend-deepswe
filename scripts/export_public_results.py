#!/usr/bin/env python3
"""Export environment-check metrics without local paths, tracebacks, or trajectories."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "arm/validation.json")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--record-date", required=True, help="Date of the original checks, YYYY-MM-DD")
    args = parser.parse_args()
    original = args.input.read_bytes()
    records = []
    for row in json.loads(original):
        exception = row.get("exception") or {}
        records.append({
            "task": row["task"], "agent": row["agent"],
            "expected_reward": row["expected_reward"], "accepted": row["accepted"],
            "rewards": row["rewards"], "exception_type": exception.get("exception_type"),
        })
    lock = json.loads((ROOT / "config/versions.json").read_text())
    output = {
        "schema_version": 1, "record_date": args.record_date, "timezone": "Asia/Shanghai",
        "kind": "environment_oracle_nop_checks_not_model_evaluation",
        "source_summary_sha256": hashlib.sha256(original).hexdigest(),
        "base_image": lock["base_image"],
        "upstream_commits": {name: spec["commit"] for name, spec in lock["upstreams"].items()},
        "pier_patch_sha256": hashlib.sha256((ROOT / lock["upstreams"]["pier"]["patch"]).read_bytes()).hexdigest(),
        "historical_trials": len(records), "accepted_trials": sum(row["accepted"] for row in records),
        "records": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n")
    print(f"Exported {len(records)} environment checks to {args.output}")


if __name__ == "__main__":
    main()
