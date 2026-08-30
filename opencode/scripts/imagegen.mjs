#!/usr/bin/env node

import { Buffer } from "node:buffer"
import { randomUUID } from "node:crypto"
import * as fsSync from "node:fs"
import * as fs from "node:fs/promises"
import * as path from "node:path"
import { fileURLToPath } from "node:url"
import { readManagedConfig, SecretStore } from "./config.mjs"

const FALLBACK_MODEL = "gpt-image-2"
const FALLBACK_SIZE = "3840x2160"
const FALLBACK_QUALITY = "high"
const FALLBACK_FORMAT = "png"
const FALLBACK_OUT_DIR = "figures/imagegen"
const MAX_VARIANTS = 4
const MAX_INPUT_IMAGES = 4
const MAX_INPUT_IMAGE_BYTES = 20 * 1024 * 1024
const MAX_TOTAL_INPUT_IMAGE_BYTES = 50 * 1024 * 1024
const MAX_OUTPUT_IMAGE_BYTES = 50 * 1024 * 1024
const MAX_ERROR_RESPONSE_BYTES = 1024 * 1024
const MAX_JSON_OVERHEAD_BYTES = 1024 * 1024
const CODEX_RESPONSES_ENDPOINT = "https://chatgpt.com/backend-api/codex/responses"

const VALID_APIS = new Set(["images", "responses", "codex"])
const VALID_QUALITIES = new Set(["low", "medium", "high", "auto"])
const VALID_FORMATS = new Set(["png", "jpeg", "jpg", "webp"])
const REPO_CONFIG_DIR = path.join(path.dirname(fileURLToPath(import.meta.url)), "..")

main().catch((error) => {
  console.error(`imagegen error: ${error.message}`)
  process.exit(1)
})

async function main() {
  const { command, flags } = parseArgs(process.argv.slice(2))
  if (flags.help || command === "help") {
    printHelp()
    return
  }
  if (command !== "generate") {
    throw new Error(`unknown command: ${command}`)
  }

  const configDir = opencodeConfigDir()
  const [managedConfig, labflowConfig, opencodeConfig] = await Promise.all([
    readManagedConfig(),
    readLabflowConfig(configDir),
    readOpencodeConfig(configDir),
  ])
  if (flags["list-profiles"]) {
    printResult(profileListing(managedConfig.imagegen))
    return
  }

  const prompt = await readPrompt(flags)
  const imagegenConfig = labflowConfig?.imagegen ?? {}
  const selection = selectProfiles(managedConfig.imagegen, flags, imagegenConfig)
  const preferManagedDefaults = selection.explicit || Boolean(selection.route)
  const attempts = selection.profiles.map((profile) => resolveGenerationConfig({
    profile,
    flags,
    imagegenConfig,
    managedConfig,
    opencodeConfig,
    route: Boolean(selection.route),
    preferManagedDefaults,
  }))
  const primary = attempts[0]
  if (attempts.some((attempt) => attempt.outputFormat !== primary.outputFormat)) {
    throw new Error("all profiles in an imagegen route must use the same outputFormat")
  }
  const size = primary.size
  const quality = primary.quality
  const outputFormat = primary.outputFormat
  const count = parseCount(firstString(
    flags.n,
    process.env.OPENCODE_IMAGEGEN_N,
    ...(preferManagedDefaults
      ? [resolveConfigString(primary.profile.n), resolveConfigString(imagegenConfig.n)]
      : [resolveConfigString(imagegenConfig.n), resolveConfigString(primary.profile.n)]),
  ))
  const outDir = firstString(
    flags["out-dir"],
    process.env.OPENCODE_IMAGEGEN_OUT_DIR,
    ...(preferManagedDefaults
      ? [
          resolveConfigString(primary.profile.outDir ?? primary.profile.out_dir),
          resolveConfigString(imagegenConfig.outDir ?? imagegenConfig.out_dir),
        ]
      : [
          resolveConfigString(imagegenConfig.outDir ?? imagegenConfig.out_dir),
          resolveConfigString(primary.profile.outDir ?? primary.profile.out_dir),
        ]),
    FALLBACK_OUT_DIR,
  )
  const inputImages = await readInputImages(flags["input-image"])

  for (const attempt of attempts) validateGenerationConfig(attempt, inputImages)

  const outputPaths = await plannedOutputPaths({
    out: flags.out,
    outDir,
    outputFormat,
    count,
    prompt,
    force: Boolean(flags.force),
  })

  if (flags["dry-run"]) {
    const dryRunAttempts = attempts.map((attempt) => ({
      profile: attempt.profileName,
      provider: attempt.provider,
      api: attempt.api,
      endpoint: apiEndpoint(attempt.baseURL, attempt.api, attempt.codexEndpoint),
      payload: redactImageData(buildPayload(attempt, { prompt, count, inputImages })),
    }))
    printResult({
      ok: true,
      dry_run: true,
      profile: primary.profileName,
      route: selection.routeName,
      provider: primary.provider,
      api: primary.api,
      endpoint: dryRunAttempts[0].endpoint,
      generation_mode: inputImages.length > 0 ? "edit" : "generate",
      input_image_count: inputImages.length,
      payload: dryRunAttempts[0].payload,
      attempts: dryRunAttempts,
      input_images: inputImages.map(inputImageSummary),
      outputs: outputPaths.map(relativeToCwd),
    })
    return
  }

  const secretStore = new SecretStore({ secretPath: path.join(managedConfig.configDir, "secrets.sops.yaml") })
  let generation
  let used
  const failedProfiles = []
  try {
    for (let index = 0; index < attempts.length; index += 1) {
      const attempt = attempts[index]
      try {
        generation = await generateAtomically({
          attempt,
          prompt,
          count,
          inputImages,
          outputPaths,
          secretStore,
          force: Boolean(flags.force),
        })
        used = attempt
        break
      } catch (error) {
        failedProfiles.push({ profile: attempt.profileName, error: safeErrorMessage(error) })
        if (index + 1 >= attempts.length || !isRetryableFailure(error, selection.route)) throw error
      }
    }
  } finally {
    secretStore.dispose()
  }
  if (!generation || !used) throw new Error("all imagegen profiles failed")

  printResult({
    ok: true,
    dry_run: false,
    profile: used.profileName,
    route: selection.routeName,
    attempted_profiles: [...failedProfiles.map((item) => item.profile), used.profileName].filter(Boolean),
    failed_profiles: failedProfiles,
    provider: used.provider,
    api: used.api,
    model: used.model,
    size: used.size,
    quality: used.quality,
    output_format: used.outputFormat,
    generation_mode: inputImages.length > 0 ? "edit" : "generate",
    input_image_count: inputImages.length,
    outputs: generation.written,
    revised_prompt: generation.revisedPrompt,
    response_id: generation.responseID,
    image_generation_call_id: generation.imageGenerationCallID,
    actual_size: generation.actualSize,
    backend_size: generation.backendSize,
    action: generation.action,
    input_images: inputImages.map(inputImageSummary),
    prompt,
  })
}

