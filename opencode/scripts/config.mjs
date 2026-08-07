import { execFile } from "node:child_process"
import * as fs from "node:fs/promises"
import * as path from "node:path"
import { fileURLToPath } from "node:url"
import { promisify } from "node:util"
import { parse as parseYaml } from "yaml"

const execFileAsync = promisify(execFile)
const OPENCODE_DIR = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..")
export const MANAGED_CONFIG_DIR = path.join(OPENCODE_DIR, "config")
const SECRET_SENTINEL = "labflow-managed"

export async function readManagedConfig(configDir = process.env.LABFLOW_CONFIG_DIR ?? MANAGED_CONFIG_DIR) {
  const defaultsDocument = await readOptionalYaml(path.join(configDir, "defaults.yaml"))
  const imagegen = await readOptionalYaml(path.join(configDir, "imagegen.yaml"))
  const plugins = await readOptionalYaml(path.join(configDir, "plugins.yaml"))
  const providers = {}
  const providersDir = path.join(configDir, "providers")

  for (const name of await yamlFiles(providersDir)) {
    const document = await readYaml(path.join(providersDir, name))
    requireVersion(document, `providers/${name}`)
    const id = requireString(document.id, `providers/${name}.id`)
    if (!isPlainObject(document.config)) throw new Error(`providers/${name}.config must be a mapping`)
    if (providers[id]) throw new Error(`duplicate managed provider ID: ${id}`)
    providers[id] = { config: document.config, auth: document.auth }
  }

  if (Object.keys(defaultsDocument).length > 0) requireVersion(defaultsDocument, "defaults.yaml")
  if (Object.keys(imagegen).length > 0) requireVersion(imagegen, "imagegen.yaml")
  if (Object.keys(plugins).length > 0) requireVersion(plugins, "plugins.yaml")

  return {
    defaults: isPlainObject(defaultsDocument.config) ? defaultsDocument.config : {},
    imagegen,
    plugins,
    providers,
    configDir,
  }
}

export class SecretStore {
  constructor(options = {}) {
    this.secretPath = options.secretPath ?? path.join(process.env.LABFLOW_CONFIG_DIR ?? MANAGED_CONFIG_DIR, "secrets.sops.yaml")
    this.sopsBin = options.sopsBin ?? process.env.LABFLOW_SOPS_BIN ?? "sops"
    this.environment = options.environment ?? process.env
    this.loader = options.loader
    this.cache = undefined
  }

  async get(alias) {
    requireString(alias, "secret alias")
    const secrets = await this.load()
    const value = secrets[alias]
    if (typeof value !== "string" || value.length === 0) {
      throw new Error(`missing encrypted secret alias: ${alias}`)
    }
    return value
  }

  async load() {
    if (this.cache) return this.cache
    const document = this.loader ? await this.loader() : await this.decrypt()
    if (!isPlainObject(document) || document.version !== 1 || !isPlainObject(document.secrets)) {
      throw new Error("decrypted secrets must contain version: 1 and a secrets mapping")
    }
    for (const [alias, value] of Object.entries(document.secrets)) {
      requireString(alias, "secret alias")
      if (typeof value !== "string" || value.length === 0) {
        throw new Error(`encrypted secret ${alias} must be a non-empty string`)
      }
    }
    this.cache = document.secrets
    return this.cache
  }

  dispose() {
    this.cache = undefined
  }

  async decrypt() {
    try {
      const { stdout } = await execFileAsync(
        this.sopsBin,
        ["--decrypt", "--input-type", "yaml", "--output-type", "json", this.secretPath],
        { encoding: "utf8", env: this.environment, maxBuffer: 4 * 1024 * 1024 },
      )
      return JSON.parse(stdout)
    } catch (error) {
      if (error?.code === "ENOENT") {
        throw new Error(`sops is required to decrypt ${this.secretPath}`)
      }
      const detail = typeof error?.stderr === "string" ? error.stderr.trim().slice(0, 800) : ""
      throw new Error(`could not decrypt ${this.secretPath}${detail ? `: ${detail}` : ""}`)
    }
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

async function readOptionalYaml(filePath) {
  try {
    return await readYaml(filePath)
  } catch (error) {
    if (error?.code === "ENOENT") return {}
    throw error
  }
}

async function readYaml(filePath) {
  try {
    const document = parseYaml(await fs.readFile(filePath, "utf8")) ?? {}
    if (!isPlainObject(document)) throw new Error("document must be a mapping")
    return document
  } catch (error) {
    if (error?.code === "ENOENT") throw error
    throw new Error(`could not read ${filePath}: ${error.message}`)
  }
}

async function yamlFiles(directory) {
  try {
    return (await fs.readdir(directory)).filter((name) => /\.ya?ml$/i.test(name)).sort()
  } catch (error) {
    if (error?.code === "ENOENT") return []
    throw error
  }
}

function normalizeAuth(auth) {
  if (!isPlainObject(auth)) throw new Error("provider auth must be a mapping")
  const models = {}
  if (auth.models !== undefined) {
    if (!isPlainObject(auth.models)) throw new Error("provider auth.models must be a mapping")
    for (const [model, binding] of Object.entries(auth.models)) models[model] = normalizeBinding(binding)
  }
  const defaultBinding = auth.default === undefined ? undefined : normalizeBinding(auth.default)
  if (!defaultBinding && Object.keys(models).length === 0) throw new Error("provider auth requires default or model bindings")
  return { default: defaultBinding, models }
}

function normalizeBinding(binding) {
  if (!isPlainObject(binding)) throw new Error("provider auth binding must be a mapping")
  const secret = requireString(binding.secret, "provider auth secret")
  const header = binding.header === undefined ? "Authorization" : requireString(binding.header, "provider auth header")
  const query = binding.query === undefined ? undefined : requireString(binding.query, "provider auth query")
  if (query && binding.header !== undefined) throw new Error("provider auth binding cannot set both header and query")
  return {
    secret,
    header,
    query,
    prefix: binding.prefix === undefined ? "Bearer " : String(binding.prefix),
  }
}

async function requestModel(request) {
  try {
    const text = await request.clone().text()
    const document = JSON.parse(text)
    return typeof document?.model === "string" ? document.model : undefined
  } catch {
    return undefined
  }
}

function requireVersion(document, name) {
  if (document.version !== 1) throw new Error(`${name} must declare version: 1`)
}

function requireString(value, name) {
  if (typeof value !== "string" || value.length === 0) throw new Error(`${name} must be a non-empty string`)
  return value
}

function isPlainObject(value) {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value)
}
