import { execFile } from "node:child_process"
import * as fs from "node:fs/promises"
import * as path from "node:path"
import { fileURLToPath } from "node:url"
import { promisify } from "node:util"

type PtyStatus = "running" | "exited" | "killing" | "killed"

type PtySession = {
  id: string
  parentSessionId: string
  title: string
  description?: string
  status: PtyStatus
  notifyOnExit: boolean
}

type PtyIntegration = {
  listPtySessions(parentSessionId?: string): PtySession[]
  getPtySession(id: string): PtySession | null
  subscribePtySessionUpdates(callback: (session: PtySession) => void): () => void
}

type AdapterOptions = {
  runtimeConfigPath?: string
  enabled?: boolean
  goalPluginUrl?: string
  ptyIntegrationUrl?: string
  goalOptions?: Record<string, unknown>
}

type RuntimeConfig = {
  version: number
  enabled: boolean
  goalPluginUrl: string
  ptyPluginUrl: string
  ptyIntegrationUrl: string
}

const ACTIVE_STATUSES = new Set<PtyStatus>(["running", "killing"])
const TERMINAL_STATUSES = new Set<PtyStatus>(["exited", "killed"])
const MAX_REMEMBERED_SESSIONS = 4096
const PTY_EXIT_ID = /^ID:\s*(pty_[A-Za-z0-9]+)\s*$/m
const AUTOPILOT_DOSSIER = /^Autopilot dossier:\s*(\/[^\r\n]+)\s*$/m
const AUTOPILOT_CLI = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../skills/autopilot/scripts/autopilot.py")
const execFileAsync = promisify(execFile)

function validateIntegration(value: unknown): asserts value is PtyIntegration {
  const candidate = value as Partial<PtyIntegration> | undefined
  if (
    !candidate ||
    typeof candidate.listPtySessions !== "function" ||
    typeof candidate.getPtySession !== "function" ||
    typeof candidate.subscribePtySessionUpdates !== "function"
  ) {
    throw new TypeError("PTY integration module does not expose the required lifecycle API")
  }
}

function parsePtyExitNotification(text: string): string {
  if (!text.startsWith("<pty_exited>\n") || !text.includes("\n</pty_exited>")) return ""
  return text.match(PTY_EXIT_ID)?.[1] ?? ""
}

export function createPtyActivityProvider(integration: PtyIntegration) {
  validateIntegration(integration)
  const sessions = new Map<string, { session: PtySession; observedAt: number }>()
  const claimedNotifications = new Map<string, string>()

  const remember = (session: PtySession) => {
    sessions.set(session.id, { session: { ...session }, observedAt: Date.now() })
    if (sessions.size <= MAX_REMEMBERED_SESSIONS) return
    for (const [id, entry] of sessions) {
      if (!TERMINAL_STATUSES.has(entry.session.status)) continue
      sessions.delete(id)
      claimedNotifications.delete(id)
      if (sessions.size <= MAX_REMEMBERED_SESSIONS) break
    }
  }

  try {
    for (const session of integration.listPtySessions()) remember(session)
  } catch {
    // Goal owns fail-open probe reporting; initialization must remain available.
  }
  const unsubscribe = integration.subscribePtySessionUpdates(remember)

  return {
    async listActive(sessionID: string) {
      const live = integration.listPtySessions(sessionID)
      for (const session of live) remember(session)
      const candidates = new Map(
        [...sessions.values()]
          .map((entry) => entry.session)
          .filter((session) => session.parentSessionId === sessionID)
          .map((session) => [session.id, session]),
      )
      for (const session of live) candidates.set(session.id, session)
      return [...candidates.values()]
        .filter(
          (session) =>
            session.notifyOnExit && ACTIVE_STATUSES.has(session.status),
        )
        .map((session) => ({
          id: session.id,
          label: session.description || session.title,
          kind: "process",
        }))
    },
    async classifyNotification({
      sessionID,
      messageID,
      text,
    }: {
      sessionID: string
      messageID: string
      text: string
    }) {
      const id = parsePtyExitNotification(text)
      if (!id || !messageID) return false
      const session = integration.getPtySession(id) || sessions.get(id)?.session
      if (
        !session ||
        session.parentSessionId !== sessionID ||
        !session.notifyOnExit ||
        !TERMINAL_STATUSES.has(session.status)
      ) {
        return false
      }
      const claimedMessageID = claimedNotifications.get(id)
      if (claimedMessageID && claimedMessageID !== messageID) return false
      claimedNotifications.set(id, messageID)
      return true
    },
    dispose() {
      unsubscribe()
      sessions.clear()
      claimedNotifications.clear()
    },
  }
}

