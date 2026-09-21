import assert from "node:assert/strict"
import * as fs from "node:fs/promises"
import * as os from "node:os"
import * as path from "node:path"
import test from "node:test"
import {
  applyManagedOpenCodeConfig,
  createSecureFetch,
  readManagedConfig,
  SecretStore,
  writeFilesTransaction,
} from "../scripts/config.mjs"

async function temporaryDirectory(t, prefix) {
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), prefix))
  t.after(() => fs.rm(directory, { recursive: true, force: true }))
  return directory
}

test("lucoo grok and gpt models declare vision and temperature capabilities", async () => {
  const managed = await readManagedConfig()
  const grok = managed.providers.lucoo.config.models["grok-4.6"]
  const gpt = managed.providers.lucoo.config.models["gpt-5.6-sol"]

  assert.equal(grok.attachment, true)
  assert.equal(grok.temperature, true)
  assert.deepEqual(grok.modalities.input, ["text", "image", "pdf"])
  assert.equal(gpt.attachment, true)
  assert.equal(gpt.temperature, true)
  assert.deepEqual(gpt.modalities.input, ["text", "image", "pdf"])
})

test("routin current models use the intended group credentials", async () => {
  const managed = await readManagedConfig()
  const routin = managed.providers.routin
  const models = routin.config.models

  assert.equal(models["muse-spark-1.2"], undefined)
  assert.equal(models["grok-4.5"], undefined)
  assert.equal(models["muse-spark-1.3"].limit.context, 1_000_000)
  assert.equal(models["grok-4.6"].limit.context, 500_000)
  assert.deepEqual(models["gemini-3.7-flash"].limit, models["gemini-3.8-flash"].limit)
  assert.equal(models["gemini-3.8-flash"].limit.context, 1_000_000)
  assert.equal(routin.auth.models["muse-spark-1.3"].secret, "routin-muse-spark")
  assert.equal(routin.auth.models["gemini-3.7-flash"], undefined)
  assert.equal(routin.auth.models["gemini-3.8-flash"], undefined)
  assert.equal(routin.auth.models["grok-4.6"], undefined)
  assert.equal(routin.auth.default.secret, "routin-grok")
})


test("LinkAPI exposes Gemini 3.8 Flash through its chat-compatible endpoint", async () => {
  const managed = await readManagedConfig()
  const provider = managed.providers.linkapi
  const model = provider.config.models["gemini-3.8-flash"]

  assert.equal(provider.config.npm, "@ai-sdk/openai-compatible")
  assert.equal(provider.config.options.baseURL, "https://api.linkapi.ai/v1")
  assert.equal(model.reasoning, true)
  assert.equal(model.attachment, true)
  assert.equal(model.tool_call, true)
  assert.deepEqual(model.modalities.input, ["text", "image"])
  assert.deepEqual(model.limit, {
    context: 1_000_000,
    input: 1_000_000,
    output: 65_536,
  })
  assert.deepEqual(provider.auth.default, {
    secret: "linkapi",
    header: "Authorization",
    prefix: "Bearer ",
  })
})

test("native OpenAI OAuth exposes GPT-5.6 modes and official GPT-6 Astra", async () => {
  const managed = await readManagedConfig()
  const openai = managed.providers.openai.config

  for (const model of ["gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna"]) {
    assert.equal(openai.whitelist.includes(model), true)
    assert.equal(openai.whitelist.includes(`${model}-fast`), true)
    assert.deepEqual(openai.models[`${model}-fast`].limit, openai.models[model].limit)
  }
  assert.equal(openai.whitelist.includes("gpt-6-astra"), true)
  assert.deepEqual(openai.models["gpt-6-astra"].limit, {
    context: 1050000,
    input: 922000,
    output: 128000,
  })
})

test("managed config keeps local overrides and secrets out of resolved config", async (t) => {
  const configDir = await temporaryDirectory(t, "labflow-config-")
  await fs.mkdir(path.join(configDir, "providers"))
  await fs.writeFile(path.join(configDir, "defaults.yaml"), [
    "version: 1",
    "config:",
    "  model: relay/default",
    "  permission:",
    "    edit: ask",
    "",
  ].join("\n"))
  await fs.writeFile(path.join(configDir, "imagegen.yaml"), "version: 1\nprofiles: {}\nroutes: {}\n")
  await fs.writeFile(path.join(configDir, "plugins.yaml"), "version: 1\nplugins: []\nbootstrap: {}\n")
  await fs.writeFile(path.join(configDir, "providers", "relay.yaml"), [
    "version: 1",
    "id: relay",
    "config:",
    "  npm: '@ai-sdk/openai-compatible'",
    "  options:",
    "    baseURL: https://relay.example/v1",
    "  models:",
    "    default: {}",
    "auth:",
    "  default:",
    "    secret: relay-key",
    "    header: Authorization",
    "    prefix: 'Bearer '",
    "",
  ].join("\n"))

  const managed = await readManagedConfig(configDir)
  const store = new SecretStore({ loader: async () => ({ version: 1, secrets: { "relay-key": "canary-secret" } }) })
  const cfg = { model: "relay/local", permission: { bash: "allow" } }
  applyManagedOpenCodeConfig(cfg, managed, store, async () => new Response("ok"))

  assert.equal(cfg.model, "relay/local")
  assert.deepEqual(cfg.permission, { edit: "ask", bash: "allow" })
  assert.equal(cfg.provider.relay.options.apiKey, "labflow-managed")
  assert.equal(typeof cfg.provider.relay.options.fetch, "function")
  assert.equal(JSON.stringify(cfg).includes("canary-secret"), false)
  assert.equal(JSON.stringify(cfg).includes("relay-key"), false)
})

