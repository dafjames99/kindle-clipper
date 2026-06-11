"""Markdown -> EPUB conversion via Pandoc."""

import re
import subprocess
from pathlib import Path
from typing import Any, Dict


def slugify(text: str, max_length: int = 80) -> str:
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    text = re.sub(r"[-\s]+", "-", text)
    return text[:max_length].strip("-") or "untitled"


def convert_to_epub(
    md_path: Path,
    output_dir: Path,
    css_path: Path,
    metadata: Dict[str, Any]
) -> Path:
    """Run Pandoc to convert a prepared, self-contained markdown file to EPUB.

    md_path should already have any referenced images copied alongside it
    (see preprocess.prepare_source). Returns the path to the generated EPUB.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    title = metadata.get("title") or md_path.stem
    out_path = output_dir / f"{slugify(title)}.epub"
    
    author = metadata.get("author") or metadata.get("site_name") or "Web Clipper"
    cmd = [
        "pandoc",
        str(md_path),
        "-o", str(out_path),
        # "--css", str(css_path),
        "--metadata", f"title={title}",
        "--metadata", f"author={author}",
        "--toc",
    ]

    source_url = metadata.get("source") or metadata.get("url")
    if source_url:
        cmd += ["--metadata", f"description=Clipped from {source_url}"]

    result = subprocess.run(cmd, cwd=md_path.parent, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Pandoc failed for {md_path.name}:\n{result.stderr}")

    return out_path