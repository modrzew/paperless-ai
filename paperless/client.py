"""Paperless-ngx API client."""

import time
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config.settings import get_settings
from paperless.models import (
    Correspondent,
    Document,
    DocumentType,
    PaginatedResponse,
    StoragePath,
    Tag,
)


class PaperlessClient:
    """Client for interacting with Paperless-ngx API."""

    def __init__(self):
        settings = get_settings()
        self.base_url = settings.paperless_url
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Token {settings.paperless_api_token}",
                "Content-Type": "application/json",
            }
        )
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def _request(self, method: str, endpoint: str, **kwargs) -> dict | None:
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.request(method, url, timeout=30, **kwargs)
            response.raise_for_status()
            if response.status_code == 204 or not response.content:
                return None
            return response.json()
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code
            if status == 401:
                raise ConnectionError("Authentication failed. Check your API token.") from e
            if status == 404:
                raise ValueError(f"Resource not found: {url}") from e
            if status == 400:
                raise ValueError(f"Bad request: {e.response.text}") from e
            raise ConnectionError(f"API request failed ({status}): {e}") from e
        except requests.exceptions.Timeout as e:
            raise TimeoutError(f"Request timed out: {url}") from e
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(f"Failed to connect to Paperless: {url}") from e

    def _get(self, endpoint: str, params: dict[str, Any] | None = None) -> dict:
        return self._request("GET", endpoint, params=params)

    def _post(self, endpoint: str, data: dict[str, Any]) -> dict:
        return self._request("POST", endpoint, json=data)

    def _patch(self, endpoint: str, data: dict[str, Any]) -> dict:
        return self._request("PATCH", endpoint, json=data)

    def _get_all_pages(self, endpoint: str, params: dict[str, Any] | None = None) -> list[dict]:
        all_results = []
        page = 1
        params = dict(params or {})

        while True:
            params["page"] = page
            data = self._get(endpoint, params)
            paginated = PaginatedResponse(**data)
            all_results.extend(paginated.results)

            if not paginated.next:
                break
            page += 1
            time.sleep(0.1)

        return all_results

    def test_connection(self) -> bool:
        try:
            self._get("/api/documents/", params={"page_size": 1})
            return True
        except Exception:
            return False

    def list_inbox_documents(self, exclude_tag_ids: list[int] | None = None) -> list[Document]:
        """List inbox documents, optionally excluding any with the given tags (server-side)."""
        params: dict[str, Any] = {"is_in_inbox": "true"}
        if exclude_tag_ids:
            params["tags__id__none"] = ",".join(str(t) for t in exclude_tag_ids)
        results = self._get_all_pages("/api/documents/", params=params)
        return [Document(**doc) for doc in results]

    def get_document(self, document_id: int) -> Document:
        data = self._get(f"/api/documents/{document_id}/")
        return Document(**data)

    def list_tags(self) -> list[Tag]:
        return [Tag(**t) for t in self._get_all_pages("/api/tags/")]

    def list_correspondents(self) -> list[Correspondent]:
        return [Correspondent(**c) for c in self._get_all_pages("/api/correspondents/")]

    def list_document_types(self) -> list[DocumentType]:
        return [DocumentType(**dt) for dt in self._get_all_pages("/api/document_types/")]

    def list_storage_paths(self) -> list[StoragePath]:
        return [StoragePath(**sp) for sp in self._get_all_pages("/api/storage_paths/")]

    def create_correspondent(self, name: str) -> Correspondent:
        # matching_algorithm 6 = MATCH_AUTO (Paperless ML matching)
        data = {"name": name, "matching_algorithm": 6}
        return Correspondent(**self._post("/api/correspondents/", data))

    def create_tag(self, name: str) -> Tag:
        return Tag(**self._post("/api/tags/", {"name": name}))

    def update_document(
        self,
        document_id: int,
        title: str | None = None,
        correspondent: int | None = None,
        document_type: int | None = None,
        storage_path: int | None = None,
        tags: list[int] | None = None,
    ) -> Document:
        """PATCH a document. Passing tags replaces the full tag list — use bulk_modify_tags
        instead when you only want to add/remove specific tags."""
        data: dict[str, Any] = {}
        if title is not None:
            data["title"] = title
        if correspondent is not None:
            data["correspondent"] = correspondent
        if document_type is not None:
            data["document_type"] = document_type
        if storage_path is not None:
            data["storage_path"] = storage_path
        if tags is not None:
            data["tags"] = tags
        return Document(**self._patch(f"/api/documents/{document_id}/", data))

    def bulk_modify_tags(
        self,
        document_ids: list[int],
        add_tags: list[int] | None = None,
        remove_tags: list[int] | None = None,
    ) -> None:
        """Atomically add and/or remove tags across documents without touching others."""
        payload = {
            "documents": document_ids,
            "method": "modify_tags",
            "parameters": {
                "add_tags": add_tags or [],
                "remove_tags": remove_tags or [],
            },
        }
        self._post("/api/documents/bulk_edit/", payload)
