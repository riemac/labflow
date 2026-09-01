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
  goalPluginUrl: string
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

async function GoalPtyAdapter(context: unknown, options: AdapterOptions) {
  if (!options || typeof options !== "object") {
    throw new TypeError("Goal-PTY adapter options are required")
  }
  const [goalModule, ptyModule] = await Promise.all([
    importFileModule(options.goalPluginUrl, "goalPluginUrl"),
    importFileModule(options.ptyIntegrationUrl, "ptyIntegrationUrl"),
  ])
  const goalPlugin = goalModule.GoalPlugin
  if (typeof goalPlugin !== "function") {
    throw new TypeError("Goal module does not export GoalPlugin")
  }
  validateIntegration(ptyModule)
  const provider = createPtyActivityProvider(ptyModule as unknown as PtyIntegration)
  try {
    const hooks = await goalPlugin(context, {
      ...(options.goalOptions ?? {}),
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
