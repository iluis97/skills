---
name: role-model-budget
description: 为多角色工作流按任务复杂度解析每个角色的模型与思考强度，读取用户配置并在宿主能力内应用，缺失时使用内置默认。
disable-model-invocation: true
---

# 角色模型预算

显式调用后，为多角色工作流的 Leader、Designer、Builder、Reviewer（如 `agent-team`）解析本轮任务的模型与思考强度，输出可执行的预算表。预算只决定已启用角色的派发参数，不决定启用哪些角色、如何调度或如何分工。

## 使用方式

```text
$role-model-budget $agent-team 完成这个需求：……
```

先解析预算并输出预算表，作为宿主 / Leader 派发各角色时的模型与思考强度依据；宿主按表执行即可，`agent-team` 或其他技能不需要内置任何预算钩子。也可在任务已启动后单独调用，为后续派发补预算。未显式调用时，本技能不介入，宿主自行决定或继承。

## 读取与解析

1. 读取 [assets/roles.json](assets/roles.json) 作为内置默认，再按 [references/model-budget.md](references/model-budget.md) 的路径和优先级合并用户配置。用户配置不存在时直接使用内置默认。
2. 确认任务复杂度 `small` / `medium` / `large`。用户已指定时采用；未指定时按 `agent-team` 的复杂度定义判断并记录依据。不同工作流复杂度不同时分别解析。
3. 对实际启用的角色逐字段解析 `model` 与 `reasoning_effort`：复杂度覆盖角色默认，同一层级内宿主专属覆盖通用段，最后回退内置默认和宿主继承。`inherit` 是显式终止值，命中后不再向下查找。
4. 输出预算表，标明每个值的来源和宿主限制；需要时交给宿主适配层应用。

详细 schema、默认表、宿主差异和失败处理见 [references/model-budget.md](references/model-budget.md)。

## 输出

```text
复杂度：medium（依据：……）
leader:   model=inherit, effort=inherit（主线程，不适用）
designer: model=opus,    effort=high（hosts.claude-code.roles + roles）
builder:  model=sonnet,  effort=medium（hosts.claude-code.roles + 内置）
reviewer: model=opus,    effort=high（hosts.claude-code.roles + roles）
```

只列实际启用的角色；未使用或不适用的角色说明原因。分别说明计划值、实际提交值和宿主确认值；宿主不返回确认时写“已提交，未确认”。

## 关键约束

- **不静默替换**：宿主不支持指定模型或档位、配置无效、环境变量覆盖时，报告具体值、来源和影响，不擅自换模型、降档或忽略覆盖。用户已授权替代配置时说明变化。
- **先核对宿主 schema**：Claude Code 的调用参数 `model` 只接受别名，完整 ID 和 `inherit` 需要 agent 定义；思考强度字段是 `effort`，不是 `reasoning_effort`，写 `thinking` 会被静默忽略。Codex 的稳定面是 per-agent TOML，spawn 参数支持随版本变化。按实际 schema 传值，不猜参数。
- **不改变职责与调度**：预算表不启用或禁用角色，不改变复杂度判断、并行方式、写入所有权或审查独立性。角色组合仍由 `agent-team` / 宿主决定。
- **不自动写宿主配置**：不擅自创建或修改 `.claude/agents/*.md`、`~/.codex/agents/*.toml` 或用户配置；需要宿主定义时报告并提供模板或请用户授权。
- **预算是档位不是费用**：这里指模型档位和思考强度上限，不是 token/费用配额；宿主自己的 `maxEffortLevel` 等限制仍然生效，二者取较低值。