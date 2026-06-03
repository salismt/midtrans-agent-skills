# Official Release Readiness

Use this checklist before publishing Midtrans Agent Skills as an official
Midtrans artifact. It separates local technical gates from external publication
decisions that must be completed by the Midtrans repository owner.

## Local Technical Gate

Run this from the repository root:

```bash
./tools/check_official_readiness.py --check-doc-links
```

Install the workflow template at `docs/github-actions/official-readiness.yml`
into `.github/workflows/official-readiness.yml` before public release. It runs
`./tools/check_official_readiness.py` on pull requests and pushes to `main`.
Live `docs.midtrans.com` link checks run on the scheduled/manual
`Live Midtrans docs links` workflow job because they depend on external network
and docs-site availability.

The checker verifies:

- `SKILL.md` frontmatter, name, description, and size target,
- catalog/evaluation version consistency,
- `.well-known/skills/index.json` file list completeness,
- JSON fixtures and structured evaluations,
- every reference points agents back to `https://docs.midtrans.com/llms.txt`,
- script executable bits, shell syntax, and Python compilation,
- deterministic Snap fixture signatures,
- remote-target and production-key safety refusals,
- clean one-line BI-SNAP malformed-key errors,
- current Midtrans product/docs links when `--check-doc-links` is passed
  (the future hosted skill index is covered by the publication gate below).

Do not claim local release readiness unless this command exits `0` on the
commit being published.

## Agent Pressure Gate

The PRD requires all pressure scenarios in
`integrate-midtrans-payments/references/evaluation-prompts.md` to pass on:

- Claude Code, and
- at least one Codex-compatible host.

Generate a prompt/evidence pack for each host:

```bash
./tools/build_pressure_pack.py --host claude-code --require-clean --output-dir /tmp/midtrans-pressure-claude
./tools/build_pressure_pack.py --host codex --require-clean --output-dir /tmp/midtrans-pressure-codex
```

Use the same repository commit and a clean merchant test repo for each host.
Install the skill using the host's documented skill path, then run every
scenario without adding hints beyond the scenario prompt. The agent passes a
scenario only if its answer or patch satisfies the expected behavior listed in
both `references/evaluation-prompts.md` and `evaluations.json`.

Capture evidence in this format:

```text
Commit:
Host:
Skill install path:
Scenario id:
Prompt:
Result: pass | fail
Evidence link or transcript id:
Reviewer notes:
Follow-up issue:
```

Any failed scenario must become a tracked finding and either be fixed in the
skill or explicitly deferred by the Midtrans owner before publication.

When both host runs are complete, copy the filled `evidence/*.json` files into
one directory and validate:

```bash
./tools/validate_pressure_evidence.py \
  --evidence-dir /tmp/midtrans-pressure-evidence \
  --commit "$(git rev-parse HEAD)" \
  --required-host claude-code \
  --required-host codex
```

This command must pass before claiming the agent pressure gate is complete.

## Publication Gate

Before public release, the Midtrans owner must confirm:

- final public repository URL and ownership,
- repository visibility,
- BSD 3-Clause license text in `LICENSE`,
- docs publishing location for `.well-known/skills/index.json`,
- installed GitHub Actions readiness workflow,
- docs page with manual install instructions for Claude Code, Codex, GitHub
  Copilot, Cursor, OpenCode, and generic Markdown agents,
- release tag/version,
- review cadence for docs drift against `https://docs.midtrans.com/llms.txt`,
- support path for merchant-reported skill routing bugs.

Do not include experimental AP2/UCP worktrees or prototypes in the official
skills release unless that scope is explicitly added to the PRD.

To prepare files for the docs site or official repository, build a clean
publication bundle:

```bash
./tools/build_publication_bundle.py \
  --require-clean \
  --output-dir /tmp/midtrans-agent-skills-publication
```

Publish the copied `.well-known/skills/index.json` and
`integrate-midtrans-payments/` folder from that output. Keep
`publication-manifest.json` as the checksum record for the release.
