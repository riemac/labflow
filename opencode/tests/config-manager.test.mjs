import assert from "node:assert/strict"
import { execFile } from "node:child_process"
import * as fs from "node:fs/promises"
import * as os from "node:os"
import * as path from "node:path"
import { fileURLToPath, pathToFileURL } from "node:url"
import { promisify } from "node:util"
import test from "node:test"
import { parse as parseYaml, stringify as stringifyYaml } from "yaml"

const execFileAsync = promisify(execFile)
const OPENCODE_DIR = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..")
const CONFIG_MANAGER = path.join(OPENCODE_DIR, "scripts", "config-manager.mjs")

async function temporaryDirectory(t, prefix) {
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), prefix))
  t.after(() => fs.rm(directory, { recursive: true, force: true }))
  return directory
}

test("bootstrap pins managed plugins and replaces stale npm specs", async (t) => {
  const root = await temporaryDirectory(t, "labflow-bootstrap-")
  const configDir = path.join(root, "managed-config")
  const globalDir = path.join(root, "global-config")
  await Promise.all([
    fs.mkdir(path.join(configDir, "providers"), { recursive: true }),
    fs.mkdir(globalDir, { recursive: true }),
  ])
  await fs.writeFile(path.join(configDir, "defaults.yaml"), "version: 1\nconfig: {}\n")
  await fs.writeFile(path.join(configDir, "imagegen.yaml"), "version: 1\nprofiles: {}\nroutes: {}\n")
  await fs.writeFile(path.join(configDir, "plugins.yaml"), [
    "version: 1",
    "plugins:",
    "  - [opencode-goal-plugin@0.9.0, {maxTurns: 20}]",
    "  - opencode-pty",
    "bootstrap: {}",
    "",
  ].join("\n"))
  await fs.writeFile(path.join(globalDir, "opencode.json"), JSON.stringify({
    plugin: [
      ["opencode-goal-plugin", { maxTurns: 3 }],
      "opencode-goal-plugin@0.4.0",
      "custom-plugin",
      "file:///old/opencode/plugins/labflow.ts",
    ],
  }))

  await execFileAsync(process.execPath, [CONFIG_MANAGER, "bootstrap"], {
    env: {
      ...process.env,
      LABFLOW_CONFIG_DIR: configDir,
      OPENCODE_CONFIG_DIR: globalDir,
    },
    encoding: "utf8",
  })

  const bootstrap = JSON.parse(await fs.readFile(path.join(globalDir, "opencode.json"), "utf8"))
  assert.deepEqual(bootstrap.plugin[0], ["opencode-goal-plugin@0.9.0", { maxTurns: 20 }])
  assert.equal(bootstrap.plugin.filter((entry) => String(Array.isArray(entry) ? entry[0] : entry).startsWith("opencode-goal-plugin")).length, 1)
  assert.equal(bootstrap.plugin.includes("opencode-pty"), true)
  assert.equal(bootstrap.plugin.includes("custom-plugin"), true)
  assert.equal(bootstrap.plugin.at(-1).endsWith("/opencode/plugins/labflow.ts"), true)
})

