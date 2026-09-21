# Figure Workspaces and Reproducible Analysis

Organize a growing paper's figures by scientific topic rather than transient figure number. A topic may remain useful after leaving the paper. Keep current exports, components, exploratory candidates and deprecated versions distinguishable; preserve old material rather than silently overwriting a better accepted design. Adopt this organization when creating or explicitly reorganizing a project, not as permission to move files during an unrelated writing task.

## A topic directory

A useful layout for an SVG-owned figure is:

```text
figures/
  overview/
    overview.svg
    overview.pdf
    preview.png
    assets/
      geometry.png
      topology.svg
      performance.svg
    candidates/
    deprecated/
```

The SVG is the editable composition master, the PDF is the manuscript artifact, and preview.png is a view of the current output for inspection. Assets contain the material actually needed to edit or rebuild the composition. Create candidates/deprecated subdirectories when they contain meaningful alternatives; avoid a large empty scaffold. Use relative asset paths inside a portable figure bundle, or explicitly documented shared inputs when copying a frozen dataset would obscure its identity.

Do not infer the master from the extension. A draw.io-owned diagram retains its .drawio master; a data figure retains its data and generating script; a TeX-owned drawing retains its TeX source. Their exported SVG can support local inspection or editing without becoming the authoritative source automatically. Declare that ownership in an existing project index or concise asset manifest. Do not wrap a PNG in SVG and label it a fully editable master, or run a historical initialization script over an accepted manually refined master.

Keep ordinary labels as text in the working master and use semantic IDs and named layers/groups for components a person may adjust. Preserve mathematical expressions even where a rendered formula uses vector paths. A separate outlined delivery copy may be needed for a specific export; it must not replace the editable source. Imported vector components need unique IDs and preserved references, dimensions and styles. A linked SVG image is still a linked component; inline editable objects require importing its vector structure, not merely placing its filename in an image element.

## Analysis modules

Group scripts by actual responsibility, such as assets, geometry, SSL, RL and validation, and keep a small number of visible rebuild/build entry points. Share path resolution or plotting utilities only where there are real users; do not create a framework merely to reorganize files. Large frozen data packages, local environments and generated previews need different ownership and lifetime from source modules.

Keep manuscript-root and data-root resolution independent of the caller's working directory. A module move changes what __file__.parents refers to and can break bare imports, subprocess calls, default outputs, documentation commands and tests. Use a small common path module or explicit entry-point arguments, stable package imports, and a clear module-invocation convention. Honor explicit output directories so validation can write to a scratch area rather than replace the paper's accepted figures.

Separate frozen-data rendering from evidence extraction, model inference, simulation and training. A figure rebuild should not secretly reload a model or restart an experiment. Expose those operations separately with the project's authorization boundary and required environment. Shared analysis dependencies should be declared rather than accidentally inherited from unrelated packages.

## A lossless migration

Before moving an existing collection, inventory the actual consumers and save a recoverable baseline, including dirty work that is not in Git. Include original bytes of input metadata as well as hashes when an old entry point might write to them. Map every old figure path, master, wrapper and source script to its new location. Determine which copies are current, candidate or deprecated from references and provenance; equal file hashes do not justify silently discarding the history.

Move the current artwork without redrawing it. Update LaTeX inputs, image paths, script imports, subprocess targets, default output locations and active documentation together. Inspect relative SVG/HTML dependencies and embedded-asset behavior. Keep a small old-to-new path map where historical records need resolution. Preserve historical reviews, frozen data, provenance and recorded commands as historical evidence; write a new current manifest rather than rewriting their identities to pretend they were produced under today's layout.

Inspect legacy entry-point code before invoking help: a script without an argument parser can ignore --help and execute its main task. First establish a side-effect-free help/dry-run contract; run unknown or changed entry points against copied inputs and temporary outputs, with before/after hashes. Run focused tests and representative frozen-data renderers with temporary output paths, then compile the manuscript using the project archive policy. For a path-only migration, compare the rendered pages with the archived PDFs; identical page pixels establish unchanged appearance, not improved appearance. Recheck data hashes and confirm deprecated material remains accessible. A later visual redesign needs its own design and review loop.

## Manuscript versions

Follow the project's explicit version and archival naming rules before replacing a compiled manuscript. The version associated with an existing PDF may differ from the newly edited repository VERSION; retain that identity or identify it explicitly. Preserve the preceding PDF once per logical build, append the required serial when a filename is already occupied, and never overwrite an old archive. Keep this separate from repeatedly running the compiler's internal passes. If an editor can automatically compile after source edits, capture the preceding PDFs before making those edits. Successful compilation does not imply author visual acceptance.
