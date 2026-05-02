# CLAUDE.md

Guidance for Claude Code working in this repository.

## What this project is

A small Python 3.13+ CLI (`paperless-ai`) that wraps the Paperless-ngx REST API. The CLI is designed to be driven by you (Claude) as an agent — there is no Python orchestrator. You decide what to do; the CLI is a tool surface.

## Setup

```bash
uv sync --dev
```

## Lint / format

```bash
uv run ruff check .
uv run ruff format .
```

## Categorizing the inbox

Run the project slash command:

```
/categorize
```

It expands `.claude/commands/categorize.md`. The slash command is the **orchestrator** — it runs in whatever model you launched `claude` with. Per-document analysis is delegated via the Task tool to the `categorize-doc` subagent (`.claude/agents/categorize-doc.md`), which is pinned to **Haiku** for speed and rate-limit efficiency. The orchestrator processes the inbox in **batches of 3 docs per subagent invocation** (configurable via `batch N` runtime arg) and refreshes the cached `correspondents` list between batches so cross-batch dedup works correctly.

To change behavior:
- Cross-doc / batch logic → edit `.claude/commands/categorize.md`
- Per-doc rules (correspondent matching, semantic tag rules) → edit `.claude/agents/categorize-doc.md`

Pass arguments inline: `/categorize dry-run`, `/categorize limit 5`, `/categorize batch 5`, `/categorize only bills`. The orchestrator forwards them appropriately.

## CLI surface

Run `paperless-ai --help` for the full list. Key commands you'll use during categorization:

- `paperless-ai list-inbox --exclude-tag <id> --json`
- `paperless-ai list-tags|list-correspondents|list-document-types|list-storage-paths --json`
- `paperless-ai get-doc <id> --include-content --json`
- `paperless-ai update-doc <id> --title ... --type ID --correspondent ID --add-tag ID ...`
- `paperless-ai create-correspondent "<name>"`
- `paperless-ai create-tag <name>`

`--add-tag`/`--remove-tag` use the server-side `bulk_edit modify_tags` operation, so they never replace the existing tag list. Use `--set-tags` only when you genuinely want to replace everything.

## Hard constraints

- **Never delete anything in Paperless.** No documents, tags, correspondents, document types, or storage paths. The `paperless-ai` CLI deliberately does not expose deletion — do not work around that with `curl`, `requests`, or by calling the Paperless API directly. This applies to every workflow in this repo, not just `/categorize`.

## Code conventions

- Use dependency injection, never monkey patching (especially in tests).
- Keep CLI commands thin — pure wrappers over `PaperlessClient` methods. Decision logic belongs in slash command markdown, not in Python.
- Do not add deletion commands to the CLI (`delete-doc`, `delete-tag`, etc.) without explicit user approval. The "no deletion" guarantee depends on the surface area staying small.
