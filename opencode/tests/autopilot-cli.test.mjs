import assert from "node:assert/strict"
import { spawnSync } from "node:child_process"
import * as fs from "node:fs/promises"
import * as os from "node:os"
import * as path from "node:path"
import test from "node:test"
import { fileURLToPath } from "node:url"

const OPENCODE_DIR = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..")
const CLI = path.join(OPENCODE_DIR, "skills", "autopilot", "scripts", "autopilot.py")
const PLUGIN_PATH = path.join(OPENCODE_DIR, "plugins", "labflow.ts")

function cli(args, { input } = {}) {
  return spawnSync("python3", [CLI, ...args], {
    cwd: OPENCODE_DIR,
    encoding: "utf8",
    input,
  })
}

function jsonResult(result) {
  assert.equal(result.status, 0, result.stderr || result.stdout)
  return JSON.parse(result.stdout)
}

function escapeRegex(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
}

async function fillSections(file, document, values) {
  let source = await fs.readFile(file, "utf8")
  for (const [field, value] of Object.entries(values)) {
    const start = `<!-- autopilot:${document}:${field}:start -->`
    const end = `<!-- autopilot:${document}:${field}:end -->`
    const pattern = new RegExp(`${escapeRegex(start)}\\s*[\\s\\S]*?\\s*${escapeRegex(end)}`)
    assert.match(source, pattern)
    source = source.replace(pattern, `${start}\n${value}\n${end}`)
  }
  await fs.writeFile(file, source)
}

async function initialize(t, title = "Autopilot CLI Test") {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), "labflow-autopilot-cli-"))
  t.after(() => fs.rm(root, { recursive: true, force: true }))
  const result = jsonResult(cli(["run", "init", "--root", root, "--title", title, "--json"]))
  return { root, run: result.data.run }
}

