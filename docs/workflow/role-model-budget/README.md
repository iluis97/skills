# role-model-budget

为多角色工作流按任务复杂度解析每个角色的模型与思考强度，读取用户配置并在宿主能力内应用，缺失时使用内置默认。当前提供[中文技能入口](../../../skills/zh-CN/workflow/role-model-budget/SKILL.md)。

## 为什么单独一个技能

`agent-team` 的契约是**宿主无关的角色职责**：Leader、Designer、Builder、Reviewer 分别对什么负责、如何交接、底线是什么。模型名、思考档位、Claude Code 与 Codex 的参数差异属于另一个关注点；直接塞进 `agent-team` 会把宿主细节带进核心契约，也会推翻它“不指定模型名、供应商或推理档位”的维护要求。

因此拆成两个技能：

- `agent-team` 继续只定义职责、复杂度和调度边界，默认由宿主决定模型与档位。
- `role-model-budget` 负责配置读取、hardness 默认、宿主适配和预算表输出。
- 需要预算时显式同时调用；预算表是宿主 / Leader 直接采纳的派发指令，`agent-team` 不需要任何预算钩子，也不读取本技能正文。

## 如何使用

```text
$role-model-budget $agent-team 完成这个需求：……
```

预算技能先输出类似下面的表，宿主 / Leader 派发各角色时按表执行：

```text
复杂度：medium（依据：多模块联动，需要方案取舍）
leader:   model=inherit, effort=inherit（主线程，不适用）
designer: model=opus,    effort=high（hosts.claude-code.roles + roles）
builder:  model=sonnet,  effort=medium（hosts.claude-code.roles + 内置）
reviewer: model=opus,    effort=high（hosts.claude-code.roles + roles）
```

也可以在 `agent-team` 已启动后单独调用，为后续派发补预算。未显式调用时，本技能不介入，宿主自行决定或继承。

预算只决定**已启用角色**的模型与思考强度，不决定启用哪些角色、是否并行、谁写哪些文件；这些仍由 `agent-team` / 宿主决定。

## 配置位置

优先级从高到低：

1. 用户在对话中的明确指定。
2. 环境变量 `AGENT_TEAM_ROLES` 指向的文件（设置后不再读默认路径）。
3. 项目级 `<项目根>/.agent-team/roles.json`。
4. 用户级 `~/.agent-team/roles.json`；Windows 为 `%USERPROFILE%\.agent-team\roles.json`。
5. 技能包内 `assets/roles.json`（内置默认，只读，升级会覆盖）。

配置可以只写需要覆盖的字段；项目级和用户级按字段合并，项目级优先。完整格式和宿主示例见[配置资料](../../../skills/zh-CN/workflow/role-model-budget/references/model-budget.md)，可复制模板见[roles.example.json](../../../skills/zh-CN/workflow/role-model-budget/assets/roles.example.json)。

最小示例：

```json
{
  "version": 1,
  "roles": {
    "designer": { "model": "inherit", "reasoning_effort": "high" },
    "builder":  { "model": "inherit", "reasoning_effort": "medium" },
    "reviewer": { "model": "inherit", "reasoning_effort": "high" }
  },
  "complexity": {
    "large": {
      "designer": { "reasoning_effort": "xhigh" },
      "builder":  { "reasoning_effort": "high" },
      "reviewer": { "reasoning_effort": "xhigh" }
    }
  },
  "hosts": {
    "claude-code": {
      "roles": {
        "designer": { "model": "opus" },
        "builder":  { "model": "sonnet" },
        "reviewer": { "model": "opus" }
      }
    }
  }
}
```

## 解析规则

每个字段独立查找，先命中者胜：

1. 用户当前对话的明确指定。
2. `hosts.<host>.complexity.<level>.<role>.<field>`
3. `complexity.<level>.<role>.<field>`
4. `hosts.<host>.roles.<role>.<field>`
5. `roles.<role>.<field>`
6. `defaults.<field>`
7. 内置 hardness 默认。
8. 宿主继承。

也就是：**复杂度覆盖角色默认；同一层级内宿主专属覆盖通用段；最后才用内置默认和宿主继承。** 只有该字段在所有配置层都缺失时，才使用内置默认——这就是“配置文件未配置就用 hardness 默认”的含义。

`inherit` 是显式终止值：命中后不再向下查找。想继续回退就省略字段，不要写 `inherit`。

内置默认：

| 复杂度 | Leader | Designer | Builder | Reviewer |
| --- | --- | --- | --- | --- |
| `small` | inherit | medium | medium | medium |
| `medium` | inherit | high | medium | high |
| `large` | inherit | xhigh | high | xhigh |

模型默认全部 `inherit`，所以不配置模型名时仍是宿主行为；用户配置可以按角色和宿主替换。

## 宿主支持

