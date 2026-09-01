import assert from "node:assert/strict"
import { spawnSync } from "node:child_process"
import * as fs from "node:fs/promises"
import * as os from "node:os"
import * as path from "node:path"
import { fileURLToPath, pathToFileURL } from "node:url"
import test from "node:test"
import adapter, { createPtyActivityProvider } from "../plugins/goal-pty-adapter.ts"

const OPENCODE_DIR = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..")
const AUTOPILOT_CLI = path.join(OPENCODE_DIR, "skills", "autopilot", "scripts", "autopilot.py")

function autopilotCli(args, input) {
  const result = spawnSync("python3", [AUTOPILOT_CLI, ...args], { encoding: "utf8", input })
  assert.equal(result.status, 0, result.stderr || result.stdout)
  return JSON.parse(result.stdout)
}

async function fillMarkedSections(file, document, values) {
  let source = await fs.readFile(file, "utf8")
  for (const [field, value] of Object.entries(values)) {
    const start = `<!-- autopilot:${document}:${field}:start -->`
    const end = `<!-- autopilot:${document}:${field}:end -->`
    const begin = source.indexOf(start)
    const finish = source.indexOf(end)
    assert.ok(begin >= 0 && finish > begin, `${document}.${field}`)
    source = source.slice(0, begin) + `${start}\n${value}\n` + source.slice(finish)
  }
  await fs.writeFile(file, source)
}

