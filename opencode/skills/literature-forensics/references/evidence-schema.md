# Literature Evidence Schema

## Relevance Classes

| Class | Meaning | Lead action |
|---|---|---|
| `exact` | Same central mechanism and sufficiently comparable setting. | Targeted verification required. |
| `close-analogue` | Same mechanism elsewhere, or comparable mechanism in the target setting. | Verify the strongest candidates. |
| `setting-analogue` | Similar task/embodiment setting without the target mechanism. | Use for positioning, not priority claims. |
| `background` | General context, platform, hardware, or algorithm citation. | Abstract/metadata may be enough if the usage is factual. |
| `counterevidence` | Challenges mechanism, novelty, or expected benefit. | Lead verification required. |
| `excluded` | Screened and intentionally not used. | Keep the exclusion reason. |

## Reading Depth

- `metadata`: bibliographic fields only.
- `abstract`: abstract screened for relevance.
- `targeted`: exact primary-source sections/pages checked.
- `full`: the whole paper read closely.

Worker and lead depths are independent. Visual review uses `pending`, `located`,
or `verified`.

## Topic Frontmatter

```yaml
---
topic: ppo-variant-imbalance
status: active
stage: screening
updated: 2026-07-10
search_cutoff: 2026-07-10
confidence: medium
---
```

Recommended body:

```text
# <Topic>
## Research Question
## Current Answer
## Search Coverage
## Exact Matches
## Close Analogues
## Setting Analogues
## Counterevidence
## Exclusions
## Unresolved Questions
## Recommended Next Search
```

## Paper Frontmatter

```yaml
---
citekey: example2026method
status: screened
relevance: close-analogue
year: 2026
doi: null
arxiv: "2601.12345"
openalex: null
semantic_scholar: null
review:
  worker: targeted
  lead: abstract
visual_review:
  worker: located
  lead: pending
updated: 2026-07-10
---
```

Recommended body:

```text
# <Paper Title>
## Why It Matters
## What The Paper Actually Establishes
## Reading Map
## Visual Evidence
## Similarity To Our Setting
## Critical Differences
## Counterevidence / Limitations
## Possible Manuscript Use
## Open Questions
```

The reading map must distinguish PDF page index from printed page number and
identify references, appendix, relevant sections, figures, captions, and bbox
when available.

## Novelty Wording

Safe:

> We did not identify an exact treatment of X in setting Y across the searched
> arXiv, OpenAlex, Semantic Scholar, and backward/forward citation facets through
> <date>; related work addresses X in setting Z or Y through mechanism W.

Unsafe:

> No prior work exists, and we are the first.
