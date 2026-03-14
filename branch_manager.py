"""
Vivioo Memory — Branch Manager (Steps 2-3)
Manages the branch tree structure: Master Index, branch creation,
aliases, and navigation.

Branch structure on disk:
  branches/
    knowledge-base/
      index.json       <- summary, aliases, security, sub-branches
      entries/          <- memory files
      marketing/
        index.json
        entries/
"""

import os
import json
import time
from typing import List, Dict, Optional

BASE_DIR = os.path.join(os.path.dirname(__file__), "branches")
MASTER_INDEX_PATH = os.path.join(os.path.dirname(__file__), "master_index.json")


def _ensure_dir(path: str) -> None:
    """Create directory if it doesn't exist."""
    os.makedirs(path, exist_ok=True)


# --- MASTER INDEX ---

def load_master_index() -> dict:
    """
    Load the Master Index — the catalog of all branches.

    Returns:
        {
            "branches": {
                "knowledge-base": {
                    "summary": "One-line description",
                    "entry_count": 4,
                    "security": "open",
                    "last_updated": "2026-03-12T...",
                    "sub_branches": ["marketing", "security"]
                },
                ...
            },
            "total_entries": 20,
            "last_rebuilt": "2026-03-12T..."
        }
    """
    if not os.path.exists(MASTER_INDEX_PATH):
        return {"branches": {}, "total_entries": 0, "last_rebuilt": None}

    with open(MASTER_INDEX_PATH, "r") as f:
        return json.load(f)


def save_master_index(index: dict) -> None:
    """Save the Master Index."""
    index["last_rebuilt"] = _now()
    with open(MASTER_INDEX_PATH, "w") as f:
        json.dump(index, f, indent=2)


def rebuild_master_index() -> dict:
    """
    Rebuild the Master Index from disk — walk all branches and count entries.
    Call this if the index gets out of sync.
    """
    index = {"branches": {}, "total_entries": 0, "last_rebuilt": _now()}

    if not os.path.exists(BASE_DIR):
        save_master_index(index)
        return index

    def _scan(dir_path, prefix=""):
        for name in sorted(os.listdir(dir_path)):
            full = os.path.join(dir_path, name)
            if not os.path.isdir(full) or name.startswith(".") or name == "entries":
                continue

            branch_path = f"{prefix}/{name}" if prefix else name
            branch_index = load_branch_index(branch_path)

            # Count entries
            entries_dir = os.path.join(full, "entries")
            entry_count = 0
            if os.path.exists(entries_dir):
                entry_count = len([
                    f for f in os.listdir(entries_dir)
                    if f.endswith(".json")
                ])

            # Find sub-branches
            sub_branches = [
                d for d in os.listdir(full)
                if os.path.isdir(os.path.join(full, d))
                and d != "entries" and not d.startswith(".")
            ]

            index["branches"][branch_path] = {
                "summary": branch_index.get("summary", ""),
                "entry_count": entry_count,
                "security": branch_index.get("security", "open"),
                "last_updated": branch_index.get("last_updated", ""),
                "sub_branches": sub_branches,
            }
            index["total_entries"] += entry_count

            # Recurse into sub-branches
            _scan(full, branch_path)

    _scan(BASE_DIR)
    save_master_index(index)
    return index


# --- BRANCH MANAGEMENT ---

def create_branch(path: str, aliases: List[str] = None,
                  security: str = "open", summary: str = "") -> dict:
    """
    Create a new branch at any depth.

    Args:
        path: e.g. "knowledge-base/marketing/paid-ads"
        aliases: shorthand words for routing, max 3
                 e.g. ["ads", "PPC"]
        security: "open", "local", or "locked"
        summary: initial one-line summary

    Returns:
        The branch index dict

    Raises:
        ValueError: if too many aliases or invalid security
    """
    if aliases and len(aliases) > 3:
        raise ValueError("Maximum 3 aliases per branch")

    if security not in {"open", "local", "locked"}:
        raise ValueError(f"Invalid security tier: {security}")

    # Create directories
    branch_dir = os.path.join(BASE_DIR, path.replace("/", os.sep))
    entries_dir = os.path.join(branch_dir, "entries")
    _ensure_dir(branch_dir)
    _ensure_dir(entries_dir)

    # Create branch index
    branch_index = {
        "path": path,
        "summary": summary,
        "aliases": aliases or [],
        "security": security,
        "created_at": _now(),
        "last_updated": _now(),
    }

    index_path = os.path.join(branch_dir, "index.json")
    with open(index_path, "w") as f:
        json.dump(branch_index, f, indent=2)

    # Update master index
    _update_master_index_entry(path, branch_index)

    return branch_index