async function reviewerHooks(t) {
  const plugin = await import(`${new URL(`file://${PLUGIN_PATH}`).href}?autopilot-cli=${Date.now()}-${Math.random()}`)
  const hooks = await plugin.default()
  t.after(() => hooks.dispose())
  return hooks
}

async function attest(hooks, run, assignment, sessionID) {
  return JSON.parse(await hooks.tool.autopilot_review_attest.execute(
    { run, reviewId: assignment.reviewId, reviewNonce: assignment.reviewNonce },
    { agent: "autopilot-reviewer", sessionID },
  ))
}

async function fillAuthority(run) {
  await fillSections(path.join(run, "source.md"), "source", {
    approved_plan: "Implement the approved semantic workflow without changing its fixed intent.",
  })
  await fillSections(path.join(run, "contract.md"), "contract", {
    intent: "Deliver a durable, low-intrusion autonomous workflow.",
    success_boundary: "The workflow is deterministic, reviewable, and fully tested.",
    failure_boundary: "A partial prototype or unverified claim is not completion.",
    fixed_decisions: "Use one Goal and one persistent reviewer identity.",
    non_goals: "Do not create an implicit runtime hook.",
    method_freedom: "Implementation details may adapt to evidence.",
    human_gates: "No additional human judgment gate is required for this fixture.",
  })
  await fillSections(path.join(run, "envelope.md"), "envelope", {
    profile: "coding",
    workspace: "The temporary test repository.",
    write_scope: "Only the temporary run and test-owned files are writable.",
    git_policy: "Local-only; do not commit.",
    budget: "Ten minutes and bounded local commands.",
    max_turns: "20",
    max_duration_ms: "600000",
    max_tokens: "1000000",
    resources: "CPU only; no external service.",
    side_effects: "No push, deploy, publish, or network mutation.",
    stop_conditions: "Stop on integrity failure or a missing required decision.",
  })
}

async function fillCurrentPhase(run, suffix) {
  await fillSections(path.join(run, "phases", "current.md"), "phase", {
    objective: `Establish semantic behavior ${suffix}.`,
    why_now: "It is the highest-information remaining boundary.",
    entry_evidence: "The authority is sealed and the previous boundary is closed.",
    exit_evidence: "A deterministic check proves the intended behavior.",
    allowed_pivots: "The implementation may change while preserving contract semantics.",
    outcome: `The semantic behavior ${suffix} is verified.`,
    next_rationale: "Proceed to convergence review or the next evidence-bearing phase.",
  })
}

async function fillOutcome(run, suffix) {
  await fillSections(path.join(run, "outcome.md"), "outcome", {
    contract_coverage: `Every contract criterion is covered ${suffix}.`,
    decisive_evidence: "The CLI lifecycle and integrity checks pass.",
    artifacts: "The run dossier and deterministic manifest are retained.",
    failed_routes: "No failed route is represented as successful.",
    limitations: "This fixture uses a temporary repository.",
    residual_risks: "Human-facing quality still requires the configured reviewer gate.",
    handoff: "Run validate, inspect the approved review, then submit goal_complete.",
  })
}

function reviewClaim(verdict, assignment, taskId = "ses_reviewer_one") {
  const approved = verdict === "approved"
  return JSON.stringify({
    schemaVersion: 1,
    reviewId: assignment.reviewId,
    reviewNonce: assignment.reviewNonce,
    reviewerTaskId: taskId,
    authorityHead: assignment.authorityHead,
    outcomeSha256: assignment.outcomeSha256,
    verdict,
    summary: approved ? "The contract is satisfied." : "One contract criterion remains unsupported.",
    criteria: [
      {
        criterion: "Deterministic lifecycle",
        result: approved ? "satisfied" : "unsatisfied",
        evidence: approved ? ["run validate passed"] : ["the first outcome lacks remediation evidence"],
        reason: approved ? "The sealed artifacts and checks agree." : "The outcome needs another phase.",
      },
    ],
    evidenceInspected: ["contract.md", "outcome.md", "closed phase records"],
    probes: approved ? ["bounded CLI validation"] : [],
    counterevidence: approved ? [] : ["missing remediation phase"],
    requiredActions: approved ? [] : ["open and complete a remediation phase"],
    knownLimitations: ["temporary test repository"],
    confidence: "high",
  })
}

test("autopilot CLI exposes self-contained nested help", () => {
  for (const args of [
    ["-h"],
    ["run", "-h"],
    ["run", "init", "-h"],
    ["run", "status", "-h"],
    ["run", "validate", "-h"],
    ["run", "resume", "-h"],
    ["run", "finalize", "-h"],
    ["authority", "seal", "-h"],
    ["authority", "verify", "-h"],
    ["amendment", "new", "-h"],
    ["amendment", "seal", "-h"],
    ["amendment", "list", "-h"],
    ["phase", "open", "-h"],
    ["phase", "close", "-h"],
    ["phase", "list", "-h"],
    ["review", "open", "-h"],
    ["review", "probe", "-h"],
    ["review", "recover", "-h"],
    ["review", "record", "-h"],
    ["review", "list", "-h"],
    ["goal", "render", "-h"],
  ]) {
    const result = cli(args)
    assert.equal(result.status, 0, `${args.join(" ")}\n${result.stderr}`)
    assert.match(result.stdout, /usage:/)
    if (args.length === 3) assert.match(result.stdout, /Example:/)
  }
  assert.equal(cli(["review", "attest", "-h"]).status, 2)
})

test("autopilot CLI drives one sealed run through rejected and approved review", async (t) => {
  const { run } = await initialize(t)
  const hooks = await reviewerHooks(t)
  assert.equal(await fs.readFile(path.join(run, ".gitignore"), "utf8"), "*\n")

  const before = await fs.readFile(path.join(run, "manifest.json"), "utf8")
  const draftValidation = cli(["run", "validate", "--run", run, "--json"])
  assert.equal(draftValidation.status, 1)
  assert.equal(await fs.readFile(path.join(run, "manifest.json"), "utf8"), before)

  await fillAuthority(run)
  const sealed = jsonResult(cli(["authority", "seal", "--run", run, "--json"]))
  assert.match(sealed.data.head, /^[0-9a-f]{64}$/)

  jsonResult(cli(["phase", "open", "--run", run, "--title", "Initial evidence", "--json"]))
  await fillCurrentPhase(run, "for the initial route")
  const projection = jsonResult(cli(["goal", "render", "--run", run, "--json"]))
  assert.equal(projection.data.mode, "normal")
  assert.ok(projection.data.objective.length <= 4000)
  assert.ok(projection.data.successCriteria.length <= 2000)
  assert.ok(projection.data.constraints.length <= 2000)
  assert.equal(projection.data.maxTurns, 20)
  assert.equal(projection.data.maxDurationMs, 600000)
  assert.equal(projection.data.maxTokens, 1000000)
  jsonResult(cli(["phase", "close", "--run", run, "--json"]))

  await fillOutcome(run, "for the initial candidate")
  const firstReview = jsonResult(cli(["review", "open", "--run", run, "--json"]))
  assert.equal(firstReview.data.reviewId, "R0001")
  assert.match(firstReview.data.cli, /autopilot\.py$/)
  assert.equal(firstReview.data.language, "en")
  assert.equal(firstReview.data.reviewerTaskId, null)
  assert.equal(firstReview.data.previousVerdict, null)
  assert.equal((await attest(hooks, run, firstReview.data, "ses_reviewer_one")).ok, true)
  const contractBeforeProbe = await fs.readFile(path.join(run, "contract.md"), "utf8")
  const sandboxProbe = cli([
    "review",
    "probe",
    "--run",
    run,
    "--review-id",
    firstReview.data.reviewId,
    "--review-nonce",
    firstReview.data.reviewNonce,
    "--task-id",
    "ses_reviewer_one",
    "--timeout-seconds",
    "5",
    "--json",
    "--",
    "bash",
    "-lc",
    `printf hacked >> ${JSON.stringify(path.join(run, "contract.md"))}; printf probe-ok > probe.txt`,
  ])
  if (sandboxProbe.status === 0) {
    const probe = jsonResult(sandboxProbe)
    assert.equal(probe.data.exitCode, 0)
    assert.equal(await fs.readFile(path.join(run, "contract.md"), "utf8"), contractBeforeProbe)
    assert.equal(await fs.readFile(path.join(firstReview.data.probeRoot, "probe.txt"), "utf8"), "probe-ok")
  } else {
    assert.equal(sandboxProbe.status, 4)
    assert.equal(await fs.readFile(path.join(run, "contract.md"), "utf8"), contractBeforeProbe)
  }
  jsonResult(cli(["review", "record", "--run", run, "--stdin", "--json"], {
    input: reviewClaim("rejected", firstReview.data),
  }))

  jsonResult(cli(["phase", "open", "--run", run, "--title", "Reviewer remediation", "--json"]))
  await fillCurrentPhase(run, "after reviewer remediation")
  jsonResult(cli(["phase", "close", "--run", run, "--json"]))
  await fillOutcome(run, "after reviewer remediation")

  const secondReview = jsonResult(cli(["review", "open", "--run", run, "--json"]))
  assert.equal(secondReview.data.reviewId, "R0002")
  assert.equal(secondReview.data.reviewerTaskId, "ses_reviewer_one")
  assert.equal(secondReview.data.previousVerdict, "rejected")
  assert.deepEqual(secondReview.data.remediationPhases, ["P0002"])
  await assert.rejects(
    () => attest(hooks, run, secondReview.data, "ses_more_compliant"),
    /already bound to reviewer task ses_reviewer_one/,
  )
  assert.equal((await attest(hooks, run, secondReview.data, "ses_reviewer_one")).ok, true)
  jsonResult(cli(["review", "record", "--run", run, "--stdin", "--json"], {
    input: reviewClaim("approved", secondReview.data),
  }))
  assert.equal(cli(["phase", "open", "--run", run, "--title", "Bypass", "--json"]).status, 1)
  assert.equal(cli(["review", "open", "--run", run, "--json"]).status, 1)

  const approvedReviewPath = path.join(run, "reviews", "R0002.md")
  const approvedReview = await fs.readFile(approvedReviewPath, "utf8")
  await fs.rm(approvedReviewPath)
  const missingReview = cli(["run", "finalize", "--run", run, "--json"])
  assert.equal(missingReview.status, 3)
  await fs.writeFile(approvedReviewPath, approvedReview)
  jsonResult(cli(["run", "finalize", "--run", run, "--json"]))

  const validation = jsonResult(cli(["run", "validate", "--run", run, "--json"]))
  assert.equal(validation.data.status, "finalized")
  const manifest = JSON.parse(await fs.readFile(path.join(run, "manifest.json"), "utf8"))
  assert.equal(manifest.review.taskId, "ses_reviewer_one")
  assert.deepEqual(manifest.review.records.map((item) => item.verdict), ["rejected", "approved"])
  assert.deepEqual(manifest.phase.closed.map((item) => item.id), ["P0001", "P0002"])
})

test("autopilot CLI fails closed on sealed mutation and dossier symlinks", async (t) => {
  const { run } = await initialize(t, "Autopilot Integrity Test")
  await fillAuthority(run)
  jsonResult(cli(["authority", "seal", "--run", run, "--json"]))

  await fs.appendFile(path.join(run, "contract.md"), "\nunauthorized mutation\n")
  const mutated = cli(["authority", "verify", "--run", run, "--json"])
  assert.equal(mutated.status, 3)
  assert.match(JSON.parse(mutated.stdout).message, /hash mismatch/)

  const { run: symlinkRun } = await initialize(t, "Autopilot Symlink Test")
  await fs.symlink("contract.md", path.join(symlinkRun, "reviews", "unexpected-link"))
  const linked = cli(["run", "status", "--run", symlinkRun, "--json"])
  assert.equal(linked.status, 3)
  assert.match(JSON.parse(linked.stdout).message, /symlink/)
})

test("autopilot CLI seals an explicit amendment chain without rewriting base authority", async (t) => {
  const { run } = await initialize(t, "Autopilot Amendment Test")
  await fillAuthority(run)
  const base = jsonResult(cli(["authority", "seal", "--run", run, "--json"])).data.head
  const contractBefore = await fs.readFile(path.join(run, "contract.md"), "utf8")

  const draft = jsonResult(cli([
    "amendment",
    "new",
    "--run",
    run,
    "--title",
    "Authorized boundary change",
    "--json",
  ]))
  await fillSections(draft.data.path, "amendment", {
    authorization: "The user explicitly authorized this semantic change.",
    change: "The final handoff must additionally include a compact reproduction command.",
    unchanged: "The overall intent, reviewer identity, and safety boundary remain unchanged.",
    implications: "Future phases and the outcome must cover the reproduction command.",
  })
  const sealed = jsonResult(cli(["amendment", "seal", "--run", run, "--json"]))
  assert.notEqual(sealed.data.head, base)
  assert.equal(await fs.readFile(path.join(run, "contract.md"), "utf8"), contractBefore)
  jsonResult(cli(["authority", "verify", "--run", run, "--json"]))

  await fs.appendFile(draft.data.path, "\nunauthorized amendment mutation\n")
  const tampered = cli(["authority", "verify", "--run", run, "--json"])
  assert.equal(tampered.status, 3)
  assert.match(JSON.parse(tampered.stdout).message, /amendment hash mismatch/)
})

test("autopilot CLI reads an approved plan from stdin only when explicitly requested", async (t) => {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), "labflow-autopilot-stdin-"))
  t.after(() => fs.rm(root, { recursive: true, force: true }))
  const plan = "Approved plan from an explicit pipeline."
  const created = jsonResult(cli([
    "run",
    "init",
    "--root",
    root,
    "--title",
    "Explicit Stdin",
    "--stdin",
    "--json",
  ], { input: plan }))
  assert.match(await fs.readFile(path.join(created.data.run, "source.md"), "utf8"), new RegExp(plan))
})

