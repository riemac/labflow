// labflow opencode plugin — injected via opencode.json "plugin" field.
// Assets live next to the plugin under .../labflow/.
import { execFile } from "node:child_process"
import * as fs from "fs"
import * as os from "node:os"
import * as path from "path"
import { fileURLToPath } from "node:url"
import { promisify } from "node:util"
import { tool } from "@opencode-ai/plugin"
import { parse as parseYaml } from "yaml"
import { applyManagedOpenCodeConfig, readManagedConfig, SecretStore } from "../scripts/config.mjs"

const ASSETS = path.join(path.dirname(fileURLToPath(import.meta.url)), "..") // opencode/ root
const IMAGEGEN_SCRIPT = path.join(ASSETS, "scripts", "imagegen.mjs")
const NODE_BIN = process.env.LABFLOW_IMAGEGEN_NODE || "node"
const execFileAsync = promisify(execFile)
const MAX_INPUT_IMAGES = 4
const MAX_INPUT_IMAGE_BYTES = 20 * 1024 * 1024
const MAX_TOTAL_INPUT_IMAGE_BYTES = 50 * 1024 * 1024
const SUPPORTED_IMAGE_MIMES = new Set(["image/png", "image/jpeg", "image/webp"])
type AttachedImageState = { images: Array<{ mime: string; url: string; filename?: string }> }
const currentAttachedImagesBySession = new Map<string, AttachedImageState>()
const latestAttachedImagesBySession = new Map<string, AttachedImageState>()

// Agent files are the single source of truth for both configuration and prompt.
// OpenCode cannot expand `{file:...}` values added by a late config hook, so the
// plugin parses the conventional Markdown frontmatter itself during startup.
// Invalid or missing definitions fail fast instead of silently inheriting the
// primary agent model or sending YAML configuration to the model as prose.
function readAgentDefinition(name: string): Record<string, unknown> {
  const source = fs.readFileSync(path.join(ASSETS, "agents", name + ".md"), "utf-8")
  const match = source.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n?([\s\S]*)$/)
  if (!match) throw new Error(`Agent definition has no valid frontmatter: ${name}`)
  const metadata = parseYaml(match[1])
  if (!metadata || typeof metadata !== "object" || Array.isArray(metadata)) {
    throw new Error(`Agent frontmatter is not a mapping: ${name}`)
  }
  return { ...(metadata as Record<string, unknown>), prompt: match[2].trimStart() }
}