function selectProfiles(imagegen, flags, legacyConfig = {}) {
  const profileName = firstString(flags.profile, process.env.OPENCODE_IMAGEGEN_PROFILE)
  const routeName = firstString(flags.route, process.env.OPENCODE_IMAGEGEN_ROUTE)
  if (profileName && routeName) throw new Error("--profile and --route are mutually exclusive")
  const profiles = isPlainObject(imagegen.profiles) ? imagegen.profiles : {}

  if (routeName) {
    rejectRouteOverrides(flags)
    return namedRoute(imagegen, profiles, routeName, true)
  }

  if (!profileName && !hasBackendOverride(flags, legacyConfig) && imagegen.defaultRoute) {
    return namedRoute(imagegen, profiles, imagegen.defaultRoute, false)
  }

  const selectedName = profileName ?? imagegen.defaultProfile
  if (selectedName) {
    return {
      explicit: Boolean(profileName),
      route: undefined,
      routeName: undefined,
      profiles: [namedProfile(profiles, selectedName)],
    }
  }
  return { explicit: false, route: undefined, routeName: undefined, profiles: [{ name: undefined, config: {} }] }
}

function namedRoute(imagegen, profiles, routeName, explicit) {
  const route = imagegen.routes?.[routeName]
  if (!isPlainObject(route) || !Array.isArray(route.profiles) || route.profiles.length === 0) {
    throw new Error(`unknown or empty imagegen route: ${routeName}`)
  }
  return {
    explicit,
    route,
    routeName,
    profiles: route.profiles.map((name) => namedProfile(profiles, name)),
  }
}

function hasBackendOverride(flags, legacyConfig) {
  return Boolean(firstString(
    flags.provider,
    flags.api,
    flags["api-key"],
    flags["base-url"],
    flags.model,
    process.env.OPENCODE_IMAGEGEN_PROVIDER,
    process.env.OPENCODE_IMAGEGEN_API,
    process.env.OPENCODE_IMAGEGEN_API_KEY,
    process.env.OPENCODE_IMAGEGEN_BASE_URL,
    process.env.OPENCODE_IMAGEGEN_MODEL,
    legacyConfig.provider,
    legacyConfig.api,
    legacyConfig.apiKey,
    legacyConfig.apiKeyFile ?? legacyConfig.api_key_file,
    legacyConfig.baseURL ?? legacyConfig.baseUrl,
    legacyConfig.model,
  ))
}

function namedProfile(profiles, name) {
  if (typeof name !== "string" || !isPlainObject(profiles[name])) throw new Error(`unknown imagegen profile: ${name}`)
  return { name, config: profiles[name] }
}

function rejectRouteOverrides(flags) {
  const conflictingFlags = ["provider", "api", "api-key", "base-url", "model"].filter((name) => flags[name] !== undefined)
  const conflictingEnvironment = [
    "OPENCODE_IMAGEGEN_PROVIDER",
    "OPENCODE_IMAGEGEN_API",
    "OPENCODE_IMAGEGEN_API_KEY",
    "OPENCODE_IMAGEGEN_BASE_URL",
    "OPENCODE_IMAGEGEN_MODEL",
  ].filter((name) => process.env[name])
  if (conflictingFlags.length > 0 || conflictingEnvironment.length > 0) {
    throw new Error("--route cannot be combined with provider, API, base URL, API key, or model overrides")
  }
}

