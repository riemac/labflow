// labflow opencode plugin — injected via opencode.json "plugin" field.
// Assets live next to the plugin under .../labflow/.
import * as path from "path"

const ASSETS = path.join(import.meta.dir, "..") // opencode/ root

export default async () => ({
  config(cfg) {
    cfg.instructions = [...(cfg.instructions ?? []), ASSETS + "/labflow-rules.md"]

    cfg.agent = {
      ...cfg.agent,
      "labflow-develop": {
        mode: "primary",
        description:
          "Research develop stage — refine ideas and engineering questions, challenge assumptions, then externalize mature design into distributed scaffolds (TODOs, docstrings, interface shells). Switch here for nonlinear R&D discussion; switch back to build for implementation.",
        prompt: "{file:" + ASSETS + "/agents/labflow-develop.md}",
        permission: {
          read: "allow",
          edit: "allow",
          glob: "allow",
          grep: "allow",
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
        prompt: "{file:" + ASSETS + "/agents/vision.md}",
        permission: { edit: "deny" },
      },
    }

    cfg.skills = { paths: [...(cfg.skills?.paths ?? []), ASSETS + "/skills"] }
  },
})
