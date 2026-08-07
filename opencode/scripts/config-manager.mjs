#!/usr/bin/env node

import { execFile, spawn } from "node:child_process"
import * as fs from "node:fs/promises"
import * as path from "node:path"
import { fileURLToPath, pathToFileURL } from "node:url"
import { promisify } from "node:util"
import { parse as parseYaml, stringify as stringifyYaml } from "yaml"
import {
  MANAGED_CONFIG_DIR,
  readManagedConfig,
  SecretStore,
  stripJsonComments,
  stripTrailingCommas,
  writeFilesTransaction,
} from "./config.mjs"

const execFileAsync = promisify(execFile)
const OPENCODE_DIR = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..")
const REPO_DIR = process.env.LABFLOW_REPO_DIR ?? path.resolve(OPENCODE_DIR, "..")
const CONFIG_DIR = process.env.LABFLOW_CONFIG_DIR ?? MANAGED_CONFIG_DIR
const GLOBAL_CONFIG_DIR = process.env.OPENCODE_CONFIG_DIR ?? path.join(homeDir(), ".config", "opencode")
const GLOBAL_CONFIG_FILE = path.join(GLOBAL_CONFIG_DIR, "opencode.json")
const PLUGIN_ENTRY = pathToFileURL(path.join(OPENCODE_DIR, "plugins", "labflow.ts")).href
const AGE_KEY_FILE = process.env.SOPS_AGE_KEY_FILE ?? path.join(homeDir(), ".config", "sops", "age", "keys.txt")
const SOPS_CONFIG_FILE = path.join(REPO_DIR, ".sops.yaml")
const SECRETS_FILE = path.join(CONFIG_DIR, "secrets.sops.yaml")

main().catch((error) => {
  console.error(`labflow config error: ${safeMessage(error)}`)
  process.exit(1)
})

async function main() {
  const [command, ...args] = process.argv.slice(2)
  if (command === "bootstrap") return syncBootstrap()
  if (command === "migrate") return migrateConfig()
  if (command === "doctor") return doctor()
  if (command === "init-age") return initAge()
  if (command === "authorize-age") return authorizeAge(args[0])
  throw new Error(`unknown config-manager command: ${command || "<missing>"}`)
}

async function syncBootstrap() {
  const managed = await readManagedConfig(CONFIG_DIR)
  const current = await readJsoncOptional(GLOBAL_CONFIG_FILE)
  const declaredPlugins = managedPluginEntries(managed.plugins)
  const currentPlugins = normalizePluginList(current.plugin).filter((entry) => !isLabflowPlugin(entry))
  const plugins = uniquePlugins([...declaredPlugins, ...currentPlugins, PLUGIN_ENTRY])
  const next = { ...current, $schema: "https://opencode.ai/config.json", plugin: plugins }
  await fs.mkdir(GLOBAL_CONFIG_DIR, { recursive: true })
  await writeFileAtomic(GLOBAL_CONFIG_FILE, `${JSON.stringify(next, null, 2)}\n`, 0o600)
  console.log(`Synchronized labflow bootstrap in ${GLOBAL_CONFIG_FILE}`)
}