function resolveGenerationConfig({ profile, flags, imagegenConfig, managedConfig, opencodeConfig, route, preferManagedDefaults }) {
  const direct = route ? {} : flags
  const environment = route ? {} : process.env
  const ordered = (managedValue, legacyValue) => preferManagedDefaults
    ? [resolveConfigString(managedValue), resolveConfigString(legacyValue)]
    : [resolveConfigString(legacyValue), resolveConfigString(managedValue)]
  const provider = firstString(
    direct.provider,
    environment.OPENCODE_IMAGEGEN_PROVIDER,
    ...ordered(profile.config.provider, imagegenConfig.provider),
    "openai",
  )
  const managedProvider = managedConfig.providers[provider] ?? {}
  const managedProviderOptions = managedProvider.config?.options ?? {}
  const nativeProviderOptions = opencodeConfig?.provider?.[provider]?.options ?? {}
  const model = firstString(
    direct.model,
    environment.OPENCODE_IMAGEGEN_MODEL,
    ...ordered(profile.config.model, imagegenConfig.model),
    FALLBACK_MODEL,
  )
  const binding = managedProvider.auth?.models?.[model] ?? managedProvider.auth?.default
  const directCredentialSelection = firstString(
    direct.provider,
    environment.OPENCODE_IMAGEGEN_PROVIDER,
    direct.model,
    environment.OPENCODE_IMAGEGEN_MODEL,
    direct.api,
    environment.OPENCODE_IMAGEGEN_API,
    direct["base-url"],
    environment.OPENCODE_IMAGEGEN_BASE_URL,
  )
  const legacyCredentialSelection = !preferManagedDefaults && firstString(
    imagegenConfig.provider,
    imagegenConfig.model,
    imagegenConfig.api,
    imagegenConfig.baseURL ?? imagegenConfig.baseUrl,
    imagegenConfig.apiKey,
    imagegenConfig.apiKeyFile ?? imagegenConfig.api_key_file,
  )
  const useProfileSecret = Boolean(profile.name) && !directCredentialSelection && !legacyCredentialSelection
  const allowProviderCredentialFallback = !useProfileSecret && !binding

  return {
    profile: profile.config,
    profileName: profile.name,
    provider,
    coordinatorModel: firstString(
      process.env.OPENCODE_IMAGEGEN_COORDINATOR_MODEL,
      profile.config.coordinatorModel ?? profile.config.coordinator_model,
      imagegenConfig.coordinatorModel ?? imagegenConfig.coordinator_model,
      "gpt-5.5",
    ),
    codexEndpoint: firstString(
      process.env.OPENCODE_IMAGEGEN_CODEX_ENDPOINT,
      profile.config.codexEndpoint ?? profile.config.codex_endpoint,
      imagegenConfig.codexEndpoint ?? imagegenConfig.codex_endpoint,
      CODEX_RESPONSES_ENDPOINT,
    ),
    api: firstString(
      direct.api,
      environment.OPENCODE_IMAGEGEN_API,
      ...ordered(profile.config.api, imagegenConfig.api),
      "images",
    ),
    apiKey: route ? undefined : firstString(
      direct["api-key"],
      environment.OPENCODE_IMAGEGEN_API_KEY,
      ...(!preferManagedDefaults ? [
          resolveConfigString(imagegenConfig.apiKey),
          resolveConfigFile(imagegenConfig.apiKeyFile ?? imagegenConfig.api_key_file),
        ] : []),
      ...(allowProviderCredentialFallback ? [
          resolveConfigString(nativeProviderOptions.apiKey),
          process.env.OPENAI_API_KEY,
        ] : []),
    ),
    secretAlias: firstString(useProfileSecret ? profile.config.secret : undefined, binding?.secret),
    baseURL: firstString(
      direct["base-url"],
      environment.OPENCODE_IMAGEGEN_BASE_URL,
      ...ordered(profile.config.baseURL ?? profile.config.baseUrl, imagegenConfig.baseURL ?? imagegenConfig.baseUrl),
      resolveConfigString(nativeProviderOptions.baseURL),
      resolveConfigString(managedProviderOptions.baseURL),
      process.env.OPENAI_BASE_URL,
      "https://api.openai.com/v1",
    ),
    model,
    size: firstString(
      flags.size,
      process.env.OPENCODE_IMAGEGEN_SIZE,
      ...ordered(profile.config.size, imagegenConfig.size),
      FALLBACK_SIZE,
    ),
    quality: firstString(
      flags.quality,
      process.env.OPENCODE_IMAGEGEN_QUALITY,
      ...ordered(profile.config.quality, imagegenConfig.quality),
      FALLBACK_QUALITY,
    ),
    outputFormat: normalizeFormat(firstString(
      flags["output-format"],
      process.env.OPENCODE_IMAGEGEN_OUTPUT_FORMAT,
      ...ordered(
        profile.config.outputFormat ?? profile.config.output_format,
        imagegenConfig.outputFormat ?? imagegenConfig.output_format,
      ),
      FALLBACK_FORMAT,
    )),
    timeoutMs: parseTimeout(firstString(...ordered(profile.config.timeoutMs, imagegenConfig.timeoutMs))),
  }
}

function validateGenerationConfig(config, inputImages) {
  if (!VALID_APIS.has(config.api)) throw new Error("--api must be one of images, responses, or codex")
  if (!VALID_QUALITIES.has(config.quality)) throw new Error("--quality must be one of low, medium, high, or auto")
  if (!VALID_FORMATS.has(config.outputFormat)) throw new Error("--output-format must be one of png, jpeg, jpg, or webp")
  if (inputImages.length > 0 && !["responses", "codex"].includes(config.api)) {
    throw new Error("input images require --api responses or codex")
  }
}

function buildPayload(config, { prompt, count, inputImages }) {
  if (config.api === "codex") {
    return codexResponsesPayload({
      model: config.coordinatorModel,
      prompt,
      size: config.size,
      quality: config.quality,
      outputFormat: config.outputFormat,
      inputImages,
    })
  }
  return config.api === "responses"
    ? responsesPayload({ model: config.model, prompt, size: config.size, quality: config.quality, outputFormat: config.outputFormat, inputImages })
    : imagesPayload({ model: config.model, prompt, count, size: config.size, quality: config.quality, outputFormat: config.outputFormat })
}

async function generateAtomically({ attempt, prompt, count, inputImages, outputPaths, secretStore, force }) {
  const apiKey = attempt.api === "codex"
    ? undefined
    : attempt.apiKey ?? (attempt.secretAlias ? await secretStore.get(attempt.secretAlias) : undefined)
  if (attempt.api !== "codex" && !apiKey) {
    throw new Error(`missing API key for provider ${attempt.provider}: configure a managed secret alias or OPENCODE_IMAGEGEN_API_KEY`)
  }
  await fs.mkdir(path.dirname(outputPaths[0]), { recursive: true })
  await assertSafeOutputPaths(outputPaths)
  const stagingDir = await fs.mkdtemp(path.join(path.dirname(outputPaths[0]), ".labflow-imagegen-"))
  const stagingPaths = outputPaths.map((outputPath) => path.join(stagingDir, path.basename(outputPath)))
  try {
    const payload = buildPayload(attempt, { prompt, count, inputImages })
    const generation = attempt.api === "codex"
      ? await generateCodexImages({
          coordinatorModel: attempt.coordinatorModel,
          codexEndpoint: attempt.codexEndpoint,
          prompt,
          size: attempt.size,
          quality: attempt.quality,
          outputFormat: attempt.outputFormat,
          inputImages,
          outputPaths: stagingPaths,
          timeoutMs: attempt.timeoutMs,
        })
      : attempt.api === "responses"
        ? await generateResponsesImages({
          apiKey,
          baseURL: attempt.baseURL,
          model: attempt.model,
          prompt,
          size: attempt.size,
          quality: attempt.quality,
          outputFormat: attempt.outputFormat,
          inputImages,
          outputPaths: stagingPaths,
          timeoutMs: attempt.timeoutMs,
        })
        : await generateImages({
          apiKey,
          baseURL: attempt.baseURL,
          payload,
          outputPaths: stagingPaths,
          timeoutMs: attempt.timeoutMs,
        })
    if (generation.written.length !== outputPaths.length) throw new Error("API returned fewer images than requested")
    await commitStagedOutputs(stagingPaths, outputPaths, stagingDir, force)
    return { ...generation, written: outputPaths.map(relativeToCwd) }
  } catch (error) {
    if (error instanceof Error && apiKey && error.message.includes(apiKey)) {
      const redacted = new Error(error.message.replaceAll(apiKey, "<redacted>"), { cause: error })
      redacted.retryable = error.retryable
      redacted.ambiguousTimeout = error.ambiguousTimeout
      throw redacted
    }
    throw error
  } finally {
    await fs.rm(stagingDir, { recursive: true, force: true })
  }
}

