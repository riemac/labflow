import * as fs from "node:fs/promises"

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
  goalOptions?: Record<string, unknown>
}

const ACTIVE_STATUSES = new Set<PtyStatus>(["running", "killing"])
const TERMINAL_STATUSES = new Set<PtyStatus>(["exited", "killed"])
const MAX_REMEMBERED_SESSIONS = 4096
const PTY_EXIT_ID = /^ID:\s*(pty_[A-Za-z0-9]+)\s*$/m

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
      goalOptions: options.goalOptions ?? {},
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
  if (config.goalOptions !== undefined && (
    !config.goalOptions ||
    typeof config.goalOptions !== "object" ||
    Array.isArray(config.goalOptions)
  )) {
    throw new TypeError("Goal-PTY runtime config goalOptions must be an object")
  }
  return {
    ...config,
    goalOptions: {
      ...(options.goalOptions ?? {}),
      ...(config.goalOptions ?? {}),
    },
  }
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
    dispose() {
      ptyProvider?.dispose()
    },
  }
  try {
    const hooks = await goalPlugin(context, {
      ...(settings.goalOptions ?? {}),
      externalActivityProvider: provider,
    }) as Record<string, unknown>
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
