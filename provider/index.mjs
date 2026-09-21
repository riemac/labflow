import { execFile } from "node:child_process"
import * as fs from "node:fs/promises"
import * as path from "node:path"
import { fileURLToPath } from "node:url"
import { promisify } from "node:util"
import { parse as parseYaml } from "yaml"

const execFileAsync = promisify(execFile)

export const PROVIDER_DIR = path.resolve(path.dirname(fileURLToPath(import.meta.url)))
export const SECRETS_FILE = path.join(PROVIDER_DIR, "secrets.sops.yaml")
export const SECRETS_EXAMPLE_FILE = path.join(PROVIDER_DIR, "secrets.sops.example.yaml")

/**
 * SecretStore manages decrypted SOPS secrets in memory with caching.
 * Decryption is performed lazily on first read via sops CLI.
 */
export class SecretStore {
  constructor(options = {}) {
    const defaultSecretPath = process.env.LABFLOW_SECRETS_FILE ?? (
      process.env.LABFLOW_CONFIG_DIR
        ? path.join(process.env.LABFLOW_CONFIG_DIR, "secrets.sops.yaml")
        : SECRETS_FILE
    )
    this.secretPath = options.secretPath ?? defaultSecretPath
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

/**
 * Loads and validates all provider definitions from the specified directory.
 * Ignores secrets.*.yaml files.
 */
export async function loadProviders(providerDir = PROVIDER_DIR) {
  const providers = {}
  for (const name of await yamlFiles(providerDir)) {
    const filePath = path.join(providerDir, name)
    const document = await readYaml(filePath)
    requireVersion(document, `providers/${name}`)
    const id = requireString(document.id, `providers/${name}.id`)
    if (!isPlainObject(document.config)) {
      throw new Error(`providers/${name}.config must be a mapping`)
    }
    if (providers[id]) {
      throw new Error(`duplicate managed provider ID: ${id}`)
    }
    providers[id] = { config: document.config, auth: document.auth }
  }
  return providers
}

export function normalizeAuth(auth) {
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

export function normalizeBinding(binding) {
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

export function resolveModelBinding(auth, modelName) {
  if (!auth) return undefined
  const normalized = normalizeAuth(auth)
  return (modelName ? normalized.models[modelName] : undefined) ?? normalized.default
}

export async function readYaml(filePath) {
  try {
    const document = parseYaml(await fs.readFile(filePath, "utf8")) ?? {}
    if (!isPlainObject(document)) throw new Error("document must be a mapping")
    return document
  } catch (error) {
    if (error?.code === "ENOENT") throw error
    throw new Error(`could not read ${filePath}: ${error.message}`)
  }
}

export async function readOptionalYaml(filePath) {
  try {
    return await readYaml(filePath)
  } catch (error) {
    if (error?.code === "ENOENT") return {}
    throw error
  }
}

export async function yamlFiles(directory) {
  try {
    return (await fs.readdir(directory))
      .filter((name) => /\.ya?ml$/i.test(name) && !name.startsWith("secrets."))
      .sort()
  } catch (error) {
    if (error?.code === "ENOENT") return []
    throw error
  }
}

export function requireVersion(document, name) {
  if (document.version !== 1) throw new Error(`${name} must declare version: 1`)
}

export function requireString(value, name) {
  if (typeof value !== "string" || value.length === 0) throw new Error(`${name} must be a non-empty string`)
  return value
}

export function isPlainObject(value) {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value)
}
