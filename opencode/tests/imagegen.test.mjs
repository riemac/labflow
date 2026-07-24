import assert from "node:assert/strict"
import { execFileSync } from "node:child_process"
import * as fs from "node:fs/promises"
import * as http from "node:http"
import * as os from "node:os"
import * as path from "node:path"
import { fileURLToPath } from "node:url"
import test from "node:test"

const OPENCODE_DIR = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..")
const IMAGEGEN_SCRIPT = path.join(OPENCODE_DIR, "scripts", "imagegen.mjs")
const PLUGIN_PATH = path.join(OPENCODE_DIR, "plugins", "labflow.ts")
const PNG_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9ZrN8AAAAASUVORK5CYII="
const PNG_BYTES = Buffer.from(PNG_BASE64, "base64")

function runImagegen(cwd, args, env = {}) {
  return execFileSync(process.execPath, [IMAGEGEN_SCRIPT, "generate", ...args], {
    cwd,
    encoding: "utf8",
    env: {
      ...process.env,
      OPENCODE_IMAGEGEN_API: "responses",
      OPENCODE_IMAGEGEN_MODEL: "test-image-model",
      ...env,
    },
    maxBuffer: 4 * 1024 * 1024,
  })
}

async function temporaryDirectory(t, prefix) {
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), prefix))
  t.after(() => fs.rm(directory, { recursive: true, force: true }))
  return directory
}

test("CLI preserves text-only Responses payloads", async (t) => {
  const cwd = await temporaryDirectory(t, "labflow-imagegen-fresh-")
  const result = JSON.parse(runImagegen(cwd, ["--prompt", "fresh image", "--dry-run"]))

  assert.equal(result.generation_mode, "generate")
  assert.equal(result.input_image_count, 0)
  assert.equal(result.payload.input, "fresh image")
  assert.equal("action" in result.payload.tools[0], false)
})

test("CLI builds a redacted multi-image edit payload", async (t) => {
  const cwd = await temporaryDirectory(t, "labflow-imagegen-edit-")
  await fs.writeFile(path.join(cwd, "first.png"), PNG_BYTES)
  await fs.writeFile(path.join(cwd, "second.png"), PNG_BYTES)

  const result = JSON.parse(runImagegen(cwd, [
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
  assert.equal(requests.length, 3)
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
