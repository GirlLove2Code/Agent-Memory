"""
Vivioo Memory — Garbage Collection
Finds stale, duplicate, and low-value entries for cleanup.

Run manually or on a schedule:
    python garbage_collect.py                  # dry run (report only)
    python garbage_collect.py --apply          # actually archive stale entries
    python garbage_collect.py --days 60        # entries older than 60 days (default 90)
"""

import os
import sys
import json
import argparse
import shutil
from typing import List, Dict
from datetime import datetime, timezone, timedelta

# Add parent dir to path
sys.path.insert(0, os.path.dirname(__file__))

from branch_manager import list_branches, get_entries_dir, get_branch_dir
from entry_manager import (
    list_entries, get_entry, mark_outdated, get_enriched_text,
    _significant_words
)


ARCHIVE_DIR = os.path.join(os.path.dirname(__file__), "archive")


def find_stale_entries(max_age_days: int = 90) -> List[dict]:
    """
    Find entries older than max_age_days that are NOT already outdated.
    These are candidates for review — they might still be valid,
    but haven't been touched in a while.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    cutoff_str = cutoff.isoformat()
    stale = []

    for branch in list_branches():
        for entry in list_entries(branch, include_outdated=False):
            stored = entry.get("stored_at", "")
            if stored and stored < cutoff_str:
                entry["_stale_reason"] = f"Not updated in {max_age_days}+ days"
                stale.append(entry)

    return stale


def find_duplicates(threshold: float = 0.6) -> List[Dict]:
    """
    Find entries within the same branch that have high keyword overlap.
    Uses keyword overlap (not embeddings) so it works without Ollama.

    Returns pairs: [{"entry_a": {...}, "entry_b": {...}, "overlap": 0.75}]
    """
    pairs = []

    for branch in list_branches():
        entries = list_entries(branch, include_outdated=False)
        if len(entries) < 2:
            continue

        # Compare every pair within the branch
        for i, a in enumerate(entries):
            words_a = _significant_words(a.get("content", ""))
            if not words_a:
                continue
            for b in entries[i + 1:]:
                words_b = _significant_words(b.get("content", ""))
                if not words_b:
                    continue
                overlap = len(words_a & words_b) / max(len(words_a), len(words_b))
                if overlap >= threshold:
                    pairs.append({
                        "entry_a": {"id": a["id"], "branch": a["branch"],
                                    "content": a["content"][:100]},
                        "entry_b": {"id": b["id"], "branch": b["branch"],
                                    "content": b["content"][:100]},
                        "overlap": round(overlap, 3),
                    })

    pairs.sort(key=lambda p: p["overlap"], reverse=True)
    return pairs


def find_already_outdated() -> List[dict]:
    """Find all entries marked outdated — candidates for archival."""
    outdated = []
    for branch in list_branches():
        for entry in list_entries(branch, include_outdated=True):
            if entry.get("_outdated"):
                outdated.append(entry)
    return outdated


def archive_entry(entry: dict) -> bool:
    """
    Move an entry to the archive directory.
    Archive preserves the entry but removes it from active search.
    """
    branch = entry.get("branch", "unknown")
    entry_id = entry.get("id")
    if not entry_id:
        return False

    # Create archive path mirroring branch structure
    archive_branch = os.path.join(ARCHIVE_DIR, branch.replace("/", os.sep))
    os.makedirs(archive_branch, exist_ok=True)

    # Copy to archive
    archive_path = os.path.join(archive_branch, f"{entry_id}.json")
    entry["_archived_at"] = datetime.now(timezone.utc).isoformat()
    with open(archive_path, "w") as f:
        json.dump(entry, f, indent=2)

    # Remove from active entries
    active_path = os.path.join(get_entries_dir(branch), f"{entry_id}.json")
    if os.path.exists(active_path):
        os.remove(active_path)
        try:
            from hooks import fire_hooks
            fire_hooks("memory_archived", {
                "entry_id": entry_id, "branch": branch,
                "content": entry.get("content", "")[:150],
            })
        except Exception:
            pass
        return True

    return False


def generate_report(max_age_days: int = 90) -> dict:
    """Generate a full garbage collection report."""
    stale = find_stale_entries(max_age_days)
    dupes = find_duplicates()
    outdated = find_already_outdated()

    # Count totals
    total_active = 0
    for branch in list_branches():
        total_active += len(list_entries(branch, include_outdated=False))

    total_all = 0
    for branch in list_branches():
        total_all += len(list_entries(branch, include_outdated=True))

    return {
        "total_entries": total_all,
        "active_entries": total_active,
        "outdated_entries": len(outdated),
        "stale_entries": len(stale),
        "duplicate_pairs": len(dupes),
        "stale": stale,
        "duplicates": dupes,
        "outdated": outdated,
        "recommendation": _recommend(stale, dupes, outdated, total_active),
    }


def _recommend(stale, dupes, outdated, total_active) -> str:
    """Generate a plain-English recommendation."""
    parts = []

    if outdated:
        parts.append(
            f"{len(outdated)} outdated entries can be archived "
            f"(they're already marked stale, just taking up space)."
        )

    if dupes:
        parts.append(
            f"{len(dupes)} duplicate pairs found — "
            f"the older entry in each pair should be marked outdated."
        )

    if stale:
        parts.append(
            f"{len(stale)} entries haven't been updated in 90+ days — "
            f"review them to see if they're still accurate."
        )

    if not parts:
        parts.append("Memory is clean. No action needed.")

    return " ".join(parts)


def main():
    parser = argparse.ArgumentParser(description="Vivioo Memory Garbage Collection")
    parser.add_argument("--days", type=int, default=90,
                        help="Max age in days before flagging as stale (default: 90)")
    parser.add_argument("--apply", action="store_true",
                        help="Actually archive outdated entries (default: dry run)")
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON instead of human-readable")
    args = parser.parse_args()

    report = generate_report(args.days)

    if args.json:
        # Clean up for JSON output (remove full entry data)
        summary = {
            "total_entries": report["total_entries"],
            "active_entries": report["active_entries"],
            "outdated_entries": report["outdated_entries"],
            "stale_entries": report["stale_entries"],
            "duplicate_pairs": report["duplicate_pairs"],
            "recommendation": report["recommendation"],
        }
        print(json.dumps(summary, indent=2))
        return

    print("\n=== Vivioo Memory — Garbage Collection Report ===\n")
    print(f"  Total entries:    {report['total_entries']}")
    print(f"  Active entries:   {report['active_entries']}")
    print(f"  Outdated entries: {report['outdated_entries']}")
    print(f"  Stale (>{args.days}d):   {report['stale_entries']}")
    print(f"  Duplicate pairs:  {report['duplicate_pairs']}")
    print()

    if report["duplicates"]:
        print("--- Duplicates ---")
        for pair in report["duplicates"][:10]:  # Show top 10
            print(f"  [{pair['overlap']:.0%} overlap]")
            print(f"    A: {pair['entry_a']['content']}...")
            print(f"    B: {pair['entry_b']['content']}...")
            print()

    if report["stale"]:
        print(f"--- Stale Entries ({len(report['stale'])}) ---")
        for entry in report["stale"][:10]:
            print(f"  [{entry['branch']}] {entry['content'][:80]}...")
        print()

    print(f"Recommendation: {report['recommendation']}")

    if args.apply and report["outdated"]:
        print(f"\n--- Archiving {len(report['outdated'])} outdated entries ---")
        archived = 0
        for entry in report["outdated"]:
            if archive_entry(entry):
                archived += 1
                print(f"  Archived: {entry['id']} ({entry['branch']})")
        print(f"\n  Done. {archived} entries moved to archive/")
    elif report["outdated"] and not args.apply:
        print(f"\n  Run with --apply to archive {len(report['outdated'])} outdated entries.")

    print()


if __name__ == "__main__":
    main()
