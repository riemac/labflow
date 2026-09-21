#!/usr/bin/env node


import * as fs from "node:fs/promises"
import * as path from "node:path"
import { fileURLToPath } from "node:url"
const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url))
const COPILOT_DIR = path.resolve(SCRIPT_DIR, "..")
const REPO_ROOT = path.resolve(COPILOT_DIR, "..")

import { loadProviders, SecretStore, PROVIDER_DIR } from "../../provider/index.mjs"

const VSCODE_USER_DIRS = [
  path.join(process.env.HOME, ".config", "Code", "User"),
  path.join(process.env.HOME, ".config", "Code - Insiders", "User"),
]

// Convert provider definition into VS Code Custom Endpoint groups
function buildVSCodeCustomEndpoints(providers, secrets) {
  const groups = []

  for (const p of providers) {
    const config = p.config || {}
    const auth = p.auth || {}
    const baseURL = (config.options?.baseURL || "").replace(/\/+$/, "")
    if (!baseURL) continue

    const isAnthropic = config.npm === "@ai-sdk/anthropic" || p.id.includes("claude")
    const isResponses = baseURL.includes("/responses") || p.id === "routin-plan"
    const apiType = isResponses ? "responses" : isAnthropic ? "messages" : "chat-completions"

    // Group models by their specific auth secret
    const secretModelMap = new Map()
    const modelsObj = config.models || {}

    for (const [modelId, modelDef] of Object.entries(modelsObj)) {
      const binding = auth.models?.[modelId] || auth.default
      const secretAlias = binding?.secret
      const rawApiKey = secretAlias ? secrets[secretAlias] : undefined

      if (!rawApiKey) continue
      const apiKey = rawApiKey.replace(/^Bearer\s+/i, "").trim()

      const key = `${secretAlias}:::${apiKey}`
      if (!secretModelMap.has(key)) {
        secretModelMap.set(key, { secretAlias, apiKey, models: [] })
      }

      // Determine model endpoint URL
      let modelUrl = baseURL
      if (apiType === "responses") {
        if (!modelUrl.endsWith("/responses")) modelUrl = `${modelUrl}/responses`
      } else if (apiType === "messages") {
        if (!modelUrl.endsWith("/messages")) modelUrl = `${modelUrl}/messages`
      } else {
        if (!modelUrl.endsWith("/chat/completions")) modelUrl = `${modelUrl}/chat/completions`
      }

      // In VS Code customendpoint, properties marked secret: true (like group.apiKey)
      // are resolved strictly via SecretStorage (${input:chat.lm.secret...}).
      // Setting requestHeaders on each model allows Copilot's UM endpoint handler
      // to supply the proper Authorization/x-api-key directly on every request.
      const requestHeaders = apiType === "messages"
        ? { "x-api-key": apiKey, "Authorization": `Bearer ${apiKey}` }
        : { "Authorization": `Bearer ${apiKey}` }

      secretModelMap.get(key).models.push({
        id: modelId,
        name: modelDef.name || modelId,
        url: modelUrl,
        toolCalling: Boolean(modelDef.tool_call),
        vision: Boolean(modelDef.modalities?.input?.includes("image")),
        thinking: Boolean(modelDef.reasoning),
        contextWindow: modelDef.limit?.context || 128000,
        maxOutputTokens: modelDef.limit?.output || 16384,
        supportsReasoningEffort: ["low", "medium", "high", "xhigh", "max"],
        reasoningEffortFormat: apiType === "responses" ? "responses" : "custom",
        requestHeaders,
      })
    }

    // Create a provider group for each key
    let subIndex = 1
    const totalSubGroups = secretModelMap.size

    for (const { secretAlias, apiKey, models } of secretModelMap.values()) {
      if (models.length === 0) continue

      const groupName = totalSubGroups > 1
        ? `${config.name || p.id} (${secretAlias.replace(/^(routin|lucoo)-/, "")})`
        : (config.name || p.id)

      groups.push({
        name: groupName,
        vendor: "customendpoint",
        apiType,
        apiKey,
        models,
      })
      subIndex++
    }
  }

  return groups
}

