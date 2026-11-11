---
name: stage-driven-research
description: >-
  Meta-skill for bootstrapping stage-driven research notebooks. Use when initializing a new Research/ Obsidian vault for a project, or scaffolding a new experimental stage within an existing one. After initialization, daily agent behavior is driven entirely by the generated nested AGENTS.md files; this skill is not invoked again.
---

# Stage-Driven Research

A meta-skill that generates research notebook scaffolding once per project. Afterwards the nested `AGENTS.md` hierarchy inside `Research/` governs all agent behavior for experiment recording and scientific-state tracking.

## Philosophy

### Stage-driven development

Scientific research — particularly in robotics, robot learning, and sim-to-real transfer — progresses through bounded experimental campaigns rather than continuous incremental commits. Each campaign targets a specific research question, accumulates evidence through reproducible experiments, and concludes with a retrospective that crystallizes what was learned.

**Stage-driven development** formalizes this rhythm:

1. **Stages are bounded campaigns, not calendar periods.** A stage begins when a research question is posed and ends with a `STAGE-REVIEW.md` that distills findings. Stages may overlap in calendar time but remain logically independent.
2. **Runs are the atomic evidence unit.** Every experiment — successful, failed, or diagnostic — is recorded as a run card with reproducible metadata (code commits, entry commands, artifact paths, dirty-worktree flags). Run cards are self-contained fact sources.
3. **The MAP captures scientific state evolution.** Significant runs earn a `node_id` in their YAML frontmatter, promoting them to nodes in a Mermaid DAG (`MAP.md`). The MAP encodes causal parentage and ablation relationships — it is a scientific state graph, not a timeline.
4. **Promotion is selective.** A run becomes a MAP node only when it crosses a capability gate, changes a mechanistic judgment, redirects the mainline, or provides lasting negative evidence. Routine checkpoints and smoke tests stay as plain runs.
5. **Dependency flows one way: runs → MAP.** Run cards never back-reference node IDs or MAP links. Deleting or restructuring the MAP must never damage run card semantics.
6. **Templates are co-designed per stage.** Different stages involve different research modalities (RL training, 3D reconstruction, sim-to-real, asset generation…). When entering a new stage, the agent and user collaboratively design a stage-specific run-card template grounded in the base template but adapted to the stage's metrics, artifacts, and evaluation protocols.

### The research notebook

The `Research/` directory is an Obsidian-compatible vault that separates personal ideation from reproducible experimental evidence:

- **Personal notes** (`总体/`, `进展/`, etc.) are user-maintained; the agent treats them as read-only context.
- **`stages/`** is the human-machine co-maintained zone where experiments are recorded, scientific state is tracked, and stage-level retrospectives are written.

Within each stage directory, experiment records (runs) and the scientific semantic graph (MAP) coexist as a single self-contained unit — there is no separate "graph" directory. A run card's YAML frontmatter optionally carries node metadata, unifying the experiment fact source with its graph identity.

## Generated structure

```text
<workspace>/
├── .agents/skills/stage-research/
│   └── SKILL.md                         # Minimal project-level skill stub
│
└── Research/
    ├── AGENTS.md                        # Top-level: format, read/write boundaries, Codex directives
    └── stages/
        ├── AGENTS.md                    # Stage-level: directory layout, run-card schema, MAP rules
        └── <stage_name>/               # Created later by daily agents per campaign
            ├── README.md                # Stage background and research question
            ├── MAP.md                   # Stage scientific state DAG (Mermaid) + index
            ├── template/
            │   └── run-card.md          # Stage-specific run-card template (co-designed with user)
            ├── runs/                    # 01-name.md, 02-name.md, …
            ├── supplementary/           # Short probes, cross-run analysis (optional)
            ├── plans/                   # Experiment plans (optional)
            ├── assets/                  # Figures, evidence artifacts (optional)
            ├── scripts/                 # Plotting or analysis scripts (optional)
            └── STAGE-REVIEW.md          # Retrospective upon stage closure
```

## Initialization workflow (Executed Once)

1. Create `Research/` and `Research/stages/` at the target location.
2. Copy [research-root-agents.md](./references/templates/research-root-agents.md) to `Research/AGENTS.md`, then fill in project placeholders (`{{PROJECT_NAME}}`, `{{CODE_REPO}}`).
3. Copy [stages-agents.md](./references/templates/stages-agents.md) to `Research/stages/AGENTS.md`, then fill in placeholders (`{{PROJECT_NAME}}`).
4. Copy [project-skill-stub.md](./references/templates/project-skill-stub.md) to `.agents/skills/stage-research/SKILL.md`.
5. Confirm the generated structure with the user. **Initialization is complete; this meta-skill is not invoked again.** Subsequent stage creation, run logging, and MAP maintenance are handled autonomously by daily agents following the local `AGENTS.md` files.

## Reference templates

| Template | Purpose | Target in Project |
| --- | --- | --- |
| [research-root-agents.md](./references/templates/research-root-agents.md) | Top-level vault rules, formatting & Codex directives | `Research/AGENTS.md` |
| [stages-agents.md](./references/templates/stages-agents.md) | Stage conventions, MAP DAG & cluster spec | `Research/stages/AGENTS.md` |
| [project-skill-stub.md](./references/templates/project-skill-stub.md) | Minimal project-level skill stub | `.agents/skills/stage-research/SKILL.md` |
