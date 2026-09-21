# AGENTS.md Template

Use this as a structural contract, not as text to copy mechanically. Omit empty subsections in nested files, keep inherited project-wide rules at the root, and keep the complete file at or below 150 lines.

````markdown
# AGENTS.md

<A concise introduction to the project or subtree and the purpose of this guidance.>

## Project Structure

```text
<A focused tree of important files and directories. Choose depth by what an agent needs to navigate correctly.>
```

<Explain important files and directories with a compact list or table. State ownership and dependency boundaries here when they matter.>

## Development Style And Conventions

### <Technology Stack And Environment>

<Runtime, package manager, frameworks, environments, configuration sources, and constraints.>

### <Development Preference Or Practice>

<Stable conventions such as cleanup discipline, declarative configuration, API style, TDD, validation strategy, or compatibility policy. Add only categories the project actually needs.>

## Important Semantics

### <Implementation Or Research Contract>

<A concise operational statement that affects correct implementation or validation and may need maintenance as the project evolves.>

## Common Operations And Tools

<Verified commands, scripts, skills, analysis tools, evaluation entry points, and important safety notes.>
````

The section names express stable roles. Projects may use their natural language and locally clearer wording, but should preserve the distinction between structure, stable development conventions, evolving important semantics, and operations.
