# Labflow OpenCode Configuration

This directory is the tracked source of truth for portable OpenCode configuration. The repository may remain public because provider credentials live only in `secrets.sops.yaml`, encrypted to the age recipients declared by the tracked root `.sops.yaml`.

## Files

- `defaults.yaml` contains portable OpenCode fields other than `provider` and `plugin`.
- `providers/*.yaml` contains one provider per file. The `config` mapping follows the OpenCode provider shape; the optional `auth` mapping names encrypted aliases and their request-time header or query placement.
- `plugins.yaml` contains third-party plugins that must be registered before the labflow plugin runs.
- `imagegen.yaml` contains named imagegen profiles plus configurable default and explicit ordered fallback routes.
- `secrets.sops.yaml` is created by explicit migration and must remain encrypted. `secrets.sops.example.yaml` documents only its pre-encryption shape.

The generated `~/.config/opencode/opencode.json` remains machine-local because its labflow `file://` URL contains the clone's absolute path. After migration it is a thin bootstrap containing only `$schema` and startup plugin registrations; the labflow plugin injects tracked defaults and providers with existing machine-local values taking precedence.

The tracked agent defaults disable OpenCode's built-in `explore` and `general` subagents and provide a portable model choice for labflow's unified `explore-worker`. User configuration may change that model or its reasoning options; tests derive expectations from the managed defaults instead of fixing one provider choice. The `learning-worker` intentionally leaves model selection to inheritance or user configuration.

Tracked startup plugins include `opencode-pty`, which exposes background PTY sessions after OpenCode restarts. Labflow global rules reserve long-running PTY ownership for the primary agent, while domain workers continue to use bounded shell commands unless an assignment grants a narrower exception.

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