function toolResultText(result: unknown): string {
  if (typeof result !== "string") return ""
  try {
    const parsed = JSON.parse(result)
    return typeof parsed?.message === "string" ? parsed.message : result
  } catch {
    return result
  }
}

function autopilotRunFromText(text: string): string {
  const candidate = text.match(AUTOPILOT_DOSSIER)?.[1]?.trim()
  return candidate && path.isAbsolute(candidate) ? path.resolve(candidate) : ""
}

async function completionBlockersForRun(run: string) {
  try {
    const { stdout } = await execFileAsync(
      "python3",
      [AUTOPILOT_CLI, "run", "validate", "--run", run, "--json"],
      { timeout: 30_000, maxBuffer: 1024 * 1024 },
    )
    const validation = JSON.parse(stdout)
    if (validation?.ok !== true || validation?.data?.status !== "finalized") {
      throw new Error("validated dossier is not finalized")
    }
    return []
  } catch (error) {
    const candidate = error as { stdout?: string; stderr?: string; message?: string }
    let message = candidate?.stderr?.trim() || candidate?.stdout?.trim() || candidate?.message || String(error)
    try {
      const parsed = JSON.parse(candidate?.stdout || "")
      if (typeof parsed?.message === "string") message = parsed.message
    } catch {
      // Keep the bounded process diagnostic.
    }
    return [{
      id: `autopilot-integrity:${path.basename(run) || "unknown"}`,
      label: `Autopilot dossier is not finalized or cannot be verified: ${message.slice(0, 160)}`,
      kind: "workflow integrity",
    }]
  }
}

async function autopilotRunIsFinalized(run: string): Promise<boolean> {
  return (await completionBlockersForRun(run)).length === 0
}

function rejectedGoalToolResult(name: string, message: string): string {
  if (name.startsWith("goal_")) {
    return JSON.stringify({
      version: 1,
      operation: name.slice("goal_".length),
      ok: false,
      error: "autopilot_goal_bound",
      message,
    })
  }
  return message
}

function bindAutopilotRunFromGoalTools(
  hooks: Record<string, unknown>,
  runsBySession: Map<string, string>,
) {
  const tools = hooks.tool as Record<string, { execute?: (args: unknown, context: { sessionID?: string }) => Promise<unknown> }> | undefined
  if (!tools) return
  for (const name of ["goal_set", "set_goal", "update_goal", "goal_status", "get_goal"]) {
    const definition = tools[name]
    if (typeof definition?.execute !== "function") continue
    const execute = definition.execute
    definition.execute = async (args, context) => {
      const sessionID = context?.sessionID
      const objective = typeof (args as { objective?: unknown })?.objective === "string"
        ? (args as { objective: string }).objective
        : ""
      const requestedRun = autopilotRunFromText(objective)
      const boundRun = sessionID ? runsBySession.get(sessionID) : ""
      if (boundRun && ["goal_set", "set_goal"].includes(name)) {
        const finalized = await autopilotRunIsFinalized(boundRun)
        if (!finalized) {
          return rejectedGoalToolResult(
            name,
            "Cannot replace the focused Goal while its Autopilot dossier is active. Update the same run objective, or finalize or explicitly stop that run first.",
          )
        }
        runsBySession.delete(sessionID!)
      }
      if (boundRun && name === "update_goal" && objective) {
        if (!(await autopilotRunIsFinalized(boundRun)) && requestedRun !== boundRun) {
          return "Cannot move the focused Goal away from its active Autopilot dossier. Use the CLI-rendered objective for the same run."
        }
      }
      const result = await execute(args, context)
      if (!sessionID) return result
      const resultText = toolResultText(result)
      const run = requestedRun || autopilotRunFromText(resultText)
      if (run) runsBySession.set(sessionID, run)
      if (!run && /No active goal/i.test(resultText)) runsBySession.delete(sessionID)
      return result
    }
  }
  for (const name of ["clear_goal"]) {
    const definition = tools[name]
    if (typeof definition?.execute !== "function") continue
    const execute = definition.execute
    definition.execute = async (args, context) => {
      const boundRun = context?.sessionID ? runsBySession.get(context.sessionID) : ""
      if (boundRun && !(await autopilotRunIsFinalized(boundRun))) {
        return "Cannot clear the focused Goal while its Autopilot dossier is active. Finalize or explicitly stop that run first."
      }
      const result = await execute(args, context)
      if (context?.sessionID && /Goal cleared/i.test(toolResultText(result))) {
        runsBySession.delete(context.sessionID)
      }
      return result
    }
  }
}

