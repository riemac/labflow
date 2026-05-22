# Deep Research Report Format

Use this format when the investigation is substantial enough to become a durable artifact. Keep sections that help the decision; omit sections that would be empty.

## Title

```md
# <topic> 调研
```

Use a concrete topic, not “Research Report”.

## Executive Summary

Lead with the decision-level answer in 1-3 paragraphs.

Include:

- direct conclusion;
- hard conditions and boundaries;
- highest-impact recommendation;
- one sentence on confidence or remaining uncertainty.

## Direct Answers

Use a compact table when the user asked multiple concrete questions.

```md
| 问题 | 结论 | 关键条件 |
|---|---|---|
| ... | **支持 / 不支持 / 条件支持** | ... |
```

## Architecture / System Overview

Use a small ASCII/Mermaid-style diagram when mechanisms matter.

Show only the pieces needed to explain the answer: data flow, API path, control loop, asset pipeline, training stack, or dependency chain.

## What the Evidence Shows

Group evidence by mechanism, not by search order.

Good subsection patterns:

- `### 1. <mechanism or source-backed fact>`
- `### 2. <constraint or counterexample>`
- `### 3. <why this matters for the user task>`

Each non-obvious claim should carry a citation.

## Implications / Recommended Route

Translate evidence into the user's project context.

Include:

- what is feasible now;
- what should be avoided;
- what needs engineering standardization;
- what needs experiment/ablation;
- suggested next implementation or validation step.

## Key Repositories / Files / Sources

Use a table for auditability.

```md
| Resource | Why it matters |
|---|---|
| `/abs/path/file.py:10-40` | Shows the runtime constraint. |
| `https://...` | Official API behavior. |
| `paper.pdf`, pp. 2-4 | Methodological support. |
```

## Confidence Assessment

Split confidence by claim type.

```md
**High confidence**
- Claim with direct source support.[^1]

**Medium confidence / informed inference**
- Claim inferred from multiple sources but not directly stated.[^2]

**Low confidence / needs validation**
- Claim requiring experiment or missing source coverage.
```

## Footnotes

Use footnotes for dense source evidence.

Examples:

```md
[^1]: `/path/to/file.py:12-30`; official docs URL section “...”.
[^2]: `paper.pdf`, pp. 3-5; `/path/to/test.py:80-110`.
```

Prefer line ranges, page ranges, section titles, commit IDs, release versions, or issue/PR numbers when available.
