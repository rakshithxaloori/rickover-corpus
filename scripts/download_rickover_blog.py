#!/usr/bin/env python3
"""Download Rickover full-text blog posts into JSONL and Markdown."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urljoin
from urllib.request import Request, urlopen


USER_AGENT = "rickover-corpus-downloader/1.0"


def normalize_space(text: str) -> str:
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t\f\v]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    return text.strip()


def yaml_quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def fetch_html(url: str, timeout: int) -> str:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


class BlogIndexParser(HTMLParser):
    """Extract post links and metadata from blog index cards."""

    def __init__(self) -> None:
        super().__init__()
        self.posts: list[dict[str, Any]] = []
        self._seen_hrefs: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return

        attr = {k: (v or "") for k, v in attrs}
        href = attr.get("href", "").strip()
        if not (href.startswith("posts/") and href.endswith(".html")):
            return
        if href in self._seen_hrefs:
            return
        self._seen_hrefs.add(href)

        year_raw = unescape(attr.get("data-year", "")).strip()
        year = int(year_raw) if year_raw.isdigit() else None
        tags = [
            normalize_space(unescape(tag))
            for tag in attr.get("data-themes", "").split(",")
            if normalize_space(unescape(tag))
        ]

        self.posts.append(
            {
                "href": href,
                "slug": Path(href).stem,
                "title": normalize_space(unescape(attr.get("data-title", ""))),
                "year": year,
                "tags": tags,
                "summary": normalize_space(unescape(attr.get("data-summary", ""))),
            }
        )


class PostPageParser(HTMLParser):
    """Extract full OCR text and canonical metadata from a post page."""

    def __init__(self) -> None:
        super().__init__()
        self.title: str = ""
        self.pdf_url: str = ""
        self.paragraphs: list[str] = []

        self._in_h1 = False
        self._h1_chunks: list[str] = []
        self._in_ocr = False
        self._ocr_depth = 0
        self._in_p = False
        self._p_chunks: list[str] = []
        self._ocr_chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {k: (v or "") for k, v in attrs}

        if tag == "h1":
            self._in_h1 = True
            self._h1_chunks = []

        if tag == "a" and not self.pdf_url:
            href = attr.get("href", "").strip()
            if href.lower().endswith(".pdf"):
                self.pdf_url = href

        if tag == "div":
            classes = set(attr.get("class", "").split())
            if self._in_ocr:
                self._ocr_depth += 1
            elif "ocr-text" in classes:
                self._in_ocr = True
                self._ocr_depth = 1

        if self._in_ocr and tag == "p":
            self._in_p = True
            self._p_chunks = []
            self._ocr_chunks.append("\n")

        if self._in_p and tag == "br":
            self._p_chunks.append("\n")
        if self._in_ocr and tag == "br":
            self._ocr_chunks.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag == "h1" and self._in_h1:
            self.title = normalize_space("".join(self._h1_chunks))
            self._in_h1 = False
            self._h1_chunks = []

        if self._in_ocr and tag == "p" and self._in_p:
            paragraph = normalize_space("".join(self._p_chunks))
            if paragraph:
                self.paragraphs.append(paragraph)
            self._in_p = False
            self._p_chunks = []
            self._ocr_chunks.append("\n")

        if self._in_ocr and tag == "div":
            self._ocr_depth -= 1
            if self._ocr_depth == 0:
                self._in_ocr = False

    def handle_data(self, data: str) -> None:
        if self._in_h1:
            self._h1_chunks.append(data)
        if self._in_p:
            self._p_chunks.append(data)
        if self._in_ocr:
            self._ocr_chunks.append(data)

    def fallback_text(self) -> str:
        raw = "".join(self._ocr_chunks)
        raw = raw.replace("\xa0", " ")
        raw = normalize_space(raw)
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        return raw.strip()


@dataclass
class SpeechRecord:
    slug: str
    title: str
    year: int | None
    tags: list[str]
    source_url: str
    pdf_url: str
    summary: str
    text: str
    retrieved_at_utc: str


def to_markdown(record: SpeechRecord) -> str:
    tags = ", ".join(yaml_quote(tag) for tag in record.tags)
    year_value = "null" if record.year is None else str(record.year)
    pdf_value = "null" if not record.pdf_url else yaml_quote(record.pdf_url)

    return (
        "---\n"
        f"title: {yaml_quote(record.title)}\n"
        f"year: {year_value}\n"
        f"tags: [{tags}]\n"
        f"slug: {yaml_quote(record.slug)}\n"
        f"source_url: {yaml_quote(record.source_url)}\n"
        f"pdf_url: {pdf_value}\n"
        "---\n\n"
        f"{record.text}\n"
    )


def build_records(base_url: str, blog_path: str, timeout: int, limit: int | None) -> list[SpeechRecord]:
    blog_url = urljoin(base_url, blog_path)
    blog_html = fetch_html(blog_url, timeout=timeout)

    blog_parser = BlogIndexParser()
    blog_parser.feed(blog_html)

    posts = blog_parser.posts if limit is None else blog_parser.posts[:limit]
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    records: list[SpeechRecord] = []

    for post in posts:
        source_url = urljoin(base_url, post["href"])
        post_html = fetch_html(source_url, timeout=timeout)

        post_parser = PostPageParser()
        post_parser.feed(post_html)

        title = post_parser.title or post["title"] or post["slug"].replace("-", " ").title()
        text = "\n\n".join(post_parser.paragraphs).strip()
        if not text:
            text = post_parser.fallback_text()
        if not text:
            raise RuntimeError(f"Extracted empty OCR text for {source_url}")

        records.append(
            SpeechRecord(
                slug=post["slug"],
                title=title,
                year=post["year"],
                tags=post["tags"],
                source_url=source_url,
                pdf_url=post_parser.pdf_url,
                summary=post["summary"],
                text=text,
                retrieved_at_utc=timestamp,
            )
        )

    return records


def write_outputs(records: list[SpeechRecord], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    md_dir = out_dir / "markdown"
    md_dir.mkdir(parents=True, exist_ok=True)

    jsonl_path = out_dir / "rickover_speeches.jsonl"
    with jsonl_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(asdict(record), ensure_ascii=False))
            handle.write("\n")

    for record in records:
        md_path = md_dir / f"{record.slug}.md"
        md_path.write_text(to_markdown(record), encoding="utf-8")

    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "count": len(records),
        "jsonl_path": str(jsonl_path),
        "markdown_dir": str(md_dir),
    }
    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="https://rickovercorpus.org/")
    parser.add_argument("--blog-path", default="blog.html")
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--out-dir", default="data")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    records = build_records(
        base_url=args.base_url,
        blog_path=args.blog_path,
        timeout=args.timeout,
        limit=args.limit,
    )
    write_outputs(records, Path(args.out_dir))
    print(f"Wrote {len(records)} speeches to {args.out_dir}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
    except Exception as exc:  # pragma: no cover
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)
