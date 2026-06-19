"""Folder-watcher: automatically converts new Obsidian clippings as they appear.

On startup, catches up on any files that arrived while the watcher was offline,
then watches for new/modified .md files and processes them after a short settle
delay (to avoid racing a partial write from Obsidian Web Clipper).

Usage:
    python -m kindle_clipper.watch --config config.yaml
    python -m kindle_clipper.watch --config config.yaml --dry-run
"""
import argparse
import logging
import threading
import time
from pathlib import Path

import yaml
from watchdog.events import FileCreatedEvent, FileModifiedEvent, FileSystemEventHandler
from watchdog.observers import Observer

from . import state
from .cli import _watched_dirs
from .pipeline import process_file

log = logging.getLogger(__name__)

# Time to wait after the last write event before processing.
# Obsidian Web Clipper typically fires created then modified in quick succession.
_SETTLE_SECONDS = 2.0


class _ClippingsHandler(FileSystemEventHandler):
    def __init__(self, cfg: dict, st: state.State, dry_run: bool) -> None:
        self._cfg = cfg
        self._st = st
        self._dry_run = dry_run
        self._pending: dict[str, threading.Timer] = {}

    def on_created(self, event: FileCreatedEvent) -> None:
        if not event.is_directory and str(event.src_path).endswith(".md"):
            self._schedule(Path(event.src_path))

    def on_modified(self, event: FileModifiedEvent) -> None:
        if not event.is_directory and str(event.src_path).endswith(".md"):
            self._schedule(Path(event.src_path))

    def _schedule(self, path: Path) -> None:
        key = str(path)
        existing = self._pending.pop(key, None)
        if existing:
            existing.cancel()
        timer = threading.Timer(_SETTLE_SECONDS, self._run, args=(path,))
        self._pending[key] = timer
        timer.start()

    def _run(self, path: Path) -> None:
        self._pending.pop(str(path), None)
        if path.exists():
            process_file(path, self._cfg, self._st, self._dry_run)


def watch(cfg: dict, dry_run: bool) -> None:
    state_path = Path(cfg.get("state_file", "state.json")).expanduser()
    st = state.State(state_path)

    dirs = _watched_dirs(cfg)

    # Catch up on anything that arrived while the watcher was offline.
    for watch_dir in dirs:
        for md_path in sorted(watch_dir.glob("*.md")):
            process_file(md_path, cfg, st, dry_run)

    handler = _ClippingsHandler(cfg, st, dry_run)
    observer = Observer()
    for watch_dir in dirs:
        observer.schedule(handler, str(watch_dir), recursive=False)
        log.info("Watching %s", watch_dir)

    observer.start()
    log.info("(Ctrl-C to stop)")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        observer.stop()
        observer.join()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s", datefmt="%H:%M:%S")

    parser = argparse.ArgumentParser(description="Watch clippings folder and send new notes to Kindle")
    parser.add_argument("--config", type=Path, default=Path("config.yaml"))
    parser.add_argument("--dry-run", action="store_true", help="Convert but don't email")
    args = parser.parse_args()

    cfg = yaml.safe_load(args.config.read_text())
    watch(cfg, args.dry_run)


if __name__ == "__main__":
    main()
