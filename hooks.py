"""
Vivioo Memory — Event Hooks
Fire callbacks when memory events happen.

This is the bridge between the memory system and external tools
(PM tracker, agents, notifications, etc.)

Supported events:
  - memory_added     — new entry created
  - memory_outdated  — entry marked stale
  - memory_expired   — entry past its expiry date
  - memory_pinned    — entry pinned (importance = 5)
  - memory_conflict  — new entry auto-resolved a conflict
  - memory_refreshed — entry confirmed still valid
  - memory_archived  — entry moved to archive

Usage:
    from hooks import register_hook, fire_hooks

    # Register a callback
    def on_new_memory(event):
        print(f"New memory in {event['branch']}: {event['content'][:50]}")

    register_hook("memory_added", on_new_memory)

    # Hooks fire automatically when add_memory(), mark_outdated(), etc. are called.
    # You can also fire manually:
    fire_hooks("memory_added", {"entry_id": "...", "branch": "...", "content": "..."})

    # File-based hooks for external tools:
    register_file_hook("memory_added", "/path/to/hook_log.jsonl")
    # Every event appends a JSON line to that file — agents can watch it.
"""

import os
import json
from typing import Callable, Dict, List, Optional
from datetime import datetime, timezone

# In-memory hook registry: {event_name: [callback_fn, ...]}
_hooks: Dict[str, List[Callable]] = {}

# File-based hooks: {event_name: [file_path, ...]}
_file_hooks: Dict[str, List[str]] = {}

# Hook log for debugging: last N events
_event_log: List[dict] = []
_MAX_LOG = 100

# Persistent hooks config
HOOKS_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "hooks_config.json")


def register_hook(event: str, callback: Callable) -> None:
    """
    Register an in-memory callback for an event.

    Args:
        event: event name (e.g. "memory_added")
        callback: function that takes a single dict argument (the event data)
    """
    if event not in _hooks:
        _hooks[event] = []
    _hooks[event].append(callback)


def unregister_hook(event: str, callback: Callable) -> bool:
    """Remove a specific callback. Returns True if found and removed."""
    if event in _hooks and callback in _hooks[event]:
        _hooks[event].remove(callback)
        return True
    return False


def register_file_hook(event: str, file_path: str) -> None:
    """
    Register a file-based hook — every event appends a JSON line to this file.
    External tools (PM tracker, agents) can tail/watch this file.

    Args:
        event: event name
        file_path: path to the JSONL file (created if doesn't exist)
    """
    if event not in _file_hooks:
        _file_hooks[event] = []
    if file_path not in _file_hooks[event]:
        _file_hooks[event].append(file_path)
    _save_hooks_config()


def unregister_file_hook(event: str, file_path: str) -> bool:
    """Remove a file hook. Returns True if found and removed."""
    if event in _file_hooks and file_path in _file_hooks[event]:
        _file_hooks[event].remove(file_path)
        _save_hooks_config()
        return True
    return False


def fire_hooks(event: str, data: dict) -> dict:
    """
    Fire all hooks registered for an event.

    Args:
        event: event name
        data: event payload (entry_id, branch, content, etc.)

    Returns:
        {"fired": int, "errors": int, "event": str}
    """
    now = datetime.now(timezone.utc).isoformat()
    event_data = {
        "event": event,
        "timestamp": now,
        **data,
    }

    fired = 0
    errors = 0

    # In-memory callbacks
    for callback in _hooks.get(event, []):
        try:
            callback(event_data)
            fired += 1
        except Exception:
            errors += 1

    # Wildcard callbacks (listen to everything)
    for callback in _hooks.get("*", []):
        try:
            callback(event_data)
            fired += 1
        except Exception:
            errors += 1

    # File-based hooks
    for file_path in _file_hooks.get(event, []):
        try:
            _append_to_file(file_path, event_data)
            fired += 1
        except Exception:
            errors += 1

    # Wildcard file hooks
    for file_path in _file_hooks.get("*", []):
        try:
            _append_to_file(file_path, event_data)
            fired += 1
        except Exception:
            errors += 1

    # Log
    _event_log.append(event_data)
    if len(_event_log) > _MAX_LOG:
        _event_log.pop(0)

    return {"fired": fired, "errors": errors, "event": event}


def get_event_log(event: str = None, limit: int = 20) -> List[dict]:
    """
    Get recent events from the in-memory log.

    Args:
        event: filter to specific event type (None = all)
        limit: max events to return
    """
    log = _event_log
    if event:
        log = [e for e in log if e["event"] == event]
    return log[-limit:]


def list_hooks() -> dict:
    """List all registered hooks (memory + file)."""
    return {
        "memory_hooks": {
            event: len(callbacks) for event, callbacks in _hooks.items()
        },
        "file_hooks": dict(_file_hooks),
    }


def _append_to_file(file_path: str, data: dict) -> None:
    """Append a JSON line to a file."""
    os.makedirs(os.path.dirname(file_path) or ".", exist_ok=True)
    with open(file_path, "a") as f:
        f.write(json.dumps(data) + "\n")


def _save_hooks_config() -> None:
    """Persist file hooks to disk so they survive restarts."""
    config = {"file_hooks": _file_hooks}
    with open(HOOKS_CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)


def _load_hooks_config() -> None:
    """Load persisted file hooks from disk."""
    global _file_hooks
    if os.path.exists(HOOKS_CONFIG_PATH):
        try:
            with open(HOOKS_CONFIG_PATH, "r") as f:
                config = json.load(f)
                _file_hooks = config.get("file_hooks", {})
        except (json.JSONDecodeError, IOError):
            pass


# Load persisted hooks on import
_load_hooks_config()
