---
name: pdf-read
description: PDF document reading skill. Use when reading local or remote PDF files to extract text, metadata, or images. Ideal for academic papers and technical documentation.
---

# PDF Reading

Two tools available — choose based on need: **MCP** (full features, images/metadata/remote URL) and **CLI pdftotext** (fast text search, no MCP context overhead).

---

## Tool 1: MCP (`mcp_pdf-reader_read_pdf`)

Full-featured, supports image extraction and remote URLs. Preferred for careful reading.

| Parameter | Description |
|-----------|-------------|
| `sources` | List of PDF sources: `path` (local) or `url` (remote) |
| `pages` | Specific page numbers, e.g. `[1, 2, 3]` |
| `include_metadata` | Extract title, authors, DOI, etc. |
| `include_page_count` | Get total page count |
| `include_full_text` | Extract all text |
| `include_images` | Extract embedded images (⚠️ must specify `pages`) |

### Basic usage

```
# Get metadata and page count
mcp_pdf-reader_read_pdf(
  sources: [{"path": "/path/to/paper.pdf"}],
  include_metadata: true,
  include_page_count: true
)

# Read specific pages
mcp_pdf-reader_read_pdf(
  sources: [{"path": "paper.pdf", "pages": [1, 2, 11, 12]}]
)

# Read remote PDF (arxiv, etc.)
mcp_pdf-reader_read_pdf(
  sources: [{"url": "https://arxiv.org/pdf/2510.12724", "pages": [1]}]
)

# Batch: read abstracts from multiple papers
mcp_pdf-reader_read_pdf(
  sources: [
    {"path": "paper1.pdf", "pages": [1]},
    {"path": "paper2.pdf", "pages": [1]}
  ]
)
```

### Image extraction

**Must specify `pages`**, otherwise no images are returned:

```
mcp_pdf-reader_read_pdf(
  sources: [{"path": "paper.pdf", "pages": [4]}],
  include_images: true
)
```

- ⚠️ No page specified → no images returned
- Returns **all** embedded images on the page (cannot filter by Figure number)
- Workflow: read text first to find the page containing the figure, then extract

---

## Tool 2: CLI pdftotext (fast text, no MCP context overhead)

Good for keyword search, grep, and quickly confirming page numbers before switching to MCP for careful reading. Requires `poppler-utils`:

```bash
which pdftotext || echo "Install with: sudo apt install poppler-utils"
```

### Common commands

```bash
# Extract full text (-layout preserves two-column layout)
pdftotext -layout paper.pdf -

# Extract specific pages (pages 1–3)
pdftotext -layout -f 1 -l 3 paper.pdf -

# Get metadata (title, authors, page count)
pdfinfo paper.pdf

# Locate keyword
pdftotext -layout paper.pdf - | grep -n "Figure 3"
pdftotext -layout paper.pdf - | grep -n "Ablation" | head -10
```

### Recommended workflow: CLI locate → MCP read

```bash
# 1. Use CLI to find keyword location
pdftotext -layout paper.pdf - | grep -n "reward shaping"

# 2. Use MCP to read those pages precisely (e.g. found near page 8)
mcp_pdf-reader_read_pdf(sources: [{"path": "paper.pdf", "pages": [7, 8, 9]}])
```

---

## Known limitations

- No OCR support (scanned PDFs)
- Math formulas converted to Unicode — may be incomplete
- Encrypted PDFs not supported