async function migrateConfig() {
  await requireCommand("sops")
  await requireCommand("age")
  await requireCommand("age-keygen")
  const identity = await fs.readFile(AGE_KEY_FILE, "utf8").catch((error) => {
    if (error?.code === "ENOENT") throw new Error(`age identity is missing: ${AGE_KEY_FILE}; run install.sh --init-age first`)
    throw error
  })
  if (!identity.includes("AGE-SECRET-KEY-")) throw new Error(`no age secret identity found in ${AGE_KEY_FILE}`)

  const current = await readJsoncRequired(GLOBAL_CONFIG_FILE)
  if (Object.keys(current.provider ?? {}).length === 0 && await exists(SECRETS_FILE)) {
    const managed = await readManagedConfig(CONFIG_DIR)
    if (Object.keys(managed.providers).length > 0) {
      await syncBootstrap()
      console.log("OpenCode config is already migrated; bootstrap synchronized.")
      return
    }
  }
  const recipient = (await execFileAsync("age-keygen", ["-y", AGE_KEY_FILE], { encoding: "utf8" })).stdout.trim()
  validateRecipient(recipient)
  const migrated = await buildMigration(current)
  const encryptedSecrets = await sopsEncrypt({ version: 1, secrets: migrated.secrets }, recipient)
  await validateMigration(migrated, encryptedSecrets)

  const timestamp = new Date().toISOString().replace(/[:.]/g, "-")
  const backupDir = path.join(GLOBAL_CONFIG_DIR, "labflow-backups", timestamp)
  await backupMigrationInputs(backupDir)

  const writes = [
    { filePath: path.join(CONFIG_DIR, "defaults.yaml"), content: yaml({ version: 1, config: migrated.defaults }) },
    { filePath: path.join(CONFIG_DIR, "plugins.yaml"), content: yaml({ version: 1, plugins: migrated.plugins, bootstrap: {} }) },
  ]
  for (const [id, provider] of Object.entries(migrated.providers)) {
    writes.push({
      filePath: path.join(CONFIG_DIR, "providers", `${safeFileName(id)}.yaml`),
      content: yaml({
        version: 1,
        id,
        config: provider.config,
        ...(provider.auth ? { auth: provider.auth } : {}),
      }),
    })
  }

  const bootstrap = {
    $schema: "https://opencode.ai/config.json",
    plugin: uniquePlugins([...migrated.plugins, ...migrated.localPlugins, PLUGIN_ENTRY]),
  }
  writes.push(
    { filePath: SECRETS_FILE, content: encryptedSecrets, mode: 0o600 },
    { filePath: SOPS_CONFIG_FILE, content: yaml(sopsConfig([recipient])) },
    { filePath: GLOBAL_CONFIG_FILE, content: `${JSON.stringify(bootstrap, null, 2)}\n`, mode: 0o600 },
  )
  await writeFilesTransaction(writes)
  console.log(`Migrated OpenCode config. Backup: ${backupDir}`)
  console.log(`Encrypted ${Object.keys(migrated.secrets).length} secret aliases for ${recipient}`)
}

async function buildMigration(current) {
  const defaults = structuredClone(current)
  delete defaults.$schema
  delete defaults.plugin
  delete defaults.provider
  assertNoUnsupportedSecrets(defaults, "config")
  const plugins = []
  const localPlugins = []
  for (const entry of normalizePluginList(current.plugin)) {
    if (isLabflowPlugin(entry)) continue
    if (isPortablePlugin(entry)) plugins.push(entry)
    else localPlugins.push(entry)
  }

  const providers = {}
  const secrets = {}
  for (const [id, rawProvider] of Object.entries(current.provider ?? {})) {
    const config = structuredClone(rawProvider)
    const auth = { models: {} }
    const providerReference = config.options?.apiKey
    if (typeof providerReference === "string") {
      const secret = await captureSecret(providerReference, secrets, id)
      if (secret) {
        delete config.options.apiKey
        auth.default = defaultAuthBinding(config.npm, secret)
      }
    }
    const providerHeaderBinding = await captureHeaderBinding(config.options?.headers, secrets, `${id}-default`)
    if (providerHeaderBinding) {
      if (auth.default) throw new Error(`provider.${id} declares multiple default credential sources`)
      auth.default = providerHeaderBinding
      if (Object.keys(config.options.headers).length === 0) delete config.options.headers
    }
    for (const [model, modelConfig] of Object.entries(config.models ?? {})) {
      const binding = await captureHeaderBinding(modelConfig.headers, secrets, `${id}-${model}`)
      if (!binding) continue
      if (Object.keys(modelConfig.headers).length === 0) delete modelConfig.headers
      auth.models[model] = binding
    }
    if (Object.keys(auth.models).length === 0) delete auth.models
    assertNoUnsupportedSecrets(config, `provider.${id}`)
    providers[id] = { config, auth: auth.default || auth.models ? auth : undefined }
  }
  return { defaults, plugins, localPlugins, providers, secrets }
}

async function captureHeaderBinding(headers, secrets, aliasPrefix) {
  if (!headers || typeof headers !== "object" || Array.isArray(headers)) return undefined
  let binding
  for (const [header, reference] of Object.entries(headers)) {
    if (!isSecretBearingField(header) || typeof reference !== "string") continue
    if (binding) throw new Error(`${aliasPrefix} declares multiple secret-bearing headers`)
    const secret = await captureSecret(reference, secrets, `${aliasPrefix}-${header}`)
    delete headers[header]
    binding = { secret, header, prefix: "" }
  }
  return binding
}

