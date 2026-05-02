"""Paperless-AI CLI — thin wrapper over the Paperless-ngx API, designed to be
driven by Claude Code as an agent."""

import json
import sys

import click
from rich.console import Console
from rich.table import Table

from paperless.client import PaperlessClient
from paperless.models import Document

console = Console()
err_console = Console(stderr=True)


def _print_json(data) -> None:
    click.echo(json.dumps(data, indent=2, default=str))


def _document_to_dict(doc: Document, include_content: bool) -> dict:
    data = doc.model_dump(mode="json")
    if not include_content:
        data.pop("content", None)
    return data


@click.group()
def cli():
    """Paperless-AI: thin CLI over Paperless-ngx for use with Claude Code."""


@cli.command("test-connection")
def test_connection():
    """Verify Paperless API credentials and connectivity."""
    try:
        client = PaperlessClient()
        ok = client.test_connection()
    except Exception as e:
        err_console.print(f"[red]✗[/red] {e}")
        sys.exit(1)
    if ok:
        console.print("[green]✓[/green] Connected to Paperless-ngx")
        sys.exit(0)
    err_console.print("[red]✗[/red] Failed to connect")
    sys.exit(1)


@cli.command("list-inbox")
@click.option(
    "--exclude-tag",
    "exclude_tag_ids",
    type=int,
    multiple=True,
    help="Exclude documents that have this tag id (can be passed multiple times).",
)
@click.option("--limit", type=int, help="Return at most N documents.")
@click.option("--json", "as_json", is_flag=True, help="Output JSON instead of a table.")
def list_inbox(exclude_tag_ids, limit, as_json):
    """List documents currently in the inbox."""
    client = PaperlessClient()
    documents = client.list_inbox_documents(exclude_tag_ids=list(exclude_tag_ids) or None)
    if limit:
        documents = documents[:limit]

    if as_json:
        _print_json([_document_to_dict(d, include_content=False) for d in documents])
        return

    table = Table(title=f"Inbox ({len(documents)} document(s))")
    table.add_column("ID", style="cyan")
    table.add_column("Title")
    table.add_column("Created", style="yellow")
    table.add_column("Original file", style="dim")
    for doc in documents:
        table.add_row(str(doc.id), doc.title, doc.created_date, doc.original_file_name)
    console.print(table)


@cli.command("get-doc")
@click.argument("document_id", type=int)
@click.option("--include-content", is_flag=True, help="Include the OCR content in the output.")
@click.option("--json", "as_json", is_flag=True, help="Output JSON (default if --include-content).")
def get_doc(document_id, include_content, as_json):
    """Fetch a single document by id."""
    client = PaperlessClient()
    doc = client.get_document(document_id)

    if as_json or include_content:
        _print_json(_document_to_dict(doc, include_content=include_content))
        return

    console.print(f"[cyan]ID[/cyan]      {doc.id}")
    console.print(f"[cyan]Title[/cyan]   {doc.title}")
    console.print(f"[cyan]Created[/cyan] {doc.created_date}")
    console.print(f"[cyan]Type[/cyan]    {doc.document_type}")
    console.print(f"[cyan]Corresp[/cyan] {doc.correspondent}")
    console.print(f"[cyan]Storage[/cyan] {doc.storage_path}")
    console.print(f"[cyan]Tags[/cyan]    {doc.tags}")


def _list_simple(items, name_attr: str, as_json: bool, title: str) -> None:
    if as_json:
        _print_json([item.model_dump(mode="json") for item in items])
        return
    table = Table(title=f"{title} ({len(items)})")
    table.add_column("ID", style="cyan")
    table.add_column("Name")
    table.add_column("Docs", style="dim")
    for item in items:
        table.add_row(str(item.id), getattr(item, name_attr), str(item.document_count))
    console.print(table)


@cli.command("list-tags")
@click.option("--json", "as_json", is_flag=True)
def list_tags(as_json):
    """List all tags."""
    _list_simple(PaperlessClient().list_tags(), "name", as_json, "Tags")