// Update chatLanguageModels.json preserving non-managed vendor entries
async function syncVSCodeFile(userDir, newEndpoints, dryRun = false) {
  const targetFile = path.join(userDir, "chatLanguageModels.json")
  let existing = []

  try {
    const raw = await fs.readFile(targetFile, "utf8")
    existing = JSON.parse(raw)
    if (!Array.isArray(existing)) existing = []
  } catch (error) {
    if (error.code !== "ENOENT") {
      console.warn(`Warning reading ${targetFile}: ${error.message}`)
    }
  }

  // Preserve non-customendpoint providers (e.g. copilot, unify-chat-provider)
  // and any custom endpoints not managed by labflow
  const newNames = new Set(newEndpoints.map((g) => g.name))
  const preserved = existing.filter((entry) => entry.vendor !== "customendpoint" || !newNames.has(entry.name))

  const merged = [...preserved, ...newEndpoints]

  if (dryRun) {
    console.log(`[DRY-RUN] Target: ${targetFile}`)
    console.log(`[DRY-RUN] Will write ${merged.length} provider groups (${newEndpoints.length} managed from labflow)`)
    return
  }

  // Create timestamped backup
  if (existing.length > 0) {
    const timestamp = new Date().toISOString().replace(/[:.]/g, "-")
    const backupFile = `${targetFile}.bak-${timestamp}`
    await fs.writeFile(backupFile, JSON.stringify(existing, null, 2), "utf8")
    console.log(`Backed up existing config to: ${backupFile}`)
  }

  await fs.mkdir(userDir, { recursive: true })
  await fs.writeFile(targetFile, JSON.stringify(merged, null, 2), "utf8")
  console.log(`Successfully updated: ${targetFile} (${newEndpoints.length} managed endpoints)`)
}

// Build shell export string for Copilot CLI
function getCopilotCliEnv(providers, secrets, targetProviderId, targetModelId) {
  const provider = providers.find((p) => p.id === targetProviderId)
  if (!provider) {
    throw new Error(`Provider "${targetProviderId}" not found. Available: ${providers.map((p) => p.id).join(", ")}`)
  }

  const config = provider.config || {}
  const auth = provider.auth || {}
  const baseURL = (config.options?.baseURL || "").replace(/\/+$/, "")
  const isAnthropic = config.npm === "@ai-sdk/anthropic" || provider.id.includes("claude")
  const isResponses = baseURL.includes("/responses") || provider.id === "routin-plan"

  const modelId = targetModelId || Object.keys(config.models || {})[0] || "gpt-5.6-terra"
  const modelDef = config.models?.[modelId] || {}
  const binding = auth.models?.[modelId] || auth.default
  const secretAlias = binding?.secret
  const rawApiKey = secretAlias ? secrets[secretAlias] : ""
  const apiKey = rawApiKey.replace(/^Bearer\s+/i, "").trim()

  const envs = [
    `export COPILOT_PROVIDER_BASE_URL="${baseURL}"`,
    `export COPILOT_PROVIDER_TYPE="${isAnthropic ? "anthropic" : "openai"}"`,
    `export COPILOT_PROVIDER_API_KEY="${apiKey}"`,
    `export COPILOT_PROVIDER_WIRE_API="${isResponses ? "responses" : "completions"}"`,
    `export COPILOT_MODEL="${modelId}"`,
  ]

  if (modelDef.limit?.context) {
    envs.push(`export COPILOT_PROVIDER_MAX_PROMPT_TOKENS="${modelDef.limit.context}"`)
  }
  if (modelDef.limit?.output) {
    envs.push(`export COPILOT_PROVIDER_MAX_OUTPUT_TOKENS="${modelDef.limit.output}"`)
  }

  return envs.join("\n")
}