const imagegenTool = tool({
  description:
    "Generate or edit raster images through labflow's configured OpenAI-compatible image API. Accepts workspace paths plus explicitly selected current-message or latest session attachments.",
  args: {
    prompt: tool.schema.string().min(1).describe("Final image prompt to send to the image model"),
    inputImages: tool.schema
      .array(tool.schema.string().min(1))
      .max(MAX_INPUT_IMAGES)
      .optional()
      .describe("Up to four workspace PNG/JPEG/WebP paths, 20 MiB each and 50 MiB total; omit for text-only generation"),
    useAttachedImages: tool.schema
      .boolean()
      .optional()
      .describe("Use image attachments from the current user message as references"),
    useLatestAttachedImages: tool.schema
      .boolean()
      .optional()
      .describe("Use images from the latest image-bearing user message in this session"),
    profile: tool.schema.string().optional().describe("Named imagegen profile; mutually exclusive with route"),
    route: tool.schema.string().optional().describe("Named ordered fallback route; mutually exclusive with profile and model"),
    model: tool.schema.string().optional().describe("Image model override"),
    size: tool.schema.string().optional().describe("Image size such as 1024x1024 or 3840x2160"),
    quality: tool.schema.enum(["low", "medium", "high", "auto"]).optional().describe("Rendering quality"),
    outputFormat: tool.schema.enum(["png", "jpeg", "jpg", "webp"]).optional().describe("Output image format"),
    n: tool.schema.number().int().min(1).max(4).optional().describe("Number of variants to generate"),
    out: tool.schema.string().optional().describe("Workspace-relative output path"),
    outDir: tool.schema.string().optional().describe("Workspace-relative output directory"),
    force: tool.schema.boolean().optional().describe("Overwrite existing output files"),
  },
  async execute(args, context) {
    if (args.useAttachedImages && args.useLatestAttachedImages) {
      throw new Error("imagegen failed: useAttachedImages and useLatestAttachedImages are mutually exclusive")
    }
    if (args.profile && args.route) throw new Error("imagegen failed: profile and route are mutually exclusive")
    if (args.route && args.model) throw new Error("imagegen failed: route and model are mutually exclusive")
    const attachedState = args.useAttachedImages
      ? currentAttachedImagesBySession.get(context.sessionID)
      : args.useLatestAttachedImages
        ? latestAttachedImagesBySession.get(context.sessionID)
        : undefined
    const attachedImages = attachedState ? [...attachedState.images] : []
    let temporaryInputs
    try {
      if (args.useAttachedImages && attachedImages.length === 0) {
        throw new Error("no supported image is attached to the current user message")
      }
      if (args.useLatestAttachedImages && attachedImages.length === 0) {
        throw new Error("no retained image is available from the latest image-bearing user message")
      }

      const budget = { bytes: 0 }
      const explicitInputImages = await snapshotWorkspaceInputImages(args.inputImages ?? [], context, budget)
      if (explicitInputImages.length + attachedImages.length > MAX_INPUT_IMAGES) {
        throw new Error(`provide at most ${MAX_INPUT_IMAGES} input images in total`)
      }
      const attachedInputImages = await snapshotAttachedImages(attachedImages, budget)
      const inputImages = [...explicitInputImages, ...attachedInputImages]

      const mode = inputImages.length > 0 ? "edit" : "generate"
      context.metadata({ title: mode === "edit" ? "Edit image" : "Generate image" })
      const inputImageMetadata = inputImages.map(({ source, mime, bytes }) => ({ source, mime, bytes: bytes.length }))
      temporaryInputs = await materializeInputImages(inputImages)
      inputImages.length = 0
      explicitInputImages.length = 0
      attachedInputImages.length = 0

      const cliArgs = buildImagegenArgs({ ...args, inputImages: temporaryInputs.paths })
      const { stdout } = await execFileAsync(NODE_BIN, [IMAGEGEN_SCRIPT, ...cliArgs], {
        cwd: context.directory,
        signal: context.abort,
        maxBuffer: 2 * 1024 * 1024,
      })
      const result = parseImagegenResult(stdout)
      result.input_images = inputImageMetadata
      context.metadata({
        title: result.generation_mode === "edit" ? "Edited image" : "Generated image",
        metadata: {
          outputs: result.outputs,
          model: result.model,
          size: result.size,
          actualSize: result.actual_size,
          quality: result.quality,
          generationMode: result.generation_mode,
          inputImageCount: result.input_image_count,
        },
      })
      return {
        output: formatImagegenToolOutput(result),
        metadata: result,
      }
    } catch (error) {
      throw new Error(`imagegen failed: ${formatExecError(error)}`)
    } finally {
      if (attachedState) consumeAttachedState(context.sessionID, attachedState)
      if (temporaryInputs?.directory) {
        await fs.promises.rm(temporaryInputs.directory, { recursive: true, force: true })
      }
    }
  },
})

function buildImagegenArgs(args): string[] {
  const cliArgs = ["generate", "--prompt", args.prompt]
  for (const inputImage of args.inputImages ?? []) pushFlag(cliArgs, "--input-image", inputImage)
  pushFlag(cliArgs, "--profile", args.profile)
  pushFlag(cliArgs, "--route", args.route)
  pushFlag(cliArgs, "--model", args.model)
  pushFlag(cliArgs, "--size", args.size)
  pushFlag(cliArgs, "--quality", args.quality)
  pushFlag(cliArgs, "--output-format", args.outputFormat)
  pushFlag(cliArgs, "--n", args.n)
  pushFlag(cliArgs, "--out", args.out)
  pushFlag(cliArgs, "--out-dir", args.outDir)
  if (args.force) cliArgs.push("--force")
  return cliArgs
}

