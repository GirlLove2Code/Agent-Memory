"""
Vivioo Memory — Bulk Import
Import memories from files into the branch system.

Supports:
  - Markdown files (splits by headings or paragraphs)
  - Plain text files (splits by paragraphs)
  - JSON files (expects array of {content, tags?, source?})
  - JSONL files (one JSON object per line)

All imports go through the full pipeline:
  - Importance scoring
  - Conflict detection
  - Auto-expiry
  - Vector sync
  - Event hooks

Usage:
    from bulk_import import import_file, import_text, import_entries

    # Import a markdown file
    result = import_file("notes.md", branch="knowledge-base")

    # Import raw text
    result = import_text("Some long text...", branch="project-notes")

    # Import structured entries
    result = import_entries([
        {"content": "First memory", "tags": ["important"]},
        {"content": "Second memory", "source": "agent"},
    ], branch="project-notes")
"""

import os
import re
import json
from typing import List, Dict, Optional

from branch_manager import create_branch, list_branches, load_branch_index
from entry_manager import add_memory


def import_file(file_path: str, branch: str, source: str = None,
                tags: List[str] = None, auto_resolve: bool = True,
                min_length: int = 30) -> dict:
    """
    Import a file into a branch as memory entries.

    Args:
        file_path: path to the file
        branch: target branch (created if doesn't exist)
        source: override source for all entries (default: "import:{filename}")
        tags: tags to add to all imported entries
        auto_resolve: if True, detect conflicts with existing entries
        min_length: skip chunks shorter than this (filters noise)

    Returns:
        {
            "imported": int,
            "skipped": int,
            "conflicts_resolved": int,
            "file": str,
            "branch": str,
            "entries": [entry_ids],
        }
    """
    if not os.path.exists(file_path):
        return {"error": f"File not found: {file_path}", "imported": 0}

    filename = os.path.basename(file_path)
    file_source = source or f"import:{filename}"

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Detect format and split
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".json":
        return _import_json(content, branch, file_source, tags, auto_resolve)
    elif ext == ".jsonl":
        return _import_jsonl(content, branch, file_source, tags, auto_resolve)
    elif ext in (".md", ".markdown"):
        chunks = _split_markdown(content, min_length)
    else:
        chunks = _split_paragraphs(content, min_length)

    return _import_chunks(chunks, branch, file_source, tags, auto_resolve, filename)


def import_text(text: str, branch: str, source: str = "import:text",
                tags: List[str] = None, auto_resolve: bool = True,
                min_length: int = 30) -> dict:
    """
    Import raw text as memory entries (split by paragraphs).

    Args:
        text: the text to import
        branch: target branch
        source: source label
        tags: tags for all entries
        auto_resolve: detect conflicts
        min_length: minimum chunk length

    Returns:
        Same format as import_file()
    """
    chunks = _split_paragraphs(text, min_length)
    return _import_chunks(chunks, branch, source, tags, auto_resolve, "text")


def import_entries(entries: List[dict], branch: str,
                   auto_resolve: bool = True) -> dict:
    """
    Import structured entries directly.

    Each entry dict should have at minimum:
        {"content": "the memory text"}

    Optional fields:
        {"content": "...", "tags": [...], "source": "...", "happened_at": "ISO"}

    Args:
        entries: list of entry dicts
        branch: target branch
        auto_resolve: detect conflicts

    Returns:
        Same format as import_file()
    """
    _ensure_branch(branch)

    imported = 0
    skipped = 0
    conflicts = 0
    entry_ids = []

    for item in entries:
        content = item.get("content", "").strip()
        if not content:
            skipped += 1
            continue

        result = add_memory(
            branch=branch,
            content=content,
            tags=item.get("tags"),
            source=item.get("source", "import:structured"),
            happened_at=item.get("happened_at"),
            auto_resolve=auto_resolve,
        )

        entry_ids.append(result["id"])
        imported += 1

        if result.get("_resolved"):
            conflicts += len(result["_resolved"])

    return {
        "imported": imported,
        "skipped": skipped,
        "conflicts_resolved": conflicts,
        "branch": branch,
        "entries": entry_ids,
    }


