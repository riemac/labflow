import assert from "node:assert/strict"
import { execFile, execFileSync } from "node:child_process"
import * as fs from "node:fs/promises"
import * as http from "node:http"
import * as os from "node:os"
import * as path from "node:path"
import { fileURLToPath } from "node:url"
import { promisify } from "node:util"
import test from "node:test"

const OPENCODE_DIR = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..")
const IMAGEGEN_SCRIPT = path.join(OPENCODE_DIR, "scripts", "imagegen.mjs")
const PLUGIN_PATH = path.join(OPENCODE_DIR, "plugins", "labflow.ts")
const PNG_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9ZrN8AAAAASUVORK5CYII="
const PNG_BYTES = Buffer.from(PNG_BASE64, "base64")
const execFileAsync = promisify(execFile)

function runImagegen(cwd, args, env = {}) {
  const childEnvironment = {
    ...process.env,
    OPENCODE_IMAGEGEN_API: "responses",
    OPENCODE_IMAGEGEN_MODEL: "test-image-model",
    ...env,
  }
  for (const [name, value] of Object.entries(childEnvironment)) {
    if (value === null) delete childEnvironment[name]
  }
  return execFileSync(process.execPath, [IMAGEGEN_SCRIPT, "generate", ...args], {
    cwd,
    encoding: "utf8",
    env: childEnvironment,
    maxBuffer: 4 * 1024 * 1024,
  })
}

async function runImagegenAsync(cwd, args, env = {}) {
  const childEnvironment = {
    ...process.env,
    OPENCODE_IMAGEGEN_API: "responses",
    OPENCODE_IMAGEGEN_MODEL: "test-image-model",
    ...env,
  }
  for (const [name, value] of Object.entries(childEnvironment)) {
    if (value === null) delete childEnvironment[name]
  }
  const { stdout } = await execFileAsync(process.execPath, [IMAGEGEN_SCRIPT, "generate", ...args], {
    cwd,
    encoding: "utf8",
    env: childEnvironment,
    maxBuffer: 4 * 1024 * 1024,
  })
  return stdout
}

async function temporaryDirectory(t, prefix) {
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), prefix))
  t.after(() => fs.rm(directory, { recursive: true, force: true }))
  return directory
}