function guardAutopilotGoalCommands(
  hooks: Record<string, unknown>,
  runsBySession: Map<string, string>,
  commandName: string,
) {
  const original = hooks["command.execute.before"] as
    | ((input: { command?: string; sessionID?: string; arguments?: string }, output: unknown) => Promise<unknown>)
    | undefined
  if (typeof original !== "function") return
  hooks["command.execute.before"] = async (
    input: { command?: string; sessionID?: string; arguments?: string },
    output: unknown,
  ) => {
    const sessionID = input?.sessionID
    const boundRun = sessionID ? runsBySession.get(sessionID) : ""
    if (boundRun && input?.command === commandName) {
      if (await autopilotRunIsFinalized(boundRun)) {
        runsBySession.delete(sessionID!)
      } else {
        const action = String(input.arguments || "").trim().split(/\s+/, 1)[0].toLowerCase()
        const allowed = new Set(["", "status", "show", "current", "history", "list", "pause", "resume"])
        if (!allowed.has(action)) {
          throw new Error(
            "Cannot replace, edit, focus, add, sequence, or clear a Goal through /goal while an Autopilot dossier is active.",
          )
        }
      }
    }
    const result = await original(input, output)
    if (sessionID) {
      const run = autopilotRunFromText(String(input.arguments || ""))
      if (run) runsBySession.set(sessionID, run)
    }
    return result
  }
}

async function importFileModule(specifier: string, label: string): Promise<Record<string, unknown>> {
  let url: URL
  try {
    url = new URL(specifier)
  } catch {
    throw new TypeError(`${label} must be an absolute file URL`)
  }
  if (url.protocol !== "file:") throw new TypeError(`${label} must use the file: protocol`)
  return import(url.href)
}

async function resolveAdapterSettings(options: AdapterOptions) {
  if (!options.runtimeConfigPath) {
    return {
      enabled: options.enabled !== false,
      goalPluginUrl: options.goalPluginUrl,
      ptyIntegrationUrl: options.ptyIntegrationUrl,
    }
  }
  let parsed: unknown
  try {
    parsed = JSON.parse(await fs.readFile(options.runtimeConfigPath, "utf8"))
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error)
    throw new Error(`Could not read Goal-PTY runtime config ${options.runtimeConfigPath}: ${message}`)
  }
  const config = parsed as Partial<RuntimeConfig>
  if (config.version !== 1 || typeof config.enabled !== "boolean") {
    throw new TypeError("Goal-PTY runtime config must declare version 1 and boolean enabled")
  }
  return config
}

async function GoalPtyAdapter(context: unknown, options: AdapterOptions) {
  if (!options || typeof options !== "object") {
    throw new TypeError("Goal-PTY adapter options are required")
  }
  const settings = await resolveAdapterSettings(options)
  if (!settings.goalPluginUrl) throw new TypeError("goalPluginUrl is required")
  if (settings.enabled && !settings.ptyIntegrationUrl) {
    throw new TypeError("ptyIntegrationUrl is required when Goal-PTY integration is enabled")
  }
  const goalModule = await importFileModule(settings.goalPluginUrl, "goalPluginUrl")
  const goalPlugin = goalModule.GoalPlugin
  if (typeof goalPlugin !== "function") {
    throw new TypeError("Goal module does not export GoalPlugin")
  }
  const runsBySession = new Map<string, string>()
  let ptyProvider: ReturnType<typeof createPtyActivityProvider> | undefined
  if (settings.enabled) {
    const ptyModule = await importFileModule(settings.ptyIntegrationUrl, "ptyIntegrationUrl")
    validateIntegration(ptyModule)
    ptyProvider = createPtyActivityProvider(ptyModule as unknown as PtyIntegration)
  }
  const provider = {
    listActive: (sessionID: string) => ptyProvider?.listActive(sessionID) ?? [],
    classifyNotification: (input: { sessionID: string; messageID: string; text: string }) =>
      ptyProvider?.classifyNotification(input) ?? false,
    listCompletionBlockers: async (sessionID: string) => {
      const run = runsBySession.get(sessionID)
      return run ? completionBlockersForRun(run) : []
    },
    dispose() {
      ptyProvider?.dispose()
      runsBySession.clear()
    },
  }
  try {
    const hooks = await goalPlugin(context, {
      ...(options.goalOptions ?? {}),
      externalActivityProvider: provider,
    }) as Record<string, unknown>
    bindAutopilotRunFromGoalTools(hooks, runsBySession)
    const configuredCommandName = typeof options.goalOptions?.commandName === "string"
      ? options.goalOptions.commandName.replace(/^\/+/, "").trim() || "goal"
      : "goal"
    guardAutopilotGoalCommands(hooks, runsBySession, configuredCommandName)
    const dispose = hooks.dispose
    return {
      ...hooks,
      async dispose() {
        provider.dispose()
        if (typeof dispose === "function") await dispose()
      },
    }
  } catch (error) {
    provider.dispose()
    throw error
  }
}

export default {
  id: "labflow-goal-pty-adapter",
  server: GoalPtyAdapter,
}
