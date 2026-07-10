// labflow opencode plugin — injected via opencode.json "plugin" field.
// Assets live next to the plugin under .../labflow/.
import { execFile } from "node:child_process"
import * as fs from "fs"
import * as path from "path"
import { fileURLToPath } from "node:url"
import { promisify } from "node:util"
import { tool } from "@opencode-ai/plugin"

const ASSETS = path.join(path.dirname(fileURLToPath(import.meta.url)), "..") // opencode/ root
const IMAGEGEN_SCRIPT = path.join(ASSETS, "scripts", "imagegen.mjs")
const NODE_BIN = process.env.LABFLOW_IMAGEGEN_NODE || "node"
const execFileAsync = promisify(execFile)

// 为什么这里手动 readFileSync，而不是用 OpenCode 的 `{file:...}` 语法？
//   `{file:...}` 的替换发生在 OpenCode *解析静态 opencode.json 的阶段*。
//   而 plugin 的 config() 钩子在解析完成之后才运行，此时再写
//   `prompt: "{file:/abs/path.md}"` 已经错过了替换时机——字符串会被原样
//   当作系统提示词发给模型，agent 因此完全读不到自己的定义（表现为
//   "agent 不知道自己是谁"）。
//   所以在 plugin 里必须自己把文件内容读进来，直接赋值给 prompt 字段。
// 注意：这是启动期同步读取；若某个 agent 定义文件缺失会导致插件加载失败、
//   进而 OpenCode 启动失败——这是有意为之的 fail-fast，避免静默退化成
//   "空 prompt agent"。
const readAgentPrompt = (name: string): string =>
  fs.readFileSync(path.join(ASSETS, "agents", name + ".md"), "utf-8")

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
  tool: {
    imagegen: imagegenTool,
  },
  config(cfg) {
    cfg.instructions = [...(cfg.instructions ?? []), ASSETS + "/labflow-rules.md"]

    cfg.agent = {
      ...cfg.agent,
      "labflow-develop": {
        mode: "primary",
        description:
          "Research develop stage — refine ideas and engineering questions, challenge assumptions, then externalize mature design into distributed scaffolds (TODOs, docstrings, interface shells). Switch here for nonlinear R&D discussion; switch back to build for implementation, or to labflow-plan for read-only structured planning.",
        prompt: readAgentPrompt("labflow-develop"),
        permission: {
          read: "allow",
          edit: "allow",
          glob: "deny",
          grep: "deny",
          list: "allow",
          bash: "ask",
          task: "allow",
          todowrite: "allow",
          webfetch: "allow",
          websearch: "allow",
          skill: "allow",
          question: "allow",
        },
      },
      "labflow-plan": {
        mode: "primary",
        color: "info",
        description:
          "Read-only structured planning agent (Codex-style). Explore first, clarify intent, then produce a decision-complete <proposed_plan>. Cannot edit code. Plan here; implement in build; scaffold R&D intent in labflow-develop.",
        prompt: readAgentPrompt("labflow-plan"),
        permission: {
          read: "allow",
          edit: "deny",
          glob: "deny",
          grep: "deny",
          list: "allow",
          bash: "allow",
          task: "allow",
          todowrite: "allow",
          webfetch: "allow",
          websearch: "allow",
          skill: "allow",
          question: "allow",
        },
      },
      "labflow-paper": {
        mode: "primary",
        color: "secondary",
        description:
          "Research paper assistant — supports paper preparation, writing guidance, evidence alignment, reviewer-style critique, polishing, and submission readiness. Use as the main agent in LaTeX/paper projects; use labflow-plan for read-only plans, labflow-develop for R&D scaffolding, and build for code implementation.",
        prompt: readAgentPrompt("labflow-paper"),
        permission: {
          read: "allow",
          edit: "allow",
          glob: "deny",
          grep: "deny",
          list: "allow",
          bash: "ask",
          task: "allow",
          todowrite: "allow",
          webfetch: "allow",
          websearch: "allow",
          skill: "allow",
          question: "allow",
        },
      },
      "literature-worker": {
        mode: "subagent",
        hidden: true,
        description:
          "Focused literature-forensics worker for one bounded prior-art topic lane. Searches and screens scholarly evidence, locates primary-source text and figures, and writes only assigned dossier artifacts.",
        prompt: readAgentPrompt("literature-worker"),
        permission: {
          read: "allow",
          edit: "allow",
          glob: "deny",
          grep: "deny",
          list: "allow",
          bash: "allow",
          task: "deny",
          todowrite: "deny",
          webfetch: "allow",
          websearch: "allow",
          skill: "allow",
          question: "deny",
        },
      },
    }

    cfg.skills = { paths: [...(cfg.skills?.paths ?? []), ASSETS + "/skills"] }
  },
})
