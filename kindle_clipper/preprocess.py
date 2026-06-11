"""Preprocessing for Obsidian Web Clipper markdown files.

Handles:
- Parsing YAML frontmatter into metadata (title, author, source url, date)
- Converting Obsidian wikilink image syntax ![[image.png]] to standard
  markdown ![](image.png), with filenames sanitized (spaces -> underscores)
- Copying referenced Obsidian attachments into the working directory
- Downloading remote markdown images
- Downloading remote HTML images
- Extracting data:image URIs into image files
- Converting inline SVGs to PNG
- Converting downloaded SVGs to PNG
- Replacing video embeds with EPUB-safe placeholders
"""
import hashlib
import base64
import mimetypes
import re
import shutil
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import cairosvg
import frontmatter
import requests

WIKILINK_IMAGE_RE = re.compile(r"!\[\[([^\]|]+)(?:\|[^\]]*)?\]\]")
MARKDOWN_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
HTML_IMG_RE = re.compile(r"<img\b[^>]*src=[\"']([^\"']+)[\"'][^>]*>", re.IGNORECASE)
INLINE_SVG_RE = re.compile(r"<svg\b.*?</svg>", re.IGNORECASE | re.DOTALL)
VIDEO_RE = re.compile(r"<(video|iframe)\b[^>]*?(?:src=[\"']([^\"']*)[\"'])?[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
SPAN_RE = re.compile(r"<(?:mark|span)\b[^>]*>(.*?)</(?:mark|span)>", re.IGNORECASE | re.DOTALL)
# ---- NEW ------------------------------------------------------------

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/136.0.0.0 Safari/537.36"
    )
}

# ---- NEW ------------------------------------------------------------


def _sanitize_filename(name: str) -> str:
    return re.sub(r"\s+", "_", name.strip())


def parse_markdown(md_path: Path) -> Tuple[str, Dict[str, Any]]:
    post = frontmatter.load(md_path)
    return post.content, dict(post.metadata)


def convert_wikilink_images(md_text: str) -> Tuple[str, List[str]]:
    referenced: List[str] = []

    def _replace(match: re.Match) -> str:
        filename = match.group(1).strip()
        referenced.append(filename)
        return f"![]({_sanitize_filename(filename)})"

    return WIKILINK_IMAGE_RE.sub(_replace, md_text), referenced


def find_attachment(filename: str, vault_path: Path, attachment_dirs: List[str]) -> Optional[Path]:
    for d in attachment_dirs:
        candidate = vault_path / d / filename
        if candidate.exists():
            return candidate

    matches = list(vault_path.rglob(filename))
    return matches[0] if matches else None


# ---- NEW ------------------------------------------------------------

def _is_remote(url: str) -> bool:
    return url.startswith("http://") or url.startswith("https://")


def _guess_extension(content_type: str) -> str:
    ext = mimetypes.guess_extension(content_type.split(";")[0].strip())
    return ext or ".bin"


def _url_filename(url: str, content_type: str = "") -> str:
    ext = _guess_extension(content_type) if content_type else ".bin"
    digest = hashlib.sha256(url.encode()).hexdigest()[:16]
    return f"{digest}{ext}"


def _svg_to_png(svg_path: Path) -> Path:
    png_path = svg_path.with_suffix(".png")
    cairosvg.svg2png(url=str(svg_path), write_to=str(png_path))
    svg_path.unlink(missing_ok=True)
    return png_path


def _save_data_uri(data_uri: str, work_dir: Path) -> str:
    header, encoded = data_uri.split(",", 1)

    if "svg+xml" in header:
        ext = ".svg"
    elif "jpeg" in header:
        ext = ".jpg"
    elif "webp" in header:
        ext = ".webp"
    elif "gif" in header:
        ext = ".gif"
    else:
        ext = ".png"

    filename = f"embedded_{uuid.uuid4().hex}{ext}"
    path = work_dir / filename
    path.write_bytes(base64.b64decode(encoded))

    if ext == ".svg":
        path = _svg_to_png(path)
        filename = path.name

    return filename