# ─── SPLITTING ──────────────────────────────────────────────

def _split_markdown(text: str, min_length: int = 30) -> List[dict]:
    """
    Split markdown by headings. Each section becomes one memory entry.
    The heading becomes a tag.
    """
    chunks = []
    current_heading = None
    current_content = []

    for line in text.split("\n"):
        heading_match = re.match(r'^(#{1,4})\s+(.+)', line)
        if heading_match:
            # Save previous section
            if current_content:
                content = "\n".join(current_content).strip()
                if len(content) >= min_length:
                    chunks.append({
                        "content": content,
                        "heading": current_heading,
                    })
            current_heading = heading_match.group(2).strip()
            current_content = []
        else:
            current_content.append(line)

    # Save last section
    if current_content:
        content = "\n".join(current_content).strip()
        if len(content) >= min_length:
            chunks.append({
                "content": content,
                "heading": current_heading,
            })

    return chunks


def _split_paragraphs(text: str, min_length: int = 30) -> List[dict]:
    """Split by double newlines (paragraphs)."""
    paragraphs = re.split(r'\n\s*\n', text)
    chunks = []

    for para in paragraphs:
        content = para.strip()
        if len(content) >= min_length:
            chunks.append({"content": content, "heading": None})

    return chunks


# ─── IMPORT HELPERS ─────────────────────────────────────────

def _import_chunks(chunks: List[dict], branch: str, source: str,
                   tags: List[str], auto_resolve: bool,
                   filename: str) -> dict:
    """Import a list of text chunks as memory entries."""
    _ensure_branch(branch)

    imported = 0
    skipped = 0
    conflicts = 0
    entry_ids = []

    for chunk in chunks:
        content = chunk["content"]
        entry_tags = list(tags) if tags else []
        if chunk.get("heading"):
            entry_tags.append(f"section:{chunk['heading']}")

        result = add_memory(
            branch=branch,
            content=content,
            tags=entry_tags if entry_tags else None,
            source=source,
            auto_resolve=auto_resolve,
        )

        entry_ids.append(result["id"])
        imported += 1

        if result.get("_resolved"):
            conflicts += len(result["_resolved"])

    return {
        "imported": imported,
        "skipped": skipped,
        "conflicts_resolved": conflicts,
        "file": filename,
        "branch": branch,
        "entries": entry_ids,
    }


def _import_json(content: str, branch: str, source: str,
                 tags: List[str], auto_resolve: bool) -> dict:
    """Import from a JSON file (expects array of objects)."""
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        return {"error": f"Invalid JSON: {e}", "imported": 0}

    if not isinstance(data, list):
        data = [data]

    # Normalize: ensure each item has "content"
    entries = []
    for item in data:
        if isinstance(item, str):
            entries.append({"content": item, "source": source})
        elif isinstance(item, dict):
            item.setdefault("source", source)
            if tags:
                item.setdefault("tags", []).extend(tags)
            entries.append(item)

    return import_entries(entries, branch, auto_resolve)


def _import_jsonl(content: str, branch: str, source: str,
                  tags: List[str], auto_resolve: bool) -> dict:
    """Import from a JSONL file (one JSON object per line)."""
    entries = []
    for line in content.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
            if isinstance(item, str):
                entries.append({"content": item, "source": source})
            elif isinstance(item, dict):
                item.setdefault("source", source)
                if tags:
                    item.setdefault("tags", []).extend(tags)
                entries.append(item)
        except json.JSONDecodeError:
            continue

    return import_entries(entries, branch, auto_resolve)


def _ensure_branch(branch: str) -> None:
    """Create branch if it doesn't exist."""
    existing = list_branches()
    if branch not in existing:
        create_branch(branch, summary=f"Imported branch: {branch}")