| 能力 | Claude Code | Codex CLI |
| --- | --- | --- |
| 按角色配模型 | agent 定义 `model`；调用参数只接受 `sonnet`/`opus`/`haiku`/`fable` 别名 | agent TOML `model`；`[agents]` 可设默认 |
| 按角色配思考强度 | `effort`，5 档 | `model_reasoning_effort` |
| 原生角色配置文件 | 没有；每个角色一个 `.claude/agents/*.md`，或 `--agents` 会话级 JSON | `~/.codex/agents/*.toml` 或 `.codex/agents/*.toml` |
| 完整模型 ID | 只能写在 agent 定义里 | TOML 可直接写 |
| 继承 | 定义文件 `inherit`；调用参数省略 | 省略字段 |
| 主要限制 | `thinking` / `reasoning_effort` 会被静默忽略；环境变量、`fork`、允许列表可能覆盖或绕过配置 | spawn 参数支持随版本变化；父 profile 可能覆盖 role effort |

细节和已知问题见[配置资料](../../../skills/zh-CN/workflow/role-model-budget/references/model-budget.md)。派发前核对宿主真实 schema；不支持的值如实报告，不静默替换。

## 常见问题

- **为什么配置键叫 `reasoning_effort`，Claude Code 却用 `effort`？**
  `reasoning_effort` 是宿主无关的配置键；Claude Code 适配层映射为 `effort`，Codex 映射为 `model_reasoning_effort`。不要直接把 `reasoning_effort` 或 `thinking` 写进 Claude Code 的 agent frontmatter，会被静默忽略。
- **为什么 Claude Code 的完整模型 ID 不能直接传？**
  Claude Code 的 Agent 调用参数只接受 4 个别名。完整 ID 和 `inherit` 要写进 `.claude/agents/<role>.md`。配置要求完整 ID 时，先查找同名定义；没有就报告，让你选择改用别名或创建定义，不会静默降级。
- **为什么没有自动调用？**
  仓库默认所有技能手动触发，避免预算技能在不相关任务中自动介入，也避免 `agent-team` 通过读取其他技能正文绕过调用限制。需要时显式同时调用即可。
- **宿主不支持按角色配置怎么办？**
  使用 `inherit`，报告一次，不阻塞其他工作。只支持全局模型或档位时，说明“仅全局生效”，不声称按角色生效。
- **配置写错了会怎样？**
  文件不存在时用内置默认；文件存在但 JSON 无效或关键字段非法时，报告具体路径和键，暂停受影响角色，其他独立工作可继续。不会静默吞掉拼写错误。
- **预算表会改变角色分工吗？**
  不会。它只影响模型与思考强度，不启用或禁用角色，不改变复杂度判断、并行方式、写入所有权或审查独立性。
- **怎么确认宿主真的用了这些值？**
  分别看“计划值、实际提交值、宿主确认值”。Claude Code 较新版本的 `/tasks` 会显示子代理模型和 effort；Codex 看宿主输出或日志。拿不到确认时写“已提交，未确认”，不把计划值当确认值。

## 如何判断符合预期

- **配置按层生效**：项目级覆盖用户级，复杂度覆盖角色默认，宿主专属覆盖通用段；只覆盖 effort 时 model 不丢。
- **缺失走默认**：没有配置文件时使用内置 hardness 默认，不报错、不阻塞；配置存在但无效时报告具体问题。
- **不支持不静默替换**：宿主不支持的模型、档位、完整 ID、fork 场景都如实说明；没有擅自降档或换模型。
- **不越界**：预算表没有改变角色职责、调度、写入边界或审查独立性；没有自动创建宿主 agent 定义。
- **交接一致**：`agent-team` 按表派发，并区分计划、提交和宿主确认；没有把预算表当成角色分工表。

## 专属维护要求

- **默认保持宿主无关**：内置默认只使用 `inherit` 模型和通用思考档位，不写供应商模型名；宿主专属示例放在 `references/` 和 `assets/roles.example.json`。
- **字段名不能混**：配置统一用 `reasoning_effort`；Claude Code 适配层映射为 `effort`，Codex 映射为 `model_reasoning_effort`。不要引入 `thinking` 作为配置键。
- **`agent-team` 保持干净**：`agent-team` 不含任何预算规则、钩子或模型名；预算由宿主直接采纳本技能输出的预算表。两个技能都不自动调用对方，需要时由用户显式同时指定。
- **不新增自动调用**：本技能和 `agent-team` 都保持显式调用；需要组合时由用户同时指定，按依赖顺序执行。
- **不新增校验脚本或测试类**：修改后人工核对 JSON、默认表、解析顺序、命名、包内链接和文档索引；实际宿主效果在新会话中验证。
- **同步文档**：新增、删除或改变行为时，同步更新根 `README.md`、本说明和包内链接。