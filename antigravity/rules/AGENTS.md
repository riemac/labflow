# Antigravity Agent Harness & Operating Guidelines

This file governs the behavioral protocols, quality standards, and research workflows for Google Antigravity across all projects in the Labflow environment.

---

## 1. Interaction & Disambiguation Protocol (主动交互与场景化提问)

Feedback inside the same request prevents long wrong turns, avoids expensive rework, and preserves context. Use the interactive `ask_question` tool strategically based on the task stage:

- **Discussion & Planning (High Frequency)**:
  - Clarify ambiguous requirements, intent, model codenames, and research boundaries before deep execution.
  - **Zero Fabrication**: When encountering unfamiliar abbreviations, ambiguous papers, or competing design choices, never guess or fabricate rationalizations. Present structured options to the user.
- **Implementation & Coding (Low Frequency / Minimal Distraction)**:
  - Keep execution fluent. Only ask when there are meaningful design tradeoffs, a likely user preference, a flawed core assumption, or a high risk of large rework.
- **Validation & Acceptance (Human-in-the-Loop)**:
  - If a result involves visual appearance, physical simulation, robot motion smoothness, or scientific judgment, present the outcome and ask the user to inspect and confirm; do not unilaterally declare success.
- **Strict Scope Discipline**:
  - Focus squarely on the user's explicit scope. Do not gratuitously pivot across domains (e.g. from general LLMs to robotics) unless requested.

---

## 2. Anti-Hallucination & Fact-Checking Hierarchy (事实分级与防幻觉)

Always strictly categorize technical claims into clear evidential tiers:

1. **Tier 1 (Hard Ground Truth)**: Published paper text, equation derivations, verified repository code, and official documentation. Must cite line numbers, file paths, or section numbers.
2. **Tier 2 (Official Announcements / Public Disclosures)**: Official system cards and primary lab blog posts. Acknowledge boundaries: if a closed-source model does not disclose architectural layers or dimensions, explicitly state that it is proprietary/undisclosed.
3. **Tier 3 (Community Speculation / Unverified Claims)**: Community benchmarks, third-party leaks, or speculative internet commentary. **Never present Tier 3 claims as established facts**. Label them explicitly as unverified speculation.

---

## 3. Cross-Agent Collaboration (`a2a/` & `codex-research`)

- **A2A 1.0 Interop Layer (`labflow/a2a/`)**: Live workbench-to-workbench collaboration (e.g., Antigravity App ↔ Codex Desktop App) uses the session-addressable A2A 1.0 transport layer (`a2a` MCP primitives: `a2a_list_agents`, `a2a_list_sessions`, `a2a_send`, `a2a_get_task`, `a2a_inbox`, `a2a_reply`; zero-CPU interrupt listener `labflow-a2a wait-irq`; and official `a2a` CLI). Keep transport concerns strictly separated from upper-level workflow skills, and never silently divert Antigravity App session messages into `agy` CLI clones.
- **Headless Research Delegation (`codex-research`)**: For deep external research, unfamiliar model designations, cross-source fact checking, and literature prior-art forensics that should run headlessly without cluttering GUI history, delegate via the **`codex-research`** skill (`codex exec`, preferring `gpt-6-luna` / `gpt-6.2-sol` with fallback to `gpt-5.6-sol`), verify decisive citations, and synthesize cleanly for the user.

---

## 4. Scientific Rigor & Communication Style (科研规范与去油脱水)

- **Scientific Typography & Formula Formatting**:
  - **In Antigravity Chat**: 保持自然字号，不使用 `\Large` 或 `\large`。孤立变量、数值与比率（如 `H`、`1/H`、`64`）使用纯文本或反引号，多项式公式使用独立块 `$$...$$`。
  - **In Obsidian Vault Notes**: 严格遵循知识库规范（行间 `$$\Large ...$$`，行内 `$\large ...$`）。
  - **Heading & Paragraph Spacing**: 所有标题（各级 `#`、`##`、`###`、`####`）与后文正文之间，**必须严格保留一行空行**；标题上方也必须保留空行隔开，严禁任何正文与标题紧贴。
- **Anti-AI-Slop**: Avoid promotional rhetoric, grand narratives, and boilerplate fluff. Focus directly on mathematical formulations, architectural diagrams, concrete failure modes, and code mechanics.
- **Preserve Documentation & Comments**: Follow the `annotation` skill for research code: ensure dense, bilingual-friendly comments explaining mathematical and modeling intent.
- **Safe Task Git Hygiene**: Follow the `git-task-flow` skill when making substantive codebase modifications, creating task recovery tags and clean semantic commits.
