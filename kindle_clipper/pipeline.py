"""Core processing pipeline for a single clipping: preprocess → convert → deliver."""
import logging
import tempfile
from pathlib import Path

from . import convert, deliver, preprocess, state

log = logging.getLogger(__name__)


def process_file(md_path: Path, cfg: dict, st: state.State, dry_run: bool) -> bool:
    """Preprocess, convert, and optionally deliver one markdown clipping.

    Returns True if the file was processed (or was already done), False on error.
    """
    if st.is_processed(md_path):
        return True

    log.info("Processing: %s", md_path.name)
    vault_path = Path(cfg["vault_path"]).expanduser()
    attachment_dirs = cfg.get("attachment_dirs", ["attachments"])
    output_dir = Path(cfg["output_dir"]).expanduser()
    css_path = Path(cfg["css_path"]).expanduser()

    with tempfile.TemporaryDirectory() as tmpdir:
        work_dir = Path(tmpdir)
        try:
            processed_md, metadata = preprocess.prepare_source(
                md_path, vault_path, attachment_dirs, work_dir
            )
            epub_path = convert.convert_to_epub(processed_md, output_dir, css_path, metadata)
        except Exception as e:
            log.error("Conversion failed for %s: %s", md_path.name, e)
            return False

        if not dry_run:
            try:
                deliver.send_to_kindle(
                    epub_path,
                    cfg["kindle_email"],
                    cfg["gmail_address"],
                    cfg["gmail_app_password"],
                )
                log.info("  -> Sent to Kindle")
            except Exception as e:
                log.error("Email failed for %s: %s", md_path.name, e)
                return False

        st.mark_processed(md_path)
        return True
