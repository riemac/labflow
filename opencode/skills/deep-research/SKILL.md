---
name: deep-research
description: Use when a complex research or engineering question needs a substantial evidence-backed investigation across local code, project docs, external documentation, upstream source, papers/PDFs, APIs, or web/GitHub evidence, and the user expects a synthesized research report rather than a short answer. Use for feasibility studies, architectural/algorithmic route selection, cross-source technical due diligence, and high-uncertainty questions that require citations and confidence assessment.
---

# Deep Research

Run a focused investigation and produce a concise, evidence-backed report. This is an ability skill: use it inside the labflow develop stage or any normal agent when the question is too complex for a quick lookup.

## Research Contract

- Answer the user's actual question, not a broader literature survey.
- Combine local code reading, project docs, external docs/source/API, papers, and web evidence only when each source type is relevant.
- Separate **facts with evidence** from **inferences** and **recommendations**.
- Prefer primary sources: local code, official docs, upstream source, papers, release notes, issues/PRs when they are the point of evidence.
- Cite every non-obvious factual claim with footnotes or inline source references.
- Keep noise out of the main context: delegate high-noise branches to the built-in `explore` (local code) or `scout` (external docs) subagents, then synthesize only durable facts.
- Stop early if evidence is insufficient for a confident conclusion; state the uncertainty rather than filling gaps with speculation.

## Workflow

1. **Frame the question**
   - Restate the decision/question in one sentence.
   - Identify subquestions, likely source types, and success criteria.
   - If a preference or boundary is unknowable from artifacts and materially changes the report, ask one focused question; otherwise proceed with explicit assumptions.

2. **Collect evidence**
   - For local code: use codebase semantic retrieval first when locations are unknown, then read key files and line-level evidence.
   - For external libraries/APIs: use `find-docs` / ctx7 first; use `gh` or web only when docs are insufficient or GitHub evidence is specifically needed.
   - For papers/PDFs: use `pdf-read` and cite page/section or extracted path when possible.
   - For broad/noisy branches: delegate read-heavy work, but the main agent must verify any claim that drives the conclusion.

3. **Synthesize**
   - Start with the answer and conditions.
   - Explain mechanisms and constraints, not just yes/no.
   - Surface counterexamples, failure modes, hidden assumptions, and engineering implications.
   - Distinguish high-confidence facts from medium-confidence inferences.

4. **Write the report**
   - Use the format in `references/report-format.md` when the user asks for a durable report or when the result is substantial.
   - For lightweight answers, use a compressed version: answer, evidence, caveats, next steps.
   - Save to the user-requested path when provided. If no path is provided, ask before writing; otherwise answer in chat.

## Report Shape

For substantial investigations, prefer this structure:

```text
# <topic> 调研
## Executive Summary
## Direct Answers
## Architecture / System Overview
## What the Evidence Shows
## Implications / Recommended Route
## Key Repositories / Files / Sources
## Confidence Assessment
## Footnotes
```

Read `references/report-format.md` for detailed section intent and citation style.

## Quality Bar

A good deep-research report should:

- make the decision easier;
- identify what is supported, unsupported, and conditionally supported;
- include enough source paths/URLs/page refs that another researcher can audit it;
- avoid dumping raw search results;
- end with confidence levels and actionable next steps.

## Anti-Patterns

- Do not write a generic survey when the user asked a feasibility question.
- Do not cite secondary summaries when primary docs/source/papers are available.
- Do not hide shape/API/schema constraints behind vague “should work” language.
- Do not let subagent output become the final report without main-agent synthesis.
- Do not use this for simple code lookup; use `codebase-research` instead.
- Do not use this for simple library syntax lookup; use `find-docs` / `external-research` instead.
