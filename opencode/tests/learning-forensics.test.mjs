import assert from "node:assert/strict"
import { execFile } from "node:child_process"
import * as fs from "node:fs/promises"
import * as os from "node:os"
import * as path from "node:path"
import { fileURLToPath } from "node:url"
import { promisify } from "node:util"
import test from "node:test"

import { readManagedConfig } from "../scripts/config.mjs"

const execFileAsync = promisify(execFile)
const OPENCODE_DIR = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..")
const REPO_DIR = path.resolve(OPENCODE_DIR, "..")
const PLUGIN_PATH = path.join(OPENCODE_DIR, "plugins", "labflow.ts")
const WORKER_PATH = path.join(OPENCODE_DIR, "agents", "learning-worker.md")
const CODEX_WORKER_PATH = path.join(REPO_DIR, "codex", "agents", "learning-worker.toml")
const CODEX_MANIFEST_PATH = path.join(REPO_DIR, "codex", ".codex-plugin", "plugin.json")
const OPENCODE_HELPER = path.join(OPENCODE_DIR, "skills", "learning-forensics", "scripts", "case.py")
const CODEX_HELPER = path.join(REPO_DIR, "codex", "skills", "learning-forensics", "scripts", "case.py")
const OPENCODE_REFERENCES = path.join(OPENCODE_DIR, "skills", "learning-forensics", "references")
const CODEX_REFERENCES = path.join(REPO_DIR, "codex", "skills", "learning-forensics", "references")
const OPENCODE_SKILL = path.join(OPENCODE_DIR, "skills", "learning-forensics", "SKILL.md")
const CODEX_SKILL = path.join(REPO_DIR, "codex", "skills", "learning-forensics", "SKILL.md")
const OPENCODE_SKILL_CN = path.join(OPENCODE_DIR, "skills", "learning-forensics", "SKILL_CN.md")
const CODEX_SKILL_CN = path.join(REPO_DIR, "codex", "skills", "learning-forensics", "SKILL_CN.md")


async function temporaryDirectory(t, prefix) {
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), prefix))
  t.after(() => fs.rm(directory, { recursive: true, force: true }))
  return directory
}


async function relativeFiles(root, directory = root) {
  const files = []
  for (const entry of await fs.readdir(directory, { withFileTypes: true })) {
    const target = path.join(directory, entry.name)
    if (entry.isDirectory()) files.push(...await relativeFiles(root, target))
    else files.push(path.relative(root, target))
  }
  return files.sort()
}


