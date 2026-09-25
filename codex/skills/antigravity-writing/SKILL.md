---
name: antigravity-writing
description: "Use Antigravity's Gemini when useful for substantial writing, including papers, reports, and defense materials: independent drafts, polishing complete arguments, expanding LaTeX TODO outlines, and editorial advice."
---

<scope>

Decide whether to involve Gemini based on the manuscript's current stage. Gemini proposes wording, structure, and narrative; Codex organizes material, maintains the paper's intent, integrates drafts, and verifies scientific content.

</scope>

<handoffs>

Use the following approaches individually or alternate between them within the same manuscript.

Give each assignment a short writing brief: who will read it, what they should understand afterward, the passage's role in the larger argument, and relevant material or style examples. Identify settled claims and evidence alongside wording, paragraph order, and narrative choices that remain open.

## Polish a complete argument

Give Gemini the existing prose, intended reader, tone, and claims to preserve. Ask it to improve the writing and briefly explain changes that could affect meaning.

## Read the project and draft independently

Let Gemini read relevant project files, author annotations, and the target section, then develop a draft from its own understanding. Codex compares the result with the original material and the paper's overall argument to select useful writing.

When seeking a different narrative approach, provide original material and the writing goal first; introduce an existing draft during comparison.

## Expand a LaTeX paragraph outline

Codex can arrange the paragraph sequence and use LaTeX TODO comments to describe each paragraph's role, claim, evidence, transitions, and open questions before asking Gemini to expand it. Preserve the intent of existing author annotations and resolve the TODOs individually during integration.

Invite Gemini to assess whether the outline serves the reader and explain worthwhile changes to the paragraph arrangement.

## Editorial advice

Ask Gemini for comments on structure, logical transitions, clarity, or tone before deciding how to revise.

</handoffs>

<session>

## First invocation

On first use in the current session, run `agy -h` to learn the installed CLI's usage. Use `agy models` to inspect available models; prefer `gemini-3.8-flash-high` unless the user specifies another model.

Send one turn with `agy --model MODEL --output-format json -p PROMPT`. Read candidate prose from a successful result's `response`, and record `conversation_id`, working directory, model, and manuscript identity.

For independent drafting, run in the relevant project directory and identify the priority source paths and target section. Ask Gemini to return candidate prose; Codex checks the project files and output before integration. Polishing existing prose may need only the relevant passage and its context.

## Reuse the conversation

Continue related revisions from the same directory with `--conversation ID`. Keep concise material and writing-decision notes to support continuation across days.

Base revisions on the currently adopted draft. After Codex or the user changes a candidate, send the updated passage and the next revision goal back to the same conversation so both collaborators work from the same version.

</session>

<review>

## Verify and integrate

Identify verified facts, untested ideas, source locations, terminology, citations, and output format at handoff. Codex checks Gemini's arguments, citations, equations, LaTeX labels, and author annotations, then compiles or renders as the manuscript requires. Bring consequential questions of scientific meaning or authorial taste to the user for review.

Preserve wording and rhythm that pass review, making local corrections to specific problems. Send substantial prose revisions back to Gemini with concrete feedback.

## Target revisions

Locate feedback in a passage and describe the intended reading effect, such as: "In paragraph two, explain the applicable conditions before introducing our method; retain the current strength of the conclusion." Address the remaining problems that affect meaning or reading, and finalize when the current writing goal is met.

</review>
