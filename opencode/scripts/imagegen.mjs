#!/usr/bin/env node

import { Buffer } from "node:buffer"
import { randomUUID } from "node:crypto"
import * as fs from "node:fs/promises"
import * as path from "node:path"

const DEFAULT_MODEL = process.env.OPENCODE_IMAGEGEN_MODEL || "gpt-image-2"
const DEFAULT_SIZE = process.env.OPENCODE_IMAGEGEN_SIZE || "3840x2160"
const DEFAULT_QUALITY = process.env.OPENCODE_IMAGEGEN_QUALITY || "high"
const DEFAULT_FORMAT = "png"
const DEFAULT_OUT_DIR = process.env.OPENCODE_IMAGEGEN_OUT_DIR || "figures/imagegen"
const MAX_VARIANTS = 4

const VALID_QUALITIES = new Set(["low", "medium", "high", "auto"])
const VALID_FORMATS = new Set(["png", "jpeg", "jpg", "webp"])

main().catch((error) => {
  console.error(`imagegen error: ${error.message}`)
  process.exit(1)
})

async function main() {
  const { command, flags } = parseArgs(process.argv.slice(2))
  if (flags.help || command === "help") {
    printHelp()
    return
  }
  if (command !== "generate") {
    throw new Error(`unknown command: ${command}`)
  }

  const prompt = await readPrompt(flags)
  const opencodeConfig = await readOpencodeConfig()
  const openaiOptions = opencodeConfig?.provider?.openai?.options ?? {}
  const apiKey =
    flags["api-key"] ||
    resolveConfigString(openaiOptions.apiKey) ||
    process.env.OPENAI_API_KEY
  const baseURL =
    flags["base-url"] ||
    resolveConfigString(openaiOptions.baseURL) ||
    process.env.OPENAI_BASE_URL ||
    "https://api.openai.com/v1"

  const model = flags.model || DEFAULT_MODEL
  const size = flags.size || DEFAULT_SIZE
  const quality = flags.quality || DEFAULT_QUALITY
  const outputFormat = normalizeFormat(flags["output-format"] || DEFAULT_FORMAT)
  const count = parseCount(flags.n)

  if (!VALID_QUALITIES.has(quality)) {
    throw new Error("--quality must be one of low, medium, high, or auto")
  }
  if (!VALID_FORMATS.has(outputFormat)) {
    throw new Error("--output-format must be one of png, jpeg, jpg, or webp")
  }

  const outputPaths = await plannedOutputPaths({
    out: flags.out,
    outDir: flags["out-dir"] || DEFAULT_OUT_DIR,
    outputFormat,
    count,
    prompt,
    force: Boolean(flags.force),
  })

  const payload = {
    model,
    prompt,
    n: count,
    size,
    quality,
    output_format: outputFormat,
  }

  if (flags["dry-run"]) {
    printResult({
      ok: true,
      dry_run: true,
      endpoint: imageEndpoint(baseURL),
      payload,
      outputs: outputPaths.map(relativeToCwd),
    })
    return
  }

  if (!apiKey) {
    throw new Error(
      "missing API key: set OPENAI_API_KEY or provider.openai.options.apiKey in ~/.config/opencode/opencode.json",
    )
  }

  await fs.mkdir(path.dirname(outputPaths[0]), { recursive: true })
  const response = await fetch(imageEndpoint(baseURL), {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  })

  const body = await response.text()
  if (!response.ok) {
    throw new Error(`API failed (${response.status} ${response.statusText}): ${body.slice(0, 1600)}`)
  }

  let result
  try {
    result = JSON.parse(body)
  } catch {
    throw new Error(`API returned non-JSON response: ${body.slice(0, 400)}`)
  }

  const images = Array.isArray(result.data) ? result.data : []
  if (images.length === 0) {
    throw new Error("API returned no images in data[]")
  }

  const written = []
  for (let index = 0; index < Math.min(images.length, outputPaths.length); index += 1) {
    const bytes = await imageBytes(images[index])
    await fs.writeFile(outputPaths[index], bytes)
    written.push(relativeToCwd(outputPaths[index]))
  }

  printResult({
    ok: true,
    dry_run: false,
    model,
    size,
    quality,
    output_format: outputFormat,
    outputs: written,
    revised_prompt: result.data?.[0]?.revised_prompt,
    prompt,
  })
}