function pushFlag(cliArgs: string[], flag: string, value: unknown) {
  if (value === undefined || value === null || value === "") return
  cliArgs.push(flag, String(value))
}

function parseImagegenResult(stdout: string) {
  try {
    return JSON.parse(stdout)
  } catch {
    throw new Error(`imagegen returned non-JSON output: ${stdout.slice(0, 800)}`)
  }
}

function formatImagegenToolOutput(result): string {
  const outputs = Array.isArray(result.outputs) ? result.outputs : []
  const lines = [result.generation_mode === "edit" ? "Edited image." : "Generated image."]
  if (outputs.length > 0) lines.push(`outputs: ${outputs.join(", ")}`)
  if (result.profile) lines.push(`profile: ${result.profile}`)
  if (result.route) lines.push(`route: ${result.route}`)
  if (result.model) lines.push(`model: ${result.model}`)
  if (result.generation_mode) lines.push(`generation_mode: ${result.generation_mode}`)
  if (Number.isInteger(result.input_image_count)) lines.push(`input_image_count: ${result.input_image_count}`)
  if (Array.isArray(result.input_images) && result.input_images.length > 0) {
    lines.push(`input_images: ${result.input_images.map((image) => image.source).join(", ")}`)
  }
  if (result.size) lines.push(`requested_size: ${result.size}`)
  if (result.actual_size) lines.push(`actual_size: ${result.actual_size}`)
  if (result.quality) lines.push(`quality: ${result.quality}`)
  if (result.output_format) lines.push(`output_format: ${result.output_format}`)
  if (result.revised_prompt) lines.push(`revised_prompt: ${result.revised_prompt}`)
  lines.push("Read the output path if you need to inspect the generated image in context.")
  return lines.join("\n")
}

async function snapshotWorkspaceInputImages(rawPaths, context, budget) {
  const roots = await Promise.all(
    [...new Set([context.directory, context.worktree])].map((root) => fs.promises.realpath(root)),
  )
  const resolved = []
  const seen = new Set()
  for (const rawPath of rawPaths) {
    if (/^[a-z][a-z0-9+.-]*:/i.test(rawPath)) {
      throw new Error(`inputImages accepts local workspace paths, not URLs: ${rawPath}`)
    }
    const candidate = path.isAbsolute(rawPath) ? rawPath : path.resolve(context.directory, rawPath)
    let realPath
    try {
      realPath = await fs.promises.realpath(candidate)
    } catch (error) {
      throw new Error(`could not read input image ${rawPath}: ${error.message}`)
    }
    if (!roots.some((root) => pathIsInside(root, realPath))) {
      throw new Error(`input image must stay inside the current worktree: ${rawPath}`)
    }
    if (seen.has(realPath)) continue
    seen.add(realPath)
    const bytes = await readBoundedFile(realPath, rawPath, budget, roots)
    const mime = imageMimeType(bytes)
    if (!mime) throw new Error(`unsupported input image format: ${rawPath} (expected PNG, JPEG, or WebP)`)
    resolved.push({
      source: workspaceDisplayPath(realPath, context.directory),
      mime,
      bytes,
    })
  }
  return resolved
}

function pathIsInside(root, candidate) {
  const relative = path.relative(root, candidate)
  return relative === "" || (!relative.startsWith("..") && !path.isAbsolute(relative))
}

function workspaceDisplayPath(filePath, directory) {
  const relative = path.relative(directory, filePath)
  return relative || path.basename(filePath)
}

