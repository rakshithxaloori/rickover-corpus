# Napkin

## Corrections
| Date | Source | What Went Wrong | What To Do Instead |
|------|--------|-----------------|--------------------|
| 2026-02-22 | self | Assumed repo already had a napkin file; it was missing. | Create `.claude/napkin.md` at session start if absent. |

## User Preferences
- For this corpus task, user prefers a storage format that is easy to convert to Markdown later, with front matter tags in resulting Markdown files.

## Patterns That Work
- Verify site structure first, then lock schema and download pipeline before bulk scraping.

## Patterns That Don't Work
- Starting bulk download before agreeing a stable output format can create avoidable rework.

## Domain Notes
- Repo path: `/Users/rakshithaloori/Personal/rickover-corpus`.
- Task domain: Rickover speech corpus extraction (title, year, tags, full speech text).
| 2026-02-22 | self | Tried network fetch in sandbox; DNS resolution failed. | If web fetch is required, rerun with escalated permissions promptly. |

## Patterns That Work
- `https://rickovercorpus.org/blog.html` is server-rendered and includes all post links with `data-title`, `data-year`, and `data-themes` attributes.
- Individual post pages include transcript under `div.ocr-text > p` blocks and visible metadata chips for year/themes.

## Domain Notes
- Blog index title currently indicates `Full Archive (143 documents)` in nav text.
- A post page also includes `View Original PDF` URL on S3 (`rickover-corpus.s3.us-east-1.amazonaws.com`).
## Domain Notes
- `blog.html` currently exposes 41 unique `posts/*.html` pages with full OCR text.
- `index.html` references 143 documents total, likely broader archive metadata/PDF links via `search.js`.
| 2026-02-22 | self | Assumed all `posts/*.html` OCR content is in `<p>` tags; one page had raw text directly inside `div.ocr-text`. | Keep parser fallback to raw OCR div text when paragraph extraction is empty. |

## Patterns That Work
- For this corpus, dual extraction path (`<p>` blocks first, raw OCR fallback second) avoids hard failures on inconsistent post markup.
## Domain Notes
- `posts/nuclear-power-and-bremerton.html` contains unusual OCR body text (editorial "Wait, check..." notes) instead of normal transcript paragraphs; scraper should preserve source text but flag for downstream QA.
## Patterns That Work
- A single local script (`scripts/download_rickover_blog.py`) that extracts index metadata and post OCR text can regenerate `data/rickover_speeches.jsonl` plus Markdown corpus deterministically.