function parseArgs(argv) {
  const tokens = [...argv]
  const command = tokens[0] && !tokens[0].startsWith("--") ? tokens.shift() : "generate"
  const flags = {}
  for (let index = 0; index < tokens.length; index += 1) {
    const token = tokens[index]
    if (!token.startsWith("--")) {
      throw new Error(`unexpected positional argument: ${token}`)
    }
    const key = token.slice(2)
    if (["dry-run", "force", "prompt-stdin", "help"].includes(key)) {
      flags[key] = true
      continue
    }
    const value = tokens[index + 1]
    if (!value || value.startsWith("--")) {
      throw new Error(`missing value for --${key}`)
    }
    flags[key] = value
    index += 1
  }
  return { command, flags }
}

async function readPrompt(flags) {
  const promptSources = [flags.prompt, flags["prompt-file"], flags["prompt-stdin"]].filter(Boolean)
  if (promptSources.length !== 1) {
    throw new Error("provide exactly one of --prompt, --prompt-file, or --prompt-stdin")
  }
  if (flags.prompt) return String(flags.prompt).trim()
  if (flags["prompt-file"]) {
    return (await fs.readFile(flags["prompt-file"], "utf8")).trim()
  }
  const chunks = []
  for await (const chunk of process.stdin) chunks.push(chunk)
  return Buffer.concat(chunks.map((chunk) => Buffer.from(chunk))).toString("utf8").trim()
}

async function readOpencodeConfig() {
  const configDir = process.env.OPENCODE_CONFIG_DIR || path.join(homeDir(), ".config", "opencode")
  const configPath = path.join(configDir, "opencode.json")
  try {
    const raw = await fs.readFile(configPath, "utf8")
    return JSON.parse(stripTrailingCommas(stripJsonComments(raw)))
  } catch (error) {
    if (error.code === "ENOENT") return {}
    throw new Error(`could not read ${configPath}: ${error.message}`)
  }
}

function stripJsonComments(input) {
  let output = ""
  let inString = false
  let escaped = false
  for (let index = 0; index < input.length; index += 1) {
    const char = input[index]
    const next = input[index + 1]
    if (inString) {
      output += char
      if (escaped) {
        escaped = false
      } else if (char === "\\") {
        escaped = true
      } else if (char === '"') {
        inString = false
      }
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
      while (index < input.length && !(input[index] === "*" && input[index + 1] === "/")) {
        index += 1
      }
      index += 1
      continue
    }
    output += char
  }
  return output
}

