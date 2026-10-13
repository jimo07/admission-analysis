# 旧版辩论 JSON 存档导入设计（S1-11）

状态：设计稿；尚未实现导入程序。字段依据当前桌面版 `debate_ui.py` 的 `save_history()` / `load_history()` 与消息追加代码梳理。计划书提到的 4 份存档文件目前不在仓库中（`history/` 目录被 Git 忽略且当前工作树未找到样本），因此本表覆盖已观察到的格式，仍需拿实际 4 份文件做导入前核对。

## 1. 目标与边界

- 将桌面版一场辩论的主题、配置和按序发言迁移为当前账号名下的个人历史会话。
- 保留源 JSON 原件，导入过程不覆盖或删除原文件，也不调用模型重新生成内容。
- 不把旧辩论“裁判评判”伪装成新版按量表生成的 `reports`；旧裁判内容作为会话中的 judge 消息保存。
- 教师只能看到依权限提交的课程任务内容。旧记录没有课程和提交关系，一律作为 `private` 私人会话导入。

## 2. 已观察到的源格式

文件名由旧版生成：`history/debate_<yyyyMMdd_HHmmss>.json`。顶层对象由 `save_history()` 写出：

```json
{
  "topic": "辩题文本",
  "mode": "AI vs AI",
  "max_turns": 3,
  "temp_zheng": 0.5,
  "temp_fan": 0.7,
  "model_zheng": "llama3.2",
  "model_fan": "gemma3:1b",
  "model_judge": "qwen3.5:4b",
  "history": [
    {"role": "正方", "phase": "AI立论", "content": "……"},
    {"role": "反方", "phase": "AI回应 第1轮", "content": "……"},
    {"role": "裁判", "phase": "评判", "content": "……"}
  ],
  "timestamp": "20261012_124147"
}
```

代码中可确认的历史项字段是 `role`、`phase`、`content`。人机模式下，用户发言仍以 `正方` 或 `反方` 写入 `role`，通过 `phase` 的 `用户发言` 标识，因此不能只靠 `role` 判断消息作者。

## 3. 字段映射

| 旧 JSON 字段 | 新系统目标 | 映射/处置规则 |
|---|---|---|
| `topic` | `sessions.topic` | 必填；去除首尾空白后导入。超过新字段 200 字上限时列入预览错误，由用户修正后再导，不静默截断。 |
| `mode` | `audit_events.detail.legacy_mode` | 保留原值作来源配置；新 `sessions` 无旧模式字段，不据此创建不同权限或课程关系。 |
| `max_turns` | `audit_events.detail.legacy_max_turns` | 原样保留为来源设置；新会话结构不存旧轮数设置。 |
| `temp_zheng` / `temp_fan` | `audit_events.detail` 对应设置项 | 作为历史配置保留，不用于再次调用模型。 |
| `model_zheng` / `model_fan` / `model_judge` | `audit_events.detail` 对应设置项 | 模型标识仅作来源记录。`model_judge` 必须保留；不能把旧裁判结论转成结构化报告。 |
| `history[]` | `messages` | 按 JSON 数组次序生成新 `seq`；不复用旧 ID（源格式没有 ID）。每项按下表转换。 |
| `timestamp` | `sessions.created_at`，并保留在导入审计详情 | 源格式为本机时间的 `yyyyMMdd_HHmmss`，无时区信息；按导入操作者确认的源时区解析，并同时保留原始字符串。解析失败则在预览报错，不擅自改成当前时间。 |
| 未知顶层字段 | 导入审计详情的 `unknown_fields` | 预览列出字段名；保留 JSON 原件。无明确映射前不写入业务列。 |

### 历史项映射

| 条件 | `messages.role` | `messages.agent_role` | `messages.content` / 其他 |
|---|---|---|---|
| `phase` 以 `用户发言` 开头 | `user` | `NULL` | 原文写入 `content`；阶段字符串保留在审计详情中的源项映射。 |
| `role=正方` 且不是用户发言 | `assistant` | `pro` | 原文写入 `content`。 |
| `role=反方` 且不是用户发言 | `assistant` | `con` | 原文写入 `content`。 |
| `role=裁判` | `assistant` | `judge` | 原文写入 `content`；不创建 `reports` 行。 |
| 其他 `role` / 缺少必要字段 | — | — | 该文件预览失败或要求人工处理；不静默改成 judge。 |

新消息的 `status` 设为 `complete`。`phase` 没有对应消息列：它用于识别用户发言，阶段标签按消息顺序写入导入审计详情中的 `message_phases`，完整旧 JSON 原件也必须保留。

## 4. 会话归属与未映射数据

- `sessions.owner_id` 使用当前登录并发起导入的用户；`visibility='private'`、`task_id=NULL`。旧文件不含账号、课程或提交人信息，不能推断其他归属。
- 有至少一条有效历史消息的会话导入为 `finished`；空 `history` 文件不创建会话，列入错误清单。
- 旧 JSON 没有观点修订、提交快照、课程信息、证据来源或新版量表分数：不生成 `revisions`、`task_submissions`、`reports`、`argument_nodes` 或 `evidence_sources`。
- `audit_events` 写一条 `legacy.session_imported`，`target_type='session'`、`target_id` 指向新会话。`detail` 记录源文件名、SHA-256、原始时间、旧配置（包括 `model_judge`）、有序 `message_phases`、未知字段名和映射版本；不写入密码、API key 或其他凭据。
- 导入完成后保留用户选定目录中的原文件。若归档原件由用户主动删除，需另行提供数据删除流程；数据库导入不代替原件备份。

## 5. 校验、预览与事务流程

1. 仅接受 UTF-8、大小受限的 JSON 对象；解析后展示文件名、主题、模式、时间、消息数、角色分布和异常项。
2. 必须经用户确认目标账号及导入数量；重复选择文件时用源文件 SHA-256 检查是否已导入。命中重复项默认跳过，不覆盖已有会话。
3. 校验 `topic`、`history` 类型和每条消息字段；拒绝非字符串或空白 `content`、未知 `role`、超长主题、无法解析时间等问题。输出可下载的逐文件错误报告。
4. 每个文件单独使用数据库事务创建 `sessions`、有序 `messages` 与导入审计记录；任一步失败则回滚该文件，不留半个会话。其他通过预检的文件可独立导入。
5. 完成后汇总成功/跳过/失败数量和会话 ID；用户可打开会话抽查顺序与文本。导入程序不得触发模型、裁判、报告或邮件通知。

## 6. 导入前待核验项

- 从原桌面版 `history/` 目录取得计划书所说的 4 份 JSON 样本，先核对顶层字段、历史项角色、阶段值、空值和编码；当前仓库没有这些存档，不能声称已经覆盖四份实文件的变体。
- 核实旧记录时间戳对应的原设备时区；若无法确认，必须在导入预览中让操作者选择，不能静默假定 UTC。
- 确认导入者账号已创建且对该数据拥有权利。历史记录可能包含个人表达，导入前向数据所有者说明用途、可见范围和删除方式。
- 完成样本核验后，再实现导入工具与对应测试；不得直接在真实 `sfb_dev` 上试跑。先用备份或独立临时 schema 演练。
