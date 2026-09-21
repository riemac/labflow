# Labflow OpenCode Configuration

This directory is the tracked source of truth for portable OpenCode-specific configuration (`defaults.yaml`, `plugins.yaml`, `imagegen.yaml`).

Model provider channels and encrypted secrets live centrally in `provider/` (`provider/*.yaml`, `provider/secrets.sops.yaml`) as the repository-wide Single Source of Truth. OpenCode directly consumes `@labflow/provider` in memory.

## Files

- `defaults.yaml` contains portable OpenCode fields other than `provider` and `plugin`.
- `plugins.yaml` contains third-party plugins that must be registered before the labflow plugin runs.
- `imagegen.yaml` contains named imagegen profiles plus configurable default and explicit ordered fallback routes.

The generated `~/.config/opencode/opencode.json` remains machine-local because its labflow `file://` URL contains the clone's absolute path. After migration it is a thin bootstrap containing only `$schema` and startup plugin registrations; the labflow plugin injects tracked defaults and providers with existing machine-local values taking precedence.

The tracked agent defaults disable OpenCode's built-in `explore` and `general` subagents and provide portable model choices for labflow's `explore-worker` and `learning-worker`. User configuration may change those models or their reasoning options; tests derive expectations from the managed defaults instead of fixing one provider choice.

Tracked startup plugins include `opencode-pty`, which exposes background PTY sessions after OpenCode restarts. Labflow global rules reserve long-running PTY ownership for the primary agent, while domain workers continue to use bounded shell commands unless an assignment grants a narrower exception.

The tracked Goal plugin is pinned to the tested release. Its `/goal` command intentionally omits an `agent` override, so Build, `labflow-develop`, and `labflow-paper` retain their current primary-agent identity; `plan` and `labflow-plan` remain held by the plugin's `restrictedAgents` safety gate.

Goal defaults permit up to 1000 automatic continuations and 40 active hours with a deliberately non-binding 100-million context-token ceiling, while retaining the five-second cooldown and child-session gate. `sessionTitleStatus` is enabled so the current objective, turn count, active duration, and context budget remain visible in the session title.

When a machine-local Goal/PTY fork is active, `~/.config/opencode/labflow-plugin-overrides.json.goalOptions` is the runtime-authoritative layer over the tracked Goal defaults copied into the bootstrap tuple. Keep `maxTurns`, `maxDurationMs`, and `maxTokens` there so a stale bootstrap cannot silently restore upstream limits; per-Goal values explicitly approved in a Plan may still override these defaults. The local fork also accepts `maxGoalTextCharacters` as a unified limit for the objective, success criteria, and constraints in the static Goal block injected into model requests.

## High-Fidelity Compaction

Labflow replaces the built-in compaction system prompt and fixed request template. The English `../agents/compaction.md` is the sole runtime prompt; `compaction_CN.md` is a Chinese discussion companion and is never registered or loaded. Model and reasoning choices remain under `config.agent.compaction` in `defaults.yaml`; an inline `prompt` does not override the managed English contract.

The shared XML containers adapt to research, engineering, and general work. Complex, sustained discussions can receive paper-length reconstructions rather than terse outlines; completed topics retain their meaningful trajectory, and completed work is not rewritten as a next action. The abstract starts directly with prose. Other headings describe the actual subject, not the container's purpose; the goal can separate the overarching topic from a distinct current-stage objective. The model chooses language and internal structure, and omits containers with no substantive content. Literal XML examples and code remain distinguished from active output containers.

Optional text-native diagrams in the understanding body serve the receiving agent's continued reasoning, not presentation. They can make processes, dependencies, branches, or conceptual relationships explicit without requiring rendering, a fixed diagram format, or an additional output container. Qualifications and supporting arguments remain available in the accompanying text.

The compaction hook supplies the latest successful prior summary from the current session. OpenCode normally summarizes only an older prefix and replays its retained recent tail separately. Labflow's immediately following message transform adds that recent context to the disposable compaction input as well, so the summary can reconcile old plans with later completion records. Existing messages are not duplicated in this input, and native verbatim replay and its retention boundary remain unchanged. The extra input uses the same native serialization and tool-result truncation as the prefix. The temporary snapshot is session-scoped and cleared after consumption, on idle/deletion/disposal, or before a retry; it is not a persistent memory store.

