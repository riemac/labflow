---
name: codex-research
description: "Use OpenAI's Codex CLI for deep external research, high-reliability fact-checking, literature exploration, and complex technical investigations with minimal hallucination. Delegates bounded research briefs to Codex (`codex exec`) and integrates structured reports."
---

# Codex Research

<scope>

Use Codex (via `codex exec`) as an external, low-hallucination research partner for deep investigations, authoritative fact verification, and complex cross-source technical audits.

Antigravity handles synthesis, user interaction, local codebase exploration, and mathematical/robotics modeling. Codex provides grounded external research, cross-verifies disputed technical claims, and retrieves auditable citations.

Use `codex-research` when:
- Investigating external frontier model architectures, proprietary systems, or disputed terminology where web search alone risks high hallucination or AI slop.
- Performing scholarly prior-art or literature forensics across disparate academic sources.
- Needing rigorous third-party fact-checking before asserting claims as ground truth.
- Scanning long external documentation, issue trackers, or technical reports that would needlessly pollute the local conversation context.

Do not use for local codebase queries (use `codebase-research`) or quick direct file reads.

</scope>

<session>

## Invocation

Execute Codex non-interactively using `run_command` in a trusted directory (default to `/home/hac/labflow`):

```bash
codex exec -m MODEL -c service_tier="fast" -C /home/hac/labflow --skip-git-repo-check "PROMPT"
```

### Configuration & Models

1. **Default Model**: Prefer `gpt-6-luna` with `-c service_tier="fast"`.
   - If the current Codex account/provider does not support `gpt-6-luna` (e.g. account tier restriction), fallback to the verified available flagship model `gpt-5.6-sol`.
2. **Execution Parameters**:
   - Set `service_tier="fast"` to minimize turnaround latency.
   - Use `--skip-git-repo-check` and point `-C` to `/home/hac/labflow` (or the relevant project root).
   - For long outputs, specify `-o /tmp/codex_research_<id>.md` to avoid shell output truncation.

## Continuation & Multi-Turn Investigation

When an investigation requires follow-up verification or deeper probing on a specific finding:
- Resume the existing session:
  ```bash
  codex exec resume --last "FOLLOWUP PROMPT"
  ```
- Or resume by explicit session ID if logged from previous run:
  ```bash
  codex exec resume <SESSION_ID> "FOLLOWUP PROMPT"
  ```

</session>

<contract>

## Research Brief Contract

Always give Codex a bounded, disciplined research brief with explicit boundaries:

1. **Problem Statement**: What exact technical question or system is being investigated?
2. **Fact vs. Speculation Boundary**: Instruct Codex to explicitly classify claims into:
   - *Verified Facts*: Grounded in published papers, official documentation, or public repository code.
   - *Architecture Speculation / Disputed Claims*: Unverified community rumors, press releases, or closed-source black-box estimates.
   - *Non-Existent / Misattributed*: Conflations or fictional designations.
3. **Evidence Requirement**: Require concrete citations, paper titles, release dates, or official URLs.
4. **Output Format**: Concise, structured report with executive summary, detailed analysis, and source list.

## Integration & Review

Upon receiving Codex's response:
- Antigravity reviews the returned report for internal consistency and relevance.
- Synthesize key findings cleanly for the user.
- If uncertainties remain, present them transparently or trigger interactive clarification via `ask_question`.

</contract>
