import assert from "node:assert/strict"
import * as fs from "node:fs/promises"
import * as os from "node:os"
import * as path from "node:path"
import { pathToFileURL } from "node:url"
import test from "node:test"
import adapter, { createPtyActivityProvider } from "../plugins/goal-pty-adapter.ts"

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

test(
  "local forks defer Goal until a real PTY exit turn finishes",
  {
    skip:
      !process.env.LABFLOW_TEST_GOAL_PLUGIN_URL ||
      !process.env.LABFLOW_TEST_PTY_PLUGIN_URL ||
      !process.env.LABFLOW_TEST_PTY_INTEGRATION_URL,
  },
  async (t) => {
    const directory = await fs.mkdtemp(path.join(os.tmpdir(), "goal-pty-live-hooks-"))
    t.after(() => fs.rm(directory, { recursive: true, force: true }))
    const ptyModule = await import(process.env.LABFLOW_TEST_PTY_PLUGIN_URL)
    let goalHooks
    let goalContinuations = 0
    let notificationResolve
    const notificationHandled = new Promise((resolve) => {
      notificationResolve = resolve
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
        setTimeout(() => reject(new Error("PTY exit notification timed out")), 5000),
      ),
    ])
    assert.equal(goalContinuations, 1)
    await ptyHooks.event({
      event: { type: "session.deleted", properties: { info: { id: "parent-session" } } },
    })
    await goalHooks.dispose()
  },
)
