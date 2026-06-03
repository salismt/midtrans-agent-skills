#!/usr/bin/env python3
"""Validate completed Claude/Codex pressure-run evidence files."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVALUATIONS = ROOT / "integrate-midtrans-payments" / "evaluations.json"
DEFAULT_REQUIRED_HOSTS = ("claude-code", "codex")


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


def load_json(path: Path) -> object:
    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception as exc:  # noqa: BLE001 - report any parse/read failure uniformly.
        fail(f"{path} is not valid JSON: {exc}")


def expected_scenarios() -> dict[str, dict]:
    data = load_json(EVALUATIONS)
    if not isinstance(data, dict):
        fail("evaluations.json must be an object")
    evaluations = data.get("evaluations")
    if not isinstance(evaluations, list) or not evaluations:
        fail("evaluations.json must contain evaluations")
    scenarios: dict[str, dict] = {}
    for item in evaluations:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            fail("each evaluation must contain id")
        scenarios[item["id"]] = item
    return scenarios


def collect_evidence(evidence_dir: Path) -> list[dict]:
    files = sorted(evidence_dir.rglob("*.json"))
    if not files:
        fail(f"no evidence JSON files found under {evidence_dir}")
    evidence = []
    for path in files:
        value = load_json(path)
        if not isinstance(value, dict):
            fail(f"{path} must contain one evidence object")
        value["_path"] = str(path)
        evidence.append(value)
    return evidence


def validate_one(record: dict, scenarios: dict[str, dict], commit: str) -> tuple[str, str]:
    path = record.get("_path", "<unknown>")
    scenario_id = record.get("scenario_id")
    host = record.get("host")
    if not isinstance(scenario_id, str) or scenario_id not in scenarios:
        fail(f"{path}: unknown scenario_id {scenario_id!r}")
    if not isinstance(host, str) or not host:
        fail(f"{path}: host is required")
    if record.get("commit") != commit:
        fail(f"{path}: commit mismatch; expected {commit}, got {record.get('commit')!r}")
    if record.get("dirty_worktree") is not False:
        fail(f"{path}: dirty_worktree must be false")
    if record.get("result") != "pass":
        fail(f"{path}: result must be pass")
    if not str(record.get("evidence_link_or_transcript_id", "")).strip():
        fail(f"{path}: evidence_link_or_transcript_id is required")

    expected = scenarios[scenario_id]["expected_behavior"]
    checks = record.get("checks")
    if not isinstance(checks, list) or len(checks) != len(expected):
        fail(f"{path}: expected {len(expected)} checks, got {len(checks) if isinstance(checks, list) else 'non-list'}")
    for index, (check, expected_text) in enumerate(zip(checks, expected), start=1):
        if not isinstance(check, dict):
            fail(f"{path}: check {index} must be an object")
        if check.get("expected_behavior") != expected_text:
            fail(f"{path}: check {index} expected_behavior does not match evaluations.json")
        if check.get("passed") is not True:
            fail(f"{path}: check {index} is not marked passed")
        if not str(check.get("evidence", "")).strip():
            fail(f"{path}: check {index} needs supporting evidence")
    return host, scenario_id


def validate_all(evidence_dir: Path, commit: str, required_hosts: list[str]) -> None:
    scenarios = expected_scenarios()
    records = collect_evidence(evidence_dir)
    seen: dict[str, set[str]] = {host: set() for host in required_hosts}
    duplicates: set[tuple[str, str]] = set()
    encountered: set[tuple[str, str]] = set()

    for record in records:
        host, scenario_id = validate_one(record, scenarios, commit)
        pair = (host, scenario_id)
        if pair in encountered:
            duplicates.add(pair)
        encountered.add(pair)
        if host in seen:
            seen[host].add(scenario_id)

    if duplicates:
        fail("duplicate evidence records: " + ", ".join(f"{host}/{scenario}" for host, scenario in sorted(duplicates)))

    expected_ids = set(scenarios)
    missing_messages = []
    for host in required_hosts:
        missing = sorted(expected_ids - seen[host])
        if missing:
            missing_messages.append(f"{host}: {', '.join(missing)}")
    if missing_messages:
        fail("missing required passing evidence: " + "; ".join(missing_messages))

    print(
        "pressure evidence valid: "
        f"commit={commit[:12]} hosts={','.join(required_hosts)} scenarios={len(expected_ids)}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--commit", default=None)
    parser.add_argument(
        "--required-host",
        action="append",
        dest="required_hosts",
        default=None,
        help="host that must have passing evidence for every scenario; repeatable",
    )
    args = parser.parse_args()

    commit = args.commit or git_commit()
    required_hosts = args.required_hosts or list(DEFAULT_REQUIRED_HOSTS)
    validate_all(args.evidence_dir, commit, required_hosts)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