test("autopilot CLI enforces review state transitions and at least one closed phase", async (t) => {
  const { run } = await initialize(t, "Autopilot State Machine Test")
  const hooks = await reviewerHooks(t)
  await fillAuthority(run)
  jsonResult(cli(["authority", "seal", "--run", run, "--json"]))
  await fillOutcome(run, "before any phase")
  assert.equal(cli(["review", "open", "--run", run, "--json"]).status, 1)

  jsonResult(cli(["phase", "open", "--run", run, "--title", "One phase", "--json"]))
  await fillCurrentPhase(run, "for state transitions")
  jsonResult(cli(["phase", "close", "--run", run, "--json"]))
  const review = jsonResult(cli(["review", "open", "--run", run, "--json"]))
  assert.equal((await attest(hooks, run, review.data, "ses_blocking_reviewer")).ok, true)
  jsonResult(cli(["review", "record", "--run", run, "--stdin", "--json"], {
    input: reviewClaim("blocked", review.data, "ses_blocking_reviewer"),
  }))
  assert.equal(cli(["review", "open", "--run", run, "--json"]).status, 1)
  assert.equal(cli([
    "amendment",
    "new",
    "--run",
    run,
    "--title",
    "Blocked bypass",
    "--json",
  ]).status, 1)
  jsonResult(cli(["run", "resume", "--run", run, "--reason", "The user supplied the missing judgment.", "--json"]))
  jsonResult(cli(["review", "open", "--run", run, "--json"]))
})