A first compaction needs no prior summary. Read failures, an unidentifiable active boundary, or an unmatched compaction input stop that compaction explicitly, without replacing history or silently returning to the built-in template. Retry after restoring session access.

For the receiving model, the message transform prefixes successful summary text with a fixed `context_checkpoint` notice: this is reconstructed history from the same session, not a new user request; newer messages update its state, and only unfinished, authorized work should continue. The notice exists only in the request copy. Stored/exported summaries and the prior-summary text used for subsequent compaction remain unchanged.

Compaction API requests set `maxOutputTokens` to `min(64000, model.limit.output)` when the model declares a valid positive limit, or `64000` otherwise. Native OpenAI OAuth is the explicit exception: its subscription endpoint rejects `max_output_tokens`, so that route leaves the limit to the service. OpenAI API-key and other provider routes retain the explicit budget. This does not change other agents and is a request budget rather than a promised body length; reasoning may consume part of it. Existing trigger settings, recent-history retention, and native tool-result truncation remain unchanged.

Changes load after restarting OpenCode; no installer rerun is needed. Validate registration with `opencode debug agent compaction`, run `node --experimental-strip-types --test tests/compaction.test.mjs` from `opencode/`, and use an isolated session to check actual compaction and provider behavior.

## Security Model

Provider secrets are decrypted lazily in memory. The plugin injects a custom AI SDK `fetch` closure that replaces sentinel authentication immediately before a request; decrypted values are never inserted into the resolved OpenCode config, written to temporary files, or logged. `install.sh --doctor` decrypts the alias set and fails if `opencode debug config` contains any managed plaintext value.

Each device owns an independent age private identity, normally `~/.config/sops/age/keys.txt`, with mode `0600`. Git stores only public `age1...` recipients. A new device cannot decrypt until an existing authorized device adds its recipient and rewraps the SOPS data key.

## First Migration

Install `sops`, `age`, and `age-keygen` from their official releases or operating-system packages. The installer checks these commands and prints links, but never invokes sudo or downloads binaries.

```bash
./opencode/install.sh --init-age
./opencode/install.sh --migrate-config
./opencode/install.sh --doctor
```

`--migrate-config` is explicit, creates a mode-`0700` timestamped backup under `~/.config/opencode/labflow-backups/` containing the global config, existing managed config, and SOPS policy, then extracts file/env/literal provider credentials directly into SOPS through stdin. Validated managed YAML, ciphertext, policy, and the thin bootstrap are installed as one rollback transaction. Migration does not delete legacy key files; remove them manually only after testing the migrated providers.

## New Device

```bash
git clone <repository>
./opencode/install.sh
./opencode/install.sh --init-age
```

Copy the printed `age1...` recipient to an already authorized device, then run this there and commit the resulting `.sops.yaml` plus rewrapped ciphertext:

```bash
./opencode/install.sh --authorize-age-recipient age1...
git add .sops.yaml opencode/config/secrets.sops.yaml
```

After the new device pulls that commit, run `./opencode/install.sh --doctor` and restart OpenCode.

## Imagegen Selection

An explicit profile attempts only that profile. `defaultRoute` selects the normal ordered route; change it between `openai-pro-first` and `relay-first` without editing tool code. The Codex profile receives the current ChatGPT OAuth credential from OpenCode's auth-loader hook and calls the hosted image-generation tool directly; it never reads `auth.json` or persists the token. A route falls back only for definitive authentication/availability failures, network failures, HTTP 408/429/5xx, `model_unavailable`, or `no_available_channel`. Ambiguous post-send timeout fallback is disabled unless the route explicitly enables `fallbackOnAmbiguousTimeout`.

```bash
node opencode/scripts/imagegen.mjs generate --list-profiles
node opencode/scripts/imagegen.mjs generate --route openai-pro-first --prompt "..."
node opencode/scripts/imagegen.mjs generate --route relay-first --prompt "..."
node opencode/scripts/imagegen.mjs generate --profile lucoo-gpt-image-2 --prompt "..."
node opencode/scripts/imagegen.mjs generate --route preferred --prompt "..."
```
