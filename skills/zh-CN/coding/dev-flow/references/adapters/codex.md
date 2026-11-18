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
6. 派出成功后运行 `workflow.py record-spawn` 记录真实 Agent ID。

## 派发记录

派出成功后运行 `workflow.py record-spawn`，由脚本追加通用记录并保留 Codex 审计字段：

```json
{
  "kind": "agent_spawned",
  "host": "codex",
  "stage": "TASK-02",
  "role_id": "architect",
  "agent_handle": "<spawn_agent 返回的 ID>",
  "model": "inherit",
  "reasoning_effort": "high",
  "context_mode": "isolated",
  "fork_turns": "none",
  "model_source": "parent",
  "reasoning_effort_source": "role",
  "fallback": false
}
```

脚本会同时把角色执行配置写入对应 `stages.<stage>`。不要手改状态文件。

如果用户在 `assets/roles.json` 中为角色配置了具体 Codex 模型，默认应同时使用 `context_mode = "isolated"`。当前仓库配置使用 `model = "inherit"`，避免把特定供应商模型写死到通用技能中。

## 不可用与降级

### 子 Agent 工具不可用

仅当工具不存在或明确返回 unavailable/not found 时，允许主线程内联执行，并记录：

```json
{
  "kind": "agent_spawn_unavailable",
  "host": "codex",
  "stage": "TASK-02",
  "role_id": "architect",
  "reason": "<实际错误>"
}
```

### 模型或推理强度不可用

- `on_spawn_error = "fail"`：停止阶段并运行 `workflow.py fail`。
- `on_spawn_error = "inherit"`：先运行 `role_registry.py check-model`。
- 有兼容档位时保留用户指定模型，只调整 `reasoning_effort`。
- 无兼容档位时去掉模型和推理强度覆盖，保留 `fork_turns` 重试一次。

发生模型错误时先用 `workflow.py fail --error-class model_capability_error` 或 `provider_error` 记录失败，再重新 `handoff` 和派发。

```json
{
  "kind": "role_runtime_fallback",
  "host": "codex",
  "stage": "TASK-02",
  "role_id": "architect",
  "configured_model": "<原模型>",
  "configured_reasoning_effort": "<原推理强度>",
  "fallback": "inherit",
  "reason": "<实际错误>"
}
```

### 上下文压缩

如果当前 Codex 会话支持显式压缩，在 TASK-01 完成后执行；否则保留精简交接卡。压缩不得删除已落盘产物。
