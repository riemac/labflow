---
name: pdf-read
description: PDF 文档读取技能。阅读本地或远程 PDF 文件，提取文本、元数据和图片时使用。适用于阅读论文、技术文档。
---

# PDF 文档读取

两种工具按需选择：**MCP**（完整功能，图片/元数据/远程URL）和 **CLI pdftotext**（快速文本搜索，无需 MCP 上下文）。

---

## 工具一：MCP（`mcp_pdf-reader_read_pdf`）

功能完整，支持图片提取和远程 URL，首选用于精读。

| 参数 | 说明 |
|------|------|
| `sources` | PDF 来源列表，支持 `path`（本地）或 `url`（远程） |
| `pages` | 指定页码，如 `[1, 2, 3]` |
| `include_metadata` | 提取标题、作者、DOI 等 |
| `include_page_count` | 获取总页数 |
| `include_full_text` | 提取全部文本 |
| `include_images` | 提取嵌入图片（⚠️ 必须配合 `pages` 使用） |

### 基本用法

```
# 获取元数据和页数
mcp_pdf-reader_read_pdf(
  sources: [{"path": "/path/to/paper.pdf"}],
  include_metadata: true,
  include_page_count: true
)

# 按页读取
mcp_pdf-reader_read_pdf(
  sources: [{"path": "paper.pdf", "pages": [1, 2, 11, 12]}]
)

# 读取远程 PDF（arxiv 等）
mcp_pdf-reader_read_pdf(
  sources: [{"url": "https://arxiv.org/pdf/2510.12724", "pages": [1]}]
)

# 批量读取多篇论文摘要
mcp_pdf-reader_read_pdf(
  sources: [
    {"path": "paper1.pdf", "pages": [1]},
    {"path": "paper2.pdf", "pages": [1]}
  ]
)
```

### 图片提取

**必须指定 `pages`**，否则不返回图片：

```
mcp_pdf-reader_read_pdf(
  sources: [{"path": "paper.pdf", "pages": [4]}],
  include_images: true
)
```

- ⚠️ 不指定页码 → 无图片返回
- 返回该页**所有**嵌入图片（无法按 Figure 编号选择）
- 需先读文本确定 Figure 所在页码，再提取

---

## 工具二：CLI pdftotext（快速文本，不消耗 MCP 上下文）

适合关键词定位、grep 搜索、快速确认页码后再用 MCP 精读。需要 `poppler-utils`：

```bash
which pdftotext || echo "需要安装: sudo apt install poppler-utils"
```

### 常用命令

```bash
# 读取全文（-layout 保留双栏排版）
pdftotext -layout paper.pdf -

# 读取指定页（第 1-3 页）
pdftotext -layout -f 1 -l 3 paper.pdf -

# 获取元数据（标题、作者、总页数）
pdfinfo paper.pdf

# 定位关键词所在行
pdftotext -layout paper.pdf - | grep -n "Figure 3"
pdftotext -layout paper.pdf - | grep -n "Ablation" | head -10
```

### 推荐工作流：CLI 定位 → MCP 精读

```bash
# 1. 先用 CLI 找到关键词所在页
pdftotext -layout paper.pdf - | grep -n "reward shaping"

# 2. 再用 MCP 按页精读（假设找到在第 8 页附近）
mcp_pdf-reader_read_pdf(sources: [{"path": "paper.pdf", "pages": [7, 8, 9]}])
```

---

## 已知限制

- 不支持 OCR（扫描版 PDF）
- 数学公式转为 Unicode，可能不完整
- 不支持加密 PDF