test("plugin preserves native agent system prompts", async (t) => {
  const plugin = await import(`${new URL(`file://${PLUGIN_PATH}`).href}?native=${Date.now()}`)
  const hooks = await plugin.default()
  t.after(() => hooks.dispose())

  for (const agent of ["build", "labflow-plan"]) {
    const output = { message: { system: "existing system" }, parts: [] }
    await hooks["chat.message"]({ sessionID: `native-${agent}`, agent }, output)
    assert.equal(output.message.system, "existing system")
  }
})

test("CLI preserves text-only Responses payloads", async (t) => {
  const cwd = await temporaryDirectory(t, "labflow-imagegen-fresh-")
  const result = JSON.parse(runImagegen(cwd, ["--prompt", "fresh image", "--dry-run"]))

  assert.equal(result.generation_mode, "generate")
  assert.equal(result.input_image_count, 0)
  assert.equal(result.payload.input, "fresh image")
  assert.equal("action" in result.payload.tools[0], false)
})

test("legacy local config overrides the default profile but not an explicit profile", async (t) => {
  const cwd = await temporaryDirectory(t, "labflow-imagegen-legacy-")
  const configDir = await temporaryDirectory(t, "labflow-imagegen-legacy-config-")
  const authorizations = []
  const server = http.createServer(async (request, response) => {
    for await (const _chunk of request) {}
    authorizations.push(request.headers.authorization)
    response.writeHead(200, { "Content-Type": "application/json" })
    response.end(JSON.stringify({ data: [{ b64_json: PNG_BASE64 }] }))
  })
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve))
  t.after(() => new Promise((resolve, reject) => server.close((error) => error ? reject(error) : resolve())))
  const address = server.address()
  await fs.writeFile(path.join(configDir, "defaults.yaml"), "version: 1\nconfig: {}\n")
  await fs.writeFile(path.join(configDir, "plugins.yaml"), "version: 1\nplugins: []\nbootstrap: {}\n")
  await fs.writeFile(path.join(configDir, "imagegen.yaml"), [
    "version: 1",
    "defaultProfile: modern",
    "profiles:",
    "  modern:",
    "    provider: modern-provider",
    "    api: images",
    `    baseURL: http://127.0.0.1:${address.port}/v1`,
    "    model: modern-model",
    "    secret: modern-key",
    "    size: 2048x1152",
    "    quality: high",
    "    outputFormat: png",
    "routes: {}",
    "",
  ].join("\n"))
  const legacyConfig = path.join(cwd, "legacy.json")
  await fs.writeFile(legacyConfig, JSON.stringify({
    imagegen: {
      provider: "legacy-provider",
      api: "responses",
      baseURL: "https://legacy.example/v1",
      model: "legacy-model",
      size: "1024x1024",
      quality: "low",
      apiKey: "legacy-plaintext-key",
    },
  }))
  const fakeSops = path.join(configDir, "fake-sops.mjs")
  await fs.writeFile(fakeSops, "#!/usr/bin/env node\nconsole.log(JSON.stringify({version: 1, secrets: {'modern-key': 'managed-secret'}}))\n")
  await fs.chmod(fakeSops, 0o755)
  const environment = {
    LABFLOW_CONFIG_DIR: configDir,
    LABFLOW_SOPS_BIN: fakeSops,
    OPENCODE_CONFIG_DIR: path.join(configDir, "global"),
    OPENCODE_IMAGEGEN_CONFIG: legacyConfig,
    OPENCODE_IMAGEGEN_API: null,
    OPENCODE_IMAGEGEN_MODEL: null,
    OPENCODE_IMAGEGEN_PROVIDER: null,
    OPENCODE_IMAGEGEN_API_KEY: null,
    OPENCODE_IMAGEGEN_BASE_URL: null,
  }

  const compatible = JSON.parse(runImagegen(cwd, ["--prompt", "legacy", "--dry-run"], environment))
  assert.equal(compatible.provider, "legacy-provider")
  assert.equal(compatible.api, "responses")
  assert.equal(compatible.payload.model, "legacy-model")
  assert.equal(compatible.payload.tools[0].size, "1024x1024")

  const explicit = JSON.parse(runImagegen(cwd, ["--prompt", "managed", "--profile", "modern", "--dry-run"], environment))
  assert.equal(explicit.provider, "modern-provider")
  assert.equal(explicit.api, "images")
  assert.equal(explicit.payload.model, "modern-model")
  assert.equal(explicit.payload.size, "2048x1152")

  const generated = JSON.parse(await runImagegenAsync(cwd, [
    "--prompt",
    "managed credential",
    "--profile",
    "modern",
    "--out",
    "managed.png",
  ], environment))
  assert.equal(generated.profile, "modern")
  assert.deepEqual(authorizations, ["Bearer managed-secret"])
  assert.deepEqual(await fs.readFile(path.join(cwd, "managed.png")), PNG_BYTES)
})

test("CLI builds a redacted multi-image edit payload", async (t) => {
  const cwd = await temporaryDirectory(t, "labflow-imagegen-edit-")
  await fs.writeFile(path.join(cwd, "first.png"), PNG_BYTES)
  await fs.writeFile(path.join(cwd, "second.png"), PNG_BYTES)

  const result = JSON.parse(await runImagegenAsync(cwd, [
    "--prompt",
    "change only the color",
    "--input-image",
    "first.png",
    "--input-image",
    "second.png",
    "--dry-run",
  ]))

  assert.equal(result.generation_mode, "edit")
  assert.equal(result.input_image_count, 2)
  assert.equal(result.payload.tools[0].action, "edit")
  assert.equal(result.payload.tools[0].output_format, "png")
  assert.equal("format" in result.payload.tools[0], false)
  assert.deepEqual(result.payload.input[0].content.map((part) => part.type), [
    "input_text",
    "input_image",
    "input_image",
  ])
  assert.equal(result.payload.input[0].content[1].image_url, "data:image/png;base64,<redacted>")
  assert.deepEqual(result.input_images.map((image) => image.source), ["first.png", "second.png"])
})