async function commitStagedOutputs(stagingPaths, outputPaths, stagingDir, force) {
  const backups = []
  const committed = []
  try {
    await assertSafeOutputPaths(outputPaths)
    for (let index = 0; index < outputPaths.length; index += 1) {
      const outputPath = outputPaths[index]
      if (await exists(outputPath)) {
        if (!force) throw new Error(`output already exists: ${relativeToCwd(outputPath)} (use --force to overwrite)`)
        const backupPath = path.join(stagingDir, `.backup-${index}-${path.basename(outputPath)}`)
        await fs.rename(outputPath, backupPath)
        backups.push({ outputPath, backupPath })
      }
      await fs.rename(stagingPaths[index], outputPath)
      committed.push(outputPath)
    }
  } catch (error) {
    for (const outputPath of committed.reverse()) await fs.rm(outputPath, { force: true })
    for (const { outputPath, backupPath } of backups.reverse()) {
      if (await exists(backupPath)) await fs.rename(backupPath, outputPath)
    }
    throw error
  }
}

function isRetryableFailure(error, route) {
  if (!route) return false
  if (error?.ambiguousTimeout) return route.fallbackOnAmbiguousTimeout === true
  return error?.retryable === true
}

function safeErrorMessage(error) {
  return error instanceof Error ? error.message.slice(0, 500) : String(error).slice(0, 500)
}

function profileListing(imagegen) {
  const profiles = isPlainObject(imagegen.profiles) ? imagegen.profiles : {}
  const routes = isPlainObject(imagegen.routes) ? imagegen.routes : {}
  return {
    ok: true,
    default_profile: imagegen.defaultProfile,
    default_route: imagegen.defaultRoute,
    profiles: Object.keys(profiles).sort(),
    routes: Object.fromEntries(Object.entries(routes).map(([name, route]) => [name, route.profiles ?? []])),
  }
}

function imagesPayload({ model, prompt, count, size, quality, outputFormat }) {
  return {
    model,
    prompt,
    n: count,
    size,
    quality,
    output_format: outputFormat,
  }
}

function responsesPayload({ model, prompt, size, quality, outputFormat, inputImages = [] }) {
  const imageGenerationTool = {
    type: "image_generation",
    size,
    quality,
    output_format: outputFormat,
  }
  if (inputImages.length > 0) imageGenerationTool.action = "edit"

  return {
    model,
    input: inputImages.length > 0
      ? [
          {
            role: "user",
            content: [
              { type: "input_text", text: prompt },
              ...inputImages.map((image) => ({
                type: "input_image",
                image_url: image.dataURL,
                detail: "high",
              })),
            ],
          },
        ]
      : prompt,
    tools: [imageGenerationTool],
  }
}

async function generateImages({ apiKey, baseURL, payload, outputPaths, timeoutMs }) {
  const result = await postJson(apiEndpoint(baseURL, "images"), apiKey, payload, timeoutMs, apiResponseLimit(outputPaths.length))
  const images = Array.isArray(result.data) ? result.data : []
  if (images.length === 0) {
    throw new Error("API returned no images in data[]")
  }

  const written = []
  for (let index = 0; index < Math.min(images.length, outputPaths.length); index += 1) {
    const bytes = await imageBytes(images[index], timeoutMs)
    await fs.writeFile(outputPaths[index], bytes)
    written.push(relativeToCwd(outputPaths[index]))
  }
  return { written, revisedPrompt: result.data?.[0]?.revised_prompt }
}

async function generateResponsesImages({ apiKey, baseURL, model, prompt, size, quality, outputFormat, inputImages, outputPaths, timeoutMs }) {
  const written = []
  let revisedPrompt
  let responseID
  let imageGenerationCallID
  let actualSize
  let action
  for (const outputPath of outputPaths) {
    const result = await postJson(apiEndpoint(baseURL, "responses"), apiKey, responsesPayload({
      model,
      prompt,
      size,
      quality,
      outputFormat,
      inputImages,
    }), timeoutMs, apiResponseLimit(1))
    const image = responseImages(result)[0]
    if (!image) {
      throw new Error("Responses API returned no image_generation_call.result")
    }
    const bytes = await imageBytes(image, timeoutMs)
    await fs.writeFile(outputPath, bytes)
    written.push(relativeToCwd(outputPath))
    revisedPrompt ||= image.revised_prompt
    responseID ||= result.id
    imageGenerationCallID ||= image.id
    actualSize ||= image.size
    action ||= image.action
  }
  return { written, revisedPrompt, responseID, imageGenerationCallID, actualSize, action }
}

async function generateCodexImages({ coordinatorModel, codexEndpoint, prompt, size, quality, outputFormat, inputImages, outputPaths, timeoutMs }) {
  if (outputFormat !== "png") {
    const error = new Error("Codex Pro imagegen returns PNG; select a relay profile for JPEG or WebP output")
    error.retryable = true
    throw error
  }

  const accessToken = process.env.LABFLOW_IMAGEGEN_OPENAI_OAUTH_ACCESS
  const accountID = process.env.LABFLOW_IMAGEGEN_OPENAI_ACCOUNT_ID
  if (!accessToken) {
    const error = new Error("OpenCode ChatGPT OAuth credentials are unavailable to the imagegen plugin")
    error.retryable = true
    throw error
  }

  const written = []
  let actualSize
  let revisedPrompt
  let imageGenerationCallID
  for (const outputPath of outputPaths) {
    const image = await postCodexResponses(codexEndpoint, codexResponsesPayload({
      model: coordinatorModel,
      prompt,
      size,
      quality,
      outputFormat,
      inputImages,
    }), accessToken, accountID, timeoutMs)
    const bytes = await imageBytes({ b64_json: image.result }, timeoutMs)
    await fs.writeFile(outputPath, bytes)
    written.push(relativeToCwd(outputPath))
    actualSize ||= imageSize(bytes)
    revisedPrompt ||= image.revised_prompt
    imageGenerationCallID ||= image.id
  }
  return {
    written,
    actualSize,
    backendSize: size,
    revisedPrompt,
    imageGenerationCallID,
    action: inputImages.length > 0 ? "edit" : "generate",
  }
}