test("bootstrap can opt into and roll back machine-local Goal and PTY plugins", async (t) => {
  const root = await temporaryDirectory(t, "labflow-local-plugins-")
  const configDir = path.join(root, "managed-config")
  const globalDir = path.join(root, "global-config")
  const localDir = path.join(root, "local-plugins")
  await Promise.all([
    fs.mkdir(path.join(configDir, "providers"), { recursive: true }),
    fs.mkdir(globalDir, { recursive: true }),
    fs.mkdir(localDir, { recursive: true }),
  ])
  await fs.writeFile(path.join(configDir, "defaults.yaml"), "version: 1\nconfig: {}\n")
  await fs.writeFile(path.join(configDir, "imagegen.yaml"), "version: 1\nprofiles: {}\nroutes: {}\n")
  await fs.writeFile(path.join(configDir, "plugins.yaml"), [
    "version: 1",
    "plugins:",
    "  - [opencode-goal-plugin@0.9.0, {maxTurns: 1000, sessionTitleStatus: true}]",
    "  - opencode-pty",
    "bootstrap: {}",
    "",
  ].join("\n"))
  const goalPath = path.join(localDir, "goal.js")
  const ptyPath = path.join(localDir, "pty.js")
  const integrationPath = path.join(localDir, "integration.js")
  await Promise.all([
    fs.writeFile(goalPath, "export const GoalPlugin = async () => ({})\n"),
    fs.writeFile(ptyPath, "export const PTYPlugin = async () => ({})\n"),
    fs.writeFile(integrationPath, "export const listPtySessions = () => []\n"),
  ])
  const overridePath = path.join(globalDir, "labflow-plugin-overrides.json")
  const override = {
    version: 1,
    enabled: true,
    goalPluginUrl: pathToFileURL(goalPath).href,
    ptyPluginUrl: pathToFileURL(ptyPath).href,
    ptyIntegrationUrl: pathToFileURL(integrationPath).href,
  }
  await fs.writeFile(overridePath, JSON.stringify(override, null, 2))
  await fs.writeFile(path.join(globalDir, "opencode.json"), JSON.stringify({
    plugin: [
      "opencode-goal-plugin@0.4.0",
      "opencode-pty",
      "custom-plugin",
      "file:///old/opencode/plugins/goal-pty-adapter.ts",
    ],
  }))
  const environment = {
    ...process.env,
    LABFLOW_CONFIG_DIR: configDir,
    LABFLOW_PLUGIN_OVERRIDES_FILE: overridePath,
    OPENCODE_CONFIG_DIR: globalDir,
  }

  await execFileAsync(process.execPath, [CONFIG_MANAGER, "bootstrap"], {
    env: environment,
    encoding: "utf8",
  })
  let bootstrap = JSON.parse(await fs.readFile(path.join(globalDir, "opencode.json"), "utf8"))
  assert.match(bootstrap.plugin[0][0], /\/opencode\/plugins\/goal-pty-adapter\.ts$/)
  assert.equal(bootstrap.plugin[0][1].goalPluginUrl, override.goalPluginUrl)
  assert.equal(bootstrap.plugin[0][1].ptyIntegrationUrl, override.ptyIntegrationUrl)
  assert.deepEqual(bootstrap.plugin[0][1].goalOptions, {
    maxTurns: 1000,
    sessionTitleStatus: true,
  })
  assert.equal(bootstrap.plugin[1], override.ptyPluginUrl)
  assert.equal(bootstrap.plugin.includes("custom-plugin"), true)
  assert.equal(JSON.stringify(bootstrap.plugin).includes("opencode-goal-plugin@0.4.0"), false)

  override.enabled = false
  await fs.writeFile(overridePath, JSON.stringify(override, null, 2))
  await execFileAsync(process.execPath, [CONFIG_MANAGER, "bootstrap"], {
    env: environment,
    encoding: "utf8",
  })
  bootstrap = JSON.parse(await fs.readFile(path.join(globalDir, "opencode.json"), "utf8"))
  assert.deepEqual(bootstrap.plugin[0], [
    "opencode-goal-plugin@0.9.0",
    { maxTurns: 1000, sessionTitleStatus: true },
  ])
  assert.equal(bootstrap.plugin[1], "opencode-pty")
  assert.equal(JSON.stringify(bootstrap.plugin).includes("goal-pty-adapter.ts"), false)
  assert.equal(JSON.stringify(bootstrap.plugin).includes(override.ptyPluginUrl), false)

  const beforeInvalidBootstrap = await fs.readFile(path.join(globalDir, "opencode.json"), "utf8")
  override.enabled = true
  override.ptyPluginUrl = pathToFileURL(path.join(localDir, "missing.js")).href
  await fs.writeFile(overridePath, JSON.stringify(override, null, 2))
  await assert.rejects(
    execFileAsync(process.execPath, [CONFIG_MANAGER, "bootstrap"], {
      env: environment,
      encoding: "utf8",
    }),
    /ptyPluginUrl does not exist/,
  )
  assert.equal(
    await fs.readFile(path.join(globalDir, "opencode.json"), "utf8"),
    beforeInvalidBootstrap,
  )
})

