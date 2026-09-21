---
name: paper-writing
description: Shape, revise, and review scientific manuscripts when evidence, claims, figures, narrative, or page budget must work together. Use for papers, theses, reports, rebuttals, and revision letters; keep small edits lightweight.
---

<paper_writing>

<purpose>
Use this skill when a scientific manuscript, thesis chapter, technical report, rebuttal, or revision response needs its claims, evidence, narrative, figures, and space to agree. Natural language is the normal entry point.
</purpose>

<argument>
Start with the research question, the central explanatory idea, the evidence that supports it, and the intended reader. Organize methods and experiments around that argument rather than the order in which modules were implemented. Preserve the author's scientific meaning and voice; distinguish measurements, interpretations, limitations, and proposed work. Do not invent data, citations, or completed validation.

Align the abstract, section order, paragraph transitions, equations, figures, captions, and conclusions with this evidence chain. Give each visual a distinct job. A teaser communicates the problem, distinctive idea, and demonstrated capability; a method figure explains relationships and learning; a result figure answers an empirical question. Keep essential qualifications beside the claims they constrain, define evaluation support in the protocol, and collect broader limitations coherently. Avoid turning the manuscript into repeated caveats, implementation settings, or audit records.
</argument>

<narrative_and_terminology>
For a terminology, related-work, or paragraph-level argument pass, first state the reader, research question, claim, evidence, and job of the affected text. Use `paper-editor` for bounded author-side advice when available; it may read explicit author notes, annotated PDFs, local read-only implementation, and opened primary sources, then return structure and candidate prose without editing the manuscript or notes. Search and open sources when a term or positioning choice is uncertain or consequential, and distinguish historical usage, current evidence, local convention, and proposal. Read [references/narrative-and-terminology.md](references/narrative-and-terminology.md) for the detailed pass and return format. Keep known conventional wording and simple copy edits lightweight.
</narrative_and_terminology>

<scope>
Use a direct edit for a local wording correction. For substantial manuscript revision, key-figure redesign, or an explicitly requested publication/revision workflow, the production and review loop below is required. Internal submission means a handoff to reviewers, not authorization to upload to a conference, email someone, or publish. Keep records in the existing task state; a new process framework or dossier is not required.
</scope>

<production_and_review_loop>

<step number="1">
Produce a coherent candidate. Preserve an editable baseline and the author's accepted visual direction. Resolve the core argument and key figures before spreading a new style across the manuscript. Under long-running authorization, make ordinary decisions autonomously while retaining their rationale; an approved plan does not make an inferior figure acceptable.
</step>

<step number="2">
Inspect the rendered result yourself. Follow the project's version/archive policy before overwriting a compiled manuscript, retaining the prior PDF's actual version identity. Open the exported figures and compiled PDF. Inspect whole-page composition, normal reading size, and enlarged details. Assess the argument and visual hierarchy as well as labels, mathematical typography, connectors, legends, cropping, and collisions. Compare changed key figures with the accepted baseline. Fix production defects before internal submission; a successful build, source hash, or image-view count is not a design verdict.
</step>

<step number="3">
Submit one fixed PDF candidate to two independent reviewers. Start two fresh `paper-reviewer` instances with no inherited author history: one with scientific focus and one with visual/editorial focus. Each receives only the same PDF and the domain/review standard, including its focus. Preserve the candidate identity and both handles. The visual review is a required result, not an optional paragraph that can disappear behind missing-experiment findings.
</step>

<step number="4">
Adjudicate and revise. Read both original reports. Decide which requests to implement, clarify, contest with reasons, or record as needing new evidence. Reviewer recommendations are evidence, not authority over the author or the argument. A reproducibility concern may call for a concise protocol and a separate implementation reference, not an indiscriminate parameter table in the main text. Preserve data and scientific boundaries while making the prose and visuals more effective.
</step>

<step number="5">
Recompile, reinspect, and return to both original reviewers. Give each the revised PDF and a response to its own report; each must verify its fixes on the actual new pages. Recheck page/figure references, changed neighboring layouts, and newly introduced defects. A response letter or edited source alone does not close an issue.
</step>

<step number="6">
Continue where work remains. Repair unresolved in-scope scientific-expression and visual defects and repeat the relevant inspection/review. Do not stop because reports exist or a checklist is green. Separate research evidence still unavailable from craft that can be repaired now; do not chase an acceptance score through unauthorized experiments. State remaining scientific gaps and author visual acceptance separately from verified production work. After a final edit, re-render affected pages; reopen review for a material change to a key figure, argument, or evidence.
</step>

</production_and_review_loop>

<references_and_tools>
Read [references/narrative-and-terminology.md](references/narrative-and-terminology.md) for the author-side narrative and terminology pass, and [references/review-correspondence.md](references/review-correspondence.md) for phase allowances, the two review streams, responses, and stopping decisions. Initial and fresh-final reviewers exclude prior reviews, author dialogue, source code, and notes. Same-reviewer resubmission may retain the original/revised PDFs, its own report, its response letter, and allowed formal correspondence. Verify actual startup context rather than assuming that an asynchronous dispatch is blind.

Use the host's document, PDF, presentation, spreadsheet, image, and research skills for their native production capabilities. This skill coordinates the scientific argument and editorial decisions; it does not reproduce those APIs. For figure construction and visual judgment, route to `scientific-figures`.
</references_and_tools>

</paper_writing>
