---
name: self-update
description: 对 labflow 的 opencode 集成本身进行自更新。当某个 skill、agent、全局规则、plugin、install 脚本或 opencode 配置需要改进时使用。普通源码改动由 file:// plugin 直接读取，重启 opencode 后生效；注册或依赖变更才需重跑 install.sh。
---

# labflow Self-Update for opencode

对 labflow 的 opencode 集成做迭代改进：编辑 `opencode/` 下的 agents、skills、规则、plugin 或 install 脚本 → 验证 → 按需注册/更新依赖 → 按需提交 → 重启 opencode。

> **关键约束：** opencode 只在启动时加载一次配置/skills/agents/规则，不热重载。plugin 通过 `file://` 从仓库直接读取这些源码，不会把它们同步到 `~/.config/opencode`。普通源码改动只需提示用户**退出并重启 opencode**；首次注册、package 依赖或 installer 变化时才重新运行 `install.sh`。

---

## 可更新的内容

- `opencode/agents/*.md`：primary / subagent 定义
- `opencode/skills/*/SKILL.md`：skills 的操作指南、模板、规范
- `opencode/labflow-rules.md`：全局跨 agent 规则
- `opencode/install.sh`：部署脚本
- 用户的 `~/.config/opencode/opencode.json`：instructions / mcp / agent 注册

> Codex 侧的内容（`.codex-plugin/`、`hooks/`、`.mcp.json`、marketplace）属于
> `main` 分支，不在 opencode 集成的自更新范围内。

---

## 更新流程

### 1. 提出并确认改动

用自然中文描述问题和建议改动，获得用户批准后再动手。一次只改一个文件或一个清晰的
改动点，除非用户明确要求结构性迁移。

### 2. 编辑文件

修改 `opencode/` 下的目标文件。SKILL.md frontmatter 只认
`name` / `description`（及可选 `license` / `compatibility` / `metadata`）；
agent frontmatter 用 `description` / `mode` / `permission` 等字段，正文即 prompt。

### 3. 按需提交到 git

```bash
cd /home/hac/labflow
git add -A
git commit -m "refactor: <改动一句话描述>"
```

Commit 类型：`refactor:` 改进现有行为，`fix:` 修正错误，`feat:` 新增 agent/skill。
若工作区存在用户未提交改动，先说明，不要把无关变更混进提交。

### 4. 按需注册 plugin 或更新依赖

```bash
/home/hac/labflow/opencode/install.sh
```

仅在首次注册、`opencode/package.json` 依赖变化或 installer 行为变化时运行。脚本安装 plugin 依赖并确保 `file://.../plugins/labflow.ts` 已注册到用户配置；agents、skills、规则和 plugin 源码仍从仓库直接读取，不复制到用户目录。

### 5. 告知用户

说明改动内容、验证结果，以及**需要退出并重启 opencode 才能观察行为变化**。

---

## 查证 opencode 官方配置 / 内部机制

改 `opencode.json` 或排查 opencode 内部行为（compaction、context、schema 键名、触发阈值等）时，**不要只信官方网页文档**（opencode.ai/docs）——它经常不全、过时、或与本机版本不符。按以下顺序查证：

1. **ctx7 优先**：`ctx7 library opencode` → `ctx7 docs /anomalyco/opencode "<关键词>"`。它能提供 spec 级线索，但结果可能指向并存的 V2 core，而不是当前 CLI runtime。
2. **gh 读真源码定地面真相**：`opencode --version` 拿版本号，再用 `gh api "repos/anomalyco/opencode/git/trees/v<版本>?recursive=1"` 定位文件、`gh api "repos/.../contents/<path>?ref=v<版本>"` 读取对应 tag。先确认当前 binary 实际使用 `packages/opencode/` 还是 `packages/core/`；同一 tag 可能同时包含两套 schema/runtime，不能凭目录名或最新 spec 猜测。
3. 本机 `~/.opencode/bin/opencode` 是编译过的 ELF，读不到 JS 源码，必须走 GitHub。

### 同会话 primary-agent 切换

如果 TUI/日志显示的当前 agent 与模型行为不一致：

1. 用日志中的 `agent=...` 和 `opencode debug agent <name>` 分开确认运行态与 resolved agent 配置，不要仅凭模型自述判断当前 agent。
2. 不要直接给 native `build` 配置短 `prompt`。在当前 OpenCode 实现中，一旦 `agent.prompt` 存在，它会替换 provider-specific 基础 prompt，而不是追加。
3. 不要通过 `chat.message` 注入单向 per-turn agent marker；这类 marker 会进入同会话历史，在反向切换时与当前 agent prompt 冲突。
4. 让 OpenCode 原生 agent 选择保持权威；若同会话历史仍使 build 困惑，让用户明确重申“现在按 build 实现”，或开启新 session。
5. 回归测试应覆盖受限 agent → build 与 build → 受限 agent 两个方向，并确认 `opencode debug agent build` 仍为 native、保留工具权限且没有自定义 `prompt`。

> 教训：OpenCode `v1.18.14` 同时包含 V2 `packages/core` 与当前 CLI `packages/opencode`。前者的 compaction 使用 `keep.tokens` / `buffer`，后者的公开 schema 与实际 runtime 使用 `tail_turns` / `preserve_recent_tokens` / `reserved`；`packages/opencode/src/session/compaction.ts` 和 `overflow.ts` 才是该版本 CLI 的地面真相。必须沿 binary 对应的调用链核实，不能把并存的新 schema 机械套到当前配置。

---

## 原则

- **最小改动**：每次只改一个清晰的问题，不做大范围重构
- **改后验证**：下次使用时观察改动是否达到预期，再决定是否继续迭代
- **不破坏已有结构**：修改前先读完整文件，理解上下文
- **不替用户做决定**：涉及行为变更的先说明取舍；明显的 typo/措辞优化可直接改
- **skill-first**：优先沉淀稳定重复动作，不把未用顺的科研工作流提前制度化