test("explicit migration encrypts file secrets, writes a thin bootstrap, and is idempotent", async (t) => {
  const root = await temporaryDirectory(t, "labflow-migration-")
  const home = path.join(root, "home")
  const configDir = path.join(root, "managed-config")
  const globalDir = path.join(home, ".config", "opencode")
  const binDir = path.join(root, "bin")
  const keyDir = path.join(home, "keys")
  const ageKey = path.join(home, ".config", "sops", "age", "keys.txt")
  await Promise.all([
    fs.mkdir(globalDir, { recursive: true }),
    fs.mkdir(configDir, { recursive: true }),
    fs.mkdir(path.join(configDir, "providers"), { recursive: true }),
    fs.mkdir(binDir, { recursive: true }),
    fs.mkdir(keyDir, { recursive: true }),
    fs.mkdir(path.dirname(ageKey), { recursive: true }),
  ])
  const providerKey = path.join(keyDir, "relay.key")
  await fs.writeFile(providerKey, "migration-canary-secret\n", { mode: 0o600 })
  await fs.writeFile(ageKey, "# created: test\nAGE-SECRET-KEY-TEST\n", { mode: 0o600 })
  await fs.writeFile(path.join(configDir, "defaults.yaml"), "version: 1\nconfig:\n  model: old/default\n")
  await fs.writeFile(path.join(configDir, "secrets.sops.yaml"), "old encrypted secrets\n", { mode: 0o600 })
  await fs.writeFile(path.join(configDir, "providers", "old.yaml"), "version: 1\nid: old\nconfig: {}\n")
  await fs.writeFile(path.join(root, ".sops.yaml"), "old sops policy\n")
  await fs.writeFile(path.join(globalDir, "opencode.json"), JSON.stringify({
    $schema: "https://opencode.ai/config.json",
    plugin: ["file:///old/opencode/plugins/labflow.ts", ["opencode-goal-plugin", { maxTurns: 20 }]],
    model: "relay/model",
    permission: { edit: "ask" },
    provider: {
      relay: {
        name: "Relay",
        npm: "@ai-sdk/openai-compatible",
        options: {
          baseURL: "https://relay.example/v1",
          apiKey: `{file:${providerKey}}`,
        },
        models: {
          model: {
            name: "Model",
            headers: { Authorization: "literal-model-secret" },
          },
          fileKeyModel: {
            name: "File key model",
            headers: { "x-api-key": `{file:${providerKey}}` },
          },
          customModel: {
            name: "Custom auth model",
            headers: { "X-Auth-Token": "literal-custom-secret" },
          },
        },
      },
    },
  }, null, 2))

  await executable(path.join(binDir, "age"), "#!/bin/sh\nexit 0\n")
  await executable(path.join(binDir, "age-keygen"), "#!/bin/sh\nif [ \"$1\" = \"-y\" ]; then printf '%s\\n' age1testrecipient123; fi\n")
  await executable(path.join(binDir, "opencode"), "#!/bin/sh\nprintf '%s\\n' '{\"provider\":{\"relay\":{\"options\":{\"apiKey\":\"labflow-managed\"}}}}'\n")
  await executable(path.join(binDir, "sops"), [
    "#!/usr/bin/env node",
    "const fs = require('node:fs')",
    "const decrypt = process.argv.includes('--decrypt')",
    "if (decrypt) {",
    "  console.log(JSON.stringify({version: 1, secrets: {relay: 'migration-canary-secret', 'relay-model-authorization': 'literal-model-secret', 'relay-custommodel-x-auth-token': 'literal-custom-secret'}}))",
    "} else {",
    "  fs.readFileSync(process.argv.at(-1), 'utf8')",
    "  console.log('version: 1\\nsecrets:\\n  relay: ENC[AES256_GCM,data:test]\\nsops:\\n  age: []')",
    "}",
    "",
  ].join("\n"))

  const environment = {
    ...process.env,
    HOME: home,
    PATH: `${binDir}:${process.env.PATH}`,
    OPENCODE_CONFIG_DIR: globalDir,
    LABFLOW_CONFIG_DIR: configDir,
    LABFLOW_REPO_DIR: root,
    SOPS_AGE_KEY_FILE: ageKey,
  }
  await execFileAsync(process.execPath, [CONFIG_MANAGER, "migrate"], { env: environment, encoding: "utf8" })

  const bootstrap = JSON.parse(await fs.readFile(path.join(globalDir, "opencode.json"), "utf8"))
  assert.deepEqual(Object.keys(bootstrap).sort(), ["$schema", "plugin"])
  assert.equal(JSON.stringify(bootstrap).includes("migration-canary-secret"), false)
  assert.deepEqual(bootstrap.plugin[0], ["opencode-goal-plugin", { maxTurns: 20 }])
  assert.equal(bootstrap.plugin[1].endsWith("/opencode/plugins/labflow.ts"), true)

  const provider = parseYaml(await fs.readFile(path.join(configDir, "providers", "relay.yaml"), "utf8"))
  assert.equal(provider.config.options.apiKey, undefined)
  assert.deepEqual(provider.auth.default, {
    secret: "relay",
    header: "Authorization",
    prefix: "Bearer ",
  })
  assert.deepEqual(provider.auth.models.model, {
    secret: "relay-model-authorization",
    header: "Authorization",
    prefix: "",
  })
  assert.deepEqual(provider.auth.models.fileKeyModel, {
    secret: "relay",
    header: "x-api-key",
    prefix: "",
  })
  assert.deepEqual(provider.auth.models.customModel, {
    secret: "relay-custommodel-x-auth-token",
    header: "X-Auth-Token",
    prefix: "",
  })
  assert.equal(provider.config.models.model.headers, undefined)
  assert.equal(provider.config.models.fileKeyModel.headers, undefined)
  assert.equal(provider.config.models.customModel.headers, undefined)
  const encrypted = await fs.readFile(path.join(configDir, "secrets.sops.yaml"), "utf8")
  assert.match(encrypted, /ENC\[AES256_GCM/)
  assert.doesNotMatch(encrypted, /migration-canary-secret/)
  assert.doesNotMatch(encrypted, /literal-model-secret/)
  assert.doesNotMatch(encrypted, /literal-custom-secret/)
  assert.equal((await fs.readdir(path.join(globalDir, "labflow-backups"))).length, 1)
  const backupName = (await fs.readdir(path.join(globalDir, "labflow-backups")))[0]
  const backupDir = path.join(globalDir, "labflow-backups", backupName)
  assert.match(await fs.readFile(path.join(backupDir, "managed-config", "defaults.yaml"), "utf8"), /old\/default/)
  assert.match(await fs.readFile(path.join(backupDir, "managed-config", "providers", "old.yaml"), "utf8"), /id: old/)
  assert.equal(await fs.readFile(path.join(backupDir, ".sops.yaml"), "utf8"), "old sops policy\n")

  const second = await execFileAsync(process.execPath, [CONFIG_MANAGER, "migrate"], { env: environment, encoding: "utf8" })
  assert.match(second.stdout, /already migrated/)
  assert.equal((await fs.readdir(path.join(globalDir, "labflow-backups"))).length, 1)

  const doctor = await execFileAsync(process.execPath, [CONFIG_MANAGER, "doctor"], { env: environment, encoding: "utf8" })
  assert.match(doctor.stdout, /doctor passed/)
  assert.doesNotMatch(doctor.stdout, /migration-canary-secret/)

  await fs.writeFile(path.join(configDir, "imagegen.yaml"), [
    "version: 1",
    "profiles:",
    "  unsafe:",
    "    apiKey: forgotten-imagegen-plaintext",
    "routes: {}",
    "",
  ].join("\n"))
  await assert.rejects(
    execFileAsync(process.execPath, [CONFIG_MANAGER, "doctor"], { env: environment, encoding: "utf8" }),
    /must reference a SOPS secret alias instead of apiKey/,
  )
  await fs.writeFile(path.join(configDir, "imagegen.yaml"), "version: 1\nprofiles: {}\nroutes: {}\n")

  provider.config.models.model.headers = { "x-api-key": "forgotten-plaintext" }
  await fs.writeFile(path.join(configDir, "providers", "relay.yaml"), stringifyProvider(provider))
  await assert.rejects(
    execFileAsync(process.execPath, [CONFIG_MANAGER, "doctor"], { env: environment, encoding: "utf8" }),
    /unsupported secret-bearing field/,
  )
})

function stringifyProvider(provider) {
  return stringifyYaml(provider)
}

async function executable(filePath, content) {
  await fs.writeFile(filePath, content, { mode: 0o755 })
  await fs.chmod(filePath, 0o755)
}
