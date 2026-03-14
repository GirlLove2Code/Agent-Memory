"""
Vivioo Memory — Expiry & Refresh System
Actively fights staleness by flagging memories that need verification.

Some info decays fast:
  - Pricing, API versions, model names → expires in 30 days
  - Project status, task lists → expires in 14 days
  - Architecture decisions, rules → expires in 90 days
  - Pinned memories → never expire

Usage:
    from expiry import set_expiry, check_expiring, refresh_entry, get_refresh_queue

    # Set expiry on a memory
    set_expiry(entry_id, branch, days=30)

    # Auto-detect expiry from content
    set_auto_expiry(entry_id, branch)

    # Get all entries needing refresh
    queue = get_refresh_queue()
    for item in queue["needs_refresh"]:
        print(f"Still true? {item['content']}")

    # Confirm an entry is still valid
    refresh_entry(entry_id, branch)    # resets the clock
"""

import os
import re
import json
from typing import List, Dict, Optional
from datetime import datetime, timezone, timedelta

from branch_manager import list_branches
from entry_manager import get_entry, list_entries, get_entries_dir


# Content patterns → expiry days
# More volatile info gets shorter expiry
_EXPIRY_RULES = [
    # Pricing, costs, billing — changes frequently
    (r'\b(pricing|cost|price|\$\d|per month|per token|subscription)\b', 30),
    # API versions, model names — updated often
    (r'\b(api|v\d|model|version|sdk|endpoint|gpt-|claude-|gemini)\b', 45),
    # Status, progress, task lists — very volatile
    (r'\b(status|progress|todo|task|blocker|blocked|pending|waiting)\b', 14),
    # Deploy, infra, env — moderately volatile
    (r'\b(deploy|server|env|config|url|domain|vercel|hosting)\b', 45),
    # Architecture, design decisions — slow to change
    (r'\b(architecture|design|pattern|approach|strategy|principle)\b', 90),
    # Rules, requirements, compliance — slow to change
    (r'\b(rule|requirement|compliance|policy|never|always|must)\b', 90),
]

# Default expiry if no pattern matches
_DEFAULT_EXPIRY_DAYS = 60


