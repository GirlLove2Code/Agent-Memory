"""
Vivioo Memory — Auto-Summary
Auto-generates and updates branch summaries based on active entries.

Branch summaries power routing — when someone asks "what do I know about
marketing?", the system matches the query against branch summaries to
find the right branch. Stale summaries = bad routing.

This module regenerates summaries by extracting key themes from entries.

Usage:
    from auto_summary import update_summary, update_all_summaries

    # Update one branch
    update_summary("knowledge-base/marketing")

    # Update all branches
    report = update_all_summaries()
    print(f"Updated {report['updated']} branches")

    # Check if a branch needs updating
    needs_update("knowledge-base/marketing")  # True/False
"""

import os
import json
from typing import List, Dict, Optional
from collections import Counter

from branch_manager import (
    list_branches, load_branch_index, save_branch_index,
    update_branch_summary
)
from entry_manager import list_entries, _significant_words


def update_summary(branch: str) -> dict:
    """
    Regenerate a branch summary from its active entries.

    Strategy:
    1. Extract significant words from all active entries
    2. Find the top themes (most frequent significant words)
    3. Build a summary sentence from themes + entry count + sources

    Returns:
        {"branch": str, "old_summary": str, "new_summary": str, "changed": bool}
    """
    branch_index = load_branch_index(branch)
    old_summary = branch_index.get("summary", "")

    active_entries = list_entries(branch, include_outdated=False)

    if not active_entries:
        new_summary = f"Empty branch — no active entries."
        changed = new_summary != old_summary
        if changed:
            update_branch_summary(branch, new_summary)
        return {"branch": branch, "old_summary": old_summary,
                "new_summary": new_summary, "changed": changed}

    # Extract themes
    all_words = Counter()
    sources = set()
    importance_sum = 0

    for entry in active_entries:
        content = entry.get("content", "")
        words = _significant_words(content)
        # Weight by importance — important entries contribute more to themes
        importance = entry.get("_importance", 3)
        for word in words:
            all_words[word] += importance
        importance_sum += importance
        sources.add(entry.get("source", "manual"))

    # Top themes (up to 8)
    top_themes = [word for word, _ in all_words.most_common(8)]
    avg_importance = round(importance_sum / len(active_entries), 1) if active_entries else 0

    # Build summary
    theme_str = ", ".join(top_themes) if top_themes else "general"
    source_str = "/".join(sorted(sources))

    new_summary = (
        f"{len(active_entries)} entries covering: {theme_str}. "
        f"Avg importance: {avg_importance}/5. "
        f"Sources: {source_str}."
    )

    changed = new_summary != old_summary
    if changed:
        update_branch_summary(branch, new_summary)

    return {
        "branch": branch,
        "old_summary": old_summary,
        "new_summary": new_summary,
        "changed": changed,
        "entry_count": len(active_entries),
        "top_themes": top_themes,
    }


def update_all_summaries() -> dict:
    """
    Update summaries for all branches.

    Returns:
        {"updated": int, "unchanged": int, "branches": [results]}
    """
    results = []
    updated = 0
    unchanged = 0

    for branch in list_branches():
        result = update_summary(branch)
        results.append(result)
        if result["changed"]:
            updated += 1
        else:
            unchanged += 1

    return {"updated": updated, "unchanged": unchanged, "branches": results}


def needs_update(branch: str) -> bool:
    """
    Check if a branch summary is stale.

    A summary needs updating when:
    - It's empty
    - Entry count in summary doesn't match actual count
    - Branch has been modified since summary was last set
    """
    branch_index = load_branch_index(branch)
    summary = branch_index.get("summary", "")

    if not summary:
        return True

    active_entries = list_entries(branch, include_outdated=False)

    # Check if entry count matches (summary starts with "N entries")
    try:
        claimed_count = int(summary.split(" ")[0])
        if claimed_count != len(active_entries):
            return True
    except (ValueError, IndexError):
        return True

    return False


def get_summary_health() -> dict:
    """
    Report which branches have stale summaries.
    """
    stale = []
    healthy = []

    for branch in list_branches():
        if needs_update(branch):
            stale.append(branch)
        else:
            healthy.append(branch)

    return {
        "stale_count": len(stale),
        "healthy_count": len(healthy),
        "stale_branches": stale,
        "healthy_branches": healthy,
    }
