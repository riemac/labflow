import assert from "node:assert/strict"
import * as fs from "node:fs/promises"
import * as os from "node:os"
import * as path from "node:path"
import test from "node:test"
import plugin from "../plugins/labflow.ts"
import { readManagedConfig } from "../scripts/config.mjs"

const SESSION = "session-a"
const tags = ["abstract", "goal", "understanding", "decisions", "state", "open_questions", "next", "preferences", "references"]

function message(id, role, parts, info = {}, sessionID = SESSION) {
  return {
    info: { id, role, sessionID, ...info },
    parts: parts.map((part, index) => ({ id: `${id}-${index}`, sessionID, messageID: id, ...part })),
  }
}

const text = (value) => ({ type: "text", text: value })
const marker = (id, sessionID = SESSION) => message(id, "user", [{ type: "compaction", auto: true }], {}, sessionID)
const summary = (id, parentID, value, info = {}, sessionID = SESSION) =>
  message(id, "assistant", [text(value)], { parentID, summary: true, finish: "stop", ...info }, sessionID)

async function hooksFor(t, load) {
  const hooks = await plugin({
    client: { session: { messages: async (args) => {
      assert.deepEqual(args, { path: { id: args.path.id }, throwOnError: true })
      return { data: await load(args.path.id) }
    } } },
  })
  t.after(() => hooks.dispose())
  return hooks
}

test("compaction uses the English agent only and preserves execution configuration", async (t) => {
  const hooks = await hooksFor(t, () => [])
  const config = {}
  hooks.config(config)
  const managed = await readManagedConfig()
  const expected = managed.defaults.agent.compaction
  assert.equal(expected.prompt, undefined)
  assert.equal(config.agent.compaction.model, expected.model)
  assert.deepEqual(config.agent.compaction.options, expected.options)
  assert.equal(config.agent.compaction.options.textVerbosity, "high")
  assert.deepEqual(config.agent.build.options, managed.defaults.agent.build.options)
  assert.equal(config.agent.compaction.mode, "primary")
  assert.equal(config.agent.compaction.hidden, true)
  assert.deepEqual(config.agent.compaction.permission, { "*": "deny" })
  assert.equal(config.agent.compaction_CN, undefined)
  assert.equal(config.agent.build.prompt, undefined)
  assert.deepEqual(config.compaction, managed.defaults.compaction)
  assert.doesNotMatch(config.agent.compaction.prompt, /[\u3400-\u9fff]/)

  const overridden = { agent: { compaction: {
    model: "custom/summary", options: { reasoningEffort: "max", textVerbosity: "medium" }, steps: 4,
    prompt: "stale inline prompt", mode: "subagent", permission: { "*": "allow" },
  } } }
  hooks.config(overridden)
  assert.equal(overridden.agent.compaction.model, "custom/summary")
  assert.equal(overridden.agent.compaction.options.reasoningEffort, "max")
  assert.equal(overridden.agent.compaction.options.textVerbosity, "medium")
  assert.equal(overridden.agent.compaction.steps, 4)
  assert.equal(overridden.agent.compaction.prompt, config.agent.compaction.prompt)
  assert.equal(overridden.agent.compaction.mode, "primary")
  assert.deepEqual(overridden.agent.compaction.permission, { "*": "deny" })
})