test("CLI rejects image edits through the Images API and more than four references", async (t) => {
  const cwd = await temporaryDirectory(t, "labflow-imagegen-limits-")
  const imagePaths = []
  for (let index = 0; index < 5; index += 1) {
    const imagePath = path.join(cwd, `${index}.png`)
    await fs.writeFile(imagePath, PNG_BYTES)
    imagePaths.push(imagePath)
  }

  assert.throws(
    () => runImagegen(cwd, ["--prompt", "edit", "--input-image", imagePaths[0], "--dry-run"], {
      OPENCODE_IMAGEGEN_API: "images",
    }),
    /input images require --api responses/,
  )
  assert.throws(
    () => runImagegen(cwd, [
      "--prompt",
      "edit",
      ...imagePaths.flatMap((imagePath) => ["--input-image", imagePath]),
      "--dry-run",
    ]),
    /provide at most 4 input images/,
  )

  const oversizedImage = path.join(cwd, "oversized.png")
  await fs.writeFile(oversizedImage, PNG_BYTES)
  await fs.truncate(oversizedImage, 20 * 1024 * 1024 + 1)
  assert.throws(
    () => runImagegen(cwd, ["--prompt", "edit", "--input-image", oversizedImage, "--dry-run"]),
    /exceeds the 20 MiB per-image limit/,
  )

  const combinedImages = []
  for (let index = 0; index < 3; index += 1) {
    const imagePath = path.join(cwd, `combined-${index}.png`)
    await fs.writeFile(imagePath, PNG_BYTES)
    await fs.truncate(imagePath, 18 * 1024 * 1024)
    combinedImages.push(imagePath)
  }
  assert.throws(
    () => runImagegen(cwd, [
      "--prompt",
      "edit",
      ...combinedImages.flatMap((imagePath) => ["--input-image", imagePath]),
      "--dry-run",
    ]),
    /input images exceed the 50 MiB total limit/,
  )
})

