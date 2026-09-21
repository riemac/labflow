# SVG and Inkscape for Scientific Composition

Use SVG/Inkscape when the figure needs precise vector composition, editable local geometry and labels, or assembly of material produced by different tools. It is especially useful for explanatory diagrams and teasers whose composition does not fit a simple flowchart. It is an option, not a compulsory replacement for a working draw.io, PPTX or scripted master. Choose it for a concrete improvement in local control or export reliability; it does not supply research taste automatically.

## Editing ownership

Keep SVG as the editable master. Give semantic objects stable IDs and arrange them in meaningful groups or layers, such as a reference geometry view, observed rollout frames, data panels, mathematical labels, connectors and annotations. A hand image and its annotation should be independently editable; a grouped explanatory unit can still move together. Do not confuse group membership with a scientific dependency. Inkscape supports nested groups and local object editing; the [grouping guide](https://inkscape-manuals.readthedocs.io/en/latest/grouping.html) describes those behaviors.

An agent can construct or revise SVG geometry and styles directly, then use the installed application for rendering/export. CLI export by object or region is also supported in the upstream [export tests](https://gitlab.com/inkscape/inkscape/-/blob/master/testfiles/cli_tests/CMakeLists.txt). This does not imply that every GUI operation has a matching command, or that native desktop control is available in the current agent environment. Inspect the installed version and help, then validate the required path with a small artifact before relying on it for the whole paper.

## Tested command-line workflow

On the tested Inkscape 1.4.4 host, use `inkscape --action-list` to discover actions; `--actions-list` is not the installed option. `--query-all` and `--query-id` expose rendered object bounds. `--actions` can select by ID, transform objects or groups, and export a separate copy. Some actions require `--with-gui`; this is a partial automation interface, not a promise that all interactive tools, dialogs and extensions work headlessly. Direct semantic SVG editing and CLI rendering complement each other.

The following operations were exercised on an isolated figure containing an unchanged recorded-image asset, an inline Matplotlib SVG panel and native SVG labels:

```bash
inkscape overview.svg --export-filename=overview.pdf
inkscape overview.svg --export-filename=preview.png --export-width=1600
inkscape overview.svg --query-all
inkscape overview.svg --actions='select-by-id:encoder_group;transform-translate:8,0;export-filename:candidate.svg;export-type:svg;export-do'
```

The source labels remained text after composition and group movement, and exported PDF fonts were embedded in that test. Rendered query coordinates and action distances are not necessarily the SVG viewBox coordinates: the tested physical-width/viewBox combination produced different numeric units. Inspect transforms and scale conversions before using a queried box as a source-coordinate edit. Do not promote a candidate merely because the command succeeded.

## Combine assets without changing evidence

Keep quantitative marks under the data script's ownership. Prefer vector exports for plotted lines, markers and text, while keeping the original data and transform source. Geometry views and real frames may remain raster images embedded in the SVG, with separate vector labels and arrows. Placing a raster image inside SVG or PDF does not make its contents vector or independently editable.

Changing annotation position should not require rerendering the physical scene. Retain camera, asset, model and time identity for the evidence-bearing layer. Cropping and masks must preserve the intended scientific subject and actual contact/geometry; generated illustrations or visual concepts must not become replacements for observed material. Inspect both the isolated subject boundary and the final page.

## Typography and mathematics

Use editable text for ordinary labels and preserve source expressions for mathematical content. Options include faithfully rendered mathematical vector assets or a PDF-plus-LaTeX export when it fits the manuscript build. Do not assume that typing a TeX expression into an ordinary SVG text node will typeset it. Group a mathematical asset with its semantic node, and keep its source expression for later corrections.

The [PDF export guide](https://inkscape-manuals.readthedocs.io/en/latest/export-pdf.html) distinguishes embedded fonts, text-to-path output and omitting text into a companion LaTeX file. Select the route according to editability, font licensing, searchability and the actual build. Keep editable text/source expressions even if a final export outlines some text. Inspect formula glyphs, hats, subscripts, baseline alignment and local spacing in the exported PDF; source validity and an attractive editor preview do not establish those properties.

A separate `--export-latex` test retained the source expression for a hatted density and a calligraphic loss, emitted a companion .pdf_tex file, and produced the intended mathematics after actual LaTeX compilation. The SVG editor alone still displays the source expression as text; inspect the compiled PDF when judging this route. Keep both companion files and the source together.

## Import compatibility

An SVG exported by another editor is not guaranteed to be a lossless native master. In an actual draw.io export test, the source contained 24 foreignObject nodes and repeated clip-path IDs; Inkscape reported unsupported foreignObject nodes, and the resulting PDF lost the two physical-hand images. Other text survived through fallback representations. This observation establishes a failed conversion for that file, not a universal cause or a rule that every draw.io SVG fails.

Inspect imported SVG for HTML foreignObject, duplicate IDs, clip/mask references, text represented as images or paths, and embedded-image behavior. Preserve the native master and compare the exported pixels before adopting a new editing backend. Do not silently strip clipping or unsupported elements to make validation pass: such changes can alter the scientific subject. Convert or rebuild the affected components deliberately in a candidate, then reinspect it.

## Reusable native-SVG export

Use [scripts/export_svg.py](../scripts/export_svg.py) for repeated native-SVG exports. It checks IDs, local image dependencies and internal references, preserves the source bytes and ordinary text, and creates a same-stem PDF plus preview.png. An explicit output directory keeps candidate exports away from the accepted artifacts. It rejects foreignObject rather than assuming HTML-based exported diagrams can be converted losslessly; use the original editor or a deliberately adapted candidate for those files.

```bash
python3 scripts/export_svg.py /path/to/overview/overview.svg --check-only
python3 scripts/export_svg.py /path/to/overview/overview.svg --output-dir /path/to/candidate
```

Resolve the script path relative to this skill. Successful validation/export covers the supported structural checks, not all SVG semantics or visual quality. Inspect any renderer diagnostics, the current preview, and the compiled paper page before accepting the result.

## Export and local-refinement loop

First settle a rough composition at the intended paper dimensions. Adjust subject scale and reading order, then route connectors, place labels/math, and refine the visual hierarchy. Render/export from the installed application, inspect normal-size and enlarged views, and change the smallest semantic group that needs repair. Compare with the accepted baseline before replacing it.

Preserve SVG when exporting PDF: the formats support different features, and repeated format conversion can lose information. Filters such as blurs or shadows may be rasterized; the export DPI affects those rasterized components rather than turning all vector marks into a higher-resolution drawing. Test fonts, clipping paths, masks, marker arrowheads, transparency, embedded images and any imported components in the actual PDF. The upstream export guide documents these distinctions; exact options and behavior should be checked against the installed version.

Place the exported figure into the real manuscript and recompile. Inspect the latest page, its caption and affected neighbors at the final column width. A locally corrected arrow can still collide after text reflow or become unreadable after scaling. Follow the separate visual-review and manuscript-review loop; do not certify a figure merely because Inkscape produced a valid PDF.

## How it complements other tools

Python remains useful for deterministic statistics and plots. Geometry-aware rendering remains useful for real assets, surfaces and spatial fields. draw.io remains useful for relation graphs and intentional connector structure. PPTX remains an option when office editing is a delivery requirement, with an actual target-suite round-trip test. SVG/Inkscape supplies fine vector arrangement and local control across those components. Avoid repeated SVG-to-PDF-to-PPTX-to-SVG conversions; retain one master for each component and a clear owner for the final composition.
