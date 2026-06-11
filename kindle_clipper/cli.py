"""CLI entry point: scans the Obsidian clippings folder, converts new notes
to EPUB via Pandoc, and emails them to your Kindle.

Usage:
    python -m kindle_clipper.cli --config config.yaml
    python -m kindle_clipper.cli --config config.yaml --dry-run
"""
import argparse
import tempfile
from pathlib import Path

import yaml

from . import convert, deliver, preprocess, state


def load_config(config_path: Path) -> dict:
    return yaml.safe_load(config_path.read_text())


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert Obsidian clippings to Kindle EPUBs")
    parser.add_argument("--config", type=Path, default=Path("config.yaml"))
    parser.add_argument("--dry-run", action="store_true", help="Convert but don't email")
    args = parser.parse_args()

    cfg = load_config(args.config)

    vault_path = Path(cfg["vault_path"]).expanduser()
    clippings_dir = vault_path / cfg.get("clippings_subdir", "Clippings")
    attachment_dirs = cfg.get("attachment_dirs", ["attachments"])
    output_dir = Path(cfg["output_dir"]).expanduser()
    css_path = Path(cfg["css_path"]).expanduser()
    state_path = Path(cfg.get("state_file", "state.json")).expanduser()

    st = state.State(state_path)

    md_files = sorted(clippings_dir.glob("*.md"))
    if not md_files:
        print(f"No markdown files found in {clippings_dir}")
        return
    
    new_count = 0
    for md_path in md_files:
        if st.is_processed(md_path):
            continue
        
        new_count += 1
        print(f"Processing: {md_path.name}")
        with tempfile.TemporaryDirectory() as tmpdir:
            work_dir = Path(tmpdir)

            processed_md, metadata = preprocess.prepare_source(
                md_path,
                vault_path,
                attachment_dirs,
                work_dir
            )
            epub_path = convert.convert_to_epub(processed_md, output_dir, css_path, metadata)
            if not args.dry_run:
                try:
                    deliver.send_to_kindle(
                        epub_path,
                        cfg["kindle_email"],
                        cfg["gmail_address"],
                        cfg["gmail_app_password"],
                    )
                    print("  -> Sent to Kindle")
                except Exception as e:
                    print(f"  ! Email failed: {e}")
                    continue

            st.mark_processed(md_path)

    if new_count == 0:
        print("Nothing new to process.")


if __name__ == "__main__":
    main()