function stripTrailingCommas(input) {
  let output = ""
  let inString = false
  let escaped = false
  for (let index = 0; index < input.length; index += 1) {
    const char = input[index]
    if (inString) {
      output += char
      if (escaped) {
        escaped = false
      } else if (char === "\\") {
        escaped = true
      } else if (char === '"') {
        inString = false
      }
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

function resolveConfigString(value) {
  if (typeof value !== "string" || value.length === 0) return undefined
  const envMatch = value.match(/^\{env:([A-Za-z_][A-Za-z0-9_]*)\}$/)
  if (envMatch) return process.env[envMatch[1]]
  return value
}

function imageEndpoint(baseURL) {
  const trimmed = String(baseURL || "https://api.openai.com/v1").replace(/\/+$/, "")
  const apiBase = trimmed.endsWith("/v1") ? trimmed : `${trimmed}/v1`
  return `${apiBase}/images/generations`
}

function normalizeFormat(format) {
  return format === "jpg" ? "jpeg" : format
}

function parseCount(raw) {
  const count = raw === undefined ? 1 : Number.parseInt(raw, 10)
  if (!Number.isInteger(count) || count < 1 || count > MAX_VARIANTS) {
    throw new Error(`--n must be an integer from 1 to ${MAX_VARIANTS}`)
  }
  return count
}

async function plannedOutputPaths(input) {
  const paths = input.out
    ? pathsFromOut(input.out, input.count, input.outputFormat)
    : pathsFromOutDir(input.outDir, input.count, input.outputFormat, input.prompt)

  if (!input.force) {
    for (const outputPath of paths) {
      if (await exists(outputPath)) {
        throw new Error(`output already exists: ${relativeToCwd(outputPath)} (use --force to overwrite)`)
      }
    }
  }
  return paths
}

function pathsFromOut(rawOut, count, outputFormat) {
  const resolved = resolveInsideCwd(rawOut)
  const parsed = path.parse(resolved)
  const extension = parsed.ext || `.${extensionFor(outputFormat)}`
  const stem = path.join(parsed.dir, parsed.name || "imagegen")
  return Array.from({ length: count }, (_, index) => {
    const suffix = count === 1 ? "" : `-${index + 1}`
    return `${stem}${suffix}${extension}`
  })
}

function pathsFromOutDir(rawOutDir, count, outputFormat, prompt) {
  const outDir = resolveInsideCwd(rawOutDir)
  const stem = `${timestampSlug()}-${promptSlug(prompt)}`
  return Array.from({ length: count }, (_, index) => {
    const suffix = count === 1 ? "" : `-${index + 1}`
    return path.join(outDir, `${stem}${suffix}.${extensionFor(outputFormat)}`)
  })
}

function resolveInsideCwd(rawPath) {
  const resolved = path.resolve(process.cwd(), rawPath)
  const relative = path.relative(process.cwd(), resolved)
  if (relative.startsWith("..") || path.isAbsolute(relative)) {
    throw new Error("output paths must stay inside the current working directory")
  }
  return resolved
}

function extensionFor(format) {
  return format === "jpeg" ? "jpg" : format
}

async function exists(filePath) {
  try {
    await fs.access(filePath)
    return true
  } catch {
    return false
  }
}

function timestampSlug() {
  return new Date().toISOString().replace(/[-:]/g, "").replace(/\.\d{3}Z$/, "Z")
}

function promptSlug(prompt) {
  const slug = prompt
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 48)
  return slug || `imagegen-${randomUUID().slice(0, 8)}`
}

async function imageBytes(image) {
  if (typeof image?.b64_json === "string") {
    return Buffer.from(image.b64_json, "base64")
  }
  if (typeof image?.url === "string") {
    const response = await fetch(image.url)
    if (!response.ok) {
      throw new Error(`could not download image URL (${response.status} ${response.statusText})`)
    }
    return Buffer.from(await response.arrayBuffer())
  }
  throw new Error("image item has neither b64_json nor url")
}

function relativeToCwd(filePath) {
  return path.relative(process.cwd(), filePath)
}

function homeDir() {
  if (!process.env.HOME) throw new Error("HOME is not set")
  return process.env.HOME
}

function printResult(result) {
  console.log(JSON.stringify(result, null, 2))
}

function printHelp() {
  console.log(`Usage:
  node imagegen.mjs generate --prompt "..." [options]
  node imagegen.mjs generate --prompt-file prompt.txt [options]
  node imagegen.mjs generate --prompt-stdin [options]

Options:
  --model MODEL             Default: ${DEFAULT_MODEL}
  --size SIZE               Default: ${DEFAULT_SIZE}
  --quality QUALITY         low | medium | high | auto. Default: ${DEFAULT_QUALITY}
  --output-format FORMAT    png | jpeg | jpg | webp. Default: ${DEFAULT_FORMAT}
  --n N                     Number of variants, 1-${MAX_VARIANTS}. Default: 1
  --out PATH                Workspace-relative output path
  --out-dir DIR             Workspace-relative output directory. Default: ${DEFAULT_OUT_DIR}
  --force                   Overwrite existing output files
  --dry-run                 Print payload and paths without calling the API
`)
}