test("paired prompts share semantic containers and the English contract protects completion and depth", async () => {
  const english = await fs.readFile(new URL("../agents/compaction.md", import.meta.url), "utf8")
  const chinese = await fs.readFile(new URL("../agents/compaction_CN.md", import.meta.url), "utf8")
  for (const source of [english, chinese]) {
    assert.match(source, /<\/compaction_contract>[\s\S]*```text\n<abstract>/)
    assert.match(source, /<\/references>\n```\s*$/)
    const layout = source.split("```text\n")[1]
    assert.doesNotMatch(layout, /^#{2,3} /m)
    for (const tag of ["compaction_contract", ...tags]) {
      assert.equal(source.split(`<${tag}>`).length, 2)
      assert.equal(source.split(`</${tag}>`).length, 2)
    }
  }
  assert.match(english, /20,000-30,000 tokens/)
  assert.match(english, /completed topics that are not immediately relevant/)
  assert.match(english, /Omit containers with no substantive content/)
  assert.match(english, /Never repackage completed work as a next action/)
  assert.match(english, /The prior summary is accumulated context/)
  assert.match(english, /Mixed work can use different flavors/)
  assert.match(english, /Begin directly with continuous prose, without an internal heading/)
  assert.match(english, /two descriptive level-two headings named for their actual subject matter/)
  assert.match(english, /with no required subsection count/)
  assert.match(english, /format their names as inline code/)
  assert.match(english, /Later completion or cancellation replaces earlier pending status/)
  assert.match(english, /Optionally use text-native diagrams within the understanding body/)
  assert.match(english, /working representations for continued reasoning, not presentation graphics/)
  assert.match(english, /remains intelligible without rendering/)
  assert.match(english, /No dedicated diagram container or mandatory diagram is required/)
  assert.doesNotMatch(english, /\bPTY\b|\bsubagent\b|Keep every section|Use terse bullets/)
})

test("first compaction replaces the fixed template without copying the new conversation", async (t) => {
  const messages = [message("user", "user", [text("new-conversation-canary")]), marker("current")]
  const before = structuredClone(messages)
  const hooks = await hooksFor(t, () => messages)
  const output = { context: ["additional-plugin-context"], prompt: undefined }
  await hooks["experimental.session.compacting"]({ sessionID: SESSION }, output)
  assert.match(output.prompt, /no prior summary/)
  assert.match(output.prompt, /additional-plugin-context/)
  assert.doesNotMatch(output.prompt, /new-conversation-canary|## Objective|## Next Move|Use terse bullets/)
  assert.deepEqual(messages, before)
})

test("three compactions carry exactly the latest successful summary, including after plugin restart", async (t) => {
  const firstSummary = "<goal>Keep the original requirement.</goal><state>Experiment finished.</state>"
  const secondSummary = `${firstSummary}<understanding>Retain the completed branch and its rationale.</understanding>`
  const histories = [
    [marker("z-current")],
    [marker("z-current"), summary("z-summary", "z-current", firstSummary), marker("m-current")],
    [marker("z-current"), summary("z-summary", "z-current", firstSummary), marker("m-current"),
      summary("m-summary", "m-current", secondSummary), marker("a-current")],
  ]
  for (const [index, messages] of histories.entries()) {
    const hooks = await hooksFor(t, () => messages)
    const output = { context: [] }
    await hooks["experimental.session.compacting"]({ sessionID: SESSION }, output)
    const expected = [undefined, firstSummary, secondSummary][index]
    if (expected === undefined) assert.doesNotMatch(output.prompt, /<prior_summary>/)
    else {
      assert.equal(output.prompt.split(expected).length, 2)
      assert.equal(output.prompt.split("<prior_summary>").length, 2)
    }
  }
})

test("summary selection ignores failed, incomplete and unrelated assistant messages and reasoning", async (t) => {
  const messages = [
    marker("one"),
    message("good", "assistant", [text("  established "), { type: "reasoning", text: "not-summary-text" }, text(" fact  ")],
      { parentID: "one", summary: true, finish: "stop" }),
    marker("two"), summary("failed", "two", "failed-canary", { error: { name: "AbortedError" } }),
    marker("three"), summary("unfinished", "three", "unfinished-canary", { finish: undefined }),
    message("ordinary", "assistant", [text("ordinary-canary")], { parentID: "three", agent: "compaction", finish: "stop" }),
    summary("orphan", "missing", "orphan-canary"),
    marker("current"), summary("future", "one", "future-canary"),
  ]
  const hooks = await hooksFor(t, () => messages)
  const output = { context: [] }
  await hooks["experimental.session.compacting"]({ sessionID: SESSION }, output)
  assert.match(output.prompt, /established\n\nfact/)
  assert.doesNotMatch(output.prompt, /canary|not-summary-text/)
})

test("a successful empty summary does not resurrect an older summary", async (t) => {
  const messages = [marker("one"), summary("old", "one", "obsolete-canary"),
    marker("two"), summary("empty", "two", "   "), marker("current")]
  const hooks = await hooksFor(t, () => messages)
  const output = { context: [] }
  await hooks["experimental.session.compacting"]({ sessionID: SESSION }, output)
  assert.match(output.prompt, /no prior summary/)
  assert.doesNotMatch(output.prompt, /obsolete-canary/)
})

test("receiving model gets one checkpoint notice without changing stored summary objects", async (t) => {
  const body = "<abstract>Established understanding.</abstract><state>Complete.</state>"
  const stored = [marker("old"),
    message("summary", "assistant", [{ type: "reasoning", text: "reasoning" }, text("  "), text(body), text("second text part")],
      { parentID: "old", summary: true, finish: "stop" }),
    message("latest", "user", [text("A later clarification.")])]
  const before = structuredClone(stored)
  const hooks = await hooksFor(t, () => stored)
  const output = { messages: [...stored] }
  const originalArray = output.messages
  await hooks["experimental.chat.messages.transform"]({}, output)
  assert.equal(output.messages, originalArray)
  assert.deepEqual(output.messages.map((message) => message.info.id), ["old", "summary", "latest"])
  const annotated = output.messages[1].parts[2].text
  assert.match(annotated, /^<context_checkpoint>\nThis is a reconstructed checkpoint/)
  assert.match(annotated, /not a new user request/)
  assert.match(annotated, /newer messages/)
  assert.match(annotated, /unfinished and authorized/)
  assert.ok(annotated.endsWith(body))
  assert.equal(output.messages[1].parts[3].text, "second text part")
  assert.equal(output.messages[1].parts[0].text, "reasoning")
  assert.deepEqual(stored, before)
  await hooks["experimental.chat.messages.transform"]({}, output)
  assert.equal(output.messages[1].parts[2].text, annotated)
  assert.deepEqual(stored, before)
})

test("checkpoint notice skips ordinary, incomplete, failed, empty and ignored messages", async (t) => {
  const messages = [
    message("user", "user", [text("<abstract>Quoted example.</abstract>")]),
    message("ordinary", "assistant", [text("Normal response.")], { agent: "compaction", finish: "stop" }),
    summary("incomplete", "user", "Partial summary.", { finish: undefined }),
    summary("failed", "user", "Failed summary.", { error: { name: "AbortedError" } }),
    summary("empty", "user", "  "),
    message("ignored", "assistant", [{ ...text("Ignored text."), ignored: true }], { summary: true, finish: "stop" }),
  ]
  const before = structuredClone(messages)
  const hooks = await hooksFor(t, () => messages)
  const output = { messages: [...messages] }
  await hooks["experimental.chat.messages.transform"]({}, output)
  assert.deepEqual(output.messages, before)
})

test("checkpoint notice does not enter the next compaction's prior summary or conversation", async (t) => {
  const body = "<abstract>Preserve the research rationale.</abstract>"
  const stored = [marker("old"), summary("summary", "old", body), message("recent", "user", [text("Latest update.")]), marker("current")]
  const before = structuredClone(stored)
  const hooks = await hooksFor(t, () => stored)
  const replay = { messages: [...stored.slice(0, 3)] }
  await hooks["experimental.chat.messages.transform"]({}, replay)
  assert.match(replay.messages[1].parts[0].text, /<context_checkpoint>/)
  const prompt = { context: [] }
  await hooks["experimental.session.compacting"]({ sessionID: SESSION }, prompt)
  assert.ok(prompt.prompt.includes(body))
  assert.doesNotMatch(prompt.prompt, /context_checkpoint|not a new user request/)
  const input = { messages: [...stored.slice(2, 3)] }
  await hooks["experimental.chat.messages.transform"]({}, input)
  assert.doesNotMatch(JSON.stringify(input), /context_checkpoint/)
  assert.deepEqual(stored, before)
})

test("compaction sees retained completion updates without changing persisted replay history", async (t) => {
  const messages = [
    message("prefix", "user", [text("Tests and review are pending.")]),
    message("recent", "user", [text("All tests passed and the review is complete. No next action.")]),
    marker("current"),
    message("future", "user", [text("Outside this compaction snapshot.")]),
  ]
  const before = structuredClone(messages)
  const hooks = await hooksFor(t, () => messages)
  const prompt = { context: [] }
  await hooks["experimental.session.compacting"]({ sessionID: SESSION }, prompt)
  const input = { messages: structuredClone(messages.slice(0, 1)) }
  await hooks["experimental.chat.messages.transform"]({}, input)
  assert.deepEqual(input.messages.map((message) => message.info.id), ["prefix", "recent"])
  assert.match(input.messages[1].parts[0].text, /No next action/)
  assert.doesNotMatch(prompt.prompt, /All tests passed/)
  assert.deepEqual(messages, before)
  input.messages[1].parts[0].text = "changed only in request clone"
  assert.deepEqual(messages, before)
  await hooks["experimental.chat.messages.transform"]({}, input)
  assert.equal(input.messages.length, 2)
})

test("recent context excludes prior compaction artifacts and does not duplicate a full input", async (t) => {
  const messages = [
    message("prefix", "user", [text("Earlier discussion.")]),
    marker("old-marker"), summary("old-summary", "old-marker", "Prior summary."),
    message("recent", "user", [text("Task finished.")]), marker("current"),
  ]
  const hooks = await hooksFor(t, () => messages)
  const prompt = { context: [] }
  await hooks["experimental.session.compacting"]({ sessionID: SESSION }, prompt)
  const input = { messages: structuredClone(messages.slice(0, 1)) }
  await hooks["experimental.chat.messages.transform"]({}, input)
  assert.deepEqual(input.messages.map((message) => message.info.id), ["prefix", "recent"])
  assert.equal(prompt.prompt.split("Prior summary.").length, 2)
  await hooks["experimental.session.compacting"]({ sessionID: SESSION }, { context: [] })
  const full = structuredClone(input)
  await hooks["experimental.chat.messages.transform"]({}, full)
  assert.deepEqual(full, input)
})

test("pending recent context is isolated across sessions and skips ordinary continuations", async (t) => {
  const histories = new Map(["a", "b"].map((id) => [id, [
    message("prefix", "user", [text(`${id}-old`)], {}, id),
    message("recent", "user", [text(`${id}-new`)], {}, id), marker("current", id),
  ]]))
  const hooks = await hooksFor(t, (id) => histories.get(id))
  await Promise.all(["a", "b"].map((sessionID) =>
    hooks["experimental.session.compacting"]({ sessionID }, { context: [] })))
  const ordinary = { messages: structuredClone(histories.get("a")) }
  const before = structuredClone(ordinary)
  await hooks["experimental.chat.messages.transform"]({}, ordinary)
  assert.deepEqual(ordinary, before)
  for (const id of ["b", "a"]) {
    const input = { messages: structuredClone(histories.get(id).slice(0, 1)) }
    await hooks["experimental.chat.messages.transform"]({}, input)
    assert.equal(input.messages.length, 2)
    assert.equal(input.messages[1].parts[0].text, `${id}-new`)
  }
})

test("idle, deletion, disposal and failed retries clear pending compaction snapshots", async (t) => {
  const messages = [message("prefix", "user", [text("Earlier.")]), message("recent", "user", [text("Later.")]), marker("current")]
  for (const cleanup of ["idle", "deleted", "disposed", "failed-read"]) {
    let fail = false
    const hooks = await hooksFor(t, () => {
      if (fail) throw new Error("unavailable")
      return messages
    })
    await hooks["experimental.session.compacting"]({ sessionID: SESSION }, { context: [] })
    if (cleanup === "idle") await hooks.event({ event: { type: "session.status", properties: { sessionID: SESSION, status: { type: "idle" } } } })
    if (cleanup === "deleted") await hooks.event({ event: { type: "session.deleted", properties: { info: { id: SESSION } } } })
    if (cleanup === "disposed") await hooks.dispose()
    if (cleanup === "failed-read") {
      fail = true
      await assert.rejects(hooks["experimental.session.compacting"]({ sessionID: SESSION }, { context: [] }), /compaction stopped/)
    }
    const input = { messages: structuredClone(messages.slice(0, 1)) }
    await hooks["experimental.chat.messages.transform"]({}, input)
    assert.equal(input.messages.length, 1)
  }
})

test("an empty compaction prefix cannot consume another session's recent context", async (t) => {
  const histories = new Map([
    ["empty", [marker("old", "empty"), summary("summary", "old", "Already summarized.", {}, "empty"), marker("current", "empty")]],
    ["active", [message("prefix", "user", [text("Earlier.")], {}, "active"), message("recent", "user", [text("Later.")], {}, "active"), marker("current", "active")]],
  ])
  const hooks = await hooksFor(t, (id) => histories.get(id))
  for (const sessionID of histories.keys()) {
    await hooks["experimental.session.compacting"]({ sessionID }, { context: [] })
  }
  const empty = { messages: [] }
  await hooks["experimental.chat.messages.transform"]({}, empty)
  assert.deepEqual(empty.messages, [])
  const active = { messages: structuredClone(histories.get("active").slice(0, 1)) }
  await hooks["experimental.chat.messages.transform"]({}, active)
  assert.equal(active.messages[1].parts[0].text, "Later.")
})

test("unmatched or mixed-session compaction prefixes stop before adding recent context", async (t) => {
  const messages = [message("prefix", "user", [text("Earlier.")]), message("recent", "user", [text("Later.")]), marker("current")]
  const hooks = await hooksFor(t, () => messages)
  for (const prefix of [
    [message("unknown", "user", [text("Unknown input.")])],
    [messages[0], message("recent", "user", [text("Other session.")], {}, "other")],
  ]) {
    await hooks["experimental.session.compacting"]({ sessionID: SESSION }, { context: [] })
    const input = { messages: structuredClone(prefix) }
    const before = structuredClone(input)
    await assert.rejects(hooks["experimental.chat.messages.transform"]({}, input), /compaction stopped/)
    assert.deepEqual(input, before)
  }
})

test("forked and concurrent sessions use their own copied history without consulting the parent", async (t) => {
  const histories = new Map(["fork", "other"].map((sessionID) => [sessionID, [
    marker("copied-marker", sessionID),
    summary("copied-summary", "copied-marker", `${sessionID}-canary`, {}, sessionID),
    marker("current", sessionID),
  ]]))
  const calls = []
  const hooks = await hooksFor(t, (sessionID) => {
    calls.push(sessionID)
    return histories.get(sessionID)
  })
  const outputs = [{ context: [] }, { context: [] }]
  await Promise.all(["fork", "other"].map((sessionID, index) =>
    hooks["experimental.session.compacting"]({ sessionID }, outputs[index])))
  assert.deepEqual(calls.sort(), ["fork", "other"])
  assert.match(outputs[0].prompt, /fork-canary/)
  assert.doesNotMatch(outputs[0].prompt, /other-canary/)
  assert.match(outputs[1].prompt, /other-canary/)
  assert.doesNotMatch(outputs[1].prompt, /fork-canary/)
})

test("old summaries beyond a typical page remain available", async (t) => {
  const messages = [marker("one"), summary("old", "one", "early-requirement")]
  for (let i = 0; i < 120; i++) messages.push(message(`user-${i}`, "user", [text(`turn ${i}`)]))
  messages.push(marker("current"))
  const hooks = await hooksFor(t, () => messages)
  const output = { context: [] }
  await hooks["experimental.session.compacting"]({ sessionID: SESSION }, output)
  assert.match(output.prompt, /early-requirement/)
})

test("history read failures stop compaction without changing the prompt and can be retried", async (t) => {
  let fail = true
  const messages = [marker("one"), summary("old", "one", "required-context"), marker("current")]
  const before = structuredClone(messages)
  const hooks = await hooksFor(t, () => {
    if (fail) throw new Error("private-response-canary")
    return messages
  })
  const output = { context: ["unchanged"], prompt: undefined }
  await assert.rejects(hooks["experimental.session.compacting"]({ sessionID: SESSION }, output), (error) => {
    assert.match(error.message, /compaction stopped/)
    assert.doesNotMatch(error.message, /private-response-canary/)
    return true
  })
  assert.deepEqual(output, { context: ["unchanged"], prompt: undefined })
  assert.deepEqual(messages, before)
  fail = false
  await hooks["experimental.session.compacting"]({ sessionID: SESSION }, output)
  assert.match(output.prompt, /required-context/)
})

test("invalid history and ambiguous boundaries stop rather than dropping accumulated context", async (t) => {
  const invalid = [
    undefined, {}, [], [null],
    [message("user", "user", [text("no marker")])],
    [marker("current"), summary("already-done", "current", "completed")],
    [marker("current", "wrong-session")],
    [message("user", "user", [text(42)]), marker("current")],
    [message("user", "user", [{ ...text("wrong owner"), messageID: "other" }]), marker("current")],
  ]
  for (const messages of invalid) {
    const hooks = await hooksFor(t, () => messages)
    const output = { context: [] }
    await assert.rejects(hooks["experimental.session.compacting"]({ sessionID: SESSION }, output), /compaction stopped/)
    assert.equal(output.prompt, undefined)
  }
})

test("compaction API providers request 64k, bounded by valid model output limits", async (t) => {
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), "labflow-compaction-auth-"))
  t.after(() => fs.rm(directory, { recursive: true, force: true }))
  const authPath = path.join(directory, "auth.json")
  await fs.writeFile(authPath, JSON.stringify({ openai: { type: "api", key: "sk-test" } }))
  const oldAuthPath = process.env.LABFLOW_OPENAI_AUTH_PATH
  process.env.LABFLOW_OPENAI_AUTH_PATH = authPath
  t.after(() => {
    if (oldAuthPath === undefined) delete process.env.LABFLOW_OPENAI_AUTH_PATH
    else process.env.LABFLOW_OPENAI_AUTH_PATH = oldAuthPath
  })

  const hooks = await hooksFor(t, () => [])
  for (const providerID of ["openai", "relay", "routin"]) {
    for (const [limit, expected] of [[128000, 64000], [64000, 64000], [32000, 32000], [0, 64000], [undefined, 64000], [NaN, 64000]]) {
      const output = { maxOutputTokens: providerID === "openai" ? undefined : 32000, options: { reasoningEffort: "high" } }
      await hooks["chat.params"]({ agent: "compaction", model: { providerID, limit: { output: limit } } }, output)
      assert.equal(output.maxOutputTokens, expected)
      assert.deepEqual(output.options, { reasoningEffort: "high" })
    }
  }
})

