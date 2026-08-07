import assert from "node:assert/strict"
import { execFile } from "node:child_process"
import * as fs from "node:fs/promises"
import * as os from "node:os"
import * as path from "node:path"
import { fileURLToPath } from "node:url"
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
