# Visual Judgment and Publication Review

Visual quality is judged from the artifact a reader receives, not from effort, software, source validity, or the number of inspection calls. Use the criteria below to explain concrete decisions. They are not a point score, a fixed defect quota, or a universal aesthetic template.

## Three views of the actual output

**Page overview.** Inspect the rendered page as a composition. Locate the focal subject, the argument, the visual entry point, grouping, reading order, text/figure balance, and neighboring material. Check whether large blank regions or dense clusters are purposeful. A float on the expected page can still break the narrative, and a technically valid two-column layout can still be a poor reading experience.

**Normal reading size.** Inspect the figure at its final column/page width. Can the reader see meaningful differences, associate marks with legends, follow the main relationship, and distinguish primary from secondary information? The physical subject must remain visible rather than being dominated by an incidental background, object color, label, or decorative network box. A caption should enrich the figure, not rescue an unexplained asset collage.

**Enlarged detail.** Examine text, symbols, image boundaries, connector endpoints, intersections, alignment, and local spacing. Look for text touching or crossing lines, labels wedged between a box and arrowhead, accidental junctions, inconsistent dash semantics, mathematical font drift, baseline/subscript errors, rough masks, and truncated geometry. Return to normal size after repairs; shrinking everything is not a reliable cure for density.

Use PDF page rendering and focused evidence crops when available, and actually forward/view the returned images. Use a local rendering fallback when needed and state the limitation. Text extraction or embedded-raster extraction does not substitute for inspecting a vector page. Preserve page or crop locations for findings that require revision.

## Judge the kind of figure

### Teaser or visual abstract

State the intended visual proposition in a sentence, then inspect the figure before consulting its caption. Identify the scientific variation/problem, the distinctive idea or shared relationship, and the demonstrated outcome. A teaser need not include every module, every result, or all three items as separate panels; it must make the work recognizable and invite the reader into its argument.

Assess meaningful differences in subjects, visual focus, motion/process evidence where the task depends on change, and relationships between examples. Additional thumbnails alone do not repair an absent proposition. An available asset, training example, unseen input, and measured successful result are not interchangeable. Time sequences come from corresponding observations, not invented intermediate states.

### Method or learning diagram

Verify causal and learning relationships, not just the presence of named modules. Trace inputs, representations, predictions, target sources, losses, trainable parameters, and retained/frozen parts as applicable. Separate ordinary data, supervision, updates, and auxiliary training information with explicit semantics. A loss label is not a substitute for showing what is compared or learned.

Choose the smallest level of mechanism detail that explains the distinctive step. Generic optimization, implementation plumbing, and exhaustive side branches can conceal it. In geometric explanations, teach a representative relation before expanding to a large set; show a complete sampled set when distribution or coverage is the figure's purpose. These are task-dependent choices, not rules to always remove context or always reduce to one point.

### Result plot or table

Identify the scientific question answered by each panel or row. Make comparison, observation unit, population, axes, units, scales, thresholds, uncertainty, and missing data interpretable. Distinguish a learning trajectory from a branch, intervention, model-selection operation, or parameter average. Preserve failures and negative evidence. Independently sorted curves or different normalizations must not imply unsupported joint correspondence.

Place essential definitions beside their first use; use short captions and readable notes rather than packing qualifications into a title. A methods map can use internal section/figure/equation references where they strengthen the argument. An external comparison needs verified sources and matching dimensions. Citation decoration and implementation settings do not automatically earn main-text space.

## Revision discipline

Keep an author-accepted baseline. Compare revisions at the same publication size and explain what improved: proposition, visibility, hierarchy, relationship, or decoding effort. A tool migration is not an improvement by itself. Native text, vector math, plots, images, and 3D views may be combined with one clear editing owner for each component.

Repair data/semantic errors and substantive communication defects before claiming readiness. For debatable aesthetic preferences, explain the tradeoff and offer a concrete alternative when useful; do not inflate preference into a scientific flaw. Conversely, a central figure that fails to express the method is an editorial blocker, not a minor cosmetic issue merely because its numerical data are honest.

After revision, inspect the new figure export, its compiled page, and affected neighboring pages. A separate visual/editorial reviewer must judge the current artifact during a substantial manuscript workflow. Preserve unresolved findings and author decisions. A report's existence, a favorable adjective, or a self-assigned score is not evidence that visual problems were repaired.
