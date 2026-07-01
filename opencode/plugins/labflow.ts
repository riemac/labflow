// labflow opencode plugin — injected via opencode.json "plugin" field.
// Assets live next to the plugin under .../labflow/.
import * as fs from "fs"
import * as path from "path"

const ASSETS = path.join(import.meta.dir, "..") // opencode/ root

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

export default async () => ({
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
      vision: {
        mode: "subagent",
        description:
          "Vision-capable subagent for reading images (screenshots, diagrams, code diffs). Use ONLY when the user uploads an image that needs describing.",
        prompt: readAgentPrompt("vision"),
        permission: { edit: "deny" },
      },
    }

    cfg.skills = { paths: [...(cfg.skills?.paths ?? []), ASSETS + "/skills"] }
  },
})
