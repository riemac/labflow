# Labflow Model Providers

This directory is the **Single Source of Truth** for model channels, endpoints, and credentials across Labflow.

## Separation of Concerns

- **`provider/` owns only the model channels**:
  - Base URLs, protocols (`openai-compatible`, `responses`, `messages`).
  - Model catalog: model IDs, context window limits, output limits.
  - Model capabilities: `tool_call`, `reasoning`, `attachment`, `modalities`.
  - SOPS-encrypted API keys and authentication bindings (`secrets.sops.yaml`).
- **Platforms independently assign models and reasoning effort**:
  - **OpenCode**: Managed under `opencode/config/defaults.yaml` and `opencode/agents/*.md`.
  - **Copilot**: Managed under `copilot/com.github.copilot/agents/*.agent.md` and user settings.
  - **Codex**: Managed under `codex/agents/*.toml` and personal `config.toml` (native GPT models).

## Files & Modules

- `*.yaml`: One YAML configuration per provider (e.g., `routin.yaml`, `lucoo.yaml`, `openai.yaml`).
- `secrets.sops.yaml`: SOPS-encrypted API keys (AES-256-GCM via `age` recipient public keys declared in root `.sops.yaml`).
- `secrets.sops.example.yaml`: Example plaintext structure for initial setup and bootstrapping.
- `index.mjs`: Self-contained domain module exporting `SecretStore`, `loadProviders()`, and credential resolution utilities.
- `package.json`: NPM module manifest (`@labflow/provider`).

## Programmatic API

```javascript
import { loadProviders, SecretStore, resolveModelBinding } from "./provider/index.mjs"

// Load all provider channel definitions
const providers = await loadProviders()

// Decrypt and cache SOPS credentials in memory
const store = new SecretStore()
const apiKey = await store.get("routin-grok")
```

## Supported Clients

- **OpenCode**: Consumes `provider/index.mjs` directly in `opencode/scripts/config.mjs` to inject in-memory credentials without fake symlinks.
- **Copilot / VS Code Agents Window**: Synchronized into `~/.config/Code/User/chatLanguageModels.json` and `~/.copilot/providers.json` using `node copilot/scripts/sync-providers.mjs`.
