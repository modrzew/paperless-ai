---
description: Categorize unprocessed documents in the Paperless-ngx inbox (Haiku does per-batch work)
argument-hint: [optional notes, e.g. "dry-run", "limit 5", "batch 5", "only bills"]
---

You are the orchestrator for categorizing the Paperless-ngx inbox. Per-document analysis is delegated to the `categorize-doc` subagent (pinned to Haiku for speed and rate-limit efficiency), processing **a batch of up to 3 documents at a time**. You stay in control of cross-document concerns: cached metadata, deduping new correspondents across batches, and the final summary.

## Workflow

1. **Bootstrap the parsed-tag.** Find the tag named `AI parsed`:

   ```
   paperless-ai list-tags --json
   ```

   If absent, create it once:

   ```
   paperless-ai create-tag "AI parsed" --json
   ```

   Remember its id as `parsed_tag_id`.

2. **Cache metadata.** Run all four list commands once and remember the JSON results:

   ```
   paperless-ai list-tags --json
   paperless-ai list-correspondents --json
   paperless-ai list-document-types --json
   paperless-ai list-storage-paths --json
   ```

   The `tags`, `document_types`, and `storage_paths` lists are static for the entire run — subagents are forbidden from creating these. Only the `correspondents` list grows during the run as subagents create new ones.

3. **List the inbox**, excluding already-processed docs:

   ```
   paperless-ai list-inbox --exclude-tag <parsed_tag_id> --json
   ```

   Apply any `limit N` from the runtime arguments here (slice the list before batching).

4. **Slice into batches** of size `batch_size` (default 3, override with `batch N` runtime arg). For each batch in sequence, invoke the `categorize-doc` subagent via the Task tool with `subagent_type: "categorize-doc"`. The prompt must contain:

   - `documents: [<doc_id>, <doc_id>, <doc_id>]` — up to `batch_size` ids from this batch
   - `parsed_tag_id`
   - `dry_run`
   - `tags`, `document_types`, `storage_paths` — the cached lists (unchanged across batches)
   - `correspondents` — **the freshest version, including every `new_correspondent` reported by every prior batch in this run**

   The subagent returns a JSON array with one result object per doc.

5. **After each batch returns, before invoking the next batch:**

   - Parse the JSON array from the subagent.
   - For every result with a non-null `new_correspondent`, append `{"id": <id>, "name": <name>}` (and any other minimal fields the schema needs to make matching work) to your in-memory `correspondents` list.
   - The next batch's prompt **must** include this updated list. If you forget this step you'll get duplicate correspondents created across batches — the whole point of the orchestrator is to prevent that.
   - Record per-doc results for the final summary.

6. **Process batches sequentially**, not in parallel. Sequential ordering is what makes the cross-batch correspondent dedup work — each batch sees everything created by previous batches. If processing 50+ docs is too slow, ask the user before switching strategies.

## Hard constraints

- **Never delete anything in Paperless** — no documents, tags, correspondents, types, or storage paths. Categorization is purely additive (and you don't have a CLI command for deletion anyway). Don't try to work around that with `curl` or by calling the Paperless API directly. If a document looks like junk, leave it; a human will handle it.
- **The only writes you (or the subagent) should ever issue** are: `paperless-ai create-tag` (only for `AI parsed` if missing), `paperless-ai create-correspondent`, and `paperless-ai update-doc` (with `--add-tag` only — not `--remove-tag` or `--set-tags`).

## Final summary

When done, print:

- Number of docs applied / dry-run / skipped / errored
- Any new correspondents created (`name → id`)
- A short list of any errors with doc ids

Use a compact human-readable format, not JSON.

## Runtime arguments

The user passed these arguments (may be empty):

$ARGUMENTS

Honor:
- **`dry-run`** — pass `dry_run: true` to every subagent. They won't write.
- **`limit N`** — only process the first N inbox docs after step 3 (before slicing into batches).
- **`batch N`** — override the default batch size of 3. Reasonable values: 1–5. Larger batches save metadata-token duplication but increase blast radius per failure.
- Any free-form scoping ("only bills", "skip payslips") — apply it as a filter when iterating in step 4. Subagents don't see this; you decide which docs to include in the batches you send.