@cli.command("list-correspondents")
@click.option("--json", "as_json", is_flag=True)
def list_correspondents(as_json):
    """List all correspondents."""
    _list_simple(PaperlessClient().list_correspondents(), "name", as_json, "Correspondents")


@cli.command("list-document-types")
@click.option("--json", "as_json", is_flag=True)
def list_document_types(as_json):
    """List all document types."""
    _list_simple(PaperlessClient().list_document_types(), "name", as_json, "Document types")


@cli.command("list-storage-paths")
@click.option("--json", "as_json", is_flag=True)
def list_storage_paths(as_json):
    """List all storage paths."""
    _list_simple(PaperlessClient().list_storage_paths(), "name", as_json, "Storage paths")


@cli.command("update-doc")
@click.argument("document_id", type=int)
@click.option("--title", type=str, help="New title.")
@click.option("--type", "type_id", type=int, help="Document type id.")
@click.option("--correspondent", type=int, help="Correspondent id.")
@click.option("--storage-path", type=int, help="Storage path id.")
@click.option(
    "--add-tag",
    "add_tags",
    type=int,
    multiple=True,
    help="Tag id to add (server-side, leaves other tags untouched). Repeatable.",
)
@click.option(
    "--remove-tag",
    "remove_tags",
    type=int,
    multiple=True,
    help="Tag id to remove (server-side). Repeatable.",
)
@click.option(
    "--set-tags",
    "set_tags",
    type=str,
    help="Replace the full tag list with this comma-separated set of ids.",
)
@click.option("--json", "as_json", is_flag=True, help="Print updated doc as JSON.")
def update_doc(
    document_id,
    title,
    type_id,
    correspondent,
    storage_path,
    add_tags,
    remove_tags,
    set_tags,
    as_json,
):
    """Update document metadata. Use --add-tag/--remove-tag for non-destructive
    tag changes, or --set-tags to replace the entire tag list."""
    if set_tags is not None and (add_tags or remove_tags):
        raise click.UsageError("--set-tags is mutually exclusive with --add-tag/--remove-tag.")

    client = PaperlessClient()

    if add_tags or remove_tags:
        client.bulk_modify_tags(
            document_ids=[document_id],
            add_tags=list(add_tags) or None,
            remove_tags=list(remove_tags) or None,
        )

    metadata_changed = any(v is not None for v in (title, type_id, correspondent, storage_path))
    set_tag_list = (
        [int(t) for t in set_tags.split(",") if t.strip()] if set_tags is not None else None
    )

    if metadata_changed or set_tag_list is not None:
        doc = client.update_document(
            document_id=document_id,
            title=title,
            correspondent=correspondent,
            document_type=type_id,
            storage_path=storage_path,
            tags=set_tag_list,
        )
    else:
        doc = client.get_document(document_id)

    if as_json:
        _print_json(_document_to_dict(doc, include_content=False))
    else:
        console.print(f"[green]✓[/green] Updated document {document_id}")


@cli.command("create-correspondent")
@click.argument("name")
@click.option("--json", "as_json", is_flag=True)
def create_correspondent(name, as_json):
    """Create a new correspondent (with ML auto-matching enabled)."""
    corr = PaperlessClient().create_correspondent(name)
    if as_json:
        _print_json(corr.model_dump(mode="json"))
    else:
        console.print(f"[green]✓[/green] Created correspondent {corr.id}: {corr.name}")


@cli.command("create-tag")
@click.argument("name")
@click.option("--json", "as_json", is_flag=True)
def create_tag(name, as_json):
    """Create a new tag."""
    tag = PaperlessClient().create_tag(name)
    if as_json:
        _print_json(tag.model_dump(mode="json"))
    else:
        console.print(f"[green]✓[/green] Created tag {tag.id}: {tag.name}")


if __name__ == "__main__":
    cli()
