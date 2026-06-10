#!/usr/bin/env python3
"""Build the exact file bundle for hosted Midtrans Agent Skills publication."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / ".well-known" / "skills" / "index.json"
SKILL_ROOT = ROOT / "integrate-midtrans-payments"
ROOT_PUBLICATION_FILES = [
    (ROOT / "LICENSE", Path("LICENSE")),
]


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


def load_index() -> dict:
    try:
        with INDEX.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception as exc:  # noqa: BLE001 - report all load failures uniformly.
        fail(f"cannot read hosted skill index: {exc}")
    if not isinstance(data, dict):
        fail("hosted skill index must be a JSON object")
    skills = data.get("skills")
    if not isinstance(skills, list) or not skills:
        fail("hosted skill index must include at least one skill")
    return data


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def indexed_files(index: dict) -> list[tuple[Path, Path]]:
    files: list[tuple[Path, Path]] = [*ROOT_PUBLICATION_FILES, (INDEX, Path(".well-known/skills/index.json"))]
    for source, _target in ROOT_PUBLICATION_FILES:
        if not source.is_file():
            fail(f"publication root file is missing: {source.relative_to(ROOT)}")
    for skill in index["skills"]:
        if not isinstance(skill, dict):
            fail("skill index entries must be objects")
        path = skill.get("path")
        listed = skill.get("files")
        if path != "integrate-midtrans-payments/":
            fail(f"unexpected skill path in index: {path!r}")
        if not isinstance(listed, list) or not listed:
            fail("skill entry must include non-empty files list")
        for rel in listed:
            if not isinstance(rel, str) or rel.startswith("/") or ".." in Path(rel).parts:
                fail(f"unsafe indexed file path: {rel!r}")
            source = SKILL_ROOT / rel
            if not source.is_file():
                fail(f"indexed file is missing: {source.relative_to(ROOT)}")
            target = Path("integrate-midtrans-payments") / rel
            files.append((source, target))
    return files


def validate_index_completeness(index: dict) -> None:
    listed = sorted(
        str(target.relative_to("integrate-midtrans-payments"))
        for _, target in indexed_files(index)
        if str(target).startswith("integrate-midtrans-payments/")
    )
    actual = sorted(
        str(path.relative_to(SKILL_ROOT))
        for path in SKILL_ROOT.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    )
    missing = [path for path in listed if not (SKILL_ROOT / path).is_file()]
    extra = [path for path in actual if path not in listed]
    if missing or extra:
        fail(f"skill index mismatch; missing={missing}, extra={extra}")


def build_bundle(output_dir: Path, *, require_clean: bool, dry_run: bool) -> None:
    index = load_index()
    validate_index_completeness(index)
    commit = git_commit()
    dirty = git_dirty()
    if require_clean and dirty:
        fail("worktree is dirty; commit or stash changes before building an official publication bundle")
    files = indexed_files(index)

    manifest_files = [
        {
            "path": str(target),
            "sha256": sha256(source),
            "bytes": source.stat().st_size,
        }
        for source, target in files
    ]
    manifest = {
        "commit": commit,
        "dirty_worktree": dirty,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "homepage": index.get("homepage"),
        "repository": index.get("repository"),
        "version": index.get("version"),
        "file_count": len(manifest_files),
        "files": manifest_files,
    }

    if dry_run:
        print(
            "publication-bundle-ok: "
            f"version={manifest['version']} files={len(files)} commit={commit[:12]} "
            f"dirty={'yes' if dirty else 'no'}"
        )
        return

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)
    for source, target in files:
        destination = output_dir / target
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    (output_dir / "publication-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"wrote publication bundle to {output_dir}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("dist/publication-bundle"))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--require-clean", action="store_true")
    args = parser.parse_args()

    output_dir = args.output_dir
    if not output_dir.is_absolute():
        output_dir = ROOT / output_dir
    build_bundle(output_dir, require_clean=args.require_clean, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