async function captureSecret(reference, secrets, suggestedAlias) {
  const match = reference.match(/^\{file:(.+)\}$/)
  const envMatch = reference.match(/^\{env:([A-Za-z_][A-Za-z0-9_]*)\}$/)
  let alias = safeAlias(suggestedAlias)
  let value = reference
  if (match) {
    const secretPath = resolveUserPath(match[1])
    alias = safeAlias(path.basename(secretPath).replace(/\.key$/i, ""))
    value = (await fs.readFile(secretPath, "utf8")).trim()
    if (!value) throw new Error(`secret file is empty: ${secretPath}`)
  } else if (envMatch) {
    value = process.env[envMatch[1]]
    if (!value) throw new Error(`environment variable is required for migration: ${envMatch[1]}`)
  }
  if (!value) throw new Error(`secret value is empty for alias: ${alias}`)
  if (secrets[alias] && secrets[alias] !== value) throw new Error(`secret alias collision: ${alias}`)
  secrets[alias] = value
  return alias
}

function defaultAuthBinding(npm, secret) {
  if (npm === "@ai-sdk/anthropic") return { secret, header: "x-api-key", prefix: "" }
  return { secret, header: "Authorization", prefix: "Bearer " }
}

async function validateMigration(migrated, encryptedSecrets) {
  if (Object.keys(migrated.providers).length === 0) throw new Error("migration found no providers")
  if (!encryptedSecrets.includes("sops:")) throw new Error("sops output does not contain encryption metadata")
  const plaintext = Object.values(migrated.secrets)
  if (plaintext.some((secret) => encryptedSecrets.includes(secret))) throw new Error("sops output still contains a plaintext secret")
  JSON.stringify(migrated.defaults)
  yaml({ version: 1, plugins: migrated.plugins, bootstrap: {} })
  for (const [id, provider] of Object.entries(migrated.providers)) {
    safeFileName(id)
    assertNoUnsupportedSecrets(provider.config, `provider.${id}`)
    yaml({ version: 1, id, ...provider })
  }
}

async function backupMigrationInputs(backupDir) {
  await fs.mkdir(backupDir, { recursive: true, mode: 0o700 })
  await fs.chmod(backupDir, 0o700)
  await fs.copyFile(GLOBAL_CONFIG_FILE, path.join(backupDir, "opencode.json"))
  if (await exists(CONFIG_DIR)) {
    await fs.cp(CONFIG_DIR, path.join(backupDir, "managed-config"), { recursive: true, preserveTimestamps: true })
  }
  if (await exists(SOPS_CONFIG_FILE)) {
    await fs.copyFile(SOPS_CONFIG_FILE, path.join(backupDir, ".sops.yaml"))
  }
}

async function doctor() {
  const missing = []
  for (const command of ["sops", "age", "age-keygen"]) {
    if (!(await commandExists(command))) missing.push(command)
  }
  if (missing.length > 0) {
    console.log(`Missing required commands: ${missing.join(", ")}`)
    printDependencyHelp()
    process.exitCode = 1
    return
  }

  const managed = await readManagedConfig(CONFIG_DIR)
  assertNoUnsupportedSecrets(managed.defaults, "defaults")
  for (const [id, provider] of Object.entries(managed.providers)) {
    assertNoUnsupportedSecrets(provider.config, `provider.${id}`)
  }
  assertNoImagegenCredentials(managed.imagegen)
  const secretStore = new SecretStore({ secretPath: SECRETS_FILE })
  const secrets = await secretStore.load()
  const referenced = referencedSecretAliases(managed)
  const unresolved = referenced.filter((alias) => !secrets[alias])
  if (unresolved.length > 0) throw new Error(`missing encrypted aliases: ${unresolved.join(", ")}`)

  if (await exists(GLOBAL_CONFIG_FILE) && await commandExists("opencode")) {
    const { stdout } = await execFileAsync("opencode", ["debug", "config"], { encoding: "utf8", maxBuffer: 8 * 1024 * 1024 })
    const leaked = Object.entries(secrets).filter(([, secret]) => stdout.includes(secret)).map(([alias]) => alias)
    if (leaked.length > 0) throw new Error(`opencode debug config exposes managed secrets: ${leaked.join(", ")}`)
  }
  secretStore.dispose()
  console.log(`Labflow config doctor passed: ${Object.keys(managed.providers).length} providers, ${referenced.length} secret bindings`)
}

