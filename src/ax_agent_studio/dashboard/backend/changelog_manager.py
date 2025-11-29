"""Simple changelog persistence for the dashboard."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple


@dataclass(slots=True)
class ChangelogEntry:
    """An immutable changelog entry."""

    id: int
    title: str
    description: str
    pr_number: int | None
    author: str | None
    created_at: str


class ChangelogManager:
    """Persist and retrieve changelog entries on disk."""

    def __init__(self, project_root: Path) -> None:
        self._file_path = project_root / "data" / "changelog.json"
        self._file_path.parent.mkdir(parents=True, exist_ok=True)

        self._state: Dict[str, Any] = {"next_id": 1, "entries": []}
        self._load()

    def _load(self) -> None:
        """Load changelog state from disk if it exists."""

        if not self._file_path.exists():
            return

        try:
            with self._file_path.open("r", encoding="utf-8") as f:
                self._state = json.load(f)
        except json.JSONDecodeError:
            # Preserve existing state but avoid crashing the dashboard if the file is corrupt
            self._state = {"next_id": 1, "entries": []}

    def _save(self) -> None:
        """Persist current changelog state to disk."""

        with self._file_path.open("w", encoding="utf-8") as f:
            json.dump(self._state, f, indent=2)

    def add_entry(
        self,
        title: str,
        description: str,
        pr_number: int | None = None,
        author: str | None = None,
    ) -> ChangelogEntry:
        """Create a new changelog entry and persist it."""

        entry = {
            "id": self._state["next_id"],
            "title": title,
            "description": description,
            "pr_number": pr_number,
            "author": author,
            "created_at": datetime.utcnow().isoformat(),
        }

        self._state["entries"].append(entry)
        self._state["next_id"] += 1
        self._save()

        return ChangelogEntry(**entry)

    def list_entries(self, limit: int = 10, offset: int = 0) -> Tuple[List[ChangelogEntry], int]:
        """Return a window of changelog entries ordered newest-first.

        Args:
            limit: Maximum number of entries to return.
            offset: How many entries to skip from the newest entry.

        Returns:
            A tuple of (entries, total_count)
        """

        entries: List[Dict[str, Any]] = self._state.get("entries", [])
        sorted_entries = sorted(entries, key=lambda e: e.get("id", 0), reverse=True)
        total = len(sorted_entries)

        window = sorted_entries[offset : offset + limit]
        return [ChangelogEntry(**entry) for entry in window], total
