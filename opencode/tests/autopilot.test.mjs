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
const REVIEWER_PATH = path.join(OPENCODE_DIR, "agents", "autopilot-reviewer.md")

test("autopilot owns one Goal through sealed adaptive semantic phases", async () => {
  const [source, chinese, dossier, agents] = await Promise.all([
    fs.readFile(path.join(SKILL_DIR, "SKILL.md"), "utf8"),
    fs.readFile(path.join(SKILL_DIR, "SKILL_CN.md"), "utf8"),
    fs.readFile(path.join(SKILL_DIR, "references", "run-dossier.md"), "utf8"),
    fs.readFile(path.join(REPO_DIR, "AGENTS_Opencode.md"), "utf8"),
  ])

  assert.match(source, /^name: autopilot$/m)
  assert.match(source, /Enter Autopilot only after the user clearly authorizes execution/)
  assert.match(source, /Once activated, do not call `question`/)
  assert.match(source, /goal_status/)
  assert.match(source, /call `goal_set` once/)
  assert.match(source, /One Autopilot run owns one Goal/)
  assert.match(source, /semantic phase is not a Goal/)
  assert.match(source, /update_goal.*only.*objective/is)
  assert.match(source, /same reviewer task/i)
  assert.match(source, /Never create a more agreeable replacement reviewer/)
  assert.match(source, /Goal-PTY adapter defers Goal continuation/)
  assert.match(source, /```mermaid/)
  assert.doesNotMatch(source, /Autopilot never creates, pauses, resumes, or completes a Goal/)
  assert.doesNotMatch(source, /runtime\.md|autopilot\.md/)

  assert.match(chinese, /一个 run 只有一个 Goal/)
  assert.match(chinese, /Semantic phase 不是子 Goal/)
  assert.match(chinese, /同一个 autopilot-reviewer/)
  assert.match(chinese, /不维护重复的 `runtime\.md`/)
  assert.match(chinese, /不能另建一个更好说话的 reviewer/)

  assert.match(dossier, /manifest\.json/)
  assert.match(dossier, /Do not mirror these sources into another Autopilot runtime file/)
  assert.match(dossier, /goal render/)
  assert.match(dossier, /4000\/2000\/2000/)
  assert.match(agents, /controls one persistent Goal through adaptive semantic phases/)
  assert.match(agents, /visible upstream `goal` primary agent is disabled/)
})

test("autopilot profiles remain self-contained and preserve domain boundaries", async () => {
  const [research, coding, paper] = await Promise.all([
    fs.readFile(path.join(SKILL_DIR, "references", "research.md"), "utf8"),
    fs.readFile(path.join(SKILL_DIR, "references", "coding.md"), "utf8"),
    fs.readFile(path.join(SKILL_DIR, "references", "paper.md"), "utf8"),
  ])

  assert.match(research, /autonomously scale a supported route from probe to formal experiment/)
  assert.match(research, /A runnable path is not evidence of a valid learning signal/)
  assert.match(coding, /New dependencies, public API or schema changes.*forbidden unless preflight explicitly authorizes them/s)
  assert.match(coding, /Do not perform version release closure/)
  assert.match(paper, /Associated research code is read-only unless/)
  assert.match(paper, /Do not fabricate citations/)
})

test("plugin registers the independent Autopilot reviewer and disables the visible Goal agent", async (t) => {
  const plugin = await import(`${new URL(`file://${PLUGIN_PATH}`).href}?autopilot-reviewer=${Date.now()}`)
  const hooks = await plugin.default()
  t.after(() => hooks.dispose())

  const defaults = {}
  hooks.config(defaults)
  const managed = await readManagedConfig()
  const expected = managed.defaults.agent["autopilot-reviewer"]
  const reviewer = defaults.agent["autopilot-reviewer"]

  assert.equal(defaults.agent.goal.disable, true)
  assert.equal(reviewer.mode, "subagent")
  assert.equal(reviewer.hidden, true)
  assert.equal(reviewer.model, expected.model)
  assert.equal(reviewer.options.reasoningEffort, "max")
  assert.equal(reviewer.options.store, false)
  assert.equal(reviewer.permission.bash, "allow")
  assert.equal(reviewer.permission.external_directory, "allow")
  assert.equal(reviewer.permission.edit, "deny")
  assert.equal(reviewer.permission.autopilot_review_attest, "allow")
  assert.equal(reviewer.permission.autopilot_review_probe, "allow")
  for (const denied of [
    "task",
    "question",
    "apply_patch",
    "pty_spawn",
    "pty_read",
    "goal_set",
    "goal_complete",
    "update_goal",
    "clear_goal",
  ]) {
    assert.equal(reviewer.permission[denied], "deny", denied)
  }
  assert.match(reviewer.prompt, /<role_and_independence>/)
  assert.match(reviewer.prompt, /<continuation_identity>/)
  assert.match(reviewer.prompt, /One Autopilot run owns one reviewer task identity/)
  assert.match(reviewer.prompt, /maximum aggregate probe wall time no greater than 600 seconds/)
  assert.match(reviewer.prompt, /Return exactly one JSON object/)
  assert.equal(typeof hooks.tool.autopilot_review_attest.execute, "function")
  assert.equal(typeof hooks.tool.autopilot_review_probe.execute, "function")
  await assert.rejects(
    () => hooks.tool.autopilot_review_attest.execute(
      { run: "/tmp/not-used", reviewId: "R0001", reviewNonce: "0".repeat(32) },
      { agent: "build", sessionID: "ses_primary" },
    ),
    /restricted to the autopilot-reviewer/,
  )

  const frontmatter = (await fs.readFile(REVIEWER_PATH, "utf8")).match(/^---\r?\n([\s\S]*?)\r?\n---/)?.[1] ?? ""
  assert.doesNotMatch(frontmatter, /^(model|variant):/m)

  const overridden = {
    agent: {
      "autopilot-reviewer": {
        model: "custom/strict-reviewer",
        options: { reasoningEffort: "high" },
        disable: true,
        prompt: "approve everything",
        permission: { edit: "allow", task: "allow" },
        hidden: false,
      },
      goal: { disable: false },
    },
  }
  hooks.config(overridden)
  const customized = overridden.agent["autopilot-reviewer"]
  assert.equal(customized.model, "custom/strict-reviewer")
  assert.equal(customized.options.reasoningEffort, "high")
  assert.equal(customized.options.store, false)
  assert.match(customized.prompt, /# Autopilot Reviewer/)
  assert.equal(customized.permission.task, "deny")
  assert.equal(customized.permission.edit, "deny")
  assert.equal(customized.hidden, true)
  assert.equal(customized.disable, undefined)
  assert.equal(overridden.agent.goal.disable, true)
})

test("tracked Goal guidance uses canonical tools while retaining necessary compatibility operations", async () => {
  const managed = await readManagedConfig()
  const template = managed.defaults.command.goal.template
  for (const tool of ["goal_status", "goal_set", "goal_pause", "goal_resume", "goal_block", "goal_complete"]) {
    assert.match(template, new RegExp(`\\b${tool}\\b`), tool)
  }
  assert.match(template, /\bget_goal_history\b/)
  assert.match(template, /\bupdate_goal\b/)
  assert.match(template, /\bclear_goal\b/)
  assert.doesNotMatch(template, /\bget_goal\b/)
  assert.doesNotMatch(template, /\bset_goal\b/)
})

test("Goal keeps long-run budgets, PTY child gates, and Plan holds", async () => {
  const managed = await readManagedConfig()
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