async function initAge() {
  await requireCommand("age-keygen")
  if (await exists(AGE_KEY_FILE)) throw new Error(`refusing to overwrite existing age identity: ${AGE_KEY_FILE}`)
  await fs.mkdir(path.dirname(AGE_KEY_FILE), { recursive: true, mode: 0o700 })
  await execFileAsync("age-keygen", ["-o", AGE_KEY_FILE], { encoding: "utf8" })
  await fs.chmod(AGE_KEY_FILE, 0o600)
  const recipient = (await execFileAsync("age-keygen", ["-y", AGE_KEY_FILE], { encoding: "utf8" })).stdout.trim()
  console.log(`Created age identity: ${AGE_KEY_FILE}`)
  console.log(`Recipient: ${recipient}`)
}

async function authorizeAge(recipient) {
  validateRecipient(recipient)
  await requireCommand("sops")
  const current = await readYamlOptional(SOPS_CONFIG_FILE)
  const recipients = new Set(sopsRecipients(current))
  recipients.add(recipient)
  let previous
  try {
    previous = await fs.readFile(SOPS_CONFIG_FILE, "utf8")
  } catch (error) {
    if (error?.code !== "ENOENT") throw error
  }
  try {
    await writeFileAtomic(SOPS_CONFIG_FILE, yaml(sopsConfig([...recipients].sort())))
    if (await exists(SECRETS_FILE)) {
      await execFileAsync("sops", ["updatekeys", "--yes", SECRETS_FILE], { cwd: REPO_DIR, encoding: "utf8" })
    }
  } catch (error) {
    if (previous === undefined) await fs.rm(SOPS_CONFIG_FILE, { force: true })
    else await writeFileAtomic(SOPS_CONFIG_FILE, previous)
    throw error
  }
  console.log(`Authorized age recipient: ${recipient}`)
}

async function sopsEncrypt(document, recipient) {
  return new Promise((resolve, reject) => {
    const stdinPath = process.platform === "linux" ? "/proc/self/fd/0" : "/dev/stdin"
    const command = `cat | sops --encrypt --age "$1" --input-type yaml --output-type yaml ${stdinPath}`
    const child = spawn("sh", ["-c", command, "sh", recipient], {
      cwd: REPO_DIR,
      stdio: ["pipe", "pipe", "pipe"],
    })
    let stdout = ""
    let stderr = ""
    child.stdout.setEncoding("utf8").on("data", (chunk) => { stdout += chunk })
    child.stderr.setEncoding("utf8").on("data", (chunk) => { stderr += chunk })
    child.on("error", reject)
    child.on("close", (code) => code === 0 ? resolve(stdout) : reject(new Error(`sops encryption failed: ${stderr.trim().slice(0, 800)}`)))
    child.stdin.end(yaml(document))
  })
}

function referencedSecretAliases(managed) {
  const aliases = new Set()
  for (const provider of Object.values(managed.providers)) {
    if (provider.auth?.default?.secret) aliases.add(provider.auth.default.secret)
    for (const binding of Object.values(provider.auth?.models ?? {})) if (binding?.secret) aliases.add(binding.secret)
  }
  for (const profile of Object.values(managed.imagegen.profiles ?? {})) if (profile?.secret) aliases.add(profile.secret)
  return [...aliases].sort()
}

function managedPluginEntries(document) {
  return Array.isArray(document.plugins) ? document.plugins : []
}

function normalizePluginList(value) {
  return Array.isArray(value) ? value : []
}

function uniquePlugins(entries) {
  const seen = new Set()
  return entries.filter((entry) => {
    const identity = pluginIdentity(entry)
    if (!identity || seen.has(identity)) return false
    seen.add(identity)
    return true
  })
}

function pluginIdentity(entry) {
  return typeof entry === "string" ? entry : Array.isArray(entry) && typeof entry[0] === "string" ? entry[0] : undefined
}

function isPortablePlugin(entry) {
  const identity = pluginIdentity(entry)
  return Boolean(identity) && !identity.startsWith("file:") && !path.isAbsolute(identity)
}

function isLabflowPlugin(entry) {
  const identity = pluginIdentity(entry)
  if (!identity) return false
  if (identity === PLUGIN_ENTRY) return true
  try {
    return identity.startsWith("file:") && fileURLToPath(identity).replaceAll("\\", "/").endsWith("/opencode/plugins/labflow.ts")
  } catch {
    return false
  }
}

function sopsConfig(recipients) {
  return {
    creation_rules: [{
      path_regex: "opencode/config/secrets\\.sops\\.yaml$",
      age: recipients.join(","),
    }],
  }
}

function sopsRecipients(document) {
  const age = document?.creation_rules?.[0]?.age
  return typeof age === "string" ? age.split(",").map((item) => item.trim()).filter(Boolean) : []
}