test("CLI falls back across a named route and commits only the successful output", async (t) => {
  const cwd = await temporaryDirectory(t, "labflow-imagegen-route-")
  const configDir = await temporaryDirectory(t, "labflow-imagegen-route-config-")
  const requests = []
  let assetMode = "unavailable"
  const first = http.createServer(async (request, response) => {
    if (request.url === "/asset") {
      if (assetMode === "timeout") {
        response.writeHead(200, { "Content-Type": "image/png" })
        response.write(PNG_BYTES.subarray(0, 8))
        setTimeout(() => response.end(PNG_BYTES.subarray(8)), 100)
        return
      }
      if (assetMode === "oversized") {
        response.writeHead(200, { "Content-Type": "image/png", "Content-Length": String(50 * 1024 * 1024 + 1) })
        response.end(PNG_BYTES)
        return
      }
      response.writeHead(503, "first-secret must be redacted")
      response.end()
      return
    }
    for await (const _chunk of request) {}
    requests.push({ provider: "first", authorization: request.headers.authorization })
    if (assetMode === "api-oversized") {
      response.writeHead(200, { "Content-Type": "application/json", "Content-Length": String(80 * 1024 * 1024) })
      response.end(JSON.stringify({ data: [{ b64_json: PNG_BASE64 }] }))
      return
    }
    response.writeHead(200, { "Content-Type": "application/json" })
    response.end(JSON.stringify({ data: [{ url: `http://${request.headers.host}/asset` }] }))
  })
  const second = http.createServer(async (request, response) => {
    for await (const _chunk of request) {}
    requests.push({ provider: "second", authorization: request.headers.authorization })
    response.writeHead(200, { "Content-Type": "application/json" })
    response.end(JSON.stringify({ data: [{ b64_json: PNG_BASE64 }] }))
  })
  await Promise.all([
    new Promise((resolve) => first.listen(0, "127.0.0.1", resolve)),
    new Promise((resolve) => second.listen(0, "127.0.0.1", resolve)),
  ])
  t.after(() => Promise.all([
    new Promise((resolve, reject) => first.close((error) => error ? reject(error) : resolve())),
    new Promise((resolve, reject) => second.close((error) => error ? reject(error) : resolve())),
  ]))

  const firstAddress = first.address()
  const secondAddress = second.address()
  await fs.writeFile(path.join(configDir, "defaults.yaml"), "version: 1\nconfig: {}\n")
  await fs.writeFile(path.join(configDir, "plugins.yaml"), "version: 1\nplugins: []\nbootstrap: {}\n")
  await fs.writeFile(path.join(configDir, "imagegen.yaml"), [
    "version: 1",
    "defaultProfile: first",
    "profiles:",
    "  first:",
    "    provider: first",
    "    api: images",
    `    baseURL: http://127.0.0.1:${firstAddress.port}/v1`,
    "    model: image-model",
    "    secret: first-key",
    "    size: 1024x1024",
    "    quality: high",
    "    outputFormat: png",
    "    timeoutMs: 30",
    "  second:",
    "    provider: second",
    "    api: images",
    `    baseURL: http://127.0.0.1:${secondAddress.port}/v1`,
    "    model: image-model",
    "    secret: second-key",
    "    size: 1024x1024",
    "    quality: high",
    "    outputFormat: png",
    "    timeoutMs: 30",
    "routes:",
    "  preferred:",
    "    profiles: [first, second]",
    "    fallbackOnAmbiguousTimeout: false",
    "",
  ].join("\n"))
  const fakeSops = path.join(configDir, "fake-sops.mjs")
  await fs.writeFile(fakeSops, [
    "#!/usr/bin/env node",
    "console.log(JSON.stringify({version: 1, secrets: {'first-key': 'first-secret', 'second-key': 'second-secret'}}))",
    "",
  ].join("\n"))
  await fs.chmod(fakeSops, 0o755)

  const result = JSON.parse(await runImagegenAsync(cwd, [
    "--prompt",
    "fallback image",
    "--route",
    "preferred",
    "--out",
    "fallback.png",
  ], {
    LABFLOW_CONFIG_DIR: configDir,
    LABFLOW_SOPS_BIN: fakeSops,
    OPENCODE_CONFIG_DIR: path.join(configDir, "global"),
    OPENCODE_IMAGEGEN_API: null,
    OPENCODE_IMAGEGEN_MODEL: null,
    OPENCODE_IMAGEGEN_PROVIDER: null,
    OPENCODE_IMAGEGEN_API_KEY: null,
    OPENCODE_IMAGEGEN_BASE_URL: null,
  }))

  assert.equal(result.profile, "second")
  assert.equal(result.route, "preferred")
  assert.equal(JSON.stringify(result).includes("first-secret"), false)
  assert.match(result.failed_profiles[0].error, /download image URL \(503 <redacted>.*\)/)
  assert.deepEqual(result.attempted_profiles, ["first", "second"])
  assert.deepEqual(requests, [
    { provider: "first", authorization: "Bearer first-secret" },
    { provider: "second", authorization: "Bearer second-secret" },
  ])
  assert.deepEqual(await fs.readFile(path.join(cwd, "fallback.png")), PNG_BYTES)
  assert.deepEqual((await fs.readdir(cwd)).filter((name) => name.startsWith(".labflow-imagegen-")), [])

  const routeArgs = ["--prompt", "bounded download", "--route", "preferred", "--out", "rejected.png"]
  const routeEnvironment = {
    LABFLOW_CONFIG_DIR: configDir,
    LABFLOW_SOPS_BIN: fakeSops,
    OPENCODE_CONFIG_DIR: path.join(configDir, "global"),
    OPENCODE_IMAGEGEN_API: null,
    OPENCODE_IMAGEGEN_MODEL: null,
    OPENCODE_IMAGEGEN_PROVIDER: null,
    OPENCODE_IMAGEGEN_API_KEY: null,
    OPENCODE_IMAGEGEN_BASE_URL: null,
  }
  assetMode = "timeout"
  await assert.rejects(runImagegenAsync(cwd, routeArgs, routeEnvironment), /timed out|aborted/i)
  assert.equal(requests.filter((request) => request.provider === "second").length, 1)

  assetMode = "oversized"
  await assert.rejects(runImagegenAsync(cwd, routeArgs, routeEnvironment), /exceeds the 50 MiB limit/)
  assert.equal(requests.filter((request) => request.provider === "second").length, 1)

  assetMode = "api-oversized"
  await assert.rejects(runImagegenAsync(cwd, routeArgs, routeEnvironment), /API response exceeds/)
  assert.equal(requests.filter((request) => request.provider === "second").length, 1)
})

