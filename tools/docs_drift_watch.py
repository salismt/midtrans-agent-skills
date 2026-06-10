#!/usr/bin/env python3
"""Detect docs.midtrans.com drift against the skill's documented dependencies.

Fetches https://docs.midtrans.com/llms.txt plus every page listed in
docs/doc-sync/doc-dependencies.json and compares them with the stored
snapshot in docs/doc-sync/doc-snapshot.json.

Exit codes: 0 no drift, 1 drift detected (report on stdout),
2 bad input or a network failure that prevents comparison.

Run with --update to (re)write the snapshot after reviewing drift.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs" / "doc-sync" / "doc-dependencies.json"
SNAPSHOT = ROOT / "docs" / "doc-sync" / "doc-snapshot.json"
REFERENCES = ROOT / "integrate-midtrans-payments" / "references"
LLMS_TXT = "https://docs.midtrans.com/llms.txt"
DOC_URL_RE = re.compile(r"https://docs\.midtrans\.com/[^\s)\]\[(`\"<]+")


def fail(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(2)


def fetch(url: str) -> tuple[int, bytes]:
    """Return (http_status, body). Raises SystemExit(2) on transport failure."""
    result = subprocess.run(
        [
            "curl",
            "--http1.1",
            "-L",
            "-sS",
            "--connect-timeout",
            "5",
            "--max-time",
            "30",
            "-A",
            "midtrans-agent-skills-docs-drift-watch/1.0",
            "-w",
            "\n%{http_code}",
            url,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        fail(f"fetch failed for {url}: {result.stderr.decode().strip()}")
    body, _, status_text = result.stdout.rpartition(b"\n")
    status = int(status_text) if status_text.isdigit() else 0
    return status, body


def load_manifest() -> dict[str, list[str]]:
    try:
        raw = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - report any parse/read failure uniformly.
        fail(f"{MANIFEST.relative_to(ROOT)} is not valid JSON: {exc}")
    manifest = {key: value for key, value in raw.items() if not key.startswith("_")}
    if not manifest:
        fail("doc-dependencies.json lists no references")
    for reference, urls in manifest.items():
        if not (REFERENCES / reference).is_file():
            fail(f"doc-dependencies.json names unknown reference: {reference}")
        if not isinstance(urls, list) or not urls:
            fail(f"doc-dependencies.json entry needs at least one URL: {reference}")
        for url in urls:
            if not DOC_URL_RE.fullmatch(url):
                fail(f"doc-dependencies.json has a non-docs URL for {reference}: {url}")
    return manifest


def collect_current(manifest: dict[str, list[str]]) -> tuple[list[str], dict[str, str], list[str]]:
    status, body = fetch(LLMS_TXT)
    if status >= 400 or status == 0:
        fail(f"llms.txt returned HTTP {status}")
    llms_urls = sorted(set(DOC_URL_RE.findall(body.decode("utf-8", errors="replace"))))

    hashes: dict[str, str] = {}
    unreachable: list[str] = []
    for url in sorted({url for urls in manifest.values() for url in urls}):
        page_status, page_body = fetch(url)
        if page_status >= 400 or page_status == 0:
            unreachable.append(f"{url} (HTTP {page_status})")
            continue
        hashes[url] = hashlib.sha256(page_body).hexdigest()
    return llms_urls, hashes, unreachable


def report_drift(
    manifest: dict[str, list[str]],
    snapshot: dict,
    llms_urls: list[str],
    hashes: dict[str, str],
    unreachable: list[str],
) -> bool:
    old_urls = set(snapshot.get("llms_urls", []))
    old_hashes = snapshot.get("hashes", {})
    added = sorted(set(llms_urls) - old_urls)
    removed = sorted(old_urls - set(llms_urls))
    changed = sorted(
        url for url, digest in hashes.items() if url in old_hashes and old_hashes[url] != digest
    )

    drift = bool(added or removed or changed or unreachable)
    if not drift:
        print(f"no docs drift since {snapshot.get('checked_at', 'unknown date')}")
        return False

    print(f"docs.midtrans.com drift since {snapshot.get('checked_at', 'unknown date')}:")
    if changed or unreachable:
        affected = {url: [] for url in changed}
        for reference, urls in manifest.items():
            for url in urls:
                if url in affected:
                    affected[url].append(reference)
        print("\nChanged pages (review the listed references):")
        for url in changed:
            print(f"- {url} -> references/{', references/'.join(affected[url])}")
        for entry in unreachable:
            print(f"- UNREACHABLE {entry}")
    if added:
        print("\nNew llms.txt pages (check whether the skill should cover them):")
        for url in added:
            print(f"- {url}")
    if removed:
        print("\nRemoved llms.txt pages:")
        for url in removed:
            print(f"- {url}")
    print("\nAfter updating the affected references, refresh the snapshot with:")
    print("  ./tools/docs_drift_watch.py --update")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--update",
        action="store_true",
        help="write the current docs state to the snapshot instead of comparing",
    )
    args = parser.parse_args()

    manifest = load_manifest()
    llms_urls, hashes, unreachable = collect_current(manifest)

    if args.update:
        if unreachable:
            fail("cannot snapshot unreachable pages: " + "; ".join(unreachable))
        SNAPSHOT.write_text(
            json.dumps(
                {
                    "checked_at": date.today().isoformat(),
                    "llms_urls": llms_urls,
                    "hashes": hashes,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"snapshot written: {SNAPSHOT.relative_to(ROOT)} ({len(hashes)} pages tracked)")
        return 0

    if not SNAPSHOT.is_file():
        fail("doc-snapshot.json is missing; run with --update to create it")
    try:
        snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - report any parse/read failure uniformly.
        fail(f"{SNAPSHOT.relative_to(ROOT)} is not valid JSON: {exc}")
    return 1 if report_drift(manifest, snapshot, llms_urls, hashes, unreachable) else 0


if __name__ == "__main__":
    raise SystemExit(main())