async function readJsoncRequired(filePath) {
  try {
    return JSON.parse(stripTrailingCommas(stripJsonComments(await fs.readFile(filePath, "utf8"))))
  } catch (error) {
    throw new Error(`could not read ${filePath}: ${error.message}`)
  }
}

async function readJsoncOptional(filePath) {
  try {
    return await readJsoncRequired(filePath)
  } catch (error) {
    if (!(await exists(filePath))) return {}
    throw error
  }
}

async function readYamlOptional(filePath) {
  try {
    return parseYaml(await fs.readFile(filePath, "utf8")) ?? {}
  } catch (error) {
    if (error?.code === "ENOENT") return {}
    throw error
  }
}

async function writeFileAtomic(filePath, content, mode = 0o644) {
  await fs.mkdir(path.dirname(filePath), { recursive: true })
  const temporary = `${filePath}.tmp-${process.pid}-${Date.now()}`
  try {
    await fs.writeFile(temporary, content, { mode })
    await fs.rename(temporary, filePath)
    await fs.chmod(filePath, mode)
  } finally {
    await fs.rm(temporary, { force: true })
  }
}

async function commandExists(command) {
  try {
    await execFileAsync("sh", ["-c", `command -v "$1" >/dev/null 2>&1`, "sh", command])
    return true
  } catch {
    return false
  }
}

async function requireCommand(command) {
  if (await commandExists(command)) return
  printDependencyHelp()
  throw new Error(`required command is missing: ${command}`)
}

function printDependencyHelp() {
  console.log("Install SOPS and age using your operating system package manager, then rerun this command.")
  console.log("Official releases: https://github.com/getsops/sops/releases and https://github.com/FiloSottile/age/releases")
}

function validateRecipient(recipient) {
  if (typeof recipient !== "string" || !/^age1[0-9a-z]+$/.test(recipient)) throw new Error("expected a valid age1... recipient")
}

function safeFileName(value) {
  if (!/^[a-z0-9][a-z0-9._-]*$/i.test(value)) throw new Error(`provider ID is not filename-safe: ${value}`)
  return value
}

function safeAlias(value) {
  const alias = String(value).toLowerCase().replace(/[^a-z0-9._-]+/g, "-").replace(/^-+|-+$/g, "")
  if (!alias) throw new Error("could not derive a safe secret alias")
  return alias
}

function assertNoUnsupportedSecrets(value, location) {
  if (!value || typeof value !== "object") return
  for (const [key, item] of Object.entries(value)) {
    const itemLocation = `${location}.${key}`
    if (isSecretBearingField(key) && typeof item === "string") {
      throw new Error(`unsupported secret-bearing field outside managed provider auth: ${itemLocation}`)
    }
    assertNoUnsupportedSecrets(item, itemLocation)
  }
}

function isSecretBearingField(value) {
  const key = String(value).toLowerCase().replace(/[^a-z0-9]/g, "")
  return key === "authorization"
    || key === "proxyauthorization"
    || key === "token"
    || key.endsWith("apikey")
    || key.endsWith("accesstoken")
    || key.endsWith("refreshtoken")
    || key.endsWith("authtoken")
    || key.endsWith("bearertoken")
    || key.endsWith("password")
    || key.endsWith("secret")
}

function assertNoImagegenCredentials(imagegen) {
  for (const [name, profile] of Object.entries(imagegen.profiles ?? {})) {
    if (!profile || typeof profile !== "object" || Array.isArray(profile)) continue
    for (const key of Object.keys(profile)) {
      const normalized = key.toLowerCase().replace(/[^a-z0-9]/g, "")
      if (normalized === "apikeyfile" || (normalized !== "secret" && isSecretBearingField(key))) {
        throw new Error(`managed imagegen profile ${name} must reference a SOPS secret alias instead of ${key}`)
      }
    }
  }
}

function resolveUserPath(value) {
  if (value === "~") return homeDir()
  if (value.startsWith("~/")) return path.join(homeDir(), value.slice(2))
  return path.resolve(value)
}

function yaml(value) {
  return stringifyYaml(value, { lineWidth: 0 })
}

async function exists(filePath) {
  try {
    await fs.access(filePath)
    return true
  } catch {
    return false
  }
}

function homeDir() {
  if (!process.env.HOME) throw new Error("HOME is not set")
  return process.env.HOME
}

function safeMessage(error) {
  return error instanceof Error ? error.message.slice(0, 1200) : String(error).slice(0, 1200)
}