test("secure provider fetch selects model bindings and overwrites request auth", async () => {
  const requests = []
  const store = new SecretStore({
    loader: async () => ({
      version: 1,
      secrets: { default: "default-secret", special: "special-secret" },
    }),
  })
  const secureFetch = createSecureFetch({
    default: { secret: "default", header: "Authorization", prefix: "Bearer " },
    models: {
      special: { secret: "special", header: "Authorization", prefix: "" },
    },
  }, store, async (request) => {
    requests.push({
      url: request.url,
      method: request.method,
      body: await request.text(),
      headers: new Headers(request.headers),
      signal: request.signal,
    })
    return new Response("ok")
  })

  const controller = new AbortController()
  await secureFetch(new Request("https://relay.example/v1/chat/completions", {
    method: "POST",
    headers: { Authorization: "Bearer labflow-managed" },
    body: JSON.stringify({ model: "special" }),
    signal: controller.signal,
  }))
  await secureFetch("https://relay.example/v1/chat/completions", {
    method: "POST",
    body: JSON.stringify({ model: "ordinary" }),
  })

  assert.equal(requests[0].headers.get("Authorization"), "special-secret")
  assert.equal(requests[1].headers.get("Authorization"), "Bearer default-secret")
  assert.deepEqual(requests.map((request) => request.method), ["POST", "POST"])
  assert.deepEqual(requests.map((request) => JSON.parse(request.body).model), ["special", "ordinary"])
  controller.abort()
  assert.equal(requests[0].signal.aborted, true)
})

test("secure provider fetch selects model bindings from Google generateContent URLs", async () => {
  const requests = []
  const store = new SecretStore({
    loader: async () => ({
      version: 1,
      secrets: { default: "default-secret", gemini: "gemini-secret" },
    }),
  })
  const secureFetch = createSecureFetch({
    default: { secret: "default", header: "Authorization", prefix: "Bearer " },
    models: {
      "gemini-3.7-flash": { secret: "gemini", header: "Authorization", prefix: "" },
    },
  }, store, async (request) => {
    requests.push(request)
    return new Response("ok")
  })

  await secureFetch(new Request("https://relay.example/v1/models/gemini-3.7-flash:generateContent", {
    method: "POST",
    headers: { Authorization: "Bearer labflow-managed" },
    body: JSON.stringify({ contents: [{ role: "user", parts: [{ text: "hi" }] }] }),
  }))

  assert.equal(requests[0].headers.get("Authorization"), "gemini-secret")
})

test("secure provider fetch supports query credentials", async () => {
  const store = new SecretStore({ loader: async () => ({ version: 1, secrets: { google: "query-secret" } }) })
  let captured
  const secureFetch = createSecureFetch({
    default: { secret: "google", query: "key", prefix: "" },
  }, store, async (request) => {
    captured = request
    return new Response("ok")
  })

  await secureFetch(new Request("https://provider.example/v1/models?key=labflow-managed", {
    method: "POST",
    headers: { Authorization: "Bearer labflow-managed" },
    body: JSON.stringify({ model: "gemini" }),
  }))
  assert.equal(new URL(captured.url).searchParams.get("key"), "query-secret")
  assert.equal(captured.headers.get("Authorization"), null)
  assert.equal(captured.method, "POST")
  assert.deepEqual(await captured.json(), { model: "gemini" })
})

test("secret store rejects invalid documents without including values", async () => {
  const store = new SecretStore({ loader: async () => ({ secrets: { sample: "do-not-print" } }) })
  await assert.rejects(store.get("sample"), (error) => {
    assert.doesNotMatch(error.message, /do-not-print/)
    return /version: 1/.test(error.message)
  })
})

test("file transaction restores earlier targets when a later install fails", async (t) => {
  const root = await temporaryDirectory(t, "labflow-config-transaction-")
  const parentTarget = path.join(root, "managed")
  const childTarget = path.join(parentTarget, "child.yaml")
  await fs.mkdir(parentTarget)
  await fs.writeFile(childTarget, "original child\n")

  await assert.rejects(writeFilesTransaction([
    { filePath: parentTarget, content: "replacement parent\n" },
    { filePath: childTarget, content: "replacement child\n" },
  ]))

  assert.equal(await fs.readFile(childTarget, "utf8"), "original child\n")
  assert.deepEqual((await fs.readdir(root)).filter((name) => name.includes("transaction-")), [])
})
