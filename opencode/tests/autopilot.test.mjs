import assert from "node:assert/strict"
import * as fs from "node:fs/promises"
import * as path from "node:path"
import { fileURLToPath } from "node:url"
import test from "node:test"

import { readManagedConfig } from "../scripts/config.mjs"

const OPENCODE_DIR = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..")
const REPO_DIR = path.resolve(OPENCODE_DIR, "..")
const SKILL_DIR = path.join(OPENCODE_DIR, "skills", "autopilot")
const PLUGIN_PATH = path.join(OPENCODE_DIR, "plugins", "labflow.ts")

test("autopilot uses one maintained Goal and native operational state", async () => {
  const [source, chinese, agents] = await Promise.all([
    fs.readFile(path.join(SKILL_DIR, "SKILL.md"), "utf8"),
    fs.readFile(path.join(SKILL_DIR, "SKILL_CN.md"), "utf8"),
    fs.readFile(path.join(REPO_DIR, "AGENTS_Opencode.md"), "utf8"),
  ])

  assert.match(source, /^name: autopilot$/m)
  assert.match(source, /Enter Autopilot only after the user clearly authorizes execution/)
  assert.match(source, /Call `goal_status` before changing Goal state/)
  assert.match(source, /call `goal_set` once/)
  assert.match(source, /Do not update the Goal after every command or minor step/)
  assert.match(source, /Use native operational state directly/)
  assert.match(source, /Do not create `\.autopilot\/`/)
  assert.match(source, /project documentation only when the user asks/)
  assert.match(source, /Goal-PTY adapter defers continuation/)
  assert.doesNotMatch(source, /scripts\/autopilot\.py|run-dossier|manifest\.json|autopilot-reviewer|convergence review/i)

  assert.match(chinese, /不创建 `\.autopilot\/`/)
  assert.match(chinese, /不要每条命令或小步骤后更新 Goal/)
  assert.match(chinese, /Goal 保存稳定结果、当前重点、约束和完成状态/)
  assert.doesNotMatch(chinese, /scripts\/autopilot\.py|run-dossier|manifest\.json|autopilot-reviewer|独立收束审查/i)

  assert.match(agents, /maintains one persistent Goal/)
  assert.match(agents, /visible upstream `goal` primary agent is disabled/)
  await assert.rejects(fs.stat(path.join(SKILL_DIR, "scripts", "autopilot.py")), /ENOENT/)
  await assert.rejects(fs.stat(path.join(SKILL_DIR, "references", "run-dossier.md")), /ENOENT/)
})

test("autopilot profiles remain self-contained and make documentation task-driven", async () => {
  const [research, coding, paper] = await Promise.all([
    fs.readFile(path.join(SKILL_DIR, "references", "research.md"), "utf8"),
    fs.readFile(path.join(SKILL_DIR, "references", "coding.md"), "utf8"),
    fs.readFile(path.join(SKILL_DIR, "references", "paper.md"), "utf8"),
  ])

  assert.match(research, /autonomously scale a supported route from probe to formal experiment/)
  assert.match(research, /A runnable path is not evidence of a valid learning signal/)
  assert.match(research, /Do not create or interrupt work to maintain a generic Autopilot log/)
  assert.match(coding, /New dependencies, public API or schema changes.*forbidden unless preflight explicitly authorizes them/s)
  assert.match(coding, /unless that side effect was explicitly authorized/)
  assert.match(paper, /Associated research code is read-only unless/)
  assert.match(paper, /Do not fabricate citations/)
})

test("plugin removes the dedicated Autopilot reviewer while retaining Goal", async (t) => {
  const plugin = await import(`${new URL(`file://${PLUGIN_PATH}`).href}?autopilot-lightweight=${Date.now()}`)
  const hooks = await plugin.default()
  t.after(() => hooks.dispose())

  const config = {}
  hooks.config(config)
  assert.equal(config.agent.goal.disable, true)
  assert.equal(config.agent["autopilot-reviewer"], undefined)
  assert.equal(hooks.tool.autopilot_review_attest, undefined)
  assert.equal(hooks.tool.autopilot_review_probe, undefined)
})

test("tracked Goal guidance uses canonical tools and long-run defaults", async () => {
  const managed = await readManagedConfig()
  const template = managed.defaults.command.goal.template
  for (const tool of ["goal_status", "goal_set", "goal_pause", "goal_resume", "goal_block", "goal_complete"]) {
    assert.match(template, new RegExp(`\\b${tool}\\b`), tool)
  }
  assert.match(template, /\bget_goal_history\b/)
  assert.match(template, /\bupdate_goal\b/)
  assert.match(template, /\bclear_goal\b/)

  const entry = managed.plugins.plugins.find((plugin) => Array.isArray(plugin) && plugin[0].startsWith("opencode-goal-plugin@"))
  assert.equal(entry[0], "opencode-goal-plugin@0.9.0")
  assert.equal(entry[1].maxTurns, 1000)
  assert.equal(entry[1].maxDurationMs, 144000000)
  assert.equal(entry[1].maxTokens, 100000000)
  assert.equal(entry[1].minDelayMs, 5000)
  assert.equal(entry[1].noContinueWhileChildrenActive, true)
  assert.equal(entry[1].sessionTitleStatus, true)
  assert.deepEqual(entry[1].restrictedAgents, ["plan", "labflow-plan"])
  assert.equal(managed.defaults.command.goal.agent, undefined)
})
