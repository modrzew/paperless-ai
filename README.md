# paperless-ai

A thin CLI for Paperless-ngx, designed to be driven by Claude Code as an agent. Uses your Claude subscription (no API tokens billed).

## What this is

A small Python CLI (`paperless-ai`) that wraps the Paperless-ngx REST API: list inbox docs, fetch OCR content, list/create tags and correspondents, update document metadata. There is no Python orchestrator and no "categorize" command — Claude is the orchestrator.

The categorization workflow lives in `.claude/commands/categorize.md` as a Claude Code slash command. Run `claude` in this directory and type `/categorize` to invoke it. The slash command runs in your default model (Sonnet/Opus) but delegates per-document analysis to a Haiku subagent (`.claude/agents/categorize-doc.md`) via the Task tool, so the bulk of the token spend hits Haiku's rate-limit budget instead of Sonnet's. The orchestrator processes the inbox in batches of 3 docs per subagent invocation (configurable) and refreshes the correspondents list between batches so newly-created correspondents are reused instead of duplicated.

## Why this shape

- **Subscription billing.** Claude Code uses your subscription, not the API. No per-token cost.
- **CLI surface, not MCP.** Claude is good at running shell commands. A CLI is debuggable end to end (every command Claude runs, you can run too) and has zero new infrastructure.
- **Prompt as code.** The categorization rules — semantic tag matching, correspondent normalization, dedup — live in `.claude/commands/categorize.md` and are version-controlled. Edit markdown to change behavior.

## Install

Requires Python 3.13+ and the [Claude Code CLI](https://docs.claude.com/en/docs/claude-code).

```bash
uv sync --dev
```

This installs the `paperless-ai` console script.

## Configure

```bash
cp .env.example .env
# edit PAPERLESS_URL and PAPERLESS_API_TOKEN
```

## Usage

### Categorize the inbox

```bash
cd /path/to/paperless-ai
claude
```

then in the Claude Code prompt:

```
/categorize
```

Pass arguments inline:

```
/categorize dry-run
/categorize limit 5
/categorize only bills, dry-run
```

Claude will list the inbox, fetch each unprocessed document, decide on metadata, and apply changes via the CLI. An `AI parsed` tag is added to every doc Claude touches so subsequent runs skip it.

### Manual primitives

The CLI is also useful directly. All read commands support `--json`.

```bash
paperless-ai test-connection
paperless-ai list-inbox
paperless-ai list-inbox --exclude-tag 12 --json
paperless-ai get-doc 42 --include-content
paperless-ai list-tags --json
paperless-ai list-correspondents --json
paperless-ai list-document-types --json
paperless-ai list-storage-paths --json

# Update metadata. --add-tag/--remove-tag use the server-side bulk_edit modify_tags
# operation, so they don't disturb existing tags (including the inbox tag).
paperless-ai update-doc 42 \
  --title "ACME Electric — Q2 invoice" \
  --type 3 --correspondent 7 --storage-path 4 \
  --add-tag 11 --add-tag 19

# Replace the full tag list (use sparingly — destructive)
paperless-ai update-doc 42 --set-tags 11,19,23

paperless-ai create-correspondent "Pacific Gas & Electric"
paperless-ai create-tag "AI parsed"
```

## Project layout

```
main.py                       # Click CLI entry points
config/settings.py            # Lazy env loader (pydantic-settings)
paperless/
  client.py                   # Paperless REST wrapper
  models.py                   # pydantic models for API responses
.claude/
  commands/categorize.md      # The /categorize slash command (orchestrator)
  agents/categorize-doc.md    # Haiku subagent for per-document analysis
  settings.json               # Permissions allowlist for the paperless-ai CLI
```

## Development

```bash
uv run ruff check .
uv run ruff format .
```

## Compatibility

API client targets Paperless-ngx 2.20.x. Uses unversioned API (`Accept: application/json`), so it serves API version 1 by default — should remain compatible with older and newer Paperless versions within reason.
