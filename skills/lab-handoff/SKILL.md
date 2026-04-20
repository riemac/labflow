---
name: lab-handoff
description: 对话收尾与 vault 全盘刷新。当用户准备结束当前 session、开新对话时触发。覆写 _context.md（当前状态快照），更新 _progress.md，创建新 atoms，清理过期条目。目标：下一个 session 读到的 vault 是准确的当前状态，不是历史堆积。
---

# Lab Handoff

对话结束前的 vault 全盘刷新。**目标：下一个 session 读到的 vault 是真实的当前状态，不是历史堆积。**

---

## 更新语义（最重要）

| 文件 | 操作 | 绝对禁止 |
|------|------|----------|
| `_context.md` | **覆写整个文件** | 在末尾追加（文件会膨胀成历史记录） |
| `_progress.md` | 覆写"当前任务"块 + 追加历史记录 | 只追加、不更新当前任务 |
| ideas/ atoms | 创建新 atom；`property:set` 更新 status | 删除 atom（改 status=abandoned 而非删除） |
| `_map.md` | 加新链接；已 abandoned 的迁入 deprecated 区 | 只追加新的 |

---

## 流程

### 1. 扫描本次 session

从对话中识别（逐条检查）：
- ✅ 完成的功能/实验
- 🎯 做出的设计决策 → `d-*.md`
- 💡 产生的新假设 → `h-*.md`
- 📋 得到的结论 → `f-*.md`
- ❓ 遗留的未解决问题 → `q-*.md`
- 🚧 已知阻塞

同时识别：已解决的旧问题、已验证的旧假设、已过时的旧决策 → 更新其 status。

### 2. 覆写 `_context.md`

先读取现有版本（了解结构和已有链接），然后整体重写：

```bash
obsidian vault=<name> read file="_context"
# 生成新内容后：
obsidian vault=<name> create name="_context" content="<新内容>" overwrite silent
```

**写什么**（严格 ≤1 页，只写当前真实状态）：

```markdown
# 研究语境：{项目名}

## 核心问题
{1-2 句话：当前在解决什么}

## 当前焦点
{最重要的一两个方向，具体到模块/假设}

## 活跃假设
- [[h-xxx]]：一句话（只列 status=active 的）

## 未解决问题
- [[q-xxx]]：一句话（只列 status=active 的）

## 最近决策
- [[d-xxx]]：一句话（只列本阶段最关键的 2-3 条）
```

**注意**：wikilinks 用 `[[atom-slug]]` 格式，只链接 `status=active` 的 atom。已 resolved/abandoned 的从这里移除。

### 3. 更新 `_progress.md`

`_progress.md` 分两部分：**当前任务**（覆写）+ **历史记录**（追加）。

先读取，然后整体重写：

```bash
obsidian vault=<name> read file="_progress"
# 整体重写，保留历史记录，更新当前任务块：
obsidian vault=<name> create name="_progress" content="<新内容>" overwrite silent
```

结构：

```markdown
# 工程进展：{项目名}

## 当前任务
{每次 handoff 覆写这一块}
- [ ] 待做：xxx
- [ ] 待做：yyy
- ⚠️ 阻塞：zzz

---
<!-- 历史记录追加在下方，勿修改 -->

## {YYYY-MM-DD} Session
### 完成
- xxx
### 遗留
- xxx
### 阻塞（已解除/仍存在）
- xxx
```

### 4. 处理 ideas/ atoms

**新 atom**（本次 session 中出现的值得持久化的新 h/q/f/d）：

```bash
obsidian vault=<name> create \
  name="ideas/d-<slug>" \
  content="---\ntype: decision\nstatus: active\n...\n---\n\n# 标题\n\n内容" \
  silent
```

**更新已有 atom status**：

```bash
# 假设已验证 → resolved
obsidian vault=<name> property:set name="status" value="resolved" file="ideas/h-xxx"
# 决策已过时 → abandoned
obsidian vault=<name> property:set name="status" value="abandoned" file="ideas/d-old"
# 问题已解答 → resolved
obsidian vault=<name> property:set name="status" value="resolved" file="ideas/q-xxx"
```

### 5. 更新 `_map.md`

```bash
# 追加新 atom 到 _map.md
obsidian vault=<name> append file="ideas/_map" \
  content="\n- [[d-new-decision]]：一句话"

# 对于已 abandoned 的，在 _map.md 中标记（加 deprecated 区块或注释）
# 用 read → 重写的方式处理（同 _context.md）
```

### 6. 向用户汇报

收尾阶段**可以输出写入日志**（用户需要确认完整性）：

```
✅ vault 已更新：
- _context.md 覆写（焦点：xxx）
- _progress.md 当前任务更新 + 历史追加
- 新 atom：d-xxx, f-yyy
- 状态更新：h-zzz → resolved, q-aaa → resolved
- _map.md 已追加新链接
```

用 `ask_user` 确认是否有遗漏，根据反馈补充后才算收尾完成。

---

## 反模式（务必避免）

- ❌ 只在 `_context.md` 末尾追加 "## 更新 2026-04-20：..." → 快照变成日志，下次读到脏数据
- ❌ 只创建新 atom，不更新旧 atom 的 status → vault 里全是 active，没有出清
- ❌ 不更新 `_progress.md` 的当前任务块，只追加历史 → "当前任务"永远是第一次写的
- ❌ 一次 handoff 做得太全面而漏了最关键的 → 不如只更新今天实际发生了变化的内容
