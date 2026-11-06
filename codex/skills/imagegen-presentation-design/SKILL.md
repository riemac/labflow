---
name: imagegen-presentation-design
description: Develop and iterate presentation layouts with the host's image generation tool, then reconstruct the chosen design as an editable deck using verified original material. Use for uncertain visual direction, weak image-text relationships, reference-driven redesign, or an explicit image-first presentation workflow; not for simple copy edits or a standalone generated image.
---

<scope>

Use image-based exploration when it can materially improve a presentation's composition, not for every slide edit. Follow the user's intended audience, existing template, approved design constraints, and desired degree of editability. Use the host's presentation skill and tools for authoring, rendering, and delivery; this skill adds a design and critique loop rather than replacing those workflows.

Use the host's built-in image-generation capability when available and follow its applicable instructions. Honor a requested model when the host exposes that choice; do not claim an undisclosed model version or silently switch to an API, CLI, or credentials. If the necessary capability is unavailable, state the limitation and use another authorized approach.

</scope>

<brief_and_iteration>

Inspect the existing slides, user comments, and original evidence. For each page, identify its purpose, essential material, relationship between text and figures, current defect, and shared deck constraints. Label image inputs by role: the current slide is the redesign target, an accepted slide is a style reference, and a paper figure, photograph, or video frame is source material. Do not treat a style reference as factual evidence.

Generate a page-level visual candidate that solves the identified composition problem. Reuse established visual rules while allowing each page to fit its content: meaningful grouping, reading order, image-label proximity, local emphasis, and purposeful spacing matter more than repeating one template. Do not make the specific colors, dashed frames, shapes, or typography of a past project into universal rules.

Inspect the candidate against the brief. In a subsequent image-generation turn, target the remaining visible issue or a coherent set of related issues and restate what must stay fixed. Adopt the stronger elements, record why others were rejected, and stop when a reviewable design has been reached or iterations stop improving it. Proceed independently within the user's authorization; final aesthetic acceptance belongs to the user.

Keep the prompts, generated-image locations, selection decisions, and any factual corrections in the task's build or working directory. Read [imagegen-prompts.md](references/imagegen-prompts.md) when a prompt structure or focused revision example would help.

</brief_and_iteration>

<reconstruction_and_validation>

Treat the generated image as a layout proposal. Rebuild the chosen design with editable presentation objects for text, labels, connectors, and other requested elements; do not deliver a flattened screenshot in place of an editable deck. Keep actual photographs, videos, experimental screenshots, and research figures from their original sources. When the user requests a paper figure or dense result graphic itself, preserve it as a replaceable, crop-capable media object rather than redrawing it solely for editability; editable annotations may be placed around it.

Verify every figure, number, denominator, formula, result, caption, and claimed relationship against the original material, version-locked experimental data when applicable, or user-confirmed evidence. Image generation can alter fine text and scientific meaning; its content is not evidence. Preserve the distinction between simulations and real-world results, shown examples and aggregate statistics, and unsuccessful and successful cases. Do not introduce fabricated measurements, motions, or scientific diagrams.

Render and inspect every changed final slide at a readable size. Compare the reconstructed page with its selected candidate and the user's reference for hierarchy, grouping, image-text relationships, emphasis, whitespace, consistency, cropping, and text fit. Fix concrete defects and check embedded media and source notes as required by the task. Report actual application-level testing and any relevant playback limitation; automated layout or package checks do not establish visual quality or the user's acceptance.

</reconstruction_and_validation>
