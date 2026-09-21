# Scientific Figure Methods

This is evolving practice for turning scientific evidence into an effective figure. Use the main [skill](../SKILL.md) for the working contract, [visual-review.md](visual-review.md) for inspection, and native tool guidance for current APIs. The examples below support judgment; they are not mandatory layouts, a software shopping list, or a scoring rubric.

## Establish the figure brief

Infer a short brief from the manuscript and verified material: what the reader should understand; what must appear; what misunderstanding must be avoided; which real material is available; and the intended physical width/height. Include the observation unit, comparison, population, units and uncertainty when those determine the message. Ask the author only when a consequential scientific choice cannot be resolved from the authorized context. Under autonomous authorization, choose ordinary layout and styling details yourself.

A broad claim such as “the model is better” is insufficient for composition. Identify the relationship that makes it assessable: a shared interface across different subjects, a prediction compared with a target, a response to an intervention, or a distribution of outcomes. Every main panel should contribute to this relationship. Implementation completeness is a different objective; do not draw every known module unless each one is needed for understanding.

## Learn from references and compare compositions

Actually inspect a few relevant reference figures and the author's accepted baseline. Note what is transferable: subject scale, consistent viewpoints, stage separation, a local enlargement, correspondence across examples, or a restrained visual hierarchy. Read enough of the reference caption to understand its scientific encoding. Borrow organization rather than copying another paper's assets, claims or decorative motifs. A folder of images without a design reading is not a useful reference library.

For an important teaser or overview with unsettled composition, compare a few low-cost layouts with different information order and focal emphasis. Examples include subjects with a small mechanism inset, examples connected by a shared relationship, or a local physical mechanism connecting two scales. Recoloring the same diagram does not test an alternative composition. Select the strongest direction within the agreed scope before polishing; routine curves with a settled comparison can proceed directly.

Reference analysis and candidate selection are author-side design work. A design critic can see a brief and alternatives; an independent blind manuscript reviewer receives only the phase-permitted PDF and standard. Have the latter describe what the actual figure communicates, then let the primary compare that account with the intended proposition. Do not give the blind reviewer the desired interpretation to make the figure seem clearer.

## Iterate at the right level

Begin with the main relationship, subject sizes and reading order. Refine grouping, connector routing, text and mathematical labels before spending effort on final imagery or color. A grayscale draft can expose weak structure that polished assets conceal. Use genuine observation units and representative data early when statistics or geometry determine the layout; do not invent intermediate states for visual smoothness.

Resolve the main figure before spreading its visual language across a manuscript. Make small reversible changes and compare with the accepted baseline at the same final width. Preserve what already works. When repeated edits produce no improvement, return to the proposition or information order instead of cycling through colors and decorative styles. The author should not have to detect that a wholesale redraw lost the original figure's useful hierarchy.

Design for the actual column or page width. Text and line weights scale with the figure, so a large source canvas says little about final readability. Inspect the exported figure and latest compiled page at overview, normal reading size and enlarged detail, then check neighboring material. The complete visual inspection and revision criteria live in [visual-review.md](visual-review.md); a successful export or editable source is not an aesthetic verdict.

## Teasers and visual abstracts

A teaser should make the work recognizable and worth reading before the caption explains all details. Choose the scientific difference/problem, distinctive relationship and demonstrated capability needed for that proposition. They can form an integrated scene, a compact sequence or a comparison; they do not require three equal panels or a complete network diagram.

Two correct subjects side by side can establish a comparison, but do not automatically explain a shared representation or controller. Use an evidenced correspondence, common path, aligned state or compact mechanism cue to make the intended relationship visible. Additional thumbnails do not repair an absent proposition. Keep the important physical differences visible: a vivid manipulated object, oversized title or decorative box can draw attention away from them.

Show change when change is the evidence. A real short sequence, matched states or a well-supported motion annotation may communicate an operation better than an isolated pose. Preserve the identity and temporal correspondence of recorded material. Do not depict an available asset, training input or unseen design as a successful control outcome without the corresponding evaluation. Concept generation can help explore arrangement, but final experimental subjects and trajectories must come from verified material.

## Method overviews and geometric explanations

Trace the distinctive mechanism before arranging boxes. Identify the inputs, representation, predictions, target sources, losses, trainable parameters, retained/frozen components and auxiliary training information that affect interpretation. Show what each loss compares and what it trains; a decorative loss symbol is insufficient. Use explicit, consistent semantics for data, supervision and parameter updates. A line into a critic can carry data even though the critic is only used during training.

Choose detail according to the figure's job. Adding all policy, value and optimizer modules can turn a readable overview into implementation plumbing; omitting a necessary dependence can also make the method wrong. Give the teaser, method diagram and experiment different primary jobs, linked by common terminology and visual meanings rather than repeated pipelines.

For geometry, decide whether the reader needs to understand one physical relation or inspect a distribution. A representative point/anchor/axis relation with controlled context or a local enlargement may teach the construction; a full sampled set may be necessary for coverage or sampling provenance. Neither choice is universally right. Preserve actual coordinates, material-point identity, geometry and axis semantics. Highlight only the relations being explained, and make every emphasized connector interpretable.

Use faithful mathematics with retained source expressions. Check hats, subscripts, italics, baseline alignment and spacing after export. Prediction, target, loss, derivative and update are different scientific objects even when their notation is related. Avoid substituting plain Unicode approximations for proper math simply because the editor accepts them. The tool may compose a rendered mathematical vector asset with editable labels, but the original expression must remain recoverable.

