"""
Vivioo Memory — Timeline
"What changed?" view across all knowledge.

Not git log — this tracks knowledge changes:
  - New memories added
  - Memories marked outdated (and why)
  - Memories superseded (old → new chain)
  - Importance changes

Usage:
    from timeline import get_timeline
    events = get_timeline()                              # last 7 days
    events = get_timeline(days=30)                       # last 30 days
    events = get_timeline(branch="vivioo")               # one branch
    events = get_timeline(event_type="decision")         # decisions only

    # Human-readable
    print(format_timeline(events))
"""

import os
import json
from typing import List, Dict, Optional
from datetime import datetime, timezone, timedelta

from branch_manager import list_branches
from entry_manager import list_entries


def get_timeline(days: int = 7, branch: str = None,
                 event_type: str = None) -> List[dict]:
    """
    Build a timeline of knowledge events.

    Args:
        days: how far back to look (default 7)
        branch: limit to one branch (None = all)
        event_type: filter to specific type:
            "added" — new memories
            "outdated" — marked stale
            "superseded" — replaced by newer info
            "decision" — entries with decision language
            None — all types

    Returns:
        List of events sorted newest first, each with:
        {
            "type": "added|outdated|superseded|decision",
            "timestamp": ISO string,
            "branch": branch path,
            "entry_id": entry ID,
            "content": first 150 chars,
            "importance": 1-5,
            "details": {} — type-specific info
        }
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    branches_to_check = [branch] if branch else list_branches()

    events = []

    for b in branches_to_check:
        all_entries = list_entries(b, include_outdated=True)

        for entry in all_entries:
            entry_events = _extract_events(entry, b, cutoff)
            events.extend(entry_events)

    # Filter by type
    if event_type:
        events = [e for e in events if e["type"] == event_type]

    # Sort newest first
    events.sort(key=lambda e: e["timestamp"], reverse=True)
    return events


def get_decision_log(days: int = 30, branch: str = None) -> List[dict]:
    """
    Get only decision events — the choices that shaped the project.
    Useful for "why did we do X?" questions.
    """
    return get_timeline(days=days, branch=branch, event_type="decision")


def get_weekly_digest(branch: str = None) -> dict:
    """
    One-week summary: how many added, outdated, superseded, decisions.
    """
    events = get_timeline(days=7, branch=branch)

    summary = {"added": 0, "outdated": 0, "superseded": 0, "decision": 0}
    for e in events:
        t = e["type"]
        if t in summary:
            summary[t] += 1

    branches_touched = set(e["branch"] for e in events)

    return {
        "period": "7 days",
        "total_events": len(events),
        "breakdown": summary,
        "branches_touched": list(branches_touched),
        "events": events,
    }


def _extract_events(entry: dict, branch: str, cutoff: str) -> List[dict]:
    """Extract timeline events from a single entry."""
    events = []
    content_preview = entry.get("content", "")[:150]
    importance = entry.get("_importance", 3)
    entry_id = entry.get("id", "unknown")

    # Event: Added
    stored_at = entry.get("stored_at", "")
    if stored_at > cutoff:
        event = {
            "type": "added",
            "timestamp": stored_at,
            "branch": branch,
            "entry_id": entry_id,
            "content": content_preview,
            "importance": importance,
            "details": {
                "source": entry.get("source", "manual"),
                "tags": entry.get("tags", []),
            },
        }

        # Check if this is a decision (has decision language)
        if _is_decision(entry.get("content", "")):
            # Add as both "added" and "decision"
            events.append(event)
            decision_event = dict(event)
            decision_event["type"] = "decision"
            events.append(decision_event)
        else:
            events.append(event)

    # Event: Marked outdated
    outdated_at = entry.get("_outdated_at", "")
    if outdated_at and outdated_at > cutoff and entry.get("_outdated"):
        events.append({
            "type": "outdated",
            "timestamp": outdated_at,
            "branch": branch,
            "entry_id": entry_id,
            "content": content_preview,
            "importance": importance,
            "details": {
                "reason": entry.get("_outdated_reason", ""),
                "superseded_by": entry.get("_superseded_by", []),
            },
        })

    # Event: Superseded something
    supersedes = entry.get("_supersedes", [])
    if supersedes and stored_at > cutoff:
        events.append({
            "type": "superseded",
            "timestamp": stored_at,
            "branch": branch,
            "entry_id": entry_id,
            "content": content_preview,
            "importance": importance,
            "details": {
                "replaced_ids": supersedes,
                "count": len(supersedes),
            },
        })

    return events


# Decision detection patterns (shared with entry_manager but kept local
# to avoid circular imports)
_DECISION_WORDS = {
    "switched", "changed", "replaced", "decided", "chose", "moved",
    "removed", "deployed", "shipped", "launched", "fixed", "blocked",
    "critical", "must", "never", "always", "requirement",
}


def _is_decision(content: str) -> bool:
    """Check if content contains decision language."""
    words = set(content.lower().split())
    return len(words & _DECISION_WORDS) >= 2


def format_timeline(events: List[dict], max_items: int = 20) -> str:
    """Format timeline events into readable text."""
    if not events:
        return "No events in this period."

    lines = []
    current_date = None

    for event in events[:max_items]:
        # Group by date
        date = event["timestamp"][:10]
        if date != current_date:
            current_date = date
            lines.append(f"\n--- {date} ---")

        time = event["timestamp"][11:16]
        icon = {
            "added": "+",
            "outdated": "x",
            "superseded": "~",
            "decision": "!",
        }.get(event["type"], "?")

        importance_bar = "*" * event.get("importance", 3)
        branch_short = event["branch"].split("/")[-1] if "/" in event["branch"] else event["branch"]

        line = f"  {time} [{icon}] [{branch_short}] [{importance_bar}] {event['content']}"

        # Add details for superseded
        if event["type"] == "superseded":
            count = event["details"].get("count", 0)
            line += f" (replaced {count} older)"

        # Add reason for outdated
        if event["type"] == "outdated":
            reason = event["details"].get("reason", "")
            if reason:
                line += f" — {reason}"

        lines.append(line)

    return "\n".join(lines)
