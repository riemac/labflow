import { execFile } from "node:child_process"
import * as fs from "node:fs/promises"
import * as path from "node:path"
import { fileURLToPath } from "node:url"
import { promisify } from "node:util"
import {
  isPlainObject,
  loadProviders,
  normalizeAuth,
  normalizeBinding,
  PROVIDER_DIR,
  readOptionalYaml,
  readYaml,
  requireString,
  requireVersion,
  resolveModelBinding,
  SECRETS_FILE,
  SecretStore,
  yamlFiles,
} from "../../provider/index.mjs"

export {
  isPlainObject,
  loadProviders,
  normalizeAuth,
  normalizeBinding,
  PROVIDER_DIR,
  resolveModelBinding,
  SECRETS_FILE,
  SecretStore,
}

const execFileAsync = promisify(execFile)
const OPENCODE_DIR = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..")
export const MANAGED_CONFIG_DIR = path.join(OPENCODE_DIR, "config")
const SECRET_SENTINEL = "labflow-managed"

export async function readManagedConfig(
  configDir = process.env.LABFLOW_CONFIG_DIR ?? MANAGED_CONFIG_DIR,
  providerDir = process.env.LABFLOW_PROVIDER_DIR ?? PROVIDER_DIR,
) {
  const defaultsDocument = await readOptionalYaml(path.join(configDir, "defaults.yaml"))
  const imagegen = await readOptionalYaml(path.join(configDir, "imagegen.yaml"))
  const plugins = await readOptionalYaml(path.join(configDir, "plugins.yaml"))

  const localProvidersDir = path.join(configDir, "providers")
  let effectiveProviderDir = providerDir
  try {
    const stat = await fs.stat(localProvidersDir)
    if (stat.isDirectory()) {
      effectiveProviderDir = localProvidersDir
    }
  } catch {}

  const localSecretPath = path.join(configDir, "secrets.sops.yaml")
  let effectiveSecretPath = SECRETS_FILE
  try {
    const stat = await fs.stat(localSecretPath)
    if (stat.isFile()) effectiveSecretPath = localSecretPath
  } catch {}

  const providers = await loadProviders(effectiveProviderDir)

  if (Object.keys(defaultsDocument).length > 0) requireVersion(defaultsDocument, "defaults.yaml")
  if (Object.keys(imagegen).length > 0) requireVersion(imagegen, "imagegen.yaml")
  if (Object.keys(plugins).length > 0) requireVersion(plugins, "plugins.yaml")

  return {
    defaults: isPlainObject(defaultsDocument.config) ? defaultsDocument.config : {},
    imagegen,
    plugins,
    providers,
    configDir,
    providerDir: effectiveProviderDir,
    secretPath: effectiveSecretPath,
  }
}

export function createSecureFetch(auth, secretStore, requestFetch = globalThis.fetch) {
  const normalized = normalizeAuth(auth)
  if (typeof requestFetch !== "function") throw new Error("secure provider fetch requires a fetch implementation")

  return async (input, init = {}) => {
    const request = new Request(input, init)
    const model = await requestModel(request)
    const binding = normalized.models[model] ?? normalized.default
    if (!binding) {
      throw new Error(`no managed credential is configured for model ${model || "<unknown>"}`)
    }
    const secret = await secretStore.get(binding.secret)
    const headers = new Headers(request.headers)
    const target = new URL(request.url)

    for (const [name, value] of headers) {
      if (value.includes(SECRET_SENTINEL)) headers.delete(name)
    }

    if (binding.query) {
      target.searchParams.set(binding.query, `${binding.prefix}${secret}`)
    } else {
      headers.set(binding.header, `${binding.prefix}${secret}`)
    }

    const authenticated = new Request(target, new Request(request, { headers }))
    return requestFetch(authenticated)
  }
}

export function prepareManagedProviders(providers, secretStore, requestFetch = globalThis.fetch) {
  const prepared = {}
  for (const [id, entry] of Object.entries(providers)) {
    const config = structuredClone(entry.config)
    if (entry.auth !== undefined) {
      config.options = {
        ...(isPlainObject(config.options) ? config.options : {}),
        apiKey: SECRET_SENTINEL,
        fetch: createSecureFetch(entry.auth, secretStore, requestFetch),
      }
    }
    prepared[id] = config
  }
  return prepared
}