## Experimental plots and tables

Choose the mark type after defining the question and observation unit. Curves reveal change along an ordered quantity; distributions expose heterogeneity and tails; scatter plots preserve paired observations; matrices reveal structured coverage and missing combinations; tables support precise values and sparse categorical distinctions. These are starting points, not compulsory mappings. A familiar plotting style cannot decide which relationship deserves a figure.

Make axes, units, populations, comparison, aggregation and uncertainty interpretable. Distinguish variability over assets from variability over seeds or trajectories. Give a plotted point a stable meaning. Keep scales comparable where comparison requires it, and explain intentionally different scales. Preserve missing observations, infeasible cases and measured failures as different states when they affect interpretation. Keep selection, weighting and normalization reproducible from the data.

A connected line implies ordering and often continuity. Independent seeds, continuation branches, interventions, parameter averaging and model selection are not one ordinary learning trajectory. Show lineage or operation boundaries with separate traces, marks or panels; retain unsuccessful branches and avoid fabricated smooth transitions. A wall-clock budget, aggregate GPU time and number of interactions are also different quantities and require the appropriate labels.

For spatial predictions, distinguish the reference geometry from predicted values displayed on or near it. Keep target/prediction/error scales honest and state the sampling domain. An attractive representative case and a population statistic have different support. Do not independently rescale or smooth predictions to make them resemble a target. When errors are small, a labelled residual panel or adjacent residual table may reveal them without distorting the main comparison.

A main-text table must answer a question the reader needs at that point. Exact optimizer and simulator settings may belong in implementation detail rather than occupying space intended for empirical evidence. Retain essential protocol locally and move secondary details only where the venue permits; do not make the submission depend on unavailable supplementary material. Methods maps may use internal section/figure/equation links; comparisons to other works require verified external sources. Citation decoration does not fix a redundant table. Check the actual template before judging small-caps captions as a format error.

## Tool selection and layered production

Choose the tool by the dominant evidence and editing need. Keep one source owner for each component and one owner for final composition. A geometry view, data plot, mathematical label and annotation layer need not come from the same application. Moving a label should not require rerendering the hand or regenerating the whole figure.

| Need | Useful owner | Boundary and verification |
| --- | --- | --- |
| Curves, distributions, uncertainty, coverage | Python plotting and deterministic data/transform scripts | Preserve raw/derived data and statistical meaning; export vector marks when useful and inspect actual paper size. |
| Relationship graphs and learning flow | draw.io/XML | Keep editable nodes and intentional edges; validate the structure, then judge the preview and exported PDF. See [drawio-strategy.md](drawio-strategy.md). |
| Free vector composition and precise local refinement | SVG, optionally edited/rendered with Inkscape | Stable IDs and semantic groups help local edits; preserve SVG and test text, formulas, images and PDF export. See [svg-inkscape.md](svg-inkscape.md). |
| Author-facing office composition | PPTX | Use editable labels/groups and suitable imported components; test the actual WPS or other target-suite export before promising compatibility. |
| Dense mathematics or manuscript-native diagrams | LaTeX/TikZ/PGF or faithful math/vector assets | Preserve expressions and inspect glyphs, baselines and final scaling; native mathematical source does not guarantee good composition. |
| Real geometry, surface fields, point clouds, camera views | Simulation replay or a geometry-aware renderer | Preserve assets, values, coordinate/camera settings and observation identity; add vector explanation separately when useful. |
| Non-precise conceptual imagery or composition exploration | Image generation or illustration tools | Identify it as illustrative; never manufacture experimental geometry, contacts, trajectories or predictions. |
| Final layout judgment | Actual figure export and compiled-PDF render | Inspect the delivered artifact, not only the source or an earlier image. |

Useful combinations include scripted plots inside a relational schematic, recorded/3D material with a vector annotation layer, and LaTeX-rendered math inside an editable SVG or draw.io composition. Prefer a small workflow with clear ownership over a chain of conversions. Placing a raster in SVG, PPTX or PDF does not make its content vector. Preserve the final annotation layer rather than claiming the original plotting script alone reproduces a later edited image.

PPTX is a possible composition canvas, not a prescribed presentation aesthetic. Use paper dimensions and scientific relationships instead of automatically adopting large slide titles, decorative cards or sparse slide copy. Inkscape and draw.io offer different editing strengths; neither automatically supplies taste. Specific WPS round-trips, font substitution, editor exports and version-dependent commands remain unverified until tested on the intended host. Use native tool guidance and current documentation for those details.

## Lessons to retain and revise

The observed failures behind this guidance were an unexplained pair of otherwise correct rendered hands, loss of hierarchy after adding policy/critic detail, prediction/target/loss ambiguity, a branching training history presented like one curve, an implementation table given main-text space without enough scientific purpose, and an editable file mistaken for a finished figure. Each suggests a concrete question about the next artifact; none is a universal ban on pairs of subjects, critic nodes, tables or a particular tool.

Keep project-specific terminology, semantic colors, line meanings, camera choices and physical dimensions in the existing project style source or task record. Preserve accepted figures as practical comparison material. During authorized workflow maintenance, revise advice when observed artifacts change the judgment: record the useful repair and scope, distinguish tested behavior from a tool option, and replace stale or redundant guidance instead of accumulating a session diary. Keep project conclusions in the project and native APIs in their tool documentation.
