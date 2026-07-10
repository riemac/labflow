---
name: imagegen
description: Use when the user explicitly asks to generate an explanatory image, concept diagram, architecture sketch, scientific visual, lab-meeting illustration, or raster bitmap asset through the labflow imagegen custom tool. Especially useful when terminal text or LaTeX would be less clear than a visual explanation. Do not use for deterministic SVG/Mermaid/code-native diagrams unless the user wants a generated bitmap.
---

# Imagegen

Generate concise explanatory raster images for research discussion, design communication, and lab-meeting visuals through the labflow `imagegen` custom tool.

This skill is intentionally narrower than Codex's built-in `imagegen`: OpenCode has no hosted image tool here, so generation goes through labflow's custom tool, backed by `node /home/hac/labflow/opencode/scripts/imagegen.mjs`. The CLI reads an independent image generation profile from repo-local `opencode/labflow.json`, optional ignored `opencode/labflow.local.json`, optional `~/.config/opencode/labflow.json`, or `OPENCODE_IMAGEGEN_*` environment variables, with legacy fallback to `provider.openai.options`. The profile can use either OpenAI-style `images` API or `responses` API.

## When To Use

- The user explicitly asks for a generated image.
- A concept, architecture, mechanism, or experiment design would be clearer as a picture than as terminal text.
- The user needs an intuitive lab-meeting figure, slide visual, conceptual schematic, or teaching diagram.
- The output should be a raster asset (`png`, `jpg`, `webp`), not a deterministic source diagram.

## When Not To Use

- The user needs exact graph topology, exact equations, or a reproducible diagram source; prefer Mermaid, SVG, TikZ, or code.
- The visual is a small edit to an existing repo-native vector/SVG asset.
- The user is asking for implementation, debugging, or literature evidence rather than a visual explanation.

## Visual Style For Research Explanations

- Prefer clear mechanism over decoration: few objects, strong spatial grouping, readable arrows, and generous whitespace.
- Use short labels instead of long paragraphs. Image models often corrupt dense text and exact formulas.
- For math-heavy ideas, represent equations as symbolic blocks such as `Q`, `K`, `V`, `softmax`, `loss`, or `reward`, and explain exact math in the chat response.
- For neural architectures, show data flow left-to-right or top-to-bottom with consistent color coding.
- For robotics or physics ideas, show coordinate frames, contact points, object state, action arrows, and failure modes when relevant.
- For lab meetings, make the image self-contained: title banner, 3-5 labeled regions, and a visual legend if needed.

## Workflow

1. Identify the teaching goal: what should the viewer understand in 5 seconds?
2. Extract only the necessary context from the current conversation.
3. Convert the user's request into a concrete visual spec:
   - subject and scene;
   - layout and reading order;
   - key labels;
   - color coding;
   - constraints and things to avoid.
4. Call the `imagegen` custom tool once by default.
5. Use defaults unless there is a reason to change them:
   - `model`: `gpt-image-2` unless configured otherwise;
   - `size`: `3840x2160` for 4K landscape explanatory diagrams;
   - `quality`: `high` for the default discussion/slide figure, `medium` for faster normal use, `low` for quick drafts;
   - `outDir`: `figures/imagegen`.
6. If you need to inspect or reason about the generated image, read the output path returned by the tool so OpenCode attaches it as an image.
7. After generation, report:
   - saved path;
   - final prompt;
   - model, size, and quality;
   - any caveat about text/equation fidelity.

## Prompt Pattern

Use a compact prompt like this, adapting labels to the user's research context:

```text
Create a clean scientific explanatory diagram for <topic>.
Purpose: help a researcher understand <core mechanism> during discussion or a lab meeting.
Layout: <left-to-right / top-to-bottom / panel structure>.
Elements: <objects, modules, arrows, coordinate frames, tokens, losses, rewards>.
Labels: use only short labels: <label list>.
Style: crisp vector-like educational illustration, high contrast, white or very light background, no clutter.
Avoid: dense paragraphs, exact long equations, decorative stock-photo elements, watermark, unreadable tiny text.
```

## Tool Guidance

- Call the `imagegen` tool with a final prompt. Do not route through `/imagegen`; labflow no longer installs that slash command.
- Set `size` to `3840x2160` by default for high-resolution slide-ready conceptual diagrams.
- Use `2048x1152` only when speed matters but a landscape slide aspect ratio is still desired.
- Use `1024x1024` for quick square drafts.
- Set `quality` to `high` by default for discussion figures; downgrade to `medium` or `low` only when speed matters.
- Set `out` when the user gives a stable asset path; otherwise let the tool create a timestamped filename under `figures/imagegen`.
- Portable defaults live in repo-local `opencode/labflow.json` under `imagegen`.
- Machine-local secrets or overrides belong in ignored `opencode/labflow.local.json`; do not put API keys in tracked files.
- Optional machine-wide overrides can live in `~/.config/opencode/labflow.json`, and environment overrides can use `OPENCODE_IMAGEGEN_*`.
- If the tool fails because configuration is missing, ask for an Image API key/base URL rather than guessing from the chat provider.

## Output Style

- If the user speaks Chinese, summarize in Chinese.
- Keep the final explanation short; the image is the main artifact.
- Do not claim the generated image is mathematically exact. If exactness matters, pair it with a code-native diagram or text derivation.
