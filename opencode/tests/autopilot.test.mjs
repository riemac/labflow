import assert from "node:assert/strict"
import * as fs from "node:fs/promises"
import * as path from "node:path"
import { fileURLToPath } from "node:url"
import test from "node:test"

import { readManagedConfig } from "../scripts/config.mjs"

const OPENCODE_DIR = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..")
const SKILL_DIR = path.join(OPENCODE_DIR, "skills", "autopilot")

test("autopilot exposes an explicit OpenCode-only autonomous contract", async () => {
  const source = await fs.readFile(path.join(SKILL_DIR, "SKILL.md"), "utf8")

  assert.match(source, /^name: autopilot$/m)
  assert.match(source, /Use ONLY when the user explicitly asks/)
  assert.match(source, /Once activated, do not call `question`/)
  assert.match(source, /<flipped_preflight>/)
  assert.match(source, /What I Think You Actually Want/)
  assert.match(source, /Separate \*\*goal uncertainty\*\* from \*\*method uncertainty\*\*/)
  assert.match(source, /Offer one reasoned recommended objective by default/)
  assert.match(source, /defaulting to 10 hours/)
  assert.match(source, /maximum useful parallelism/i)
  assert.match(source, /notifyOnExit: true/)
  assert.match(source, /Autopilot never creates, pauses, resumes, or completes a Goal/)
  assert.match(source, /do not bump versions/)
  assert.match(source, /\.autopilot\/\n├── contract\.md\n└── autopilot\.md/)
  assert.doesNotMatch(source, /state\.json|events\.jsonl/)
})

test("autopilot profiles are self-contained and preserve their domain boundaries", async () => {
  const [research, coding, paper, chinese] = await Promise.all([
    fs.readFile(path.join(SKILL_DIR, "references", "research.md"), "utf8"),
    fs.readFile(path.join(SKILL_DIR, "references", "coding.md"), "utf8"),
    fs.readFile(path.join(SKILL_DIR, "references", "paper.md"), "utf8"),
    fs.readFile(path.join(SKILL_DIR, "SKILL_CN.md"), "utf8"),
  ])

  assert.match(research, /autonomously scale a supported route from probe to formal experiment/)
  assert.match(research, /A runnable path is not evidence of a valid learning signal/)
  assert.match(coding, /New dependencies, public API or schema changes.*forbidden unless preflight explicitly authorizes them/s)
  assert.match(coding, /Do not perform version release closure/)
  assert.match(paper, /Associated research code is read-only unless/)
  assert.match(paper, /Do not fabricate citations/)
  assert.match(chinese, /最大有效并行/)
  assert.match(chinese, /翻转式目标澄清/)
  assert.match(chinese, /目标不确定性.*方法不确定性/)
  assert.match(chinese, /不得调用 `question`/)
})

test("Goal waits for background children and remains held in both Plan agents", async () => {
  const managed = await readManagedConfig()
  const entry = managed.plugins.plugins.find((plugin) => Array.isArray(plugin) && plugin[0] === "opencode-goal-plugin")

  assert.equal(entry[1].noContinueWhileChildrenActive, true)
  assert.deepEqual(entry[1].restrictedAgents, ["plan", "labflow-plan"])
})