async function createFinalizedDossier(root, finalize = true) {
  const initialized = autopilotCli(["run", "init", "--root", root, "--title", "Adapter Finalized Run", "--json"])
  const run = initialized.data.run
  await fillMarkedSections(path.join(run, "source.md"), "source", { approved_plan: "Approved adapter integration plan." })
  await fillMarkedSections(path.join(run, "contract.md"), "contract", {
    intent: "Verify completion-only adapter policy.",
    success_boundary: "A strict finalized dossier releases Goal completion.",
    failure_boundary: "A status-only or malformed dossier is insufficient.",
    fixed_decisions: "Use one session-bound Autopilot run.",
    non_goals: "Do not weaken PTY continuation behavior.",
    method_freedom: "Implementation details may vary.",
    human_gates: "No human-only gate remains in this fixture.",
  })
  await fillMarkedSections(path.join(run, "envelope.md"), "envelope", {
    profile: "coding",
    workspace: root,
    write_scope: "Only test-owned files.",
    git_policy: "Local-only.",
    budget: "Bounded test run.",
    max_turns: "10",
    max_duration_ms: "600000",
    max_tokens: "1000000",
    resources: "CPU only.",
    side_effects: "No external side effects.",
    stop_conditions: "Stop on failed validation.",
  })
  autopilotCli(["authority", "seal", "--run", run, "--json"])
  autopilotCli(["phase", "open", "--run", run, "--title", "Verify completion", "--json"])
  await fillMarkedSections(path.join(run, "phases", "current.md"), "phase", {
    objective: "Verify strict completion release.",
    why_now: "It is the remaining acceptance boundary.",
    entry_evidence: "Authority is sealed.",
    exit_evidence: "The adapter accepts only a fully finalized run.",
    allowed_pivots: "Use an equivalent strict validation route.",
    outcome: "Strict validation is demonstrated.",
    next_rationale: "Proceed to convergence review.",
  })
  autopilotCli(["phase", "close", "--run", run, "--json"])
  await fillMarkedSections(path.join(run, "outcome.md"), "outcome", {
    contract_coverage: "Every fixture criterion is covered.",
    decisive_evidence: "Strict CLI validation passes.",
    artifacts: "The finalized test dossier.",
    failed_routes: "Status-only finalization is rejected.",
    limitations: "Temporary test fixture.",
    residual_risks: "None material to this adapter contract.",
    handoff: "Use the dossier for completion policy verification.",
  })
  const review = autopilotCli(["review", "open", "--run", run, "--json"]).data
  const manifestPath = path.join(run, "manifest.json")
  const manifest = JSON.parse(await fs.readFile(manifestPath, "utf8"))
  manifest.review.taskId = "ses_adapter_reviewer"
  manifest.review.open.taskId = "ses_adapter_reviewer"
  await fs.writeFile(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`)
  const claim = {
    schemaVersion: 1,
    reviewId: review.reviewId,
    reviewNonce: review.reviewNonce,
    reviewerTaskId: "ses_adapter_reviewer",
    authorityHead: review.authorityHead,
    outcomeSha256: review.outcomeSha256,
    verdict: "approved",
    summary: "The adapter completion contract is satisfied.",
    criteria: [{ criterion: "Strict completion", result: "satisfied", evidence: ["run validate passed"], reason: "All finalized identities agree." }],
    evidenceInspected: ["contract.md", "outcome.md"],
    probes: [],
    counterevidence: [],
    requiredActions: [],
    knownLimitations: ["temporary fixture"],
    confidence: "high",
  }
  autopilotCli(["review", "record", "--run", run, "--stdin", "--json"], JSON.stringify(claim))
  if (finalize) autopilotCli(["run", "finalize", "--run", run, "--json"])
  return run
}

function pty(id, parentSessionId, overrides = {}) {
  return {
    id,
    parentSessionId,
    title: id,
    description: `${id} job`,
    status: "running",
    notifyOnExit: true,
    ...overrides,
  }
}

function integration(initial = []) {
  const sessions = new Map(initial.map((session) => [session.id, session]))
  const callbacks = new Set()
  return {
    sessions,
    callbacks,
    listPtySessions(parentSessionId) {
      return [...sessions.values()].filter(
        (session) => !parentSessionId || session.parentSessionId === parentSessionId,
      )
    },
    getPtySession(id) {
      return sessions.get(id) ?? null
    },
    subscribePtySessionUpdates(callback) {
      callbacks.add(callback)
      return () => callbacks.delete(callback)
    },
    update(session, { remove = false } = {}) {
      if (remove) sessions.delete(session.id)
      else sessions.set(session.id, session)
      for (const callback of callbacks) callback(session)
    },
  }
}

function exitMessage(id) {
  return [
    "<pty_exited>",
    `ID: ${id}`,
    "Exit Code: 0",
    "Output Lines: 1",
    "Last Line: done",
    "</pty_exited>",
    "",
    "Use pty_read to check the full output.",
  ].join("\n")
}

test("adapter exports the OpenCode v1 plugin module shape", () => {
  assert.equal(adapter.id, "labflow-goal-pty-adapter")
  assert.equal(typeof adapter.server, "function")
})

test("PTY activity provider blocks only notifying work owned by the session", async () => {
  const api = integration([
    pty("pty_training", "parent-1"),
    pty("pty_tensorboard", "parent-1", { notifyOnExit: false }),
    pty("pty_other", "parent-2"),
    pty("pty_finished", "parent-1", { status: "exited" }),
    pty("pty_stopping", "parent-1", { status: "killing" }),
  ])
  const provider = createPtyActivityProvider(api)

  assert.deepEqual(await provider.listActive("parent-1"), [
    { id: "pty_training", label: "pty_training job", kind: "process" },
    { id: "pty_stopping", label: "pty_stopping job", kind: "process" },
  ])
  provider.dispose()
  assert.equal(api.callbacks.size, 0)
})

test("PTY completion notification is trusted once for its owning session", async () => {
  const running = pty("pty_fast", "parent-1")
  const api = integration([running])
  const provider = createPtyActivityProvider(api)
  const finished = { ...running, status: "exited" }
  api.update(finished, { remove: true })

  const notification = {
    sessionID: "parent-1",
    messageID: "message-1",
    text: exitMessage("pty_fast"),
  }
  assert.equal(await provider.classifyNotification(notification), true)
  assert.equal(await provider.classifyNotification(notification), true)
  assert.equal(
    await provider.classifyNotification({ ...notification, messageID: "message-replay" }),
    false,
  )
  assert.equal(
    await provider.classifyNotification({ ...notification, sessionID: "parent-2" }),
    false,
  )
  assert.equal(
    await provider.classifyNotification({ ...notification, text: "human message" }),
    false,
  )
  assert.deepEqual(await provider.listActive("parent-1"), [])
  provider.dispose()
})

test("adapter composes local Goal and PTY modules without a package dependency", async (t) => {
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), "goal-pty-adapter-"))
  t.after(() => fs.rm(directory, { recursive: true, force: true }))
  const goalModule = path.join(directory, "goal.mjs")
  const ptyModule = path.join(directory, "pty.mjs")
  await fs.writeFile(goalModule, [
    "export async function GoalPlugin(_context, options) {",
    "  return {",
    "    inheritedMaxTurns: options.maxTurns,",
    "    listActive: (sessionID) => options.externalActivityProvider.listActive(sessionID),",
    "    dispose: async () => {},",
    "  }",
    "}",
    "",
  ].join("\n"))
  await fs.writeFile(ptyModule, [
    "const sessions = [{id:'pty_1', parentSessionId:'parent', title:'training', status:'running', notifyOnExit:true}]",
    "export const listPtySessions = (parent) => sessions.filter((session) => !parent || session.parentSessionId === parent)",
    "export const getPtySession = (id) => sessions.find((session) => session.id === id) || null",
    "export const subscribePtySessionUpdates = () => () => {}",
    "",
  ].join("\n"))

  const hooks = await adapter.server({}, {
    goalPluginUrl: pathToFileURL(goalModule).href,
    ptyIntegrationUrl: pathToFileURL(ptyModule).href,
    goalOptions: { maxTurns: 1000 },
  })
  assert.equal(hooks.inheritedMaxTurns, 1000)
  assert.deepEqual(await hooks.listActive("parent"), [
    { id: "pty_1", label: "training", kind: "process" },
  ])
  await hooks.dispose()
})

test("runtime config toggles PTY gating while retaining completion policy support", async (t) => {
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), "goal-pty-runtime-toggle-"))
  t.after(() => fs.rm(directory, { recursive: true, force: true }))
  const goalModule = path.join(directory, "goal.mjs")
  const ptyModule = path.join(directory, "pty.mjs")
  const runtimeConfigPath = path.join(directory, "runtime.json")
  await fs.writeFile(goalModule, [
    "export async function GoalPlugin(_context, options) {",
    "  return {",
    "    hasExternalProvider: Boolean(options.externalActivityProvider),",
    "    listActive: (sessionID) => options.externalActivityProvider.listActive(sessionID),",
    "    dispose: async () => {},",
    "  }",
    "}",
    "",
  ].join("\n"))
  await fs.writeFile(ptyModule, [
    "export const listPtySessions = () => []",
    "export const getPtySession = () => null",
    "export const subscribePtySessionUpdates = () => () => {}",
    "",
  ].join("\n"))
  const runtimeConfig = {
    version: 1,
    enabled: false,
    goalPluginUrl: pathToFileURL(goalModule).href,
    ptyPluginUrl: pathToFileURL(ptyModule).href,
    ptyIntegrationUrl: pathToFileURL(ptyModule).href,
  }
  await fs.writeFile(runtimeConfigPath, JSON.stringify(runtimeConfig))

  let hooks = await adapter.server({}, { runtimeConfigPath })
  assert.equal(hooks.hasExternalProvider, true)
  assert.deepEqual(await hooks.listActive("session"), [])
  await hooks.dispose()

  runtimeConfig.enabled = true
  await fs.writeFile(runtimeConfigPath, JSON.stringify(runtimeConfig))
  hooks = await adapter.server({}, { runtimeConfigPath })
  assert.equal(hooks.hasExternalProvider, true)
  await hooks.dispose()
})

test("Autopilot completion blockers bind through Goal tools and release after finalization", async (t) => {
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), "goal-autopilot-completion-"))
  t.after(() => fs.rm(directory, { recursive: true, force: true }))
  const run = await createFinalizedDossier(directory, false)
  const goalModule = path.join(directory, "goal.mjs")
  await fs.writeFile(goalModule, [
    "let commandCalls = 0",
    "export const getCommandCalls = () => commandCalls",
    "export async function GoalPlugin(_context, options) {",
    "  return {",
    "    'command.execute.before': async () => { commandCalls += 1 },",
    "    tool: {",
    "      goal_set: { execute: async (args) => JSON.stringify({ok:true,message:`New active goal: ${args.objective}`}) },",
    "      goal_complete: { execute: async (_args, context) => JSON.stringify(await options.externalActivityProvider.listCompletionBlockers(context.sessionID)) },",
    "    },",
    "    dispose: async () => {},",
    "  }",
    "}",
    "",
  ].join("\n"))

  const hooks = await adapter.server({}, { goalPluginUrl: pathToFileURL(goalModule).href, enabled: false })
  const context = { sessionID: "session-autopilot" }
  await hooks.tool.goal_set.execute({ objective: `Autopilot run: review-run\nAutopilot dossier: ${run}` }, context)
  let blockers = JSON.parse(await hooks.tool.goal_complete.execute({}, context))
  assert.equal(blockers.length, 1)
  assert.match(blockers[0].label, /not finalized|cannot be verified/)
  const replacement = JSON.parse(await hooks.tool.goal_set.execute({ objective: "ordinary replacement" }, context))
  assert.equal(replacement.ok, false)
  assert.equal(replacement.error, "autopilot_goal_bound")
  await assert.rejects(
    () => hooks["command.execute.before"](
      { command: "goal", sessionID: context.sessionID, arguments: "add another goal" },
      { parts: [] },
    ),
    /while an Autopilot dossier is active/,
  )
  await hooks["command.execute.before"](
    { command: "goal", sessionID: context.sessionID, arguments: "status" },
    { parts: [] },
  )
  const fakeGoal = await import(pathToFileURL(goalModule).href)
  assert.equal(fakeGoal.getCommandCalls(), 1, "read-only status reaches Goal, blocked add does not")

  autopilotCli(["run", "finalize", "--run", run, "--json"])
  blockers = JSON.parse(await hooks.tool.goal_complete.execute({}, context))
  assert.deepEqual(blockers, [])
  await hooks.dispose()
})

test(
  "local Goal fork enforces Autopilot finalization before canonical completion",
  { skip: !process.env.LABFLOW_TEST_GOAL_PLUGIN_URL, timeout: 30000 },
  async (t) => {
    const directory = await fs.mkdtemp(path.join(os.tmpdir(), "goal-autopilot-live-completion-"))
    t.after(() => fs.rm(directory, { recursive: true, force: true }))
    const run = await createFinalizedDossier(directory, false)
    const client = {
      app: { log: async () => {} },
      session: {
        get: async () => ({ data: { id: "session-live-completion", agent: "build" } }),
        update: async () => ({ data: {} }),
        messages: async () => ({ data: [] }),
        promptAsync: async () => ({}),
      },
    }
    const hooks = await adapter.server({ client, directory }, {
      goalPluginUrl: process.env.LABFLOW_TEST_GOAL_PLUGIN_URL,
      enabled: false,
      goalOptions: { persistState: false, lifecycleMessages: false, sessionTitleStatus: false },
    })
    const context = { sessionID: "session-live-completion" }
    const objective = `Autopilot run: live-completion\nAutopilot dossier: ${run}\nCurrent semantic phase P0001: verify completion policy`
    const created = JSON.parse(await hooks.tool.goal_set.execute({ objective }, context))
    assert.equal(created.ok, true)

    const rejected = JSON.parse(await hooks.tool.goal_complete.execute({ summary: "Not finalized" }, context))
    assert.equal(rejected.ok, false)
    assert.match(rejected.message, /Autopilot dossier.*not finalized|cannot be verified/)
    await assert.rejects(
      () => hooks["command.execute.before"](
        { command: "goal", sessionID: context.sessionID, arguments: "add bypass goal" },
        { parts: [] },
      ),
      /while an Autopilot dossier is active/,
    )

    autopilotCli(["run", "finalize", "--run", run, "--json"])
    const completed = JSON.parse(await hooks.tool.goal_complete.execute({ summary: "Finalized and verified" }, context))
    assert.equal(completed.ok, true)
    await hooks.dispose()
  },
)

test(
  "local forks defer Goal until a real PTY exit turn finishes",
  {
    skip:
      !process.env.LABFLOW_TEST_GOAL_PLUGIN_URL ||
      !process.env.LABFLOW_TEST_PTY_PLUGIN_URL ||
      !process.env.LABFLOW_TEST_PTY_INTEGRATION_URL,
    timeout: 30000,
  },
  async () => {
    const directory = await fs.mkdtemp(path.join(os.tmpdir(), "goal-pty-live-hooks-"))
    try {
      const ptyModule = await import(process.env.LABFLOW_TEST_PTY_PLUGIN_URL)
      let goalHooks
      let goalContinuations = 0
      let notificationResolve
      let notificationReject
      const notificationHandled = new Promise((resolve, reject) => {
        notificationResolve = resolve
        notificationReject = reject
      })
      const messages = [
      {
        info: {
          id: "assistant-spawned-pty",
          role: "assistant",
          sessionID: "parent-session",
          tokens: { input: 10, output: 20, reasoning: 0 },
        },
        parts: [
          { type: "text", text: "Started formal training." },
          { type: "tool", tool: "pty_spawn", state: { status: "completed" } },
        ],
      },
    ]
      const client = {
      app: { log: async () => {} },
      config: {
        get: async () => ({
          data: { permission: { bash: "allow", external_directory: "allow" } },
        }),
      },
      tui: { showToast: async () => ({}) },
      session: {
        get: async () => ({ data: { id: "parent-session", agent: "build" } }),
        update: async () => ({ data: {} }),
        messages: async () => ({ data: messages }),
        abort: async () => ({}),
        promptAsync: async (input) => {
          try {
            const sessionID = input?.path?.id || input?.sessionID
            const parts = input?.body?.parts || input?.parts || []
            const text = parts.map((part) => part.text || "").join("\n")
            if (!text.startsWith("<pty_exited>")) {
              goalContinuations += 1
              return {}
            }
            const messageID = "pty-exit-notification"
            const user = {
              info: { id: messageID, role: "user", sessionID },
              parts,
            }
            messages.push(user)
            await goalHooks["chat.message"](
              { sessionID, messageID, agent: "build" },
              { message: user.info, parts },
            )
            messages.push({
              info: {
                id: "assistant-processed-exit",
                role: "assistant",
                sessionID,
                parentID: messageID,
                tokens: { input: 20, output: 30, reasoning: 0 },
              },
              parts: [
                { type: "text", text: "Verified the final PTY result." },
                { type: "tool", tool: "pty_read", state: { status: "completed" } },
              ],
            })
            await goalHooks.event({
              event: {
                type: "session.status",
                properties: { sessionID, status: { type: "idle" } },
              },
            })
            notificationResolve()
            return {}
          } catch (error) {
            notificationReject(error)
            throw error
          }
        },
      },
    }
      const ptyHooks = await ptyModule.PTYPlugin({ client, directory })
      goalHooks = await adapter.server(
      { client, directory },
      {
        goalPluginUrl: process.env.LABFLOW_TEST_GOAL_PLUGIN_URL,
        ptyIntegrationUrl: process.env.LABFLOW_TEST_PTY_INTEGRATION_URL,
        goalOptions: {
          persistState: false,
          minDelayMs: 1,
          noToolCallTurnsBeforePause: 0,
        },
      },
    )
      await goalHooks["command.execute.before"](
      { command: "goal", sessionID: "parent-session", arguments: "finish training" },
      { parts: [] },
    )
      await ptyHooks.tool.pty_spawn.execute(
      {
        command: "sh",
        args: ["-c", "sleep 0.2; printf 'training done\\n'"],
        workdir: directory,
        description: "Short formal training",
        notifyOnExit: true,
      },
      {
        sessionID: "parent-session",
        messageID: "spawn-call",
        agent: "build",
        abort: new AbortController().signal,
        metadata: () => {},
        ask: async () => {},
        directory,
        worktree: directory,
      },
    )
      await goalHooks.event({
      event: {
        type: "session.status",
        properties: { sessionID: "parent-session", status: { type: "idle" } },
      },
    })
      assert.equal(goalContinuations, 0)

      await Promise.race([
        notificationHandled,
        new Promise((_, reject) =>
          setTimeout(() => reject(new Error("PTY exit notification timed out")), 10000),
        ),
      ])
      assert.equal(goalContinuations, 1)
      await ptyHooks.event({
        event: { type: "session.deleted", properties: { info: { id: "parent-session" } } },
      })
      await goalHooks.dispose()
    } finally {
      await fs.rm(directory, { recursive: true, force: true })
    }
  },
)
