# Narrative and Terminology Pass

This reference supports an author-side pass on scientific argument, paragraph structure, terminology, and related-work positioning. It is generic guidance: the manuscript, explicit author intent, venue requirements, and verified sources determine the final choice.

## Choose the pass

For a local grammar, punctuation, or consistency correction, edit the smallest unit that fixes the problem and preserve the author's defined terms, symbols, citations, and voice. Do not turn an obvious copy edit into a manuscript-wide rewrite.

For a narrative pass, identify the intended reader, research question, central claim, evidence, qualification, and job of the affected section or paragraph. For a terminology pass, identify the object being named, its scope, neighboring terms, and the decision the word must support. For a related-work pass, identify the comparison axis and the evidence required for each positioning statement.

Use `paper-editor` for a bounded author-side reading when the task benefits from a separate editorial perspective. The editor returns recommendations and candidate prose to the primary; the primary owns manuscript edits, scientific decisions, and author communication.

## Evidence map

Keep these layers separate while reasoning:

- Author intent: the meaning, emphasis, audience, and accepted terminology the author states or annotates.
- Manuscript evidence: claims, definitions, equations, figures, tables, citations, and limitations already present in the draft.
- Local implementation: read-only code or configuration consulted only when the manuscript leaves a technical meaning unresolved.
- External evidence: opened primary papers, standards, official definitions, or venue guidance that establishes usage or context.
- Historical notes: earlier names, deprecated meanings, or research lineage that should not silently become a current claim.

Distinguish measurements, interpretations, limitations, historical statements, and editorial proposals in the reasoning. Explain consequential differences in the editorial rationale without tagging every sentence or filling the manuscript with bookkeeping. If evidence cannot support stronger wording, narrow it or leave the choice with the author.

## Narrative pass

1. Write the paragraph's question in plain language. A reader should be able to tell what uncertainty, comparison, or mechanism the paragraph resolves.
2. State the paragraph's main claim before its supporting detail unless the intended rhetorical order requires a delayed reveal. Tie every important claim to the evidence that supports it.
3. Give each sentence one job: establish context, define an object, state a method, report a result, interpret an observation, qualify a claim, or transition to the next question.
4. Remove steps that describe implementation history when they do not help the reader understand the research argument. Preserve details needed to interpret the method, result, reproducibility, or limitation.
5. Keep a qualification beside the claim it constrains. Distinguish what was measured from what is inferred and what is proposed for future work.
6. Check section transitions: the last sentence should close the current question or expose the next one, and the next paragraph should answer the question the transition creates.

For a larger change, propose the section or paragraph order before supplying polished prose. Offer a conservative rewrite that preserves the current claim and a stronger alternative only when the supplied evidence supports it. Explain the semantic change, evidence assumption, and cost in page space for each meaningful alternative.

## Terminology pass

Build a small term map for affected text: preferred term, definition, scope, aliases, symbol or abbreviation, first-use location, and nearby terms that could be confused with it. Use one stable term for one object unless the distinction is scientifically intended. Keep an acronym only when it reduces repeated load for the intended reader.

Before changing a term, ask whether the change would alter the object, operation, population, time point, evaluation setting, or strength of the claim. A smoother synonym is unsafe when it changes one of those dimensions. Preserve established mathematical notation and explain a notation change separately from a prose change.

Search and open authoritative sources when the term's field convention, historical meaning, related-work placement, or claim strength is uncertain or consequential. Read definitions in context, nearby caveats, relevant method or results pages, and the source's date or version when it matters. Record the source, locator, and exact proposition that supports the recommendation. A search hit, a familiar phrase, or a count of exact matches is only a candidate lead.

Known conventional words and straightforward local copy edits need no ceremonial per-word search. Spend source effort where a terminology choice could mislead the reader, change a technical claim, or affect how prior work is compared.

When sources disagree, describe the competing conventions and choose a local definition that prevents ambiguity, or present two wording options for the author. Do not manufacture a field consensus. Distinguish historical terminology from the current usage adopted in the manuscript.

Do not copy internal class names, variable names, experiment identifiers, or repository labels into a paper without checking what scientific object they denote. Prefer a reader-facing term and state the implementation identifier only when reproducibility requires it and the author has approved that level of detail.

## Related-work positioning

Describe a paper by the mechanism, data or task setting, supervision, evaluation, and claim that the source actually supports. Classify a comparison as an exact match, close analogue, setting analogue, background, or counterexample when that distinction affects the argument. State the comparison axis before saying how the present work differs.

Avoid global novelty statements such as “the first” or “no prior work” unless a separately bounded, auditable search supports the exact scope; even then, prefer a qualified description of what was found. Do not turn a missing search result into evidence that a method is absent from the literature. Preserve negative, contradictory, and historical evidence when it changes the positioning.

For every consequential positioning sentence, record the source or evidence supporting the shared premise, the difference being claimed, and the boundary of the comparison. If that chain is incomplete, return a narrower candidate sentence and identify the missing verification.

## Return format

An author-side report should contain:

1. The understood reader, research question, author intent, and affected text.
2. The current narrative or terminology issue and its scientific consequence, if any.
3. The proposed section, paragraph, sentence, or term structure.
4. Candidate wording alternatives, with symbols and citations preserved.
5. A short explanation of the evidence and semantic tradeoff for each consequential alternative.
6. Opened source references with page, section, figure, or stable URL locators when external evidence was needed.
7. Unresolved author choices, missing evidence, and the smallest next decision.

Label recommendations as proposals. Keep the report bounded to the requested text and return manuscript changes to the primary for application and verification.

## Boundary

The supporting `paper-editor` role does not directly edit manuscript files, assign an acceptance grade, or launch the two-reviewer production loop. The primary may apply authorized edits while using this reference. Substantial manuscript or key-figure work follows the main `paper-writing` workflow after the author and primary decide that the broader loop is needed.
