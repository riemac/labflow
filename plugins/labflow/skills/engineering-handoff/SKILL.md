---
name: engineering-handoff
description: 跨对话工程续接技能。用于用户明确要求更新工程 handoff、进度快照、下次接手说明，并显式指定目标路径时。只记录当前工程任务状态、关键文件、未完成步骤和阻塞；不维护科研语境、不写 ideas、不做知识图谱。
---

# Engineering Handoff

本 skill 只做**工程续接快照**，帮助下一个 Codex session 或未来的用户直接接上当前任务。

它不负责科研语境、假设、finding、decision atom，也不自动维护 Obsidian 知识图谱。

## 触发条件

必须同时满足：

- 用户要求更新 handoff / 进度快照 / 续接文档。
- 用户显式给出目标路径。

路径可以是：

- Obsidian：`vault=Research path=_progress.md`
- 普通文件：`/abs/path/to/progress.md`

如果用户没有给路径，先请用户提供；不要猜 vault，也不要读取 `.labflow` 自动写入。

## 安全规则

- 写入前先读取旧内容。
- Obsidian 写入前先确认目标 vault：

```bash
obsidian vault info=name
obsidian vault info=path
```

- Obsidian 优先使用 `path=`，不要用易撞名的 `file=`。
- `_progress.md` 这类 handoff 文件使用**覆写快照语义**，不要 append 成历史日志。
- 只记录已确认事实，不替用户编造研究判断。

## 内容模板

```markdown
# 工程续接：{项目名或任务名}

## 当前目标
{当前正在完成什么，1-3 句话}

## 当前进度
{已经完成哪些具体改动，尽量到文件/函数/配置级别}

## 未完成
- [ ] {下一步，具体可执行}
- [ ] {次优先级}

## 关键上下文
{下个 session 必须知道的设计约束、坑、依赖、用户偏好}

## 相关文件
- `/abs/path/file.py`：作用或当前状态

## 验证状态
{已运行/未运行的测试、结果、还需要人工判断的部分}

## 阻塞
{没有就写“无已知阻塞”}
```

## 输出给用户

写入后简短汇报：

- 目标路径。
- 覆写了哪些主要内容。
- 是否有未验证项或阻塞。

不要输出冗长写入日志。