function codexResponsesPayload({ model, prompt, size, quality, outputFormat, inputImages }) {
  const userContent = [
    { type: "input_text", text: prompt },
    ...inputImages.map((image) => ({ type: "input_image", image_url: image.dataURL })),
  ]
  return {
    model,
    instructions: "You are an image generation assistant running inside the Codex backend. Always satisfy the request by invoking the image_generation tool exactly once. Do not respond with text only.",
    input: [{ role: "user", content: userContent }],
    tools: [{ type: "image_generation", output_format: outputFormat, quality, ...(size ? { size } : {}) }],
    tool_choice: { type: "image_generation" },
    stream: true,
    store: false,
  }
}

async function postCodexResponses(endpoint, payload, accessToken, accountID, timeoutMs) {
  let response
  let body
  try {
    response = await fetch(endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${accessToken}`,
        ...(accountID ? { "ChatGPT-Account-Id": accountID } : {}),
        originator: "opencode",
        Accept: "text/event-stream",
      },
      body: JSON.stringify(payload),
      signal: timeoutMs ? AbortSignal.timeout(timeoutMs) : undefined,
    })
    body = await responseTextBounded(
      response,
      response.ok ? apiResponseLimit(1) : MAX_ERROR_RESPONSE_BYTES,
      !response.ok,
    )
  } catch (error) {
    if (error?.name === "TimeoutError" || error?.name === "AbortError") error.ambiguousTimeout = true
    else if (error instanceof TypeError) error.retryable = true
    throw error
  }

  if (!response.ok) {
    const error = new Error(`Codex responses request failed (${response.status} ${response.statusText}): ${body.slice(0, 1600)}`)
    error.retryable = [401, 403, 408, 429].includes(response.status) || response.status >= 500
    throw error
  }

  return codexImageFromSse(body)
}

function imageSize(bytes) {
  if (imageMimeType(bytes) !== "image/png" || bytes.length < 24) return undefined
  return `${bytes.readUInt32BE(16)}x${bytes.readUInt32BE(20)}`
}

function codexImageFromSse(body) {
  for (const line of body.split(/\r?\n/)) {
    if (!line.startsWith("data:")) continue
    const data = line.slice(5).trim()
    if (!data || data === "[DONE]") continue
    try {
      const event = JSON.parse(data)
      const item = event?.item
      if (event?.type === "response.output_item.done" && item?.type === "image_generation_call" && typeof item.result === "string" && item.result.length > 0) {
        return item
      }
    } catch {}
  }
  throw new Error("Codex responses returned no image_generation result")
}

async function postJson(endpoint, apiKey, payload, timeoutMs, maxResponseBytes) {
  let response
  let body
  try {
    response = await fetch(endpoint, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
      signal: timeoutMs ? AbortSignal.timeout(timeoutMs) : undefined,
    })
    body = await responseTextBounded(
      response,
      response.ok ? maxResponseBytes : MAX_ERROR_RESPONSE_BYTES,
      !response.ok,
    )
  } catch (error) {
    if (error?.name === "TimeoutError" || error?.name === "AbortError") error.ambiguousTimeout = true
    else if (error instanceof TypeError) error.retryable = true
    throw error
  }

  if (!response.ok) {
    const error = new Error(`API failed (${response.status} ${response.statusText}): ${body.slice(0, 1600)}`)
    const code = responseErrorCode(body)
    error.retryable = response.status === 408 || response.status === 429 || response.status >= 500 || [
      "model_unavailable",
      "no_available_channel",
    ].includes(code)
    throw error
  }

  try {
    return JSON.parse(body)
  } catch {
    throw new Error(`API returned non-JSON response: ${body.slice(0, 400)}`)
  }
}

function apiResponseLimit(imageCount) {
  const encodedImageBytes = 4 * Math.ceil(MAX_OUTPUT_IMAGE_BYTES / 3)
  return encodedImageBytes * imageCount + MAX_JSON_OVERHEAD_BYTES
}

async function responseTextBounded(response, maxBytes, truncate) {
  const declaredLength = Number(response.headers.get("content-length"))
  if (!truncate && Number.isFinite(declaredLength) && declaredLength > maxBytes) {
    await response.body?.cancel()
    throw new Error(`API response exceeds the ${formatMiB(maxBytes)} limit`)
  }
  const reader = response.body?.getReader()
  if (!reader) return ""
  const chunks = []
  let length = 0
  let truncated = false
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    if (length + value.byteLength > maxBytes) {
      if (!truncate) {
        await reader.cancel()
        throw new Error(`API response exceeds the ${formatMiB(maxBytes)} limit`)
      }
      const remaining = Math.max(0, maxBytes - length)
      if (remaining > 0) chunks.push(Buffer.from(value.subarray(0, remaining)))
      length = maxBytes
      truncated = true
      await reader.cancel()
      break
    }
    length += value.byteLength
    chunks.push(Buffer.from(value))
  }
  return `${Buffer.concat(chunks, length).toString("utf8")}${truncated ? "<truncated>" : ""}`
}

function parseArgs(argv) {
  const tokens = [...argv]
  const command = tokens[0] && !tokens[0].startsWith("--") ? tokens.shift() : "generate"
  const flags = {}
  for (let index = 0; index < tokens.length; index += 1) {
    const token = tokens[index]
    if (!token.startsWith("--")) {
      throw new Error(`unexpected positional argument: ${token}`)
    }
    const key = token.slice(2)
    if (["dry-run", "force", "prompt-stdin", "help", "list-profiles"].includes(key)) {
      flags[key] = true
      continue
    }
    const value = tokens[index + 1]
    if (!value || value.startsWith("--")) {
      throw new Error(`missing value for --${key}`)
    }
    if (key === "input-image") {
      flags[key] = [...(flags[key] ?? []), value]
    } else {
      flags[key] = value
    }
    index += 1
  }
  return { command, flags }
}

function responseErrorCode(body) {
  try {
    const document = JSON.parse(body)
    const code = document?.error?.code ?? document?.code
    return typeof code === "string" ? code : undefined
  } catch {
    return undefined
  }
}

function parseTimeout(raw) {
  if (raw === undefined) return undefined
  const timeout = Number.parseInt(raw, 10)
  if (!Number.isInteger(timeout) || timeout < 1) throw new Error("imagegen timeoutMs must be a positive integer")
  return timeout
}

async function readPrompt(flags) {
  const promptSources = [flags.prompt, flags["prompt-file"], flags["prompt-stdin"]].filter(Boolean)
  if (promptSources.length !== 1) {
    throw new Error("provide exactly one of --prompt, --prompt-file, or --prompt-stdin")
  }
  if (flags.prompt) return String(flags.prompt).trim()
  if (flags["prompt-file"]) {
    return (await fs.readFile(flags["prompt-file"], "utf8")).trim()
  }
  const chunks = []
  for await (const chunk of process.stdin) chunks.push(chunk)
  return Buffer.concat(chunks.map((chunk) => Buffer.from(chunk))).toString("utf8").trim()
}

async function readInputImages(rawSources) {
  const sources = Array.isArray(rawSources) ? rawSources : rawSources ? [rawSources] : []
  if (sources.length > MAX_INPUT_IMAGES) {
    throw new Error(`provide at most ${MAX_INPUT_IMAGES} input images`)
  }

  const images = []
  const budget = { bytes: 0 }
  for (const source of sources) {
    let filePath
    let bytes
    try {
      filePath = await fs.realpath(path.resolve(process.cwd(), source))
      bytes = await readBoundedFile(filePath, budget)
    } catch (error) {
      throw new Error(`could not read input image ${source}: ${error.message}`)
    }
    const mime = imageMimeType(bytes)
    if (!mime) {
      throw new Error(`unsupported input image format: ${source} (expected PNG, JPEG, or WebP)`)
    }
    images.push({
      source: inputImageDisplayPath(filePath),
      mime,
      bytes: bytes.length,
      content: bytes,
      dataURL: `data:${mime};base64,${bytes.toString("base64")}`,
    })
  }
  return images
}

async function readBoundedFile(filePath, budget) {
  const noFollow = fsSync.constants.O_NOFOLLOW ?? 0
  const handle = await fs.open(filePath, fsSync.constants.O_RDONLY | noFollow)
  try {
    const stat = await handle.stat()
    if (!stat.isFile()) throw new Error("not a regular file")
    claimInputBytes(stat.size, budget)
    const buffer = Buffer.alloc(stat.size)
    let offset = 0
    while (offset < buffer.length) {
      const { bytesRead } = await handle.read(buffer, offset, buffer.length - offset, offset)
      if (bytesRead === 0) break
      offset += bytesRead
    }
    return buffer.subarray(0, offset)
  } finally {
    await handle.close()
  }
}

function claimInputBytes(bytes, budget) {
  if (bytes > MAX_INPUT_IMAGE_BYTES) {
    throw new Error(`exceeds the ${formatMiB(MAX_INPUT_IMAGE_BYTES)} per-image limit`)
  }
  if (budget.bytes + bytes > MAX_TOTAL_INPUT_IMAGE_BYTES) {
    throw new Error(`input images exceed the ${formatMiB(MAX_TOTAL_INPUT_IMAGE_BYTES)} total limit`)
  }
  budget.bytes += bytes
}

function formatMiB(bytes) {
  return `${bytes / (1024 * 1024)} MiB`
}

function imageMimeType(bytes) {
  if (bytes.length >= 8 && bytes.subarray(0, 8).equals(Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]))) {
    return "image/png"
  }
  if (bytes.length >= 3 && bytes[0] === 0xff && bytes[1] === 0xd8 && bytes[2] === 0xff) {
    return "image/jpeg"
  }
  if (bytes.length >= 12 && bytes.toString("ascii", 0, 4) === "RIFF" && bytes.toString("ascii", 8, 12) === "WEBP") {
    return "image/webp"
  }
  return undefined
}

function inputImageDisplayPath(filePath) {
  const relative = path.relative(process.cwd(), filePath)
  return relative && !relative.startsWith("..") && !path.isAbsolute(relative)
    ? relative
    : path.basename(filePath)
}

function inputImageSummary(image) {
  return {
    source: image.source,
    mime: image.mime,
    bytes: image.bytes,
  }
}

function redactImageData(value) {
  if (Array.isArray(value)) return value.map(redactImageData)
  if (isPlainObject(value)) {
    return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, redactImageData(item)]))
  }
  if (typeof value === "string" && /^data:image\/(?:png|jpeg|webp);base64,/.test(value)) {
    const comma = value.indexOf(",")
    return `${value.slice(0, comma + 1)}<redacted>`
  }
  return value
}

async function readOpencodeConfig(configDir = opencodeConfigDir()) {
  const configPath = path.join(configDir, "opencode.json")
  try {
    const raw = await fs.readFile(configPath, "utf8")
    return JSON.parse(stripTrailingCommas(stripJsonComments(raw)))
  } catch (error) {
    if (error.code === "ENOENT") return {}
    throw new Error(`could not read ${configPath}: ${error.message}`)
  }
}

async function readLabflowConfig(configDir = opencodeConfigDir()) {
  const configPaths = uniqueStrings([
    path.join(REPO_CONFIG_DIR, "labflow.json"),
    path.join(configDir, "labflow.json"),
    path.join(REPO_CONFIG_DIR, "labflow.local.json"),
    process.env.OPENCODE_IMAGEGEN_CONFIG ? resolveUserPath(process.env.OPENCODE_IMAGEGEN_CONFIG) : undefined,
  ])
  let merged = {}
  for (const configPath of configPaths) {
    merged = mergeObjects(merged, await readOptionalJson(configPath))
  }
  return merged
}

async function readOptionalJson(configPath) {
  try {
    const raw = await fs.readFile(configPath, "utf8")
    return JSON.parse(stripTrailingCommas(stripJsonComments(raw)))
  } catch (error) {
    if (error.code === "ENOENT") return {}
    throw new Error(`could not read ${configPath}: ${error.message}`)
  }
}

function mergeObjects(base, override) {
  if (!isPlainObject(base) || !isPlainObject(override)) return override
  const merged = { ...base }
  for (const [key, value] of Object.entries(override)) {
    merged[key] = isPlainObject(value) && isPlainObject(merged[key])
      ? mergeObjects(merged[key], value)
      : value
  }
  return merged
}

function isPlainObject(value) {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value)
}

function uniqueStrings(values) {
  return [...new Set(values.filter((value) => typeof value === "string" && value.length > 0))]
}

function stripJsonComments(input) {
  let output = ""
  let inString = false
  let escaped = false
  for (let index = 0; index < input.length; index += 1) {
    const char = input[index]
    const next = input[index + 1]
    if (inString) {
      output += char
      if (escaped) {
        escaped = false
      } else if (char === "\\") {
        escaped = true
      } else if (char === '"') {
        inString = false
      }
      continue
    }
    if (char === '"') {
      inString = true
      output += char
      continue
    }
    if (char === "/" && next === "/") {
      while (index < input.length && input[index] !== "\n") index += 1
      output += "\n"
      continue
    }
    if (char === "/" && next === "*") {
      index += 2
      while (index < input.length && !(input[index] === "*" && input[index + 1] === "/")) {
        index += 1
      }
      index += 1
      continue
    }
    output += char
  }
  return output
}

function stripTrailingCommas(input) {
  let output = ""
  let inString = false
  let escaped = false
  for (let index = 0; index < input.length; index += 1) {
    const char = input[index]
    if (inString) {
      output += char
      if (escaped) {
        escaped = false
      } else if (char === "\\") {
        escaped = true
      } else if (char === '"') {
        inString = false
      }
      continue
    }
    if (char === '"') {
      inString = true
      output += char
      continue
    }
    if (char === ",") {
      let cursor = index + 1
      while (cursor < input.length && /\s/.test(input[cursor])) cursor += 1
      if (input[cursor] === "}" || input[cursor] === "]") continue
    }
    output += char
  }
  return output
}

function resolveConfigString(value) {
  if (value === undefined || value === null) return undefined
  if (typeof value === "number" || typeof value === "boolean") return String(value)
  if (typeof value !== "string" || value.length === 0) return undefined
  const envMatch = value.match(/^\{env:([A-Za-z_][A-Za-z0-9_]*)\}$/)
  if (envMatch) return process.env[envMatch[1]]
  const fileMatch = value.match(/^\{file:(.+)\}$/)
  if (fileMatch) return resolveConfigFile(fileMatch[1])
  return value
}

function resolveConfigFile(value) {
  const filePath = resolveConfigString(value)
  if (!filePath) return undefined
  try {
    return fsSync.readFileSync(resolveConfigPath(filePath), "utf8").trim()
  } catch (error) {
    if (error.code === "ENOENT") return undefined
    throw new Error(`could not read configured imagegen file ${filePath}: ${error.message}`)
  }
}

function firstString(...values) {
  for (const value of values) {
    const resolved = resolveConfigString(value)
    if (resolved) return resolved
  }
  return undefined
}

function apiEndpoint(baseURL, api, codexEndpoint = CODEX_RESPONSES_ENDPOINT) {
  if (api === "codex") return codexEndpoint
  const trimmed = String(baseURL || "https://api.openai.com/v1").replace(/\/+$/, "")
  const apiBase = trimmed.endsWith("/v1") ? trimmed : `${trimmed}/v1`
  return api === "responses" ? `${apiBase}/responses` : `${apiBase}/images/generations`
}

function normalizeFormat(format) {
  return format === "jpg" ? "jpeg" : format
}

function parseCount(raw) {
  const count = raw === undefined ? 1 : Number.parseInt(raw, 10)
  if (!Number.isInteger(count) || count < 1 || count > MAX_VARIANTS) {
    throw new Error(`--n must be an integer from 1 to ${MAX_VARIANTS}`)
  }
  return count
}

async function plannedOutputPaths(input) {
  const paths = input.out
    ? pathsFromOut(input.out, input.count, input.outputFormat)
    : pathsFromOutDir(input.outDir, input.count, input.outputFormat, input.prompt)

  await assertSafeOutputPaths(paths)
  if (!input.force) {
    for (const outputPath of paths) {
      if (await exists(outputPath)) {
        throw new Error(`output already exists: ${relativeToCwd(outputPath)} (use --force to overwrite)`)
      }
    }
  }
  return paths
}

async function assertSafeOutputPaths(outputPaths) {
  const root = await fs.realpath(process.cwd())
  for (const outputPath of outputPaths) {
    const ancestor = await nearestExistingAncestor(path.dirname(outputPath))
    const resolvedAncestor = await fs.realpath(ancestor)
    const relative = path.relative(root, resolvedAncestor)
    if (relative.startsWith("..") || path.isAbsolute(relative)) {
      throw new Error("output paths must not escape the current working directory through symlinks")
    }
  }
}

async function nearestExistingAncestor(input) {
  let current = input
  while (true) {
    try {
      await fs.lstat(current)
      return current
    } catch (error) {
      if (error?.code !== "ENOENT") throw error
      const parent = path.dirname(current)
      if (parent === current) throw error
      current = parent
    }
  }
}

function pathsFromOut(rawOut, count, outputFormat) {
  const resolved = resolveInsideCwd(rawOut)
  const parsed = path.parse(resolved)
  const extension = parsed.ext || `.${extensionFor(outputFormat)}`
  const stem = path.join(parsed.dir, parsed.name || "imagegen")
  return Array.from({ length: count }, (_, index) => {
    const suffix = count === 1 ? "" : `-${index + 1}`
    return `${stem}${suffix}${extension}`
  })
}

function pathsFromOutDir(rawOutDir, count, outputFormat, prompt) {
  const outDir = resolveInsideCwd(rawOutDir)
  const stem = `${timestampSlug()}-${promptSlug(prompt)}`
  return Array.from({ length: count }, (_, index) => {
    const suffix = count === 1 ? "" : `-${index + 1}`
    return path.join(outDir, `${stem}${suffix}.${extensionFor(outputFormat)}`)
  })
}

function resolveInsideCwd(rawPath) {
  const resolved = path.resolve(process.cwd(), rawPath)
  const relative = path.relative(process.cwd(), resolved)
  if (relative.startsWith("..") || path.isAbsolute(relative)) {
    throw new Error("output paths must stay inside the current working directory")
  }
  return resolved
}

function extensionFor(format) {
  return format === "jpeg" ? "jpg" : format
}

async function exists(filePath) {
  try {
    await fs.access(filePath)
    return true
  } catch {
    return false
  }
}

function timestampSlug() {
  return new Date().toISOString().replace(/[-:]/g, "").replace(/\.\d{3}Z$/, "Z")
}

function promptSlug(prompt) {
  const slug = prompt
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 48)
  return slug || `imagegen-${randomUUID().slice(0, 8)}`
}

async function imageBytes(image, timeoutMs) {
  if (typeof image?.b64_json === "string") {
    const maxEncodedBytes = 4 * Math.ceil(MAX_OUTPUT_IMAGE_BYTES / 3)
    if (image.b64_json.length > maxEncodedBytes) throw new Error(`generated image exceeds the ${formatMiB(MAX_OUTPUT_IMAGE_BYTES)} limit`)
    const bytes = Buffer.from(image.b64_json, "base64")
    if (bytes.length > MAX_OUTPUT_IMAGE_BYTES) throw new Error(`generated image exceeds the ${formatMiB(MAX_OUTPUT_IMAGE_BYTES)} limit`)
    return bytes
  }
  if (typeof image?.url === "string") {
    return downloadImageBytes(image.url, timeoutMs)
  }
  throw new Error("image item has neither b64_json nor url")
}

async function downloadImageBytes(url, timeoutMs) {
  try {
    const response = await fetch(url, { signal: timeoutMs ? AbortSignal.timeout(timeoutMs) : undefined })
    if (!response.ok) {
      const error = new Error(`could not download image URL (${response.status} ${response.statusText})`)
      error.retryable = response.status === 408 || response.status === 429 || response.status >= 500
      throw error
    }
    const declaredLength = Number(response.headers.get("content-length"))
    if (Number.isFinite(declaredLength) && declaredLength > MAX_OUTPUT_IMAGE_BYTES) {
      throw new Error(`generated image exceeds the ${formatMiB(MAX_OUTPUT_IMAGE_BYTES)} limit`)
    }
    const reader = response.body?.getReader()
    if (!reader) throw new Error("image URL returned no response body")
    const chunks = []
    let length = 0
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      length += value.byteLength
      if (length > MAX_OUTPUT_IMAGE_BYTES) {
        await reader.cancel()
        throw new Error(`generated image exceeds the ${formatMiB(MAX_OUTPUT_IMAGE_BYTES)} limit`)
      }
      chunks.push(Buffer.from(value))
    }
    if (length === 0) throw new Error("image URL returned an empty response body")
    return Buffer.concat(chunks, length)
  } catch (error) {
    if (error?.name === "TimeoutError" || error?.name === "AbortError") error.ambiguousTimeout = true
    else if (error instanceof TypeError) error.retryable = true
    throw error
  }
}

function responseImages(result) {
  const output = Array.isArray(result.output) ? result.output : []
  return output
    .filter((item) => item?.type === "image_generation_call" && typeof item.result === "string")
    .map((item) => ({
      id: item.id,
      action: item.action,
      status: item.status,
      b64_json: item.result,
      revised_prompt: item.revised_prompt,
      output_format: item.output_format,
      size: item.size,
      quality: item.quality,
    }))
}

function relativeToCwd(filePath) {
  return path.relative(process.cwd(), filePath)
}

function homeDir() {
  if (!process.env.HOME) throw new Error("HOME is not set")
  return process.env.HOME
}

function opencodeConfigDir() {
  return process.env.OPENCODE_CONFIG_DIR || path.join(homeDir(), ".config", "opencode")
}

function resolveUserPath(rawPath) {
  if (rawPath === "~") return homeDir()
  if (rawPath.startsWith("~/")) return path.join(homeDir(), rawPath.slice(2))
  return path.resolve(rawPath)
}

function resolveConfigPath(rawPath) {
  if (rawPath === "~") return homeDir()
  if (rawPath.startsWith("~/")) return path.join(homeDir(), rawPath.slice(2))
  if (path.isAbsolute(rawPath)) return rawPath
  return path.join(REPO_CONFIG_DIR, rawPath)
}

function printResult(result) {
  console.log(JSON.stringify(result, null, 2))
}

function printHelp() {
  console.log(`Usage:
  node imagegen.mjs generate --prompt "..." [options]
  node imagegen.mjs generate --prompt-file prompt.txt [options]
  node imagegen.mjs generate --prompt-stdin [options]

Options:
  --profile PROFILE         Named profile from opencode/config/imagegen.yaml
  --route ROUTE             Ordered fallback route; cannot use direct provider/model overrides
  --list-profiles           Print configured profiles and routes without generating
  --provider PROVIDER       OpenCode provider ID. Fallback: openai
  --api API                 images | responses | codex. Fallback: images
  --input-image PATH        PNG, JPEG, or WebP reference; repeat up to ${MAX_INPUT_IMAGES} times (Responses or Codex)
  --model MODEL             Fallback: ${FALLBACK_MODEL}
  --size SIZE               Fallback: ${FALLBACK_SIZE}
  --quality QUALITY         low | medium | high | auto. Fallback: ${FALLBACK_QUALITY}
  --output-format FORMAT    png | jpeg | jpg | webp. Fallback: ${FALLBACK_FORMAT}
  --n N                     Number of variants, 1-${MAX_VARIANTS}. Default: 1
  --out PATH                Workspace-relative output path
  --out-dir DIR             Workspace-relative output directory. Fallback: ${FALLBACK_OUT_DIR}
  --force                   Overwrite existing output files
  --dry-run                 Print payload and paths without calling the API

Input limits:
  ${formatMiB(MAX_INPUT_IMAGE_BYTES)} per image and ${formatMiB(MAX_TOTAL_INPUT_IMAGE_BYTES)} total before base64 encoding.

Config:
  Reads named profiles/routes from opencode/config/imagegen.yaml, with legacy defaults from
  opencode/labflow.json, ~/.config/opencode/labflow.json, opencode/labflow.local.json,
  then OPENCODE_IMAGEGEN_CONFIG.
  Environment overrides: OPENCODE_IMAGEGEN_PROVIDER, OPENCODE_IMAGEGEN_API_KEY,
  OPENCODE_IMAGEGEN_BASE_URL, OPENCODE_IMAGEGEN_API, OPENCODE_IMAGEGEN_MODEL,
  OPENCODE_IMAGEGEN_COORDINATOR_MODEL, OPENCODE_IMAGEGEN_CODEX_ENDPOINT,
  OPENCODE_IMAGEGEN_PROFILE, OPENCODE_IMAGEGEN_ROUTE,
  OPENCODE_IMAGEGEN_SIZE, OPENCODE_IMAGEGEN_QUALITY,
  OPENCODE_IMAGEGEN_OUTPUT_FORMAT, OPENCODE_IMAGEGEN_OUT_DIR, OPENCODE_IMAGEGEN_N.
  Secrets can also be loaded from imagegen.apiKeyFile, resolved relative to opencode/.
`)
}
