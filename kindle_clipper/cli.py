"""CLI entry point: scans the Obsidian clippings folder, converts new notes
to EPUB via Pandoc, and emails them to your Kindle.

Usage:
    python -m kindle_clipper.cli --config config.yaml
    python -m kindle_clipper.cli --config config.yaml --dry-run
"""
import argparse
import logging
from pathlib import Path

import yaml

from . import state
from .pipeline import process_file

log = logging.getLogger(__name__)


def _watched_dirs(cfg: dict) -> list[Path]:
    vault_path = Path(cfg["vault_path"]).expanduser()
    dirs = [vault_path / cfg.get("clippings_subdir", "Clippings")]
    if arxiv := cfg.get("arxiv_clippings_dir"):
        dirs.append(vault_path / arxiv)
    return dirs


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    parser = argparse.ArgumentParser(description="Convert Obsidian clippings to Kindle EPUBs")
    parser.add_argument("--config", type=Path, default=Path("config.yaml"))
    parser.add_argument("--dry-run", action="store_true", help="Convert but don't email")
    args = parser.parse_args()

    cfg = yaml.safe_load(args.config.read_text())
    state_path = Path(cfg.get("state_file", "state.json")).expanduser()
    st = state.State(state_path)

    new_count = 0
    for watch_dir in _watched_dirs(cfg):
        for md_path in sorted(watch_dir.glob("*.md")):
            if st.is_processed(md_path):
                continue
            new_count += 1
            process_file(md_path, cfg, st, args.dry_run)

    if new_count == 0:
        log.info("Nothing new to process.")


if __name__ == "__main__":
    main()
