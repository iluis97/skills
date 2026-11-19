# 宿主适配协议

核心流程只依赖宿主能力，不依赖某个产品的工具名。开始派发前先确认当前宿主是否支持独立 Agent。

## 能力契约

宿主适配层提供以下能力：

```text
spawn(prompt, context_mode, model?, reasoning_effort?) -> agent_handle
wait(agent_handle) -> stage_report
send(agent_handle, message)
cancel(agent_handle)
```

`context_mode` 取值：

- `isolated`：新 Agent 不继承主线程对话历史，派发消息必须自包含。
- `inherit`：允许继承主线程上下文；仍应在消息中给出目标、产物和边界。

`model` 和 `reasoning_effort` 是可选偏好。宿主不支持对应能力时忽略覆盖并记录降级，不得把不支持的能力伪装成已生效。

## 适配规则

1. 优先使用宿主原生、真实的独立 Agent 生命周期能力。
2. 只把宿主真实返回的句柄登记为 `agent_handle`，不伪造 ID。
3. 一个流程只使用一个宿主适配器，不混用两套 Agent 生命周期。
4. 宿主支持显式上下文压缩时执行压缩；不支持时保留精简交接卡。
5. 宿主没有独立 Agent 能力时，才允许主线程内联执行阶段，并在 `decisions[]` 记录 `agent_spawn_unavailable`。
6. 宿主不接受某个参数时，不传该参数；模型或推理强度不可用时按 `on_spawn_error` 重试或停止。
7. 派出成功后立即运行 `workflow.py record-spawn` 登记真实句柄。
8. 阶段角色只写业务产物和 `stage-result.json`；主线程负责 `validate` 和 `complete`。
9. 使用 `handoff` 的本次快照构造调用，并从真实调用提取 `submitted`；分别登记 `configured`、`submitted` 和带证据来源的 `reported`。没有宿主回报的字段不标为已确认，详见 [execution-reporting.md](execution-reporting.md)。
10. 将宿主实际提供的 `agent_type` 与业务角色分开记录，不为显示类型而添加不支持的参数。归一化 `context_mode` 必须对应真实宿主上下文参数，专有控制参数写入 `host_metadata`，不得从配置反推实际提交。

## 适配器选择

- Codex：读取 [adapters/codex.md](adapters/codex.md)。
- 其他宿主：使用上述通用能力；如果宿主提供原生生命周期工具，在派发消息和状态中记录实际工具名与返回句柄。
- 没有专用适配器时，不新增宿主专有字段，不把某个产品的限制写成全局规则。

宿主专有的工具名、上下文继承参数、模型参数和降级字段只放在对应适配器中，核心流程和角色提示不得写死。