test("OpenAI subscription omits the unsupported output limit without affecting API-key or relay routes", async (t) => {
  const hooks = await hooksFor(t, () => [])
  assert.equal(hooks.auth, undefined)
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), "labflow-compaction-auth-"))
  t.after(() => fs.rm(directory, { recursive: true, force: true }))
  const authPath = path.join(directory, "auth.json")
  const writeAuth = (auth) => fs.writeFile(authPath, JSON.stringify({ openai: auth }))
  const oldAuthPath = process.env.LABFLOW_OPENAI_AUTH_PATH
  process.env.LABFLOW_OPENAI_AUTH_PATH = authPath
  t.after(() => {
    if (oldAuthPath === undefined) delete process.env.LABFLOW_OPENAI_AUTH_PATH
    else process.env.LABFLOW_OPENAI_AUTH_PATH = oldAuthPath
  })
  await writeAuth({ type: "oauth", access: "private-auth-canary" })
  const input = { agent: "compaction", model: { providerID: "openai", limit: { output: 128000 } } }
  const output = { maxOutputTokens: 32000, options: { store: false } }
  await hooks["chat.params"](input, output)
  assert.equal(output.maxOutputTokens, undefined)
  assert.doesNotMatch(JSON.stringify(output), /private-auth-canary/)
  input.model.providerID = "relay"
  await hooks["chat.params"](input, output)
  assert.equal(output.maxOutputTokens, 64000)
  input.model.providerID = "openai"
  await writeAuth({ type: "api", key: "private-auth-canary" })
  await hooks["chat.params"](input, output)
  assert.equal(output.maxOutputTokens, 64000)
})

test("normal conversation and other internal agents keep their original parameters", async (t) => {
  const hooks = await hooksFor(t, () => [])
  for (const agent of ["build", "explore-worker", "title", "summary", "labflow-paper"]) {
    const output = { maxOutputTokens: undefined, temperature: 0.5, options: { store: false } }
    const before = structuredClone(output)
    await hooks["chat.params"]({ agent, model: { limit: { output: 128000 } } }, output)
    assert.deepEqual(output, before)
  }
})
