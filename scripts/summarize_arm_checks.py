#!/usr/bin/env python3
"""Report measured oracle/nop task checks, including infrastructure failures."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
records = []
for path in sorted((ROOT / "arm/jobs").glob("*/*/result.json")):
    trial = json.loads(path.read_text())
    agent = trial.get("agent_info", {}).get("name")
    if agent not in ("oracle", "nop"):
        continue
    rewards = (trial.get("verifier_result") or {}).get("rewards") or {}
    expected = 1 if agent == "oracle" else 0
    # A broken test runner must not masquerade as a valid negative control.
    accepted = (
        trial.get("finished_at") is not None
        and trial.get("exception_info") is None
        and rewards.get("reward") == expected
        and rewards.get("p2p") == 1
        and rewards.get("p2p_total", 0) > 0
        and rewards.get("f2p_total", 0) > 0
        and (agent != "oracle" or rewards.get("f2p") == 1)
        and (agent != "nop" or rewards.get("f2p", 1) < 1)
    )
    records.append({
        "task": trial["task_name"], "agent": agent,
        "expected_reward": expected, "accepted": accepted,
        "rewards": rewards, "exception": trial.get("exception_info"),
        "trial_result": str(path.relative_to(ROOT)),
    })
output = ROOT / "arm/validation.json"
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(records, indent=2) + "\n")
for record in records:
    print(record["task"], record["agent"], "PASS" if record["accepted"] else "FAIL", record["rewards"])
print(f"Recorded {len(records)} actual trials; {sum(r['accepted'] for r in records)} accepted.")
