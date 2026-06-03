#!/usr/bin/env python3
"""Generate host-specific pressure-run prompt and evidence files."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVALUATIONS = ROOT / "integrate-midtrans-payments" / "evaluations.json"
SKILL_NAME = "integrate-midtrans-payments"


HOSTS = {
    "claude-code": {
        "skill_path": ".claude/skills/integrate-midtrans-payments",
        "install": "mkdir -p .claude/skills && cp -R <repo>/integrate-midtrans-payments .claude/skills/",
    },
    "codex": {
        "skill_path": ".codex/skills/integrate-midtrans-payments",
        "install": "mkdir -p .codex/skills && cp -R <repo>/integrate-midtrans-payments .codex/skills/",
    },
    "agents": {
        "skill_path": ".agents/skills/integrate-midtrans-payments",
        "install": "mkdir -p .agents/skills && cp -R <repo>/integrate-midtrans-payments .agents/skills/",
    },
}


def fail(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(1)


def git_commit() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        fail(result.stderr.strip() or "cannot resolve git commit")
    return result.stdout.strip()


def git_dirty() -> bool:
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=str(ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        fail(result.stderr.strip() or "cannot inspect git status")
    return bool(result.stdout.strip())


def load_evaluations() -> dict:
    try:
        with EVALUATIONS.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception as exc:  # noqa: BLE001 - report any parse/read failure uniformly.
        fail(f"cannot read evaluations.json: {exc}")
    validate_evaluations(data)
    return data


def validate_evaluations(data: dict) -> None:
    if data.get("skill") != SKILL_NAME:
        fail(f"evaluations.json skill must be {SKILL_NAME}")
    evaluations = data.get("evaluations")
    if not isinstance(evaluations, list) or not evaluations:
        fail("evaluations.json must contain a non-empty evaluations list")
    seen: set[str] = set()
    for item in evaluations:
        if not isinstance(item, dict):
            fail("each evaluation must be an object")
        scenario_id = item.get("id")
        if not isinstance(scenario_id, str) or not scenario_id:
            fail("each evaluation needs a non-empty id")
        if scenario_id in seen:
            fail(f"duplicate evaluation id: {scenario_id}")
        seen.add(scenario_id)
        if item.get("skills") != [SKILL_NAME]:
            fail(f"{scenario_id}: skills must be [{SKILL_NAME!r}]")
        if not isinstance(item.get("query"), str) or not item["query"].strip():
            fail(f"{scenario_id}: query is required")
        expected = item.get("expected_behavior")
        if not isinstance(expected, list) or len(expected) < 3:
            fail(f"{scenario_id}: expected_behavior must contain at least 3 checks")
        if not all(isinstance(value, str) and value.strip() for value in expected):
            fail(f"{scenario_id}: expected_behavior entries must be non-empty strings")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def scenario_markdown(host: str, commit: str, version: str, dirty: bool, item: dict) -> str:
    expected = "\n".join(f"- [ ] {line}" for line in item["expected_behavior"])
    host_info = HOSTS[host]
    dirty_note = " (dirty worktree)" if dirty else ""
    return f"""# Pressure Scenario: {item["id"]}

Commit: `{commit}`{dirty_note}
Skill version: `{version}`
Host: `{host}`
Skill install path: `{host_info["skill_path"]}`

## Prompt

```text
{item["query"]}
```

## Expected Behavior Checklist

{expected}

## Evidence

Fill the matching JSON evidence file under `evidence/` and validate it with
`tools/validate_pressure_evidence.py`.

```text
Commit: {commit}
Dirty worktree: {"yes" if dirty else "no"}
Host: {host}
Skill install path: {host_info["skill_path"]}
Scenario id: {item["id"]}
Prompt: {item["query"]}
Result: pass | fail
Evidence link or transcript id:
Reviewer notes:
Follow-up issue:
```
"""


def scenario_evidence_json(host: str, commit: str, item: dict) -> dict:
    host_info = HOSTS[host]
    return {
        "commit": commit,
        "dirty_worktree": False,
        "host": host,
        "skill_install_path": host_info["skill_path"],
        "scenario_id": item["id"],
        "prompt": item["query"],
        "result": "pending",
        "evidence_link_or_transcript_id": "",
        "reviewer_notes": "",
        "follow_up_issue": "",
        "checks": [
            {
                "expected_behavior": expected,
                "passed": False,
                "evidence": "",
            }
            for expected in item["expected_behavior"]
        ],
    }


def readme(host: str, commit: str, version: str, count: int, dirty: bool) -> str:
    host_info = HOSTS[host]
    dirty_note = " (dirty worktree)" if dirty else ""
    return f"""# Midtrans Skill Pressure Pack

Commit: `{commit}`{dirty_note}
Skill version: `{version}`
Host: `{host}`
Scenario count: `{count}`

## Install

Run this in a clean merchant test repository:

```bash
{host_info["install"]}
```

Replace `<repo>` with the local path to the `midtrans-agent-skills` checkout at
the commit above.

## Run Rules

- Use exactly one scenario prompt at a time.
- Do not add hints beyond the prompt file.
- Let the host load `integrate-midtrans-payments` naturally or invoke it exactly
  as the prompt says.
- Mark a scenario as pass only when every checklist item in that scenario file
  is satisfied by the host's answer or patch.
- Fill the matching JSON file under `evidence/` and validate the completed
  evidence with `tools/validate_pressure_evidence.py`.

Any failed scenario becomes a finding to fix in the skill or explicitly defer
before official publication.
"""


def build(host: str, output_dir: Path, *, dry_run: bool, require_clean: bool) -> None:
    data = load_evaluations()
    commit = git_commit()
    dirty = git_dirty()
    if require_clean and dirty:
        fail("worktree is dirty; commit or stash changes before generating an official pressure pack")
    version = data.get("version", "")
    evaluations = data["evaluations"]

    if dry_run:
        print(
            f"pressure-pack-ok: host={host} scenarios={len(evaluations)} "
            f"commit={commit[:12]} dirty={'yes' if dirty else 'no'}"
        )
        return

    write_text(output_dir / "README.md", readme(host, commit, version, len(evaluations), dirty))
    manifest = {
        "commit": commit,
        "dirty_worktree": dirty,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "host": host,
        "skill": SKILL_NAME,
        "version": version,
        "scenario_count": len(evaluations),
        "scenarios": [item["id"] for item in evaluations],
    }
    write_text(output_dir / "manifest.json", json.dumps(manifest, indent=2) + "\n")
    for index, item in enumerate(evaluations, start=1):
        path = output_dir / f"{index:02d}-{item['id']}.md"
        write_text(path, scenario_markdown(host, commit, version, dirty, item))
        evidence_path = output_dir / "evidence" / f"{host}-{index:02d}-{item['id']}.json"
        write_text(evidence_path, json.dumps(scenario_evidence_json(host, commit, item), indent=2) + "\n")
    print(f"wrote {len(evaluations)} scenarios to {output_dir}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", choices=sorted(HOSTS), required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("pressure-pack"))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--require-clean",
        action="store_true",
        help="fail if the git worktree has uncommitted changes",
    )
    args = parser.parse_args()

    output_dir = args.output_dir
    if not output_dir.is_absolute():
        output_dir = ROOT / output_dir
    build(args.host, output_dir, dry_run=args.dry_run, require_clean=args.require_clean)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
