# labflow — GitHub Copilot & Agents Window Integration Development

Platform-specific guidance for editing the **GitHub Copilot** integration.
Cross-platform conventions (skill-first, bilingual, ability vs stage, tooling,
git hygiene) live in the thin entry [../AGENTS.md](../AGENTS.md); read that first.

## Product Shape

The Copilot integration is packaged as an **Agent Plugins 1.0** plugin located under `copilot/`. It supports both the **VS Code Agents Window** and **Copilot CLI**.

Model provider channels and credentials live in `/home/hac/labflow/provider/` as the repository-wide Single Source of Truth. Copilot consumes them through `copilot/scripts/sync-providers.mjs`.

Copilot surfaces (all under `copilot/`):

```text
copilot/
├── AGENTS.md                 # this platform-specific guidance
├── plugin.json               # Agent Plugins 1.0 manifest ($schema: agent-plugins.org/schemas/1.0.0)
├── mcp.json                  # Agent Plugins 1.0 MCP spec (pdf-reader, deepwiki)
├── scripts/
│   ├── sync-providers.mjs    # sync provider/ into VS Code chatLanguageModels.json & CLI
│   ├── doctor.mjs            # environment & provider diagnostic checker
│   └── use-provider.sh       # helper to export COPILOT_PROVIDER_* for CLI BYOK
├── com.github.copilot/
│   ├── agents/               # custom agent definitions (*.agent.md)
│   └── rules/                # research evidence and rigor instructions
└── skills/                   # portable/adapted skills
```

## Provider Synchronization (BYOK & Custom Endpoints)

Provider channels are decoupled from agent definitions. `provider/*.yaml` defines model capabilities and base URLs, and `provider/secrets.sops.yaml` holds encrypted keys.

### Synchronize to VS Code & Copilot CLI

Run the synchronizer to decrypt secrets in-memory and update your local configuration:

```bash
node copilot/scripts/sync-providers.mjs
```

This command:
1. Backs up existing `~/.config/Code/User/chatLanguageModels.json` (and `Code - Insiders`) with a timestamp.
2. Updates `chatLanguageModels.json` with `customendpoint` groups, preserving non-managed vendor configurations.
3. Automatically maps `thinking: true`, `supportsReasoningEffort`, `toolCalling: true`, `vision: true`, and token limits.
4. Updates `~/.copilot/providers.json` for Copilot CLI.

### Inspect Available Channels

```bash
node copilot/scripts/sync-providers.mjs --list
```

### Dry Run / Verify

```bash
node copilot/scripts/sync-providers.mjs --dry-run
```

### Run Copilot CLI with a Specific Custom Provider

```bash
source copilot/scripts/use-provider.sh routin-plan gpt-5.6-terra
copilot
```

## Multi-Agent Workflow in Copilot

1. **Context Isolation (Blindness Contract)**:
   - When conducting causal investigation (`learning-forensics`) or independent manuscript review (`paper-reviewer`), subagents run with isolated prompts without inheriting the coordinator's subjective history.
   - VS Code Agents Window provides native subagent context isolation and collapsible tool execution trees.
2. **Native Workbench Inspection**:
   - Intermediate research deliverables (PDF papers, MP4 rollouts, SVGs, diffs) open directly inside VS Code's editor panes, avoiding unnecessary format conversions.
3. **Dual Reviewer Symmetry**:
   - Two independent instances of `paper-reviewer` run concurrently (one focused on scientific reasoning, one on editorial/visual layout), returning structured conflict matrices to the coordinator.

## Diagnostics

Run the doctor script to verify system dependencies (`sops`, `age`), provider YAML integrity, and configuration synchronization:

```bash
node copilot/scripts/doctor.mjs
```
