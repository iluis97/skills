# 执行记录与简洁播报

主线程在开始执行阶段前读取。执行详情保存在 `workflow-state.json`，对话默认只展示必要的一行。

## 对话规则

- 阶段启动后，由主线程展示登记命令返回的 `notice`，不依赖子 Agent 自报身份。
- 默认一行包含阶段、业务角色、执行方式或真实 Agent 句柄、模型、推理等级及其确认依据。宿主提供 `agent_type` 时与业务角色分开显示，不把 `architect` 等角色 ID 当作宿主类型。
- 正常进度不重复身份信息。阶段结束简述结果和必要的验证结论；可与下一阶段启动信息合并，不额外播报整张身份卡。
- 重试或降级时补充一句“原配置 → 新配置：原因”。新句柄和新请求使用本次启动行展示，不再重复相同信息。工具失败尚无句柄时只报告失败，不宣称 Agent 已启动。
- 最终回复以交付、验证和关键剩余问题为主，不默认附执行配置表。`workflow-summary.md` 链接状态文件供追溯，不复制完整执行日志。
- 用户询问“谁在跑”“用了什么模型”等问题，或执行 `status` 时，再按查询范围展示记录；只有需要历史尝试、快照或降级原因时才使用 `status --details`。

示例：

```text
[TASK-02] architect · Agent a81f（worker） · 模型：继承（未知） · 推理：high（已提交）
[TASK-02] 推理 high → 继承：宿主不接受等级覆盖，已重试。
[SOLO] solo-developer · 主线程 · 模型：继承（未知） · 推理：继承（未知）
```

示例句柄只用于说明；实际播报必须使用宿主返回的句柄。

## 三类依据

`execution` 分别保存以下信息，模型和推理等级各自判断，不能用其中一项的依据替另一项背书：

- `configured`：本次解析得到的配置要求，保留兼容档位调整前的原值。
- `submitted`：从真实宿主调用中提取的实际提交参数。只保留 `model`、`reasoning_effort`、归一化的 `context_mode`、实际提供的 `agent_type` 和 `host_metadata`，不保存提示词、凭据或完整响应。继承时省略对应覆盖字段，不填 `inherit`。
- `reported`：宿主明确回报的具体值及每个字段的证据来源。无回报时为 `null`。

只有 `reported` 有该字段及来源时，才标注“已确认”；仅有实际提交参数时标注“已提交”。省略覆盖参数时显示“继承（未知）”。旧记录缺少提交依据时显示“未知（仅有配置）”，不得补猜。

宿主接受参数不代表已确认实际运行配置。父会话的型号、模型自述、回答风格、角色提示词都不能代替当前执行的宿主回报。宿主或供应商未提供更底层路由信息时，不推断真实后端模型。

## 派发与登记

1. `handoff` 一次解析配置，生成包含 `dispatch_id` 的任务卡和快照，并通过脚本写入 `stages.<stage>.dispatch_plan`、追加 `dispatch_prepared` 决策。重新 `handoff` 会使上一次尚未登记的 ID 失效，保留历史快照。
2. 按快照及当前宿主 schema 构造调用。不能为播报完整而传入不支持的参数，也不能把请求值当成宿主回报。
3. 从本次真实调用参数提取执行信息，写入本阶段目录下独立的 `spawn-request-<dispatch_id>.json`。宿主专有参数保存在 `host_metadata`，映射以当前适配器为准。
4. 成功返回真实句柄后，登记本次快照和实际提交信息：

```bash
python3 "$SKILL_DIR/scripts/workflow.py" record-spawn \
  --state "$workflow_state_path" --stage TASK-02 \
  --handle "<真实句柄>" --host codex \
  --dispatch-id "<本次 handoff 的 dispatch_id>" \
  --request-file "<本次 spawn-request JSON 路径>"
```

登记时不重新解析角色配置。同一快照仅登记一次；参数与快照不一致时必须提供 `--fallback-reason "<原因>"`，不得静默丢弃覆盖。实际提交信息不能由快照机械复制后冒充调用记录。

宿主确实回报配置时，才附加 `--reported-model` 或 `--reported-reasoning-effort`，并用 `--report-source` 指向宿主响应字段、查询结果或日志证据位置。只返回 Agent 句柄时省略这些选项。

稍后获取回报时：

```bash
python3 "$SKILL_DIR/scripts/workflow.py" record-runtime \
  --state "$workflow_state_path" --stage TASK-02 \
  --handle "<当前真实句柄>" \
  --reported-model "<宿主回报的具体模型>" \
  --report-source "<宿主证据来源>"
```

只补记本次执行对应的回报，不覆盖其他尝试。普通对话不因补记回报重复身份卡；若实际值与请求不符且影响执行判断，按异常简述。

## 重试与降级

- 派发失败但没有句柄时，运行 `fail`，同时提供本次 `--dispatch-id` 和 `--request-file`，记录快照、实际请求和错误；不调用 `record-spawn`，不伪造句柄。
- 按原有重试上限和 `on_spawn_error` 处理；不因新增播报扩大重试或模型切换权限。用户显式指定但不受支持的推理档仍按原规则停止报告。
- 每次重新派发前重新 `handoff`，使用独立请求文件。新执行清空上一尝试的宿主回报；历史尝试、失败和降级只追加到 `decisions[]`。
- 兼容档位调整、覆盖参数被忽略、继承降级和主线程内联降级均需如实记录原因，并在对话中补充一句。

## 主线程执行

TASK-01 和 SOLO 在开始时运行：

```bash
python3 "$SKILL_DIR/scripts/workflow.py" record-execution \
  --state "$workflow_state_path" --stage SOLO --mode main_thread
```

只有子 Agent 工具不存在或明确 unavailable 时，其他阶段才使用 `--mode inline --reason "<实际不可用原因>"`。这会登记 `agent_spawn_unavailable`。

主线程没有独立子 Agent 句柄，模型和推理等级沿用当前会话。角色配置保留为审计要求，不能宣称主线程已按配置切换；没有宿主回报时显示继承且未知。现有流程没有主线程配置切换接口，不通过填写角色配置模拟切换。主线程有真实回报时，也通过上述回报参数登记来源。

## 兼容读取

状态版本保持 `2.0`，新字段为增量扩展。历史 `model`、`reasoning_effort` 等平面字段仅作配置兼容读取；展示优先使用 `execution`。旧式 `record-spawn --model/--reasoning-effort` 仍可登记句柄和配置，但 `submitted` 为 `null`，不能标为“已提交”或“已确认”。新派发使用快照和请求文件。