test("autopilot CLI rejects malformed manifest paths, invalid profiles, and ignore removal", async (t) => {
  const { run } = await initialize(t, "Autopilot Schema Test")
  await fillAuthority(run)
  await fillSections(path.join(run, "envelope.md"), "envelope", { profile: "arbitrary" })
  assert.equal(cli(["authority", "seal", "--run", run, "--json"]).status, 1)
  await fillSections(path.join(run, "envelope.md"), "envelope", { profile: "coding" })
  jsonResult(cli(["authority", "seal", "--run", run, "--json"]))

  await fs.writeFile(path.join(run, ".gitignore"), "")
  assert.equal(cli(["run", "validate", "--run", run, "--json"]).status, 3)
  await fs.writeFile(path.join(run, ".gitignore"), "*\n")

  const manifestPath = path.join(run, "manifest.json")
  const originalManifest = JSON.parse(await fs.readFile(manifestPath, "utf8"))
  const forgedFinal = structuredClone(originalManifest)
  forgedFinal.status = "finalized"
  forgedFinal.outcome = { sha256: "0".repeat(64), finalizedAt: new Date().toISOString() }
  await fs.writeFile(manifestPath, `${JSON.stringify(forgedFinal, null, 2)}\n`)
  const invalidFinal = cli(["run", "status", "--run", run, "--json"])
  assert.equal(invalidFinal.status, 3)
  assert.match(JSON.parse(invalidFinal.stdout).message, /finalized run/)

  const manifest = structuredClone(originalManifest)
  manifest.authority.amendments.push({
    id: "A0001",
    path: "../../escape.md",
    sha256: "0".repeat(64),
    head: "0".repeat(64),
  })
  manifest.authority.nextAmendment = 2
  await fs.writeFile(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`)
  const escaped = cli(["run", "status", "--run", run, "--json"])
  assert.equal(escaped.status, 3)
  assert.match(JSON.parse(escaped.stdout).message, /invalid dossier path|escapes/)
})

test("autopilot CLI safely recovers an expired probe reservation before review record", async (t) => {
  const { run } = await initialize(t, "Autopilot Probe Recovery Test")
  const hooks = await reviewerHooks(t)
  await fillAuthority(run)
  jsonResult(cli(["authority", "seal", "--run", run, "--json"]))
  jsonResult(cli(["phase", "open", "--run", run, "--title", "Recovery phase", "--json"]))
  await fillCurrentPhase(run, "for recovery")
  jsonResult(cli(["phase", "close", "--run", run, "--json"]))
  await fillOutcome(run, "for recovery")
  const review = jsonResult(cli(["review", "open", "--run", run, "--json"])).data
  await attest(hooks, run, review, "ses_recovery_reviewer")

  const manifestPath = path.join(run, "manifest.json")
  const manifest = JSON.parse(await fs.readFile(manifestPath, "utf8"))
  manifest.review.open.probeUsedSeconds = 5
  manifest.review.open.probeNext = 2
  manifest.review.open.probeInFlight.push({
    id: "probe-0001",
    ownerPid: 999999,
    ownerStart: "dead-process-token",
    reservedAt: new Date(Date.now() - 60_000).toISOString(),
    deadlineEpoch: Math.floor(Date.now() / 1000) - 30,
    timeoutSeconds: 5,
  })
  await fs.writeFile(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`)

  const blockedRecord = cli(["review", "record", "--run", run, "--stdin", "--json"], {
    input: reviewClaim("rejected", review, "ses_recovery_reviewer"),
  })
  assert.equal(blockedRecord.status, 1)
  const recovered = jsonResult(cli([
    "review",
    "recover",
    "--run",
    run,
    "--review-id",
    review.reviewId,
    "--review-nonce",
    review.reviewNonce,
    "--reason",
    "Reviewer host process terminated",
    "--json",
  ]))
  assert.equal(recovered.data.probes[0].id, "probe-0001")
  assert.equal(
    JSON.parse(await fs.readFile(path.join(run, "reviews", "probes", "R0001", "probe-0001.json"), "utf8")).status,
    "aborted",
  )
  jsonResult(cli(["review", "record", "--run", run, "--stdin", "--json"], {
    input: reviewClaim("rejected", review, "ses_recovery_reviewer"),
  }))
})
