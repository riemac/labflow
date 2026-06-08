---
name: git-task-flow
description: Git 任务流管理技能。用于有语义产出的实现或文档任务：起始锚点、checkpoint commit、diff 核对、历史整理、最终语义提交，以及轻量 SemVer / VERSION / CHANGELOG 收尾。
---

# Git Task Flow

用于需要可恢复 git 边界、checkpoint commit、语义化历史整理，以及版本感知收尾的实现或文档任务。

## 适用场景

- 新任务开始，需要清晰的 git 恢复锚点。
- 编辑前后需要核对真实工作区变化。
- 需要 checkpoint commit 保留可恢复现场。
- 发现漏提、混提、补丁型尾随提交，需要整理历史。
- 任务完成后，需要形成一个语义清晰的最终提交或少量提交。
- 任务有版本语义产出，需要更新 `VERSION` / `CHANGELOG`。

## 核心规则

1. 任务开始时创建恢复 tag，通常为 `task/<name>/<YYYYMMDD>`。
2. `task/...` tag 是恢复锚点，不是 release/version tag。
3. staging 前先看 `git status`，用 `git diff` 核对真实变更。
4. checkpoint 与最终提交都使用 conventional commit message。
5. 中间 commit 是 checkpoint，不等于最终历史，也不能单独触发版本 bump。
6. 不把无关本地改动混进任务提交；若存在无关改动，保持 unstaged 并说明。
7. 若任务依赖仿真、可视化、实验或人工科研判断，用户确认前不要视为最终验收。
8. checkpoint 后验证失败时，保留 checkpoint 继续修复，不做破坏性回退。
9. 不使用 `git reset --hard` 或破坏性 checkout/reset，除非用户明确要求。

## 版本收尾

当用户明确使用 `git-task-flow` 时，默认认为这个任务在真正收尾时至少会产生 patch 级语义进展。

任务收尾时：

- 先判断每个相关版本面应为 `patch`、`minor` 还是 `major`。
- 若判断为 `patch`，默认更新相关 `VERSION` / `CHANGELOG`，并纳入最终语义提交。
- 若判断为 `minor` 或 `major`，先暂停并询问用户确认，再编辑版本文件或创建 release tag。
- `CHANGELOG` 按人/agent 可共读的语义任务摘要来写，不按每个 commit 流水账记录。
- 最新版本段放在靠顶部位置；agent 默认只读顶部最近版本段，除非需要追溯旧历史。
- 版本收尾绑定已验收的任务结果，而不是每个 checkpoint commit。

SemVer 判断：

- `patch`：修 bug、文档、测试、清理、小行为修正、内部重构，且不改变公开 contract。
- `minor`：新增能力，或改变用户可见行为/API/contract，但仍处于当前兼容语境内。
- `major`：稳定 major 线之后，对公开 API、持久化格式、生成产物语义或工作流 contract 的破坏性变化。

对 `0.x` 阶段的科研项目，破坏性 contract 变化通常映射到 `minor`，除非仓库已有更严格的 release 规则。

## 仓库与子项目版本

- 仓库级 release tag，例如 `v0.2.1`，绑定仓库级版本文件和 changelog。
- 自包含子项目即便还不是独立 package、submodule 或独立 release 面，也可以维护自己的 `VERSION` / `CHANGELOG`。
- 不强制子项目创建 git tag、submodule 或 package metadata，除非仓库已有这种约定或用户明确要求。
- 如果任务 bump 了子项目版本，而仓库也有顶层版本，默认倾向仓库也做一次 `patch` bump，除非项目文档另有规定或用户选择不这么做。
- release tag 应指向已经包含对应 `VERSION` / `CHANGELOG` 状态的 commit。

## 历史整理原则

- 把 commit 当作语义边界，而不是时间顺序日志。
- 如果后续改动本应属于更早的语义提交，安全时用 `git commit --amend`、`fixup` 或交互式 rebase 折回去。
- 补丁型尾随提交优先 squash 回它修补的提交。
- 真正独立的任务阶段保留为独立提交。
- 改写本地历史前，如果还没有恢复锚点，先创建一个。
- 除非用户明确选择这个取舍，否则避免改写已共享历史。

## 常用命令

- `git status --short`
- `git diff`
- `git diff --staged`
- `git log <task-tag>..HEAD --oneline`
- `git commit --amend`
- `git rebase -i <base>`
- `git reset --soft <tag-or-commit>`
- `git cherry-pick <commit>`
- `git stash push -u`

## 推荐流程

1. 起点：检查 status，必要时创建 `task/...` 恢复 tag。
2. 过程中：只在清晰恢复点创建 checkpoint commit。
3. staging 前：核对 unstaged / staged diff，排除无关改动。
4. 最终提交前：判断语义提交边界，以及是否需要历史整理。
5. 版本收尾：判断 `patch` / `minor` / `major`；`patch` 默认执行，`minor` / `major` 先问用户。
6. 完成：提交已验收的代码、文档和版本变更；只有真正做 release/version 收尾时才创建 release tag。
7. 汇报：总结最终提交、版本变化、验证结果，以及仍保留未动的无关工作区改动。
