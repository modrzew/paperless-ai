"""Data models for Paperless-ngx API responses."""

from datetime import datetime

from pydantic import BaseModel, Field


class Tag(BaseModel):
    """Paperless tag model."""

    id: int
    name: str
    slug: str
    color: str = "#000000"
    text_color: str = "#ffffff"
    match: str = ""
    matching_algorithm: int = 0
    is_inbox_tag: bool = False
    document_count: int = 0


class Correspondent(BaseModel):
    """Paperless correspondent model."""

    id: int
    name: str
    slug: str
    match: str = ""
    matching_algorithm: int = 0
    is_insensitive: bool = True
    document_count: int = 0


class DocumentType(BaseModel):
    """Paperless document type model."""

    id: int
    name: str
    slug: str
    match: str = ""
    matching_algorithm: int = 0
    is_insensitive: bool = True
    document_count: int = 0


class StoragePath(BaseModel):
    """Paperless storage path model."""

    id: int
    name: str
    slug: str
    path: str
    match: str = ""
    matching_algorithm: int = 0
    is_insensitive: bool = True
    document_count: int = 0


class Document(BaseModel):
    """Paperless document model."""

    id: int
    title: str
    content: str = ""
    correspondent: int | None = None
    document_type: int | None = None
    storage_path: int | None = None
    tags: list[int] = Field(default_factory=list)
    created: datetime
    created_date: str
    modified: datetime
    added: datetime
    archive_serial_number: int | None = None
    original_file_name: str
    archived_file_name: str | None = None
    owner: int | None = None
    user_can_change: bool = True


class PaginatedResponse(BaseModel):
    """Generic paginated API response."""

    count: int
    next: str | None = None
    previous: str | None = None
    all: list[int] = Field(default_factory=list)
    results: list[dict] = Field(default_factory=list)