function normalizePlatformDelegation(text) {
  return text
    .replaceAll("`explore-worker`", "<retrieval-role>")
    .replaceAll("`explorer`", "<retrieval-role>")
    .replace(/^Use the Task tool with .*$/m, "<platform-delegation>")
    .replace(/^Use Codex's native background-agent mechanism\..*$/m, "<platform-delegation>")
    .replace(/^Record every returned task ID/m, "Record every returned runtime handle")
    .replace(/^Record every returned thread handle/m, "Record every returned runtime handle")
    .replace(/^OpenCode 使用 Task 工具的 .*$/m, "<platform-delegation-cn>")
    .replace(/^Codex 优先使用通过 .*$/m, "<platform-delegation-cn>")
}


test("plugin registers the bounded learning worker and preserves user model overrides", async (t) => {
  const plugin = await import(`${new URL(`file://${PLUGIN_PATH}`).href}?learning-worker=${Date.now()}`)
  const hooks = await plugin.default()
  t.after(() => hooks.dispose())

  const defaults = {}
  hooks.config(defaults)

  const managed = await readManagedConfig()
  const expectedWorker = managed.defaults.agent["learning-worker"]
  const worker = defaults.agent["learning-worker"]
  assert.equal(worker.mode, "subagent")
  assert.equal(worker.hidden, true)
  assert.equal(worker.model, expectedWorker.model)
  assert.equal(worker.options.reasoningEffort, expectedWorker.options.reasoningEffort)
  assert.equal(worker.options.store, expectedWorker.options.store)
  assert.equal(worker.permission.edit["*"], "deny")
  assert.equal(worker.permission.edit["**/.learning/audit/lanes/**"], "allow")
  assert.equal(worker.permission.edit["**/.learning/probes/**"], "allow")
  assert.equal(worker.permission.read["**/.learning/brief.md"], "deny")
  assert.equal(worker.permission.read["**/.learning/state/**"], "deny")
  assert.equal(worker.permission.read["**/.learning/cases/**"], "allow")
  assert.equal(worker.permission.external_directory, "deny")
  assert.equal(worker.permission.bash, "allow")
  assert.equal(worker.permission.task, "deny")
  assert.equal(worker.permission.question, "deny")
  for (const tool of ["pty_spawn", "pty_write", "pty_read", "pty_list", "pty_kill"]) {
    assert.equal(worker.permission[tool], "deny")
  }
  assert.match(worker.prompt, /<blindness_contract>/)
  assert.match(worker.prompt, /`investigation_stage` controls orchestration breadth/)
  assert.match(worker.prompt, /primary normally owns probes and PTY feedback/)
  assert.match(worker.prompt, /maximum of 600 wall-clock seconds/)

  const source = await fs.readFile(WORKER_PATH, "utf8")
  const frontmatter = source.match(/^---\r?\n([\s\S]*?)\r?\n---/)?.[1] ?? ""
  assert.doesNotMatch(frontmatter, /^(model|variant):/m)

  const overridden = {
    agent: {
      "learning-worker": {
        model: "custom/learning-expert",
        options: { reasoningEffort: "max" },
        prompt: "replace the scientific contract",
        permission: { edit: "allow", task: "allow" },
        hidden: false,
      },
    },
  }
  hooks.config(overridden)
  assert.equal(overridden.agent["learning-worker"].model, "custom/learning-expert")
  assert.equal(overridden.agent["learning-worker"].options.reasoningEffort, "max")
  assert.match(overridden.agent["learning-worker"].prompt, /# Learning Worker/)
  assert.equal(overridden.agent["learning-worker"].permission.task, "deny")
  assert.equal(overridden.agent["learning-worker"].permission.edit["*"], "deny")
  assert.equal(overridden.agent["learning-worker"].hidden, true)
})


test("Codex learning worker uses the documented custom-agent TOML schema", async () => {
  const script = [
    "import json, pathlib, tomllib",
    `p=pathlib.Path(${JSON.stringify(CODEX_WORKER_PATH)})`,
    "d=tomllib.loads(p.read_text())",
    "print(json.dumps({'name':d.get('name'),'description':bool(d.get('description')),'instructions':bool(d.get('developer_instructions')),'sandbox':d.get('sandbox_mode')}))",
  ].join(";")
  const { stdout } = await execFileAsync("python3", ["-c", script])
  assert.deepEqual(JSON.parse(stdout), {
    name: "learning-worker",
    description: true,
    instructions: true,
    sandbox: "workspace-write",
  })
})


test("repository and Codex plugin publish one learning-forensics version", async () => {
  const version = (await fs.readFile(path.join(REPO_DIR, "VERSION"), "utf8")).trim()
  const manifest = JSON.parse(await fs.readFile(CODEX_MANIFEST_PATH, "utf8"))
  assert.equal(version, "1.3.0")
  assert.equal(manifest.version, version)
  assert.equal(manifest.keywords.includes("learning-forensics"), true)
})


test("managed startup plugins include opencode-pty without removing existing plugins", async () => {
  const managed = await readManagedConfig()
  assert.equal(managed.plugins.plugins.includes("opencode-pty"), true)
  assert.equal(managed.plugins.plugins.some((entry) => Array.isArray(entry) && entry[0] === "opencode-goal-plugin@0.9.0"), true)
})


test("Codex and OpenCode share identical learning-forensics references", async () => {
  const expected = await relativeFiles(CODEX_REFERENCES)
  const actual = await relativeFiles(OPENCODE_REFERENCES)
  assert.deepEqual(actual, expected)
  for (const relative of expected) {
    assert.equal(
      await fs.readFile(path.join(OPENCODE_REFERENCES, relative), "utf8"),
      await fs.readFile(path.join(CODEX_REFERENCES, relative), "utf8"),
      `reference drift: ${relative}`,
    )
  }
})


test("Codex and OpenCode share one scientific skill contract", async () => {
  assert.equal(
    normalizePlatformDelegation(await fs.readFile(OPENCODE_SKILL, "utf8")),
    normalizePlatformDelegation(await fs.readFile(CODEX_SKILL, "utf8")),
  )
  assert.equal(
    normalizePlatformDelegation(await fs.readFile(OPENCODE_SKILL_CN, "utf8")),
    normalizePlatformDelegation(await fs.readFile(CODEX_SKILL_CN, "utf8")),
  )
})


test("learning-forensics starts comprehensive and then adapts investigation intensity", async () => {
  const [skill, chinese, assignment, probe, dossier, codexWorker] = await Promise.all([
    fs.readFile(OPENCODE_SKILL, "utf8"),
    fs.readFile(OPENCODE_SKILL_CN, "utf8"),
    fs.readFile(path.join(OPENCODE_REFERENCES, "assignment-schema.md"), "utf8"),
    fs.readFile(path.join(OPENCODE_REFERENCES, "probe-protocol.md"), "utf8"),
    fs.readFile(path.join(OPENCODE_REFERENCES, "dossier-layout.md"), "utf8"),
    fs.readFile(CODEX_WORKER_PATH, "utf8"),
  ])

  assert.match(skill, /<engagement_gate>/)
  assert.match(skill, /Loading or consulting this skill does not by itself require a dossier/)
  assert.match(skill, /Cover The Comprehensive First Round/)
  assert.match(skill, /launch every remaining independent blind lane concurrently/)
  assert.match(skill, /one to three learning-worker lanes/)
  assert.match(skill, /Primary-Owned Probes By Default/)
  assert.match(skill, /learning-worker.*causal analysis and `explore-worker` for retrieval support/)
  assert.match(chinese, /focused \/ lite.*1–3 条 learning-worker lanes/)
  assert.match(assignment, /investigation_stage: comprehensive-first-pass \| focused \| re-expansion/)
  assert.match(assignment, /one of at most three active high-information lanes/)
  assert.match(probe, /The primary agent owns probe execution by default/)
  assert.match(probe, /maximum useful parallel wave/)
  assert.match(dossier, /Create the next snapshot only when a later blind round needs materially updated facts/)
  assert.match(dossier, /Start a new dossier only when the model\/task\/data object or core decision changes materially/)
  assert.match(codexWorker, /primary normally owns probes and PTY feedback/)
})


test("case helper creates, seals, validates, and detects mutation", async (t) => {
  const root = await temporaryDirectory(t, "learning-forensics-case-")
  const caseRoot = path.join(root, "case")

  await execFileAsync("python3", [
    OPENCODE_HELPER,
    "init",
    "--path",
    caseRoot,
    "--language",
    "zh-CN",
    "--title",
    "测试学习问题",
    "--question",
    "最早断点在哪里？",
  ])
  const { stdout: caseOutput } = await execFileAsync("python3", [OPENCODE_HELPER, "new-case", "--path", caseRoot])
  assert.equal(path.basename(caseOutput.trim()), "case-0001.md")
  const casePath = path.join(caseRoot, ".learning", "cases", "case-0001.md")
  const caseSections = [
    "Case Identity",
    "Decision To Support",
    "Frozen Observations",
    "Case-Specific Causal Chain",
    "Authoritative Design Sources",
    "Available Evidence",
    "Withheld Diagnosis Sources",
    "Constraints And Safety",
    "Missing Facts",
  ]
  let caseText = await fs.readFile(casePath, "utf8")
  for (const heading of caseSections) {
    caseText = caseText.replace(`## ${heading}\n`, `## ${heading}\n\nFact for ${heading}.\n`)
  }
  await fs.writeFile(casePath, caseText)

  await execFileAsync("python3", [OPENCODE_HELPER, "seal-case", "--path", caseRoot, "--case", "case-0001.md"])
  assert.match(await fs.readFile(casePath, "utf8"), /^status: sealed$/m)
  await execFileAsync("python3", [
    OPENCODE_HELPER,
    "new-probe",
    "--path",
    caseRoot,
    "--id",
    "frozen-readout",
    "--case",
    "case-0001.md",
  ])
  const { stdout: validOutput } = await execFileAsync("python3", [OPENCODE_HELPER, "validate", "--path", caseRoot, "--json"])
  const valid = JSON.parse(validOutput)
  assert.equal(valid.ok, true)
  assert.deepEqual(valid.errors, [])
  assert.equal(valid.language, "zh-CN")
  assert.equal(valid.warnings.includes("draft probe: frozen-readout"), true)
  assert.equal(await fs.readFile(path.join(caseRoot, ".gitignore"), "utf8"), "*\n")
  const probeRoot = path.join(caseRoot, ".learning", "probes", "frozen-readout")
  const manifestPath = path.join(probeRoot, "manifest.yaml")
  assert.equal((await fs.readFile(manifestPath, "utf8")).includes("max_wall_seconds: 600"), true)

  let manifest = await fs.readFile(manifestPath, "utf8")
  manifest = manifest
    .replace("status: draft", "status: ready")
    .replace("hypothesis: ''", "hypothesis: 'frozen representation lacks target information'")
    .replace("prediction_if_true: ''", "prediction_if_true: 'probe remains at baseline'")
    .replace("prediction_if_false: ''", "prediction_if_false: 'probe exceeds baseline'")
    .replace("changed_variable: ''", "changed_variable: 'probe capacity'")
    .replace("controlled_variables: []", "controlled_variables: ['case', 'checkpoint', 'metric']")
    .replace("inputs: []", "inputs: ['sealed case', 'frozen checkpoint']")
    .replace("writes: []", "writes: ['.learning/probes/frozen-readout']")
    .replace("evaluation_measure: ''", "evaluation_measure: 'baseline-normalized skill'")
    .replace("seed: null", "seed: 53")
    .replace("workdir: ''", `workdir: '${probeRoot}'`)
    .replace("commands: []", "commands: ['python .learning/probes/frozen-readout/scripts/probe.py']")
  await fs.writeFile(manifestPath, manifest)
  let plan = await fs.readFile(path.join(probeRoot, "plan.md"), "utf8")
  for (const heading of ["Hypothesis", "Prediction If True", "Prediction If False", "Inputs And Frozen Evidence", "Changed And Controlled Variables", "Evaluation Measure", "Stop Conditions"]) {
    plan = plan.replace(`## ${heading}\n`, `## ${heading}\n\nDefined ${heading}.\n`)
  }
  await fs.writeFile(path.join(probeRoot, "plan.md"), plan)
  const { stdout: readyOutput } = await execFileAsync("python3", [OPENCODE_HELPER, "validate", "--path", caseRoot, "--json"])
  assert.equal(JSON.parse(readyOutput).ok, true)

  await fs.writeFile(manifestPath, manifest.replace("max_wall_seconds: 600", "max_wall_seconds: 601"))
  await assert.rejects(
    execFileAsync("python3", [OPENCODE_HELPER, "validate", "--path", caseRoot, "--json"]),
    (error) => JSON.parse(error.stdout).errors.includes("probe frozen-readout must retain max_wall_seconds=600"),
  )
  await fs.writeFile(manifestPath, manifest)

  const digest = (await fs.readFile(`${casePath}.sha256`, "ascii")).split(/\s+/)[0]
  const duplicatedWorkers = {
    schema_version: "1.0.0",
    workers: [1, 2].map((index) => ({
      worker_id: `worker-${index}`,
      runtime_handle: `task-${index}`,
      primary_lens: "representation",
      phase: "blind-audit",
      case_file: "case-0001.md",
      case_sha256: digest,
      lane_path: ".learning/audit/lanes/representation.md",
      status: "running",
    })),
  }
  const workersPath = path.join(caseRoot, ".learning", "state", "workers.json")
  await fs.writeFile(workersPath, `${JSON.stringify(duplicatedWorkers)}\n`)
  await assert.rejects(
    execFileAsync("python3", [OPENCODE_HELPER, "validate", "--path", caseRoot, "--json"]),
    (error) => JSON.parse(error.stdout).errors.includes("workers.json has duplicate active lane owner: .learning/audit/lanes/representation.md"),
  )
  await fs.writeFile(workersPath, '{"schema_version":"1.0.0","workers":[]}\n')

  await assert.rejects(
    execFileAsync("python3", [OPENCODE_HELPER, "init", "--path", caseRoot, "--language", "zh-CN", "--title", "重复初始化"]),
    /refusing to overwrite existing files/,
  )

  const { stdout: secondCaseOutput } = await execFileAsync("python3", [OPENCODE_HELPER, "new-case", "--path", caseRoot])
  const secondCasePath = path.join(caseRoot, ".learning", "cases", path.basename(secondCaseOutput.trim()))
  await assert.rejects(
    execFileAsync("python3", [OPENCODE_HELPER, "seal-case", "--path", caseRoot, "--case", path.basename(secondCaseOutput.trim())]),
    /has an empty section/,
  )
  let interruptedCase = await fs.readFile(secondCasePath, "utf8")
  for (const heading of caseSections) {
    interruptedCase = interruptedCase.replace(`## ${heading}\n`, `## ${heading}\n\nFact for ${heading}.\n`)
  }
  await fs.writeFile(secondCasePath, interruptedCase.replace("status: draft", "status: sealed"))
  await assert.rejects(
    execFileAsync("python3", [OPENCODE_HELPER, "validate", "--path", caseRoot, "--json"]),
    (error) => JSON.parse(error.stdout).errors.includes(`sealed case lacks SHA-256 sidecar: ${path.basename(secondCasePath)}`),
  )

  await fs.appendFile(casePath, "\nmutation\n")
  await assert.rejects(
    execFileAsync("python3", [OPENCODE_HELPER, "validate", "--path", caseRoot, "--json"]),
    (error) => JSON.parse(error.stdout).errors.includes("sealed case hash mismatch: case-0001.md"),
  )

  assert.equal(await fs.readFile(OPENCODE_HELPER, "utf8"), await fs.readFile(CODEX_HELPER, "utf8"))
})
