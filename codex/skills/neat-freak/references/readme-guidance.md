# README Writing Guidance

A README is a human-facing explanation, not an agent rulebook. Its structure should follow the subject rather than a universal template.

## Research And Algorithmic Modules

Use a natural conference-paper flavor when it helps: establish the problem and motivation, define the object of study and notation, explain the method or decomposition, state invariances and contracts, present evidence or validation boundaries, and connect the components into a coherent argument. Do not force Abstract, Related Work, Method, and Experiments headings when the module is not a paper.

Prefer precise claims over promotion. Distinguish implemented behavior, experimental contracts, candidates, and future work. Explain equations, frames, units, tensor shapes, assumptions, counterexamples, and evaluation criteria where they determine interpretation.

## Engineering Projects

Explain what the system does, how its important pieces fit, how a person uses it, and which constraints matter. Installation, configuration, commands, architecture, and troubleshooting belong only when they help the intended reader. Avoid a generic badge-and-feature-list README when a coherent technical narrative is clearer.

## Root And Nested README

- A root README introduces the complete project and provides the reading or usage path into its major components.
- A nested README explains the local module's subject and boundary. It should not restate the entire repository or copy parent prose.
- Link to deeper material instead of duplicating it, but keep enough local context that the README remains understandable.

## Style

- Write complete, fluent paragraphs and use the project's research language.
- Use headings that reflect the actual argument or system, not compulsory boilerplate.
- Use tables for exact mappings, diagrams for structure or flow, equations for formal contracts, and lists for genuinely parallel items.
- Keep engineering detail subordinate to the scientific or practical explanation in research-heavy modules.
- Remove stale implementation claims, historical session narration, agent-facing instructions, and unsupported novelty or performance claims.
