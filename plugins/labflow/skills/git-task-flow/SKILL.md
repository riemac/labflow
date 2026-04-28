---
name: git-task-flow
description: Git 任务流管理技能。用于实现型任务的起始 tag、分步提交、变更核对、历史回溯与最终合并；只关注 git 机制，不包含 memory 持久化。
---

# Git Task Flow

用于需要可回溯、可恢复、分步提交的实现型任务。

## 适用场景

- 新任务开始，需要建立清晰的 git 边界
- 进行中，需要核对实际变更与提交历史
- 完成后，需要把中间提交整理成一个语义完整的最终提交
- 任务中断或放弃时，需要保留可恢复现场

## 核心规则

1. 任务开始时创建起始 tag，格式建议为 `task/<name>/<YYYYMMDD>`。
2. 编辑前后使用 `git status`、`git diff` 检查真实变更。
3. 需要回顾任务历史时，使用 `git log <tag>..HEAD --oneline`。
4. 每完成一个独立步骤就提交一次，commit message 使用 conventional commits。
5. 用户确认任务成功后，用 `git reset --soft <tag>` 将中间提交合并为一个语义完整的最终 commit。
6. 任务失败、暂停或放弃时，保留现有 commits，不做破坏性回退。

## 操作约束

- 默认只使用非破坏性 git 命令。
- 不随意重写与当前任务无关的历史。
- 不使用 `git reset --hard`，除非用户明确要求。
- 如果任务被拆成多个步骤，每一步都应能对应到一个清晰的 commit。

## 推荐检查顺序

1. 起点：确认当前分支与工作区状态。
2. 过程中：用 `git diff` 验证改动是否符合预期。
3. 收尾前：用 `git log <tag>..HEAD --oneline` 回看本任务提交链。
4. 完成后：确认是否需要 squash 成单一语义提交，或保留分步历史。
