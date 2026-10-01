"""Read-only Employee Knowledge catalog.

This does not call the chat endpoint and does not change retrieval.
"""

from __future__ import annotations

import json
from urllib.parse import quote

import requests

from backend.config import get_settings

_CATALOG_TIMEOUT_SECONDS = 20


def employee_knowledge_catalog(usage: dict[str, dict]) -> dict:
    settings = get_settings()
    slug = settings.anythingllm_employee_workspace_slug
    if settings.missing_anythingllm():
        return _unavailable(slug, documents=[])

    quoted = quote(slug, safe="")
    endpoint = f"{settings.anythingllm_base_url}/api/v1/workspace/{quoted}"
    api_key = settings.anythingllm_api_key
    if api_key.lower().startswith("bearer "):
        api_key = api_key[7:].strip()
    try:
        response = requests.get(
            endpoint,
            headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
            timeout=_CATALOG_TIMEOUT_SECONDS,
        )
    except requests.RequestException:
        return _unavailable(slug, documents=_usage_only(usage))
    if response.status_code != 200:
        return _unavailable(slug, documents=_usage_only(usage))
    try:
        body = response.json()
    except ValueError:
        return _unavailable(slug, documents=_usage_only(usage))

    workspace = _workspace(body)
    if workspace is None:
        return _unavailable(slug, documents=_usage_only(usage))

    documents = []
    seen: set[str] = set()
    for item in workspace.get("documents") or []:
        if not isinstance(item, dict):
            continue
        title = _document_title(item)
        if not title:
            continue
        key = title.casefold()
        seen.add(key)
        documents.append(_public_document(title, usage.get(key)))
    for key, stats in usage.items():
        if key in seen:
            continue
        title = stats.get("title") or ""
        if title:
            documents.append(_public_document(title, stats))
    return {
        "connected": True,
        "workspace_name": str(workspace.get("name") or "").strip(),
        "workspace_slug": str(workspace.get("slug") or slug).strip(),
        "documents": documents,
    }


def _workspace(body: object) -> dict | None:
    if not isinstance(body, dict):
        return None
    workspace = body.get("workspace")
    if isinstance(workspace, dict):
        return workspace
    if isinstance(workspace, list) and workspace and isinstance(workspace[0], dict):
        return workspace[0]
    return None


def _document_title(item: dict) -> str:
    metadata = item.get("metadata")
    parsed: dict = {}
    if isinstance(metadata, str):
        try:
            loaded = json.loads(metadata)
        except ValueError:
            loaded = None
        if isinstance(loaded, dict):
            parsed = loaded
    elif isinstance(metadata, dict):
        parsed = metadata
    title = str(parsed.get("title") or item.get("filename") or "").strip()
    return _canonical_title(title)


def _canonical_title(title: str) -> str:
    name = title.replace("\\", "/").rsplit("/", 1)[-1]
    if name.lower().endswith(".json"):
        stem = name[:-5]
        marker = stem.lower().rfind(".pdf-")
        if marker != -1:
            return stem[: marker + 4]
    return name


def _public_document(title: str, stats: dict | None) -> dict:
    kind = _kind(title)
    document = {
        "title": title,
        "use_count": 0 if stats is None else int(stats.get("use_count") or 0),
        "last_used_at": None if stats is None else stats.get("last_used_at"),
        "last_request_id": None if stats is None else stats.get("last_request_id"),
        "last_request_preview": None if stats is None else stats.get("last_request_preview"),
    }
    if kind:
        document["kind"] = kind
    return document


def _kind(title: str) -> str | None:
    lowered = title.casefold()
    if lowered.endswith(".pdf"):
        return "PDF"
    if lowered.endswith(".docx"):
        return "DOCX"
    if lowered.endswith(".txt"):
        return "TXT"
    return None


def _usage_only(usage: dict[str, dict]) -> list[dict]:
    documents = []
    for stats in usage.values():
        title = str(stats.get("title") or "").strip()
        if title:
            documents.append(_public_document(title, stats))
    return documents


def _unavailable(slug: str, documents: list[dict]) -> dict:
    return {
        "connected": False,
        "workspace_name": "",
        "workspace_slug": slug,
        "documents": documents,
    }