def _download_asset(
    session: requests.Session,
    url: str,
    work_dir: Path,
    cache: Dict[str, str],
) -> str:
    if url in cache:
        return cache[url]

    response = session.get(url, timeout=30)
    response.raise_for_status()

    content_type = response.headers.get("Content-Type", "")
    
    filename = _url_filename(url, content_type)
    path = work_dir / filename
    path.write_bytes(response.content)

    if path.suffix.lower() == ".svg" or "image/svg+xml" in content_type:
        path = _svg_to_png(path)
        filename = path.name

    cache[url] = filename
    return filename


def process_media(md_text: str, work_dir: Path) -> str:
    url_cache: Dict[str, str] = {}
    remote_urls = set()
    
    for _, url in MARKDOWN_IMAGE_RE.findall(md_text):
        if _is_remote(url.strip()):
            remote_urls.add(url.strip())

    for src in HTML_IMG_RE.findall(md_text):
        if _is_remote(src):
            remote_urls.add(src)

    session = None
    if remote_urls:
        session = requests.Session()
        session.headers.update(DEFAULT_HEADERS)
    
    def replace_markdown_image(match: re.Match) -> str:
        alt_text = match.group(1)
        target = match.group(2).strip()

        if session and _is_remote(target):
            filename = _download_asset(session, target, work_dir, url_cache)
            return f"![{alt_text}]({filename})"

        return match.group(0)

    md_text = MARKDOWN_IMAGE_RE.sub(replace_markdown_image, md_text)

    def replace_html_image(match: re.Match) -> str:
        src = match.group(1)

        if src.startswith("data:image"):
            filename = _save_data_uri(src, work_dir)
            return f"![]({filename})"

        if session and _is_remote(src):
            filename = _download_asset(session, src, work_dir, url_cache)
            return f"![]({filename})"

        return f"![]({src})"

    md_text = HTML_IMG_RE.sub(replace_html_image, md_text)

    def replace_svg(match: re.Match) -> str:
        svg_text = match.group(0)
        svg_file = work_dir / f"inline_svg_{uuid.uuid4().hex}.svg"
        svg_file.write_text(svg_text, encoding="utf-8")
        png_file = _svg_to_png(svg_file)
        return f"![]({png_file.name})"

    md_text = INLINE_SVG_RE.sub(replace_svg, md_text)

    def replace_video(match: re.Match) -> str:
        src = match.group(2) or "unknown source"
        return f"\n\n> Video omitted from EPUB.\n> View online: {src}\n\n"

    md_text = VIDEO_RE.sub(replace_video, md_text)
    md_text = SPAN_RE.sub(r"\1", md_text)

    if session:
        session.close()

    return md_text

# ---- NEW ------------------------------------------------------------


def prepare_source(
    md_path: Path,
    vault_path: Path,
    attachment_dirs: List[str],
    work_dir: Path,
) -> Tuple[Path, Dict[str, Any]]:
    work_dir.mkdir(parents=True, exist_ok=True)

    body, metadata = parse_markdown(md_path)
    body, image_refs = convert_wikilink_images(body)

    for original_name in image_refs:
        src = find_attachment(original_name, vault_path, attachment_dirs)

        if src is None:
            print(f"  ! Warning: could not find attachment '{original_name}', skipping")
            continue

        dest = work_dir / _sanitize_filename(original_name)
        shutil.copy2(src, dest)

        if dest.suffix.lower() == ".svg":
            png_dest = _svg_to_png(dest)
            body = body.replace(
                f"![]({_sanitize_filename(original_name)})",
                f"![]({png_dest.name})",
            )

    body = process_media(body, work_dir)

    out_md = work_dir / "source.md"
    out_md.write_text(body, encoding="utf-8")

    return out_md, metadata