async function snapshotAttachedImages(images, budget) {
  const snapshots = []
  for (let index = 0; index < images.length; index += 1) {
    const image = images[index]
    const declaredMime = normalizeImageMime(image.mime)
    if (!SUPPORTED_IMAGE_MIMES.has(declaredMime)) {
      throw new Error(`unsupported attached image MIME: ${image.mime}`)
    }

    let bytes
    if (image.url.startsWith("data:")) {
      const match = image.url.match(/^data:([^;,]+);base64,([\s\S]+)$/)
      if (!match || normalizeImageMime(match[1]) !== declaredMime) {
        throw new Error(`invalid attached ${declaredMime} data URL`)
      }
      claimInputBytes(decodedBase64Bytes(match[2]), budget, "attached image")
      bytes = Buffer.from(match[2], "base64")
    } else if (image.url.startsWith("file:")) {
      const filePath = await fs.promises.realpath(fileURLToPath(image.url))
      bytes = await readBoundedFile(filePath, image.filename ?? `attachment ${index + 1}`, budget)
    } else {
      throw new Error("attached images must use data: or file: URLs")
    }

    const actualMime = imageMimeType(bytes)
    if (actualMime !== declaredMime) {
      throw new Error(`attached image content does not match declared MIME ${image.mime}`)
    }
    snapshots.push({
      source: `attached:${image.filename || `image-${index + 1}.${extensionForMime(actualMime)}`}`,
      mime: actualMime,
      bytes,
    })
  }
  return snapshots
}

async function materializeInputImages(images) {
  if (images.length === 0) return { directory: undefined, paths: [] }
  const directory = await fs.promises.mkdtemp(path.join(os.tmpdir(), "labflow-imagegen-"))
  try {
    const paths = []
    for (let index = 0; index < images.length; index += 1) {
      const image = images[index]
      const outputPath = path.join(directory, `input-${index + 1}.${extensionForMime(image.mime)}`)
      await fs.promises.writeFile(outputPath, image.bytes)
      paths.push(outputPath)
    }
    return { directory, paths }
  } catch (error) {
    await fs.promises.rm(directory, { recursive: true, force: true })
    throw error
  }
}

async function readBoundedFile(filePath, displayPath, budget, allowedRoots) {
  const noFollow = fs.constants.O_NOFOLLOW ?? 0
  const handle = await fs.promises.open(filePath, fs.constants.O_RDONLY | noFollow)
  try {
    const stat = await handle.stat()
    if (!stat.isFile()) throw new Error(`input image is not a regular file: ${displayPath}`)
    if (allowedRoots) {
      const openedPath = await openedFilePath(handle, filePath, stat)
      if (!allowedRoots.some((root) => pathIsInside(root, openedPath))) {
        throw new Error(`input image must stay inside the current worktree: ${displayPath}`)
      }
    }
    claimInputBytes(stat.size, budget, `input image ${displayPath}`)
    const buffer = Buffer.alloc(stat.size)
    let offset = 0
    while (offset < buffer.length) {
      const { bytesRead } = await handle.read(buffer, offset, buffer.length - offset, offset)
      if (bytesRead === 0) break
      offset += bytesRead
    }
    return buffer.subarray(0, offset)
  } finally {
    await handle.close()
  }
}

async function openedFilePath(handle, fallbackPath, openedStat) {
  for (const descriptorPath of [`/proc/self/fd/${handle.fd}`, `/dev/fd/${handle.fd}`]) {
    try {
      return await fs.promises.realpath(descriptorPath)
    } catch {}
  }

  const currentPath = await fs.promises.realpath(fallbackPath)
  const currentStat = await fs.promises.stat(currentPath)
  if (currentStat.dev !== openedStat.dev || currentStat.ino !== openedStat.ino) {
    throw new Error("input image changed while it was being opened")
  }
  return currentPath
}

function claimInputBytes(bytes, budget, label) {
  if (bytes > MAX_INPUT_IMAGE_BYTES) {
    throw new Error(`${label} exceeds the ${formatMiB(MAX_INPUT_IMAGE_BYTES)} per-image limit`)
  }
  if (budget.bytes + bytes > MAX_TOTAL_INPUT_IMAGE_BYTES) {
    throw new Error(`input images exceed the ${formatMiB(MAX_TOTAL_INPUT_IMAGE_BYTES)} total limit`)
  }
  budget.bytes += bytes
}

