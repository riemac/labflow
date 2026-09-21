---
name: neat-freak
description: Maintain existing root and nested AGENTS.md and README.md files against the actual project. Use when the user asks to sync, tidy, update, clean up, or review project documentation, including "整理文档", "同步一下", "更新 AGENTS", "梳理一下", "收尾", or "新人能直接上手", or when development reveals stale or conflicting guidance. Create new AGENTS.md or README.md files only when the user explicitly requests them.
---

# AGENTS And README Governance

Keep project guidance accurate, compact, and useful to its intended reader. Treat root and nested files by the same principles, while respecting each file's local scope.

## Two Documents, Two Jobs

`AGENTS.md` is an engineering contract for agents working in its directory tree. It should explain the project or subtree, structure and ownership, stable development conventions, important engineering or research semantics that affect implementation, and reliable commands or tools. It is not a changelog, design diary, handoff memo, or duplicate README.

`README.md` is a human-facing explanation of the project or module. It should develop the actual scientific, algorithmic, or technical subject naturally: motivation, object of study, method, mathematical or semantic contracts, evidence, boundaries, and practical use as appropriate. Research-heavy README files should use the explanatory flavor of ICRA, ICLR, or NeurIPS papers without imitating a paper template mechanically. Pure engineering projects should remain clear technical narratives.

Read `references/agents-template.md` before creating or substantially restructuring an `AGENTS.md`. Read `references/readme-guidance.md` before creating or substantially restructuring a `README.md`.

## Creation And Authorization

- Do not create a root or nested `AGENTS.md` or `README.md` on your own. Creation requires an explicit user request naming or clearly requesting that document.
- A direct request such as "sync up", "tidy up docs", "update AGENTS.md", "整理文档", "同步一下", "收尾", or an equivalent instruction authorizes maintenance of existing in-scope files.
- During ordinary development, proactively notice stale, missing, duplicated, or conflicting guidance. Before editing existing documents for that reason, use `question` to show the affected files and proposed maintenance scope.
- Do not turn a maintenance request into an unsolicited documentation expansion. Other files under `docs/` are outside the normal scope unless they directly conflict with an in-scope `AGENTS.md` or `README.md`.

## Scope And Hierarchy

- Root `AGENTS.md` contains project-wide engineering guidance. Nested `AGENTS.md` contains only subtree-specific structure, conventions, commands, risks, and semantics.
- Do not repeat an inherited rule in every nested file. Preserve a local rule only when an agent working in that subtree needs a narrower or different instruction.
- Root README explains the whole project. Nested README explains the local scientific or technical subject, not the repository again.
- Reconcile conflicts from the project root toward the target directory. If two instructions are both plausible and the correct intent cannot be proven from the project, ask the user.
- Keep every `AGENTS.md` at or below 150 lines. Shorter is preferred when it preserves the engineering contract.

## Maintenance Method

1. Establish the authorized project and file scope. Enumerate existing root and nested `AGENTS.md` and `README.md` files in that scope; do not infer that missing files should be created.
2. Read the applicable instruction chain and inspect the current code, configuration, tests, commands, and neighboring documentation needed to verify each statement.
3. Classify content before editing:
   - keep stable engineering rules that still prevent likely mistakes;
   - update stale paths, structure, commands, dependencies, contracts, and research semantics;
   - move detailed human explanation from AGENTS to README when it is useful there;
   - remove duplicated parent rules, historical narration, completed temporary plans, obsolete alternatives, and unsupported claims.
4. Edit the existing structure instead of appending a session summary. Prefer one precise current statement over a sequence of historical corrections.
5. Verify every named path, command, tool, environment assumption, interface, and quantitative threshold against the project. Check root and nested files for contradictions and confirm each AGENTS file remains within 150 lines.

## AGENTS Content Test

Keep a statement in `AGENTS.md` when omitting it would make a future agent more likely to violate an ownership boundary, use the wrong environment or command, misunderstand an important implementation contract, or validate the work incorrectly.

Move or remove a statement when it mainly teaches the research topic, narrates what happened in a previous session, records a release or bug-fix history, reproduces implementation details already explained for humans, or describes code that no longer exists.

Important scientific semantics may remain in AGENTS when they constrain implementation or validation. Keep them concise and operational; place the full explanation in README or another user-authorized research document.

## README Content Test

Write for a technically capable human who wants to understand what the project or module means and why it is designed that way. Lead with the real subject, not repository ceremony. Use equations, diagrams, tables, examples, and commands only when they materially clarify the content.

Avoid generic feature lists, speculative claims, unexplained implementation dumps, forced paper headings, agent instructions, session history, and boilerplate sections that do not serve the reader. Engineering details are welcome when needed to reproduce, use, or correctly interpret the work, but they should not dominate a research README.

## Completion

Report only the files actually changed, the important stale or conflicting content corrected, and any unresolved decision requiring the user. Do not claim that documentation is current unless its concrete paths, commands, and contracts were checked against the project.