test("CLI rejects output directories that escape through symlinks", async (t) => {
  const cwd = await temporaryDirectory(t, "labflow-imagegen-symlink-")
  const outside = await temporaryDirectory(t, "labflow-imagegen-symlink-outside-")
  await fs.symlink(outside, path.join(cwd, "escape"), "dir")

  assert.throws(
    () => runImagegen(cwd, ["--prompt", "escape", "--out", "escape/image.png", "--force", "--dry-run"]),
    /must not escape.*symlinks/,
  )
  assert.deepEqual(await fs.readdir(outside), [])
})

test("plugin edits the current user attachment through the CLI", async (t) => {
  const cwd = await temporaryDirectory(t, "labflow-imagegen-plugin-")
  const requests = []
  const server = http.createServer(async (request, response) => {
    const chunks = []
    for await (const chunk of request) chunks.push(chunk)
    requests.push(JSON.parse(Buffer.concat(chunks).toString("utf8")))
    response.writeHead(200, { "Content-Type": "application/json" })
    response.end(JSON.stringify({
      id: "resp_test",
      output: [
        {
          id: "ig_test",
          type: "image_generation_call",
          action: "edit",
          status: "completed",
          result: PNG_BASE64,
          revised_prompt: "Change only the color.",
          output_format: "png",
          size: "1254x1254",
          quality: "low",
        },
      ],
    }))
  })
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve))
  t.after(() => new Promise((resolve, reject) => server.close((error) => error ? reject(error) : resolve())))

  const address = server.address()
  const previousEnvironment = {
    baseURL: process.env.OPENCODE_IMAGEGEN_BASE_URL,
    apiKey: process.env.OPENCODE_IMAGEGEN_API_KEY,
    api: process.env.OPENCODE_IMAGEGEN_API,
    model: process.env.OPENCODE_IMAGEGEN_MODEL,
  }
  process.env.OPENCODE_IMAGEGEN_BASE_URL = `http://127.0.0.1:${address.port}/v1`
  process.env.OPENCODE_IMAGEGEN_API_KEY = "test-key"
  process.env.OPENCODE_IMAGEGEN_API = "responses"
  process.env.OPENCODE_IMAGEGEN_MODEL = "test-image-model"
  t.after(() => {
    restoreEnvironment("OPENCODE_IMAGEGEN_BASE_URL", previousEnvironment.baseURL)
    restoreEnvironment("OPENCODE_IMAGEGEN_API_KEY", previousEnvironment.apiKey)
    restoreEnvironment("OPENCODE_IMAGEGEN_API", previousEnvironment.api)
    restoreEnvironment("OPENCODE_IMAGEGEN_MODEL", previousEnvironment.model)
  })

  const plugin = await import(`${new URL(`file://${PLUGIN_PATH}`).href}?test=${Date.now()}`)
  const hooks = await plugin.default()
  t.after(() => hooks.dispose())

  const sessionID = "attachment-session"
  await hooks["chat.message"](
    { sessionID, agent: "labflow-develop" },
    {
      message: {},
      parts: [
        {
          type: "file",
          mime: "image/png",
          url: `data:image/png;base64,${PNG_BASE64}`,
          filename: "reference.png",
        },
      ],
    },
  )

  const metadata = []
  const result = await hooks.tool.imagegen.execute(
    {
      prompt: "Change only the color.",
      useAttachedImages: true,
      size: "1024x1024",
      quality: "low",
      outputFormat: "png",
      out: "edited.png",
    },
    {
      sessionID,
      messageID: "assistant-message",
      agent: "labflow-develop",
      directory: cwd,
      worktree: cwd,
      abort: new AbortController().signal,
      metadata: (value) => metadata.push(value),
      ask: async () => {},
    },
  )

  assert.equal(requests.length, 1)
  assert.equal(requests[0].tools[0].action, "edit")
  assert.equal(requests[0].tools[0].output_format, "png")
  assert.equal("format" in requests[0].tools[0], false)
  assert.equal(requests[0].input[0].content[1].type, "input_image")
  assert.match(requests[0].input[0].content[1].image_url, /^data:image\/png;base64,/)
  assert.equal(result.metadata.generation_mode, "edit")
  assert.equal(result.metadata.input_image_count, 1)
  assert.equal(result.metadata.actual_size, "1254x1254")
  assert.match(result.output, /Edited image\./)
  assert.match(result.output, /requested_size: 1024x1024/)
  assert.match(result.output, /actual_size: 1254x1254/)
  assert.match(result.output, /input_images: attached:reference\.png/)
  assert.deepEqual(await fs.readFile(path.join(cwd, "edited.png")), PNG_BYTES)
  assert.equal(metadata.at(-1).title, "Edited image")

  await assert.rejects(
    hooks.tool.imagegen.execute(
      { prompt: "retry", useAttachedImages: true, out: "retry.png" },
      {
        sessionID,
        messageID: "assistant-message-2",
        agent: "labflow-develop",
        directory: cwd,
        worktree: cwd,
        abort: new AbortController().signal,
        metadata: () => {},
        ask: async () => {},
      },
    ),
    /no supported image is attached to the current user message/,
  )

  const concurrentSessionID = "concurrent-attachment-session"
  await hooks["chat.message"](
    { sessionID: concurrentSessionID, agent: "labflow-develop" },
    {
      message: {},
      parts: [{ type: "file", mime: "image/png", url: `data:image/png;base64,${PNG_BASE64}`, filename: "old.png" }],
    },
  )
  const concurrentContext = {
    sessionID: concurrentSessionID,
    messageID: "concurrent-assistant-message",
    agent: "labflow-develop",
    directory: cwd,
    worktree: cwd,
    abort: new AbortController().signal,
    metadata: () => {},
    ask: async () => {},
  }
  const oldStateCall = hooks.tool.imagegen.execute(
    { prompt: "edit old", useAttachedImages: true, out: "old-state.png" },
    concurrentContext,
  )
  await hooks["chat.message"](
    { sessionID: concurrentSessionID, agent: "labflow-develop" },
    {
      message: {},
      parts: [{ type: "file", mime: "image/png", url: `data:image/png;base64,${PNG_BASE64}`, filename: "new.png" }],
    },
  )
  await oldStateCall
  const newStateResult = await hooks.tool.imagegen.execute(
    { prompt: "edit new", useAttachedImages: true, out: "new-state.png" },
    { ...concurrentContext, messageID: "concurrent-assistant-message-2" },
  )
  assert.match(newStateResult.output, /input_images: attached:new\.png/)

  const latestSessionID = "latest-attachment-session"
  await hooks["chat.message"](
    { sessionID: latestSessionID, agent: "labflow-develop" },
    {
      message: {},
      parts: [{ type: "file", mime: "image/png", url: `data:image/png;base64,${PNG_BASE64}`, filename: "previous.png" }],
    },
  )
  await hooks["chat.message"](
    { sessionID: latestSessionID, agent: "labflow-develop" },
    { message: {}, parts: [] },
  )
  const latestContext = { ...concurrentContext, sessionID: latestSessionID }
  await assert.rejects(
    hooks.tool.imagegen.execute({ prompt: "current only", useAttachedImages: true }, latestContext),
    /no supported image is attached to the current user message/,
  )
  const latestResult = await hooks.tool.imagegen.execute(
    { prompt: "use previous upload", useLatestAttachedImages: true, out: "latest-state.png" },
    latestContext,
  )
  assert.match(latestResult.output, /input_images: attached:previous\.png/)
  await assert.rejects(
    hooks.tool.imagegen.execute({ prompt: "retry latest", useLatestAttachedImages: true }, latestContext),
    /no retained image is available from the latest image-bearing user message/,
  )
  await assert.rejects(
    hooks.tool.imagegen.execute(
      { prompt: "ambiguous", useAttachedImages: true, useLatestAttachedImages: true },
      latestContext,
    ),
    /mutually exclusive/,
  )
  assert.equal(requests.length, 4)
})

