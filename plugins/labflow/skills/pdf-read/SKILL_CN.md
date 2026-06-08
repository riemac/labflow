---
name: pdf-read
description: PDF 文档阅读技能。用于读取本地或远程 PDF，提取文字、元数据或图片。适合学术论文和技术文档。
---

# PDF 阅读

已附带的 PDF 交给宿主自身处理，不需要这个 skill。以下用于你有**本地路径或远程 URL**、
需要自己读 PDF 的场景。

主力工具是 `pdf-reader` MCP。它按页读取、提取元数据，更重要的是可以返回**嵌入图片**——
宿主直接将图送进上下文，让你看图而不是只读文字。

> MCP 直取远程 URL 在代理环境下可能失败。失败时先把 PDF 下到本地，再用 MCP `path` 读。

## MCP（`mcp_pdf-reader_read_pdf`）

| 参数 | 说明 |
|------|------|
| `sources` | PDF 来源列表：`{path}`（本地）或 `{url}`（远程） |
| `pages` | 页码（`[1,2,3]`）或范围字符串（`"1-5,10"`） |
| `include_metadata` | 标题、作者、DOI |
| `include_page_count` | 总页数 |
| `include_full_text` | 提取文字 |
| `include_images` | 提取嵌入图片（需指定 `pages`） |

### 读论文

```
# 确认元数据和页数
mcp_pdf-reader_read_pdf(
  sources: [{"url": "https://arxiv.org/pdf/2210.04887"}],
  include_metadata: true,
  include_page_count: true,
  include_full_text: false
)

# 读目标页
mcp_pdf-reader_read_pdf(
  sources: [{"url": "https://arxiv.org/pdf/2210.04887", "pages": "1-4"}],
  include_full_text: true
)
```

### 读图（不止读文字）

设 `include_images: true` 并指定 `pages`。工具返回该页文字和嵌入图片。

```
mcp_pdf-reader_read_pdf(
  sources: [{"path": "paper.pdf", "pages": [3]}],
  include_images: true,
  include_full_text: true
)
```

- 返回的是页面里的**嵌入图片对象**（照片、渲染好的图），不是整页截图。
- 返回该页**所有**图片，无法按图号过滤 —— 先用文字定位到正确页码。
- 只要回答需要看图、示意图、定性结果或曲线，就提出来看，描述你实际看到的内容。

## CLI pdftotext（本地快速搜索）

本地 PDF 做 grep 式关键词定位。需要 `poppler-utils`。

```bash
# 提取文字
pdftotext -layout paper.pdf -

# 指定页
pdftotext -layout -f 1 -l 3 paper.pdf -

# 元数据
pdfinfo paper.pdf

# 定位关键词，再用 MCP 读那页
pdftotext -layout paper.pdf - | grep -n "Figure 3"
```

## 批量

一次调用读多篇 PDF 的元数据或文字。

```
mcp_pdf-reader_read_pdf(
  sources: [
    {"path": "paper1.pdf", "pages": [1]},
    {"path": "paper2.pdf", "pages": [1]}
  ]
)
```

## 已知限制

- 不支持 OCR（扫描版 PDF）
- 数学公式转为 Unicode，可能不完整
- 不支持加密 PDF
