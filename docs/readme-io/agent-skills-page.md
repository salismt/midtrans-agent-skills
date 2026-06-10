---
title: AI Agent Skills
excerpt: Official Midtrans skill for AI coding agents — Claude Code, Codex, Copilot, Cursor, OpenCode, and more.
---

> Ready-to-publish source for the docs.midtrans.com "AI Agent Skills" page.
> Publish it under Guides (for example next to "Developer Tools"); ReadMe will
> add it to https://docs.midtrans.com/llms.txt automatically, so coding agents
> reading Midtrans docs discover the skill on their own. Remove this note
> before publishing.

Midtrans ships an official **Agent Skill** that teaches AI coding agents how to integrate Midtrans payments safely: product selection (Snap, Core API, BI-SNAP, Payment Link), merchant readiness preflight, payment state modeling, webhook signature verification, idempotent fulfillment, and sandbox-first verification.

The skill is a folder of Markdown instructions plus deterministic helper scripts. It needs **no credentials and calls no Midtrans APIs by itself** — your agent reads it and applies it to your codebase.

## Quick install

With the [skills CLI](https://github.com/vercel-labs/skills) (works with Claude Code, Codex, Cursor, and other supported agents):

```bash
npx skills add https://github.com/midtrans/midtrans-agent-skills --yes
```

Or copy the folder manually from the [midtrans/midtrans-agent-skills](https://github.com/midtrans/midtrans-agent-skills) repository:

| Agent | Project location |
| --- | --- |
| Claude Code | `.claude/skills/integrate-midtrans-payments/` |
| OpenAI Codex and compatible agents | `.codex/skills/` or `.agents/skills/` |
| GitHub Copilot / VS Code | `.github/skills/` |
| OpenCode | `.opencode/skills/` |
| Cursor and tools without native skills | copy the folder, then point a rule in `.cursor/rules/` or `AGENTS.md` at `integrate-midtrans-payments/SKILL.md` |

Then ask your agent, for example:

```text
Use integrate-midtrans-payments to add Midtrans Snap checkout to this app.
```

## What the skill enforces

- Inspects your project and confirms merchant readiness (account, sandbox keys, active payment methods, callback URLs) before writing code.
- Routes each payment method to the right Midtrans product instead of mixing Snap, Core API, and BI-SNAP request shapes.
- Keeps server keys and signing on the backend, verifies webhook signatures, and fulfills orders only from trusted signals.
- Verifies in sandbox with deterministic signature checks and webhook replay before any go-live step.

## Notes

- Manually copied skills do not auto-update — refresh the folder before major payment work.
- The skill treats this documentation site as the source of truth and re-reads [https://docs.midtrans.com/llms.txt](https://docs.midtrans.com/llms.txt) on every engagement; the skill files carry integration discipline, not API reference copies.
- Found a misroute or a gap? File an issue at [github.com/midtrans/midtrans-agent-skills](https://github.com/midtrans/midtrans-agent-skills/issues).
- A Midtrans MCP server for authenticated sandbox interaction is a separate, later phase; the skill stays the lightweight no-credentials option.
