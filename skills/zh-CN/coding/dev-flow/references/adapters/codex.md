# Codex 适配器

仅在当前宿主为 Codex 时读取。其他宿主使用 `references/host-adapters.md`。

## 工具映射

不同 Codex 版本可能暴露不同的工具命名空间，常见形式包括：

- `spawn_agent`
- `multi_agent_v1.spawn_agent`
- `collaboration.spawn_agent`

以当前会话实际提供的工具 schema 为准，不推测不存在的参数。`spawn_agent` 通常返回真实 Agent ID 或句柄，用它作为 `agent_handle`。

## 参数映射

| 通用字段 | Codex 参数 |
|----------|------------|
| `context_mode = "isolated"` | `fork_turns = "none"` |
| `context_mode = "inherit"` | `fork_turns = "all"` |
| `model != "inherit"` | 传 `model` |
| `reasoning_effort != "inherit"` | 传 `reasoning_effort` |

规则：

1. 设置 `model` 或 `reasoning_effort` 时，`fork_turns` 必须为 `"none"`。
2. `fork_turns = "all"` 时不覆盖模型或推理强度。
3. 只传当前工具 schema 接受且任务需要的参数；不传 `agent_type` 等未声明参数。
4. 派发消息在 `fork_turns = "none"` 时必须自包含。
5. 派发前运行 `workflow.py handoff` 生成自包含任务卡。
6. 按本次 `handoff` 快照派发，成功后运行 `workflow.py record-spawn` 记录真实 Agent ID、本次 `dispatch_id` 和实际提交参数。

## 派发记录

从本次真实工具调用提取参数，写入阶段目录的 `spawn-request-<dispatch_id>.json`。例如实际使用了 `reasoning_effort=high` 和 `fork_turns=none`、省略模型覆盖时：

```json
{
  "reasoning_effort": "high",
  "context_mode": "isolated",
  "host_metadata": {
    "fork_turns": "none"
  }
}
```

只有实际传入 `agent_type` 时才将该字段加入 JSON。`context_mode` 根据真实 `fork_turns` 映射，不直接复制期望配置；`fork_turns=all` 不得登记为隔离。实际省略的模型或推理覆盖在 JSON 中同样省略。

成功后运行 `record-spawn --dispatch-id ... --request-file ... --handle ...`，脚本在对应阶段及 `decisions[]` 保存三类依据。只返回 Agent ID 的响应不能确认模型和推理等级；只有宿主明确返回的具体字段才通过 `--reported-model` / `--reported-reasoning-effort` 和 `--report-source` 登记。稍后回报用 `record-runtime`，不得采信子 Agent 自述。

主线程只展示命令返回的一行 `notice`。完整协议见 [../execution-reporting.md](../execution-reporting.md)，不要手改状态文件。

如果用户在 `assets/roles.json` 中为角色配置了具体 Codex 模型，默认应同时使用 `context_mode = "isolated"`。当前仓库配置使用 `model = "inherit"`，避免把特定供应商模型写死到通用技能中。

## 不可用与降级

### 子 Agent 工具不可用

仅当工具不存在或明确返回 unavailable/not found 时，允许主线程内联执行，运行：

```bash
python3 "$SKILL_DIR/scripts/workflow.py" record-execution \
  --state "$workflow_state_path" --stage TASK-02 \
  --mode inline --host codex --reason "<实际工具不可用原因>"
```

### 模型或推理强度不可用

- `on_spawn_error = "fail"`：停止阶段并运行 `workflow.py fail`。
- `on_spawn_error = "inherit"`：先运行 `role_registry.py check-model`。
- 有兼容档位时保留用户指定模型，只调整 `reasoning_effort`。
- 无兼容档位时去掉模型和推理强度覆盖，保留 `fork_turns` 重试一次。

发生模型错误时先用 `workflow.py fail --error-class model_capability_error` 或 `provider_error` 记录失败，并提供失败尝试的 `--dispatch-id` 和 `--request-file`。再重新 `handoff` 和派发，成功登记时用 `--fallback-reason` 记录实际调整原因。对话补充一句配置变化，详情落盘；新尝试不沿用旧回报。

`role_runtime_fallback` 决策由脚本追加；其中 `execution.configured` 保留原要求，`execution.submitted` 保存本次实际参数。不要将移除覆盖后的继承值填成具体模型或等级。

### 上下文压缩

如果当前 Codex 会话支持显式压缩，在 TASK-01 完成后执行；否则保留精简交接卡。压缩不得删除已落盘产物。