function imageMimeType(bytes) {
  if (bytes.length >= 8 && bytes.subarray(0, 8).equals(Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]))) {
    return "image/png"
  }
  if (bytes.length >= 3 && bytes[0] === 0xff && bytes[1] === 0xd8 && bytes[2] === 0xff) {
    return "image/jpeg"
  }
  if (bytes.length >= 12 && bytes.toString("ascii", 0, 4) === "RIFF" && bytes.toString("ascii", 8, 12) === "WEBP") {
    return "image/webp"
  }
  return undefined
}

function normalizeImageMime(mime) {
  const normalized = String(mime).toLowerCase()
  return normalized === "image/jpg" ? "image/jpeg" : normalized
}

function decodedBase64Bytes(value) {
  const padding = value.endsWith("==") ? 2 : value.endsWith("=") ? 1 : 0
  return Math.floor((value.length * 3) / 4) - padding
}

function formatMiB(bytes) {
  return `${bytes / (1024 * 1024)} MiB`
}

function extensionForMime(mime) {
  if (mime === "image/jpeg") return "jpg"
  return mime.slice("image/".length)
}

function captureAttachedImages(sessionID, parts) {
  const images = parts
    .filter((part) => part?.type === "file" && typeof part.mime === "string" && part.mime.startsWith("image/") && typeof part.url === "string")
    .map((part) => ({ mime: part.mime, url: part.url, filename: part.filename }))
    .filter((part, index, all) => all.findIndex((candidate) => candidate.url === part.url) === index)
  if (images.length > 0) {
    const state = { images }
    currentAttachedImagesBySession.set(sessionID, state)
    latestAttachedImagesBySession.set(sessionID, state)
  } else {
    currentAttachedImagesBySession.delete(sessionID)
  }
}

function consumeAttachedState(sessionID, state) {
  if (currentAttachedImagesBySession.get(sessionID) === state) currentAttachedImagesBySession.delete(sessionID)
  if (latestAttachedImagesBySession.get(sessionID) === state) latestAttachedImagesBySession.delete(sessionID)
}

function clearAttachedStates(sessionID) {
  currentAttachedImagesBySession.delete(sessionID)
  latestAttachedImagesBySession.delete(sessionID)
}

function formatExecError(error: unknown): string {
  if (!(error instanceof Error)) return String(error)
  const detail = [
    error.message,
    typeof (error as any).stderr === "string" ? (error as any).stderr.trim() : "",
    typeof (error as any).stdout === "string" ? (error as any).stdout.trim() : "",
  ]
    .filter(Boolean)
    .join("\n")
  return detail.slice(0, 2000)
}

export default async () => {
  const managedConfig = await readManagedConfig()
  const secretStore = new SecretStore({
    secretPath: path.join(managedConfig.configDir, "secrets.sops.yaml"),
  })

  return {
  dispose: async () => {
    secretStore.dispose()
    currentAttachedImagesBySession.clear()
    latestAttachedImagesBySession.clear()
  },
  event: async ({ event }) => {
    if (event.type === "session.deleted") clearAttachedStates(event.properties.info.id)
  },
  "chat.message": async (input, output) => {
    captureAttachedImages(input.sessionID, output.parts)
  },
  tool: {
    imagegen: imagegenTool,
  },
  config(cfg) {
    applyManagedOpenCodeConfig(cfg, managedConfig, secretStore)
    cfg.instructions = [...(cfg.instructions ?? []), ASSETS + "/labflow-rules.md"]

    cfg.agent = {
      ...cfg.agent,
      "labflow-develop": readAgentDefinition("labflow-develop"),
      "labflow-plan": readAgentDefinition("labflow-plan"),
      "labflow-paper": readAgentDefinition("labflow-paper"),
      // Keep the bundled worker definition portable while allowing user config to select its provider/model.
      "literature-worker": {
        ...readAgentDefinition("literature-worker"),
        ...cfg.agent?.["literature-worker"],
      },
    }

    cfg.skills = { paths: [...(cfg.skills?.paths ?? []), ASSETS + "/skills"] }
  },
  }
}
