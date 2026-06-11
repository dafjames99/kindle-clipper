"""Tracks which markdown files have already been processed/delivered.

Uses a content hash (not just the path) so editing a previously-clipped
note will cause it to be reprocessed and re-sent.
"""

import hashlib
import json
from pathlib import Path


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

class State:
    def __init__(self, state_path: Path):
        self.state_path = state_path
        self._data = self._load()

    def _load(self) -> dict:
        if self.state_path.exists():
            return json.loads(self.state_path.read_text())
        return {"processed": {}}

    def save(self) -> None:
        self.state_path.write_text(json.dumps(self._data, indent=2))

    def is_processed(self, md_path: Path) -> bool:
        key = str(md_path)
        return self._data["processed"].get(key) == _file_hash(md_path)

    def mark_processed(self, md_path: Path) -> None:
        self._data["processed"][str(md_path)] = _file_hash(md_path)
        self.save()
