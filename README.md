# labflow

Labflow is a personal research workflow toolbox for Codex, OpenCode, and Copilot. The platforms share useful scientific contracts while serving different work: OpenCode carries the coding agents; Codex keeps its native primary agent and adds focused research evidence skills for papers and document work; Copilot leverages the VS Code Agents Window and CLI.

## Research Evidence

`literature-forensics` investigates a bounded mechanism or novelty question through prior art, counterevidence, primary-paper verification, and explicit reading depth. `learning-forensics` investigates failed learning behavior through sealed factual cases, independent causal lenses, and discriminating probes. Both separate researcher-facing reports from hidden audit material, and keep the dossier layouts and portable helpers compatible across platforms.

Dedicated `literature-worker` and `learning-worker` subagents gather evidence asynchronously, while `paper-editor` provides bounded author-side narrative and terminology advice. The primary continues independent work, verifies decisive claims, and owns scientific synthesis and manuscript edits. Same-lane follow-ups reuse the worker while its handle remains available; dossier artifacts provide recovery when a host session cannot be resumed. A learning blind round starts without the primary's conversation history.

`pdf-read` supplies page and region provenance for scientific PDFs, including vector figures, captions, and tables. The PDF reader MCP exposes reading, searching, and evidence operations; available OCR and region-analysis providers depend on the deployment. `external-research` routes official documentation, public repository evidence, papers, and web sources through appropriate tools, including ctx7 and DeepWiki.

`paper-writing` coordinates evidence-backed claims, narrative, figure placement, page budgets, and revision correspondence while keeping local edits lightweight. `scientific-figures` covers scientific encodings, statistics, units, target print size, editable masters, and tool choice across scripts, draw.io, PPTX, images, and 3D. Substantial manuscript and key-figure work follows production, rendered self-inspection, two independent PDF-only reviews, revision, and same-reviewer verification. Two instances of the same `paper-reviewer` role focus on scientific reasoning and visual/editorial judgment, each with its own report and continuation. Visual taste includes the figure's proposition, focal subject, hierarchy and learning semantics as well as legibility; a successful render or completed report is not acceptance.

Codex's host skills handle Word, presentations, spreadsheets, PDF production, image generation, and general Deep Research when available. Labflow does not duplicate those production workflows or install a replacement primary agent. Native Plan Mode remains available. Other independent skills cover codebase research, scientific brainstorming, annotation, Git task flow, documentation maintenance, and explicit Obsidian operations.

OpenCode additionally maintains Develop, Plan, and Paper primary agents, profiled configuration, image generation, and explicitly activated Autopilot. See [opencode/AGENTS.md](opencode/AGENTS.md) for its implementation and [opencode/config/README.md](opencode/config/README.md) for configuration.

## Layout

```text
provider/
├── *.yaml
└── secrets.sops.yaml
codex/
├── .codex-plugin/plugin.json
├── .mcp.json
├── agents/
│   ├── learning-worker.toml
│   ├── literature-worker.toml
│   ├── paper-editor.toml
│   └── paper-reviewer.toml
└── skills/
opencode/
├── agents/
├── config/
├── plugins/
└── skills/
copilot/
├── plugin.json
├── mcp.json
├── com.github.copilot/
└── scripts/
```

The `main` branch contains all peer platform integrations.

## Codex Install And Reload

From this repository:

```bash
codex/skills/self-update/scripts/reload_labflow_plugin.sh
```

The helper refreshes the local marketplace and plugin cache, then installs managed regular copies of the four tracked custom workers (`learning-worker`, `literature-worker`, `paper-editor`, and `paper-reviewer`) into `~/.codex/agents/` (or `CODEX_HOME/agents`). It resolves the newest cache version containing the reviewer skills before injecting and validating their actual `SKILL.md` paths for `paper-reviewer` only; `paper-editor` retains the author-side writing skill. It converts only legacy symlinks pointing to exact source files, and preserves user-owned or modified managed files using a checksum ledger. Manual plugin installation does not install those global worker files; the skills document a native-worker fallback.

The helper uses `codex` from `PATH`. To test with the App's bundled executable on this Linux installation:

```bash
LABFLOW_CODEX_BIN=/usr/lib/chatgpt/resources/codex codex/skills/self-update/scripts/reload_labflow_plugin.sh
```

Start a new session after reload so the complete skill and custom-role catalog is refreshed. No Labflow stage hooks or HUD are installed.

The plugin configures the PDF reader through `npx @sylphx/pdf-reader-mcp` and DeepWiki through its HTTP MCP endpoint. Litnav is an independently installed CLI for scholarly metadata, citation graphs, PDF retrieval, and bibliography export. ctx7/find-docs handle library documentation when installed. Runtime tool capabilities should be checked before relying on optional providers.

## Codex Worker Models

The native `explorer`, `default`, and other general workers use the personal `config.toml` subagent defaults. Dedicated research roles set their model and reasoning effort in the tracked TOML sources and are installed through the reload helper.

| Worker | Model | Reasoning effort |
| --- | --- | --- |
| Native general workers, including `explorer` | `gpt-5.6-luna` | `max` |
| `learning-worker` | `gpt-5.6-terra` | `max` |
| `literature-worker` | `gpt-5.6-terra` | `max` |
| `paper-editor` | `gpt-5.6-terra` | `max` |
| `paper-reviewer` | `gpt-5.6-terra` | `max` |

These are user-selected settings. Global defaults are stored under `[agents]` as `default_subagent_model` and `default_subagent_reasoning_effort`; they are personal configuration, not installed by the plugin helper. The primary omits runtime model overrides and starts independent workers without a full-history fork. No custom `explore-worker` is installed.

## Example Requests

- “用 literature-forensics 查证这个机制有没有先例，并找最强反证。”
- “用 pdf-read 核验这篇论文的图 3 和相邻结论。”
- “用 external-research 查官方接口和版本变化。”
- “用 learning-forensics 调查这次训练的失败原因。”
- “用 paper-writing 梳理这篇论文的证据链和版面预算。”
- “让 paper-editor 检查术语、相关工作定位和段落论证，并给出候选措辞。”
- “用 scientific-figures 检查图 2 的统计、单位和印刷可读性。”
- “给 paper-reviewer 一份 PDF 和领域标准，做一次独立首审。”

Skills can also be selected when the request matches their documented scope. Worker contracts and static helper tests support the workflow, but actual research conclusions and visual deliverables still require source verification and user review.
