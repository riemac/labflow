#!/usr/bin/env node

import { execFileSync } from "node:child_process"
import * as fs from "node:fs/promises"
import * as path from "node:path"
import { fileURLToPath } from "node:url"

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url))
const COPILOT_DIR = path.resolve(SCRIPT_DIR, "..")
const REPO_ROOT = path.resolve(COPILOT_DIR, "..")
import { loadProviders, SecretStore, PROVIDER_DIR, SECRETS_FILE } from "../../provider/index.mjs"

async function checkFile(p) {
  try {
    await fs.access(p)
    return true
  } catch {
    return false
  }
}

async function main() {
  console.log("=== Labflow Copilot Diagnostic Doctor ===")
  let ok = true

  // 1. Check SOPS
  try {
    const version = execFileSync("sops", ["--version"], { encoding: "utf8" }).trim()
    console.log(`✔ sops binary: found (${version.split("\n")[0]})`)
  } catch (error) {
    console.error(`✖ sops binary: not found or failed (${error.message})`)
    ok = false
  }

  // 2. Check SOPS secret decryption via SecretStore
  try {
    const store = new SecretStore()
    const secrets = await store.load()
    console.log(`✔ provider/secrets.sops.yaml: successfully decrypted with age key (${Object.keys(secrets).length} secrets)`)
  } catch (error) {
    console.error(`✖ provider/secrets.sops.yaml: decryption failed (${error.message})`)
    ok = false
  }

  // 3. Check provider definitions via loadProviders
  try {
    const providers = await loadProviders()
    const ids = Object.keys(providers)
    console.log(`✔ provider definitions: loaded ${ids.length} providers (${ids.join(", ")})`)
  } catch (error) {
    console.error(`✖ provider directory: failed to load (${error.message})`)
    ok = false
  }

  // 4. Check VS Code configurations
  const vscodeDir = path.join(process.env.HOME, ".config", "Code", "User")
  const vscodeInsidersDir = path.join(process.env.HOME, ".config", "Code - Insiders", "User")

  if (await checkFile(vscodeDir)) {
    const lmFile = path.join(vscodeDir, "chatLanguageModels.json")
    const lmExists = await checkFile(lmFile)
    console.log(`✔ VS Code: directory found (${lmExists ? "chatLanguageModels.json present" : "no chatLanguageModels.json yet"})`)
  }

  if (await checkFile(vscodeInsidersDir)) {
    const lmFile = path.join(vscodeInsidersDir, "chatLanguageModels.json")
    const lmExists = await checkFile(lmFile)
    console.log(`✔ VS Code Insiders: directory found (${lmExists ? "chatLanguageModels.json present" : "no chatLanguageModels.json yet"})`)
  }

  // 5. Check Copilot CLI & providers.json
  try {
    const version = execFileSync("copilot", ["--version"], { encoding: "utf8" }).trim()
    console.log(`✔ Copilot CLI: found (${version.split("\n")[0]})`)

    const cliProvidersFile = path.join(process.env.HOME, ".copilot", "providers.json")
    if (await checkFile(cliProvidersFile)) {
      const parsed = JSON.parse(await fs.readFile(cliProvidersFile, "utf8"))
      if (Array.isArray(parsed?.providers)) {
        console.log(`✔ ~/.copilot/providers.json: valid JSON array (${parsed.providers.length} providers registered)`)
      } else {
        console.error(`✖ ~/.copilot/providers.json: 'providers' must be a JSON array`)
        ok = false
      }
    }
  } catch {
    console.log(`ℹ Copilot CLI: not in PATH (optional if using VS Code only)`)
  }

  // 6. Check Copilot plugin manifest and mcp.json
  const pluginJson = path.join(COPILOT_DIR, "plugin.json")
  const mcpJson = path.join(COPILOT_DIR, "mcp.json")
  console.log(`${await checkFile(pluginJson) ? "✔" : "✖"} copilot/plugin.json: ${await checkFile(pluginJson) ? "present" : "missing"}`)
  console.log(`${await checkFile(mcpJson) ? "✔" : "✖"} copilot/mcp.json: ${await checkFile(mcpJson) ? "present" : "missing"}`)

  console.log("\nStatus: " + (ok ? "All core diagnostics passed!" : "Some diagnostics failed."))
}

main().catch((err) => {
  console.error("Doctor error:", err)
  process.exit(1)
})
