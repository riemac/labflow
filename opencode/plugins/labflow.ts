// labflow opencode plugin — injected via opencode.json "plugin" field.
// Assets live next to the plugin under .../labflow/.
import { execFile } from "node:child_process"
import * as fs from "fs"
import * as path from "path"
import { fileURLToPath } from "node:url"
import { promisify } from "node:util"
import { tool } from "@opencode-ai/plugin"
import { parse as parseYaml } from "yaml"

const ASSETS = path.join(path.dirname(fileURLToPath(import.meta.url)), "..") // opencode/ root
const IMAGEGEN_SCRIPT = path.join(ASSETS, "scripts", "imagegen.mjs")
const NODE_BIN = process.env.LABFLOW_IMAGEGEN_NODE || "node"
const execFileAsync = promisify(execFile)
const BUILD_MODE_SYSTEM = [
  "<active-agent>",
  "The current OpenCode primary agent is build. Execute implementation requests using the available tools.",
  "This current-agent marker supersedes mode restrictions from primary agents that were active earlier in the same session. Do not ask the user to switch to build.",
  "</active-agent>",
].join("\n")

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
    "Generate a raster image through labflow's configured OpenAI-compatible image API. Use for explicit image generation requests, concept diagrams, and lab-meeting visuals.",
  args: {
    prompt: tool.schema.string().min(1).describe("Final image prompt to send to the image model"),
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
    context.metadata({ title: "Generate image" })

    const cliArgs = buildImagegenArgs(args)
    try {
      const { stdout } = await execFileAsync(NODE_BIN, [IMAGEGEN_SCRIPT, ...cliArgs], {
        cwd: context.directory,
        signal: context.abort,
        maxBuffer: 2 * 1024 * 1024,
      })
      const result = parseImagegenResult(stdout)
      context.metadata({
        title: "Generated image",
        metadata: {
          outputs: result.outputs,
          model: result.model,
          size: result.size,
          quality: result.quality,
        },
      })
      return {
        output: formatImagegenToolOutput(result),
        metadata: result,
      }
    } catch (error) {
      throw new Error(`imagegen failed: ${formatExecError(error)}`)
    }
  },
})

function buildImagegenArgs(args): string[] {
  const cliArgs = ["generate", "--prompt", args.prompt]
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
  const lines = ["Generated image."]
  if (outputs.length > 0) lines.push(`outputs: ${outputs.join(", ")}`)
  if (result.model) lines.push(`model: ${result.model}`)
  if (result.size) lines.push(`size: ${result.size}`)
  if (result.quality) lines.push(`quality: ${result.quality}`)
  if (result.output_format) lines.push(`output_format: ${result.output_format}`)
  if (result.revised_prompt) lines.push(`revised_prompt: ${result.revised_prompt}`)
  lines.push("Read the output path if you need to inspect the generated image in context.")
  return lines.join("\n")
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

export default async () => ({
  "chat.message": async (input, output) => {
    if (input.agent !== "build") return
    output.message.system = [output.message.system, BUILD_MODE_SYSTEM].filter(Boolean).join("\n")
  },
  tool: {
    imagegen: imagegenTool,
  },
  config(cfg) {
    cfg.instructions = [...(cfg.instructions ?? []), ASSETS + "/labflow-rules.md"]

    cfg.agent = {
      ...cfg.agent,
      "labflow-develop": readAgentDefinition("labflow-develop"),
      "labflow-plan": readAgentDefinition("labflow-plan"),
      "labflow-paper": readAgentDefinition("labflow-paper"),
      "literature-worker": readAgentDefinition("literature-worker"),
    }

    cfg.skills = { paths: [...(cfg.skills?.paths ?? []), ASSETS + "/skills"] }
  },
})