def load_branch_index(path: str) -> dict:
    """Load a branch's index.json."""
    index_path = os.path.join(
        BASE_DIR, path.replace("/", os.sep), "index.json"
    )
    if not os.path.exists(index_path):
        return {"path": path, "summary": "", "aliases": [], "security": "open"}

    with open(index_path, "r") as f:
        return json.load(f)


def save_branch_index(path: str, index: dict) -> None:
    """Save a branch's index.json."""
    index["last_updated"] = _now()
    index_path = os.path.join(
        BASE_DIR, path.replace("/", os.sep), "index.json"
    )
    with open(index_path, "w") as f:
        json.dump(index, f, indent=2)


def get_branch_dir(path: str) -> str:
    """Get the filesystem path for a branch."""
    return os.path.join(BASE_DIR, path.replace("/", os.sep))


def get_entries_dir(path: str) -> str:
    """Get the entries directory for a branch."""
    return os.path.join(get_branch_dir(path), "entries")


def list_branches() -> List[str]:
    """List all branch paths."""
    index = load_master_index()
    return list(index.get("branches", {}).keys())


def get_branch(path: str) -> Optional[dict]:
    """Get branch info from the Master Index."""
    index = load_master_index()
    return index.get("branches", {}).get(path)


def find_branch_by_alias(word: str) -> Optional[str]:
    """
    Find a branch by alias match.

    Args:
        word: a single word to check against all branch aliases

    Returns:
        Branch path if found, None otherwise
    """
    word_lower = word.lower()

    if not os.path.exists(BASE_DIR):
        return None

    def _search(dir_path, prefix=""):
        for name in sorted(os.listdir(dir_path)):
            full = os.path.join(dir_path, name)
            if not os.path.isdir(full) or name.startswith(".") or name == "entries":
                continue

            branch_path = f"{prefix}/{name}" if prefix else name
            branch_index = load_branch_index(branch_path)

            for alias in branch_index.get("aliases", []):
                if alias.lower() == word_lower:
                    return branch_path

            # Check sub-branches
            result = _search(full, branch_path)
            if result:
                return result

        return None

    return _search(BASE_DIR)


def find_branches_by_query(query: str) -> List[str]:
    """
    Find branches whose aliases match any word in the query.

    Args:
        query: natural language query text

    Returns:
        List of matching branch paths
    """
    words = query.lower().split()
    matches = []

    for word in words:
        match = find_branch_by_alias(word)
        if match and match not in matches:
            matches.append(match)

    return matches


def update_branch_summary(path: str, summary: str) -> None:
    """Update a branch's summary text."""
    index = load_branch_index(path)
    index["summary"] = summary
    save_branch_index(path, index)
    _update_master_index_entry(path, index)


# --- HELPERS ---

def _now() -> str:
    """Current timestamp in ISO format."""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _update_master_index_entry(path: str, branch_index: dict) -> None:
    """Update a single branch entry in the Master Index."""
    master = load_master_index()
    entries_dir = get_entries_dir(path)
    entry_count = 0
    if os.path.exists(entries_dir):
        entry_count = len([
            f for f in os.listdir(entries_dir) if f.endswith(".json")
        ])

    branch_dir = get_branch_dir(path)
    sub_branches = []
    if os.path.exists(branch_dir):
        sub_branches = [
            d for d in os.listdir(branch_dir)
            if os.path.isdir(os.path.join(branch_dir, d))
            and d != "entries" and not d.startswith(".")
        ]

    master.setdefault("branches", {})[path] = {
        "summary": branch_index.get("summary", ""),
        "entry_count": entry_count,
        "security": branch_index.get("security", "open"),
        "last_updated": branch_index.get("last_updated", ""),
        "sub_branches": sub_branches,
    }

    # Recount total
    master["total_entries"] = sum(
        b["entry_count"] for b in master["branches"].values()
    )

    save_master_index(master)