def set_expiry(entry_id: str, branch: str, days: int = None) -> Optional[dict]:
    """
    Set an expiry date on a memory entry.

    Args:
        entry_id: the entry's unique ID
        branch: the branch path
        days: number of days from now until expiry.
              If None, auto-detects from content.

    Returns:
        Updated entry dict, or None if not found.
    """
    entry = get_entry(entry_id, branch)
    if entry is None:
        return None

    # Pinned memories don't expire
    if entry.get("_importance_source") == "pinned":
        entry["_expires_at"] = None
        entry["_expiry_days"] = None
        entry["_expiry_rule"] = "pinned — never expires"
    else:
        if days is None:
            days = _detect_expiry_days(entry.get("content", ""))

        # Calculate from stored_at (not now) — so expiry is relative to when info was captured
        stored = entry.get("stored_at", datetime.now(timezone.utc).isoformat())
        try:
            stored_dt = datetime.fromisoformat(stored.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            stored_dt = datetime.now(timezone.utc)

        expires_dt = stored_dt + timedelta(days=days)
        entry["_expires_at"] = expires_dt.isoformat()
        entry["_expiry_days"] = days

    entry_path = os.path.join(get_entries_dir(branch), f"{entry_id}.json")
    with open(entry_path, "w") as f:
        json.dump(entry, f, indent=2)

    _fire_event("memory_expired", {
        "entry_id": entry_id, "branch": branch,
        "expires_at": entry["_expires_at"],
        "content": entry.get("content", "")[:150],
    })

    return entry


def set_auto_expiry(entry_id: str, branch: str) -> Optional[dict]:
    """Auto-detect expiry from content patterns and set it."""
    return set_expiry(entry_id, branch, days=None)


def refresh_entry(entry_id: str, branch: str, new_expiry_days: int = None) -> Optional[dict]:
    """
    Confirm a memory is still valid — resets the expiry clock.

    Args:
        entry_id: the entry's unique ID
        branch: the branch path
        new_expiry_days: set a new expiry period (or keep the same)

    Returns:
        Updated entry dict with refreshed expiry.
    """
    entry = get_entry(entry_id, branch)
    if entry is None:
        return None

    now = datetime.now(timezone.utc)

    # Record the refresh
    entry["_last_refreshed"] = now.isoformat()
    entry.setdefault("_refresh_count", 0)
    entry["_refresh_count"] += 1

    # Reset expiry from NOW (not original stored_at)
    days = new_expiry_days or entry.get("_expiry_days", _DEFAULT_EXPIRY_DAYS)
    entry["_expires_at"] = (now + timedelta(days=days)).isoformat()
    entry["_expiry_days"] = days

    entry_path = os.path.join(get_entries_dir(branch), f"{entry_id}.json")
    with open(entry_path, "w") as f:
        json.dump(entry, f, indent=2)

    _fire_event("memory_refreshed", {
        "entry_id": entry_id, "branch": branch,
        "refresh_count": entry["_refresh_count"],
        "content": entry.get("content", "")[:150],
    })

    return entry


def get_refresh_queue(branch: str = None, include_no_expiry: bool = False) -> dict:
    """
    Get all entries that need a "still true?" check.

    Returns:
        {
            "needs_refresh": [entries past their expiry],
            "expiring_soon": [entries expiring within 7 days],
            "healthy": int — count of entries not expiring,
            "no_expiry_set": int — entries without any expiry,
        }
    """
    now = datetime.now(timezone.utc).isoformat()
    soon = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()

    branches = [branch] if branch else list_branches()

    needs_refresh = []
    expiring_soon = []
    healthy = 0
    no_expiry = 0

    for b in branches:
        for entry in list_entries(b, include_outdated=False):
            expires_at = entry.get("_expires_at")

            if not expires_at:
                no_expiry += 1
                if include_no_expiry:
                    # Estimate based on content
                    est_days = _detect_expiry_days(entry.get("content", ""))
                    stored = entry.get("stored_at", "")
                    if stored:
                        try:
                            stored_dt = datetime.fromisoformat(stored.replace("Z", "+00:00"))
                            est_expires = (stored_dt + timedelta(days=est_days)).isoformat()
                            if est_expires < now:
                                needs_refresh.append(_entry_summary(entry, b, est_days, estimated=True))
                                continue
                        except (ValueError, TypeError):
                            pass
                continue

            if expires_at < now:
                days_past = _days_between(expires_at, now)
                needs_refresh.append(_entry_summary(entry, b, days_past_expiry=days_past))
            elif expires_at < soon:
                expiring_soon.append(_entry_summary(entry, b))
            else:
                healthy += 1

    # Sort by importance (high importance expired = most urgent)
    needs_refresh.sort(key=lambda e: e["importance"], reverse=True)
    expiring_soon.sort(key=lambda e: e["importance"], reverse=True)

    return {
        "needs_refresh": needs_refresh,
        "expiring_soon": expiring_soon,
        "healthy": healthy,
        "no_expiry_set": no_expiry,
    }


def backfill_expiry(branch: str = None) -> dict:
    """
    Set auto-expiry on all entries that don't have one yet.
    Safe to run multiple times — skips entries that already have expiry.

    Returns:
        {"updated": int, "skipped": int}
    """
    branches = [branch] if branch else list_branches()
    updated = 0
    skipped = 0

    for b in branches:
        for entry in list_entries(b, include_outdated=False):
            if entry.get("_expires_at") is not None:
                skipped += 1
                continue

            result = set_auto_expiry(entry["id"], b)
            if result:
                updated += 1
            else:
                skipped += 1

    return {"updated": updated, "skipped": skipped}


def _detect_expiry_days(content: str) -> int:
    """Auto-detect expiry period from content patterns."""
    content_lower = content.lower()

    # Check each rule — use the shortest matching expiry
    matching_days = []
    for pattern, days in _EXPIRY_RULES:
        if re.search(pattern, content_lower):
            matching_days.append(days)

    if matching_days:
        return min(matching_days)  # Most volatile match wins

    return _DEFAULT_EXPIRY_DAYS


def _entry_summary(entry: dict, branch: str, est_days: int = None,
                   days_past_expiry: int = None, estimated: bool = False) -> dict:
    """Create a summary dict for refresh queue display."""
    result = {
        "entry_id": entry["id"],
        "branch": branch,
        "content": entry.get("content", "")[:150],
        "importance": entry.get("_importance", 3),
        "stored_at": entry.get("stored_at", ""),
        "expires_at": entry.get("_expires_at", ""),
        "refresh_count": entry.get("_refresh_count", 0),
        "last_refreshed": entry.get("_last_refreshed"),
    }

    if days_past_expiry is not None:
        result["days_past_expiry"] = days_past_expiry

    if estimated:
        result["expiry_estimated"] = True
        result["estimated_days"] = est_days

    return result


def _days_between(iso_a: str, iso_b: str) -> int:
    """Days between two ISO timestamps."""
    try:
        a = datetime.fromisoformat(iso_a.replace("Z", "+00:00"))
        b = datetime.fromisoformat(iso_b.replace("Z", "+00:00"))
        return abs((b - a).days)
    except (ValueError, TypeError):
        return 0


def _fire_event(event: str, data: dict) -> None:
    """Fire hooks if available. Best-effort."""
    try:
        from hooks import fire_hooks
        fire_hooks(event, data)
    except Exception:
        pass