async function main() {
  const args = process.argv.slice(2)
  const dryRun = args.includes("--dry-run")
  const listOnly = args.includes("--list")
  const envIndex = args.indexOf("--env")

  const secretStore = new SecretStore()
  const secrets = await secretStore.load()
  const providerMap = await loadProviders()
  const providers = Object.entries(providerMap).map(([id, p]) => ({ id, ...p }))

  if (listOnly) {
    console.log("Available providers in provider/:")
    for (const p of providers) {
      const models = Object.keys(p.config?.models || {})
      console.log(`- ${p.id} (${p.config?.name || p.id}): ${models.join(", ")}`)
    }
    return
  }

  if (envIndex !== -1) {
    const targetProviderId = args[envIndex + 1]
    const targetModelId = args[envIndex + 2]
    if (!targetProviderId) {
      console.error("Usage: node sync-providers.mjs --env <provider-id> [model-id]")
      process.exit(1)
    }
    const envStr = getCopilotCliEnv(providers, secrets, targetProviderId, targetModelId)
    console.log(envStr)
    return
  }

  console.log(`Loaded ${providers.length} provider definitions and decrypted SOPS secrets.`)
  const newEndpoints = buildVSCodeCustomEndpoints(providers, secrets)
  console.log(`Generated ${newEndpoints.length} VS Code Custom Endpoint groups.`)

  for (const userDir of VSCODE_USER_DIRS) {
    try {
      await fs.access(path.dirname(userDir))
      await syncVSCodeFile(userDir, newEndpoints, dryRun)
    } catch {
      // User directory parent doesn't exist, skip
    }
  }

  // Sync ~/.copilot/providers.json
  const copilotDir = path.join(process.env.HOME, ".copilot")
  const copilotProvidersFile = path.join(copilotDir, "providers.json")
  try {
    await fs.access(copilotDir)
    const cliProviders = []
    for (const p of providers) {
      const config = p.config || {}
      const auth = p.auth || {}
      const baseURL = config.options?.baseURL
      if (!baseURL) continue

      const secretModelMap = new Map()
      const modelsObj = config.models || {}
      for (const [modelId, modelDef] of Object.entries(modelsObj)) {
        const binding = auth.models?.[modelId] || auth.default
        const secretAlias = binding?.secret
        const rawApiKey = secretAlias ? secrets[secretAlias] : undefined
        if (!rawApiKey) continue
        const apiKey = rawApiKey.replace(/^Bearer\s+/i, "").trim()
        const key = `${secretAlias}:::${apiKey}`
        if (!secretModelMap.has(key)) {
          secretModelMap.set(key, { secretAlias, apiKey, models: [] })
        }
        secretModelMap.get(key).models.push(modelId)
      }

      if (secretModelMap.size === 0) {
        const secretAlias = auth.default?.secret
        const rawApiKey = secretAlias ? secrets[secretAlias] : ""
        const apiKey = rawApiKey.replace(/^Bearer\s+/i, "").trim()
        if (apiKey) {
          cliProviders.push({
            name: p.id,
            baseUrl: baseURL,
            apiKey,
            type: config.npm === "@ai-sdk/anthropic" || p.id.includes("claude") ? "anthropic" : "openai",
            wireApi: baseURL.includes("/responses") || p.id === "routin-plan" ? "responses" : "completions",
            models: Object.keys(config.models || {}),
          })
        }
      } else {
        const totalSubGroups = secretModelMap.size
        for (const { secretAlias, apiKey, models } of secretModelMap.values()) {
          const entryName = totalSubGroups > 1
            ? `${p.id}-${secretAlias.replace(/^(routin|lucoo)-/, "")}`
            : p.id

          cliProviders.push({
            name: entryName,
            baseUrl: baseURL,
            apiKey,
            type: config.npm === "@ai-sdk/anthropic" || p.id.includes("claude") ? "anthropic" : "openai",
            wireApi: baseURL.includes("/responses") || p.id === "routin-plan" ? "responses" : "completions",
            models,
          })
        }
      }
    }
    if (dryRun) {
      console.log(`[DRY-RUN] Target: ${copilotProvidersFile} (${cliProviders.length} providers)`)
    } else {
      await fs.writeFile(copilotProvidersFile, JSON.stringify({ providers: cliProviders }, null, 2), "utf8")
      console.log(`Successfully updated: ${copilotProvidersFile} (${cliProviders.length} providers)`)
    }
  } catch {
    // ~/.copilot doesn't exist
  }

  console.log("Provider synchronization complete.")
}

main().catch((err) => {
  console.error("Error syncing providers:", err.message)
  process.exit(1)
})