export function applyManagedOpenCodeConfig(cfg, managed, secretStore, requestFetch = globalThis.fetch) {
  const tracked = mergeObjects(managed.defaults, {
    provider: prepareManagedProviders(managed.providers, secretStore, requestFetch),
  })
  const merged = mergeObjects(tracked, cfg)
  for (const key of Object.keys(cfg)) delete cfg[key]
  Object.assign(cfg, merged)
  return cfg
}

export function mergeObjects(base, override) {
  if (!isPlainObject(base) || !isPlainObject(override)) return override
  const merged = { ...base }
  for (const [key, value] of Object.entries(override)) {
    merged[key] = isPlainObject(value) && isPlainObject(merged[key])
      ? mergeObjects(merged[key], value)
      : value
  }
  return merged
}

export async function writeFilesTransaction(entries) {
  const token = `${process.pid}-${Date.now()}-${Math.random().toString(16).slice(2)}`
  const states = []
  let rollbackIncomplete = false
  try {
    for (const [index, entry] of entries.entries()) {
      const mode = entry.mode ?? 0o644
      await fs.mkdir(path.dirname(entry.filePath), { recursive: true })
      const temporary = `${entry.filePath}.transaction-${token}-${index}`
      await fs.writeFile(temporary, entry.content, { mode })
      states.push({ ...entry, mode, temporary, backup: `${temporary}.backup`, hadOriginal: false, installed: false })
    }

    for (const state of states) {
      try {
        await fs.rename(state.filePath, state.backup)
        state.hadOriginal = true
      } catch (error) {
        if (error?.code !== "ENOENT") throw error
      }
      await fs.rename(state.temporary, state.filePath)
      state.installed = true
      await fs.chmod(state.filePath, state.mode)
    }
  } catch (error) {
    const rollbackErrors = []
    for (const state of [...states].reverse()) {
      if (state.installed) {
        try {
          await fs.rm(state.filePath, { recursive: true, force: true })
        } catch (rollbackError) {
          rollbackErrors.push(rollbackError)
        }
      }
      if (state.hadOriginal) {
        try {
          await fs.rename(state.backup, state.filePath)
        } catch (rollbackError) {
          rollbackErrors.push(rollbackError)
        }
      }
    }
    if (rollbackErrors.length > 0) {
      rollbackIncomplete = true
      throw new AggregateError([error, ...rollbackErrors], "file transaction failed and rollback was incomplete")
    }
    throw error
  } finally {
    for (const state of states) {
      await fs.rm(state.temporary, { recursive: true, force: true }).catch(() => {})
      if (!rollbackIncomplete) await fs.rm(state.backup, { recursive: true, force: true }).catch(() => {})
    }
  }
}

export function stripJsonComments(input) {
  let output = ""
  let inString = false
  let escaped = false
  for (let index = 0; index < input.length; index += 1) {
    const char = input[index]
    const next = input[index + 1]
    if (inString) {
      output += char
      if (escaped) escaped = false
      else if (char === "\\") escaped = true
      else if (char === '"') inString = false
      continue
    }
    if (char === '"') {
      inString = true
      output += char
      continue
    }
    if (char === "/" && next === "/") {
      while (index < input.length && input[index] !== "\n") index += 1
      output += "\n"
      continue
    }
    if (char === "/" && next === "*") {
      index += 2
      while (index < input.length && !(input[index] === "*" && input[index + 1] === "/")) index += 1
      index += 1
      continue
    }
    output += char
  }
  return output
}

export function stripTrailingCommas(input) {
  let output = ""
  let inString = false
  let escaped = false
  for (let index = 0; index < input.length; index += 1) {
    const char = input[index]
    if (inString) {
      output += char
      if (escaped) escaped = false
      else if (char === "\\") escaped = true
      else if (char === '"') inString = false
      continue
    }
    if (char === '"') {
      inString = true
      output += char
      continue
    }
    if (char === ",") {
      let cursor = index + 1
      while (cursor < input.length && /\s/.test(input[cursor])) cursor += 1
      if (input[cursor] === "}" || input[cursor] === "]") continue
    }
    output += char
  }
  return output
}



async function requestModel(request) {
  return (await requestModelFromBody(request)) ?? requestModelFromUrl(request.url)
}

async function requestModelFromBody(request) {
  try {
    const document = JSON.parse(await request.clone().text())
    return typeof document?.model === "string" ? document.model : undefined
  } catch {
    return undefined
  }
}

function requestModelFromUrl(url) {
  try {
    const match = new URL(url).pathname.match(/\/models\/([^/:]+)(?::|$)/)
    return match ? decodeURIComponent(match[1]) : undefined
  } catch {
    return undefined
  }
}


