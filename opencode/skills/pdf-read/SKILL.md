---
name: pdf-read
description: PDF document reading skill. Use when reading local or remote PDF files to extract text, metadata, or images. Ideal for academic papers and technical documentation.
---

# PDF Reading

Attached PDFs are handled by opencode's own harness — skip this skill. Use it
when you have a **local path or remote URL** and need to read the PDF yourself.

The primary tool is the `pdf-reader` MCP server. It reads pages, extracts
metadata, and — critically — returns **embedded images** that opencode feeds
straight into context so you see figures, not just text.

> MCP URL fetch may fail behind a proxy. If a remote URL fails, download the PDF
> locally first, then read it via MCP `path`.

## MCP (`mcp_pdf-reader_read_pdf`)

| Parameter | Description |
|-----------|-------------|
| `sources` | Array of `{path}` (local) or `{url}` (remote) |
| `pages` | Page numbers (`[1,2,3]`) or range string (`"1-5,10"`) |
| `include_metadata` | Title, authors, DOI |
| `include_page_count` | Total pages |
| `include_full_text` | Extract text |
| `include_images` | Extract embedded images (requires `pages`) |

### Read a paper (no upload needed)

```
# Confirm metadata and page count.
mcp_pdf-reader_read_pdf(
  sources: [{"url": "https://arxiv.org/pdf/2210.04887"}],
  include_metadata: true,
  include_page_count: true,
  include_full_text: false
)

# Read target pages.
mcp_pdf-reader_read_pdf(
  sources: [{"url": "https://arxiv.org/pdf/2210.04887", "pages": "1-4"}],
  include_full_text: true
)
```

### Read figures (not just text)

Add `include_images: true` with `pages`. The tool returns page text and
embedded images together; opencode passes images straight into context.

```
mcp_pdf-reader_read_pdf(
  sources: [{"path": "paper.pdf", "pages": [3]}],
  include_images: true,
  include_full_text: true
)
```

- Returns **embedded image objects** (photos, rendered figures), not full-page
  screenshots.
- Returns **all** images on the page — locate the right page from text first.
- When a figure, diagram, or plot matters, extract it and describe what you see.

## CLI pdftotext (fast local search)

For grep-style keyword lookup on local PDFs. Requires `poppler-utils`.

```bash
# Extract text
pdftotext -layout paper.pdf -

# Specific pages
pdftotext -layout -f 1 -l 3 paper.pdf -

# Metadata
pdfinfo paper.pdf

# Locate keyword, then read the page with MCP
pdftotext -layout paper.pdf - | grep -n "Figure 3"
```

## Batch

Read metadata/text from multiple PDFs in one call.

```
mcp_pdf-reader_read_pdf(
  sources: [
    {"path": "paper1.pdf", "pages": [1]},
    {"path": "paper2.pdf", "pages": [1]}
  ]
)
```

## Limitations

- No OCR (scanned PDFs)
- Math formulas → Unicode, may be incomplete
- Encrypted PDFs unsupported
