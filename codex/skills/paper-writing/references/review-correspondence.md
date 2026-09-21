# Independent Reviews and Revision Correspondence

For substantial manuscript work, use the required production → internal submission → two independent reviews → revision → reinspection/resubmission loop in `paper-writing`. Keep it in native task orchestration, without a stage runtime or a new dossier framework.

## One candidate, two independent streams

Freeze a specific PDF revision before dispatch. State its edition and review scope: an eight-page submission must stand on the material it contains, while a supplied extended draft may have a different intended scope. Do not silently treat an extended appendix as available to a submission-only review. Use one `paper-reviewer` instance with scientific focus and another with visual-editorial focus; no model override is needed because the role owns its configuration.

Each first reviewer receives only the same PDF and domain/review standard, with the focus included in that standard. The scientific reviewer concentrates on the argument, correctness and evidence. The visual/editorial reviewer must inspect the teaser, method figures, results and actual page design in their own right, then verify against the complete text. Both actually view every supplied page. The visual report must not disappear behind generic missing-experiment findings.

Keep a compact mapping in the existing task state: PDF path/revision identity, scientific handle, visual handle, original reports, per-stream responses, revised PDF, and verification status. Separate viewing coverage from design judgments. Images successfully reaching vision input prove that inspection was possible, not that it was good.

## Phase allowances

| Phase | Reviewer instance | Allowed manuscript materials |
| --- | --- | --- |
| Initial | Fresh, no inherited author history | Current PDF and domain/review standard only |
| Resubmission | Same instance for that stream | Original/revised PDFs, its own report, response to that report, and allowed formal review correspondence |
| Fresh final, when requested or needed | New instance | Current PDF and the same domain/review standard only |

Keep the two initial/fresh-final streams independent: no other reviewer report, author discussion, preferred redesign, external critique, source code, project notes or memory. An outside expert report is valuable author-side material; do not feed it to a purported fresh blind reviewer or convert its suggestions into universal skill rules. In same-reviewer resubmission, remembering its own review and the permitted response is expected context, not contamination.

The role's disabled author skills, memory settings and zero project-document budget are defense layers. Start from a clean coordinator root with project-document and memory injection disabled where supported, a separate working directory, and native no-history children. Inspect actual startup content and I/O. A generic global collaboration/formatting block may remain without becoming manuscript evidence; project-specific author content requires discarding that instance's blind judgment. Prompt constraints are not complete filesystem isolation.

## Author adjudication

Treat each review as evidence to reason about. Preserve the actual observation and decide whether to implement, clarify, partly address, or contest the request. Explain conflicts with author intent, accepted visual direction, the scientific question, or another review. Do not mechanically expand the main text because a reviewer requested details: decide which conditions are essential to interpreting the experiment and where complete reproducibility material belongs.

For each substantive point preserve:

`review observation → interpretation → action or reasoned response → revised location → actual verification → remaining issue`

A research change alters method, data, analysis or claim scope and needs evidence. An expression change improves argument, organization or wording. A visual change improves encoding, hierarchy, composition, typography, local clarity or figure semantics. A visually compelling figure must keep its scientific meaning. Necessary limitations belong beside constrained claims and in a coherent scope/limitations account, without taking over every caption and paragraph.

## Return to the original reviewers

Recompile and inspect before sending the revision. Give each original reviewer the revised PDF and its own response letter with updated page/figure/equation locations. A moved figure may affect several pages; review the neighboring reading flow, not only the cropped repaired symbol. If a handle is unavailable, recover only the phase-allowed correspondence into a clearly identified replacement; do not silently call it the original reviewer or give it author-side notes.

Every claimed repair needs a finding on the actual revised artifact. A report with no visual inspection, missing key-figure judgments, or inaccurate locators is an incomplete review: continue that reviewer to finish the assigned inspection rather than treating the report's existence as closure. Do not prescribe the verdict or force agreement with another reviewer.

## Closure and remaining work

Continue revising in-scope scientific-expression and visual defects. Missing experiments may remain explicitly unresolved without preventing a well-crafted reading draft, when the user has allowed that boundary. A key figure still requiring redesign does prevent claiming visual completion. Do not chase Accept, remove honest failures, or create extra experiments to clear a review score.

Separate: artifact produced; author self-inspection; scientific review status; visual/editorial review status; and author acceptance. The author's rejection of a delivered figure is new evidence requiring revision, not a dispute settled by a prior 'passed' checklist. An unresolved aesthetic preference should be presented with concrete alternatives when an author decision is useful; routine arrow, spacing and notation repairs remain the agent's work.

After the last edit, inspect affected rendered pages and check cross-references. Return material changes to a key figure, argument or evidence to the relevant reviewer; minor copy corrections can be verified locally and recorded. Keep original reviews, replies and unresolved research needs, but do not put routine provenance/check bookkeeping into the paper itself.

## Runtime validation

Reload the complete plugin and managed worker installation, then use a new session to test actual role loading, skill exclusion, blind context and same-handle continuation. A fresh visual/editorial review of a previously rejected but unmodified PDF can test whether the new contract identifies communication defects without receiving the expected findings. A separate synthetic before/after document can test whether the same reviewer recognizes actual visual repairs without continuing to invent defects. Keep expectations and outside critiques out of reviewer input.

Judge these tests from the rendered-artifact findings and observed behavior, not just TOML parsing or keyword presence. A successful fixture demonstrates bounded behavior on that material; it does not guarantee aesthetic judgment on all future papers.
