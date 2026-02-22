# Rickover Corpus (Full-Text Blog Subset)

This repository contains a reproducible extraction of the full-text blog posts from [The Rickover Corpus](https://rickovercorpus.org/blog.html), including:

- title
- year
- tags/themes
- full OCR text
- source links

The latest generated manifest reports:

- `count`: 41 speeches
- `generated_at_utc`: `2026-02-22T10:16:53Z`

## What Was Done

1. Parsed the blog index (`/blog.html`) to collect all unique `posts/*.html` links.
2. Extracted metadata from index card attributes (`data-title`, `data-year`, `data-themes`, `data-summary`).
3. Fetched each post page and extracted:
   - canonical title (`<h1>`)
   - PDF source URL (`.pdf` link)
   - full OCR text (`div.ocr-text`)
4. Wrote outputs in two formats:
   - JSONL for structured downstream processing
   - Markdown files with YAML front matter for publishing/conversion workflows

## Repository Contents

- `scripts/download_rickover_blog.py`
  - Main scraper/downloader.
  - Produces both JSONL and Markdown outputs.
- `data/rickover_speeches.jsonl`
  - One JSON object per speech/document.
- `data/markdown/*.md`
  - One Markdown file per speech, with YAML front matter.
- `data/manifest.json`
  - Generation metadata (`count`, timestamp, output paths).
- `.claude/napkin.md`
  - Working notes, mistakes, and extraction quirks logged during the build.

## Data Schema

Each JSONL record contains:

- `slug`
- `title`
- `year`
- `tags`
- `source_url`
- `pdf_url`
- `summary`
- `text`
- `retrieved_at_utc`

Each Markdown file front matter contains:

```yaml
---
title: "..."
year: 1982
tags: ["Management", "Leadership"]
slug: "..."
source_url: "https://rickovercorpus.org/posts/....html"
pdf_url: "https://rickover-corpus.s3.us-east-1.amazonaws.com/....pdf"
---
```

The body is the full extracted OCR text.

## How To Regenerate

Run:

```bash
python3 scripts/download_rickover_blog.py --out-dir data
```

Optional flags:

- `--base-url` (default: `https://rickovercorpus.org/`)
- `--blog-path` (default: `blog.html`)
- `--timeout` (default: `60`)
- `--limit` (for test runs)
- `--out-dir` (default: `data`)

## Notes and Caveats

- Scope is currently the blog full-text subset: 41 documents from `blog.html`.
- The site archive page mentions 143 total documents; those broader entries are not yet fully extracted here.
- One source page (`nuclear-power-and-bremerton`) currently contains unusual OCR/editorial note text on the source site, and this repository preserves that source content as-is.

## Provenance

This repository setup, scraper implementation, and dataset generation were completed in an interactive Codex session under the repository owner's instructions. In short: you used me to do this end-to-end run.