test("plugin clears stale attachments and rejects paths outside the worktree", async (t) => {
  const cwd = await temporaryDirectory(t, "labflow-imagegen-scope-")
  const outside = await temporaryDirectory(t, "labflow-imagegen-outside-")
  const outsideImage = path.join(outside, "outside.png")
  await fs.writeFile(outsideImage, PNG_BYTES)

  const plugin = await import(`${new URL(`file://${PLUGIN_PATH}`).href}?scope=${Date.now()}`)
  const hooks = await plugin.default()
  t.after(() => hooks.dispose())

  await hooks["chat.message"](
    { sessionID: "stale-session", agent: "labflow-develop" },
    {
      message: {},
      parts: [{ type: "file", mime: "image/png", url: `data:image/png;base64,${PNG_BASE64}` }],
    },
  )
  await hooks.event({
    event: {
      type: "session.deleted",
      properties: { info: { id: "stale-session" } },
    },
  })

  const context = {
    sessionID: "stale-session",
    messageID: "assistant-message",
    agent: "labflow-develop",
    directory: cwd,
    worktree: cwd,
    abort: new AbortController().signal,
    metadata: () => {},
    ask: async () => {},
  }
  await assert.rejects(
    hooks.tool.imagegen.execute({ prompt: "edit", useAttachedImages: true }, context),
    /no supported image is attached to the current user message/,
  )
  await assert.rejects(
    hooks.tool.imagegen.execute({ prompt: "edit", useLatestAttachedImages: true }, context),
    /no retained image is available from the latest image-bearing user message/,
  )

  await hooks["chat.message"](
    { sessionID: "next-turn-session", agent: "labflow-develop" },
    {
      message: {},
      parts: [{ type: "file", mime: "image/png", url: `data:image/png;base64,${PNG_BASE64}` }],
    },
  )
  await hooks["chat.message"](
    { sessionID: "next-turn-session", agent: "labflow-develop" },
    { message: {}, parts: [] },
  )
  await assert.rejects(
    hooks.tool.imagegen.execute(
      { prompt: "edit", useAttachedImages: true },
      { ...context, sessionID: "next-turn-session" },
    ),
    /no supported image is attached to the current user message/,
  )

  await hooks["chat.message"](
    { sessionID: "failed-session", agent: "labflow-develop" },
    {
      message: {},
      parts: [{ type: "file", mime: "image/png", url: "data:image/png;base64,AAAA" }],
    },
  )
  const failedContext = { ...context, sessionID: "failed-session" }
  await assert.rejects(
    hooks.tool.imagegen.execute({ prompt: "edit", useAttachedImages: true }, failedContext),
    /content does not match declared MIME/,
  )
  await assert.rejects(
    hooks.tool.imagegen.execute({ prompt: "retry", useAttachedImages: true }, failedContext),
    /no supported image is attached to the current user message/,
  )

  await assert.rejects(
    hooks.tool.imagegen.execute({ prompt: "edit", inputImages: [outsideImage] }, context),
    /input image must stay inside the current worktree/,
  )
  const outsideLink = path.join(cwd, "outside-link.png")
  await fs.symlink(outsideImage, outsideLink)
  await assert.rejects(
    hooks.tool.imagegen.execute({ prompt: "edit", inputImages: [outsideLink] }, context),
    /input image must stay inside the current worktree/,
  )

  const largeImages = []
  for (let index = 0; index < 3; index += 1) {
    const imagePath = path.join(cwd, `large-${index}.png`)
    await fs.writeFile(imagePath, PNG_BYTES)
    await fs.truncate(imagePath, 18 * 1024 * 1024)
    largeImages.push(imagePath)
  }
  await assert.rejects(
    hooks.tool.imagegen.execute({ prompt: "edit", inputImages: largeImages }, context),
    /input images exceed the 50 MiB total limit/,
  )
})

function restoreEnvironment(name, value) {
  if (value === undefined) {
    delete process.env[name]
  } else {
    process.env[name] = value
  }
}
