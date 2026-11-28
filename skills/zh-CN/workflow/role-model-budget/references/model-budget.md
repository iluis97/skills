# 角色模型预算资料

本文件补充配置格式、解析规则和宿主差异。执行入口和输出要求见 [SKILL.md](../SKILL.md)；内置默认见 [assets/roles.json](../assets/roles.json)，可复制模板见 [assets/roles.example.json](../assets/roles.example.json)。

## 配置位置与优先级

配置按以下顺序合并，越靠前优先：

1. 用户在对话中的明确指定，例如“这次 reviewer 用 opus，思考强度 high”。
2. 环境变量 `AGENT_TEAM_ROLES` 指向的文件。设置后只读该文件作为用户配置，不再读取项目级和用户级默认路径。
3. 项目级 `<项目根>/.agent-team/roles.json`。
4. 用户级 `~/.agent-team/roles.json`；Windows 为 `%USERPROFILE%\.agent-team\roles.json`。
5. 技能包内 [assets/roles.json](../assets/roles.json)。这是内置默认，升级技能时会被覆盖，不直接编辑。

用户配置可以只写需要覆盖的字段，未写的字段继续向下回退。项目级和用户级同时存在时按字段合并，项目级优先。

配置文件不存在时正常使用内置默认，不报错。文件存在但无法读取、JSON 无效或关键字段类型错误时，报告具体路径和键，暂停受影响角色的预算解析；其他独立工作可以继续。用户授权后才改用内置默认。

## 配置格式

只使用标准 JSON，不支持注释。顶层字段：

| 字段 | 说明 |
| --- | --- |
| `version` | 当前为 `1`。缺失时按 `1` 处理；大于 `1` 时报告并使用内置默认。 |
| `defaults` | 全局默认值，字段为 `model`、`reasoning_effort`。 |
| `roles` | 角色默认值，键为角色名。内置角色为 `leader`、`designer`、`builder`、`reviewer`。 |
| `complexity` | 按 `small` / `medium` / `large` 覆盖角色值。 |
| `hosts` | 宿主专属覆盖，键为 `claude-code`、`codex`；内部结构与 `roles`、`complexity` 相同。 |

角色对象的字段：

| 字段 | 允许值 |
| --- | --- |
| `model` | 字符串或 `inherit`。具体模型名由宿主校验，通用段通常只放 `inherit`。 |
| `reasoning_effort` | `inherit`、`low`、`medium`、`high`、`xhigh`、`max`。宿主不支持的档位要报告，不静默降档。 |

示例：

```json
{
  "version": 1,
  "defaults": { "model": "inherit", "reasoning_effort": "inherit" },
  "roles": {
    "designer": { "model": "inherit", "reasoning_effort": "high" },
    "builder":  { "model": "inherit", "reasoning_effort": "medium" },
    "reviewer": { "model": "inherit", "reasoning_effort": "high" }
  },
  "complexity": {
    "small": {
      "reviewer": { "reasoning_effort": "medium" }
    },
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

`inherit` 是显式终止值：命中后不再向下查找。希望继续回退时省略字段，不要写 `inherit`。配置按字段合并，不整段覆盖；只覆盖 `reasoning_effort` 不会丢掉同一角色的 `model`。

## 内置默认

模型默认全部 `inherit`；`roles` 是 `medium` 的基础值，`small` 和 `large` 只覆盖思考强度：

| 复杂度 | Leader | Designer | Builder | Reviewer |
| --- | --- | --- | --- | --- |
| `small` | inherit | medium | medium | medium |
| `medium` | inherit | high | medium | high |
| `large` | inherit | xhigh | high | xhigh |

判断类角色（Designer、Reviewer）比执行类角色（Builder）高一档；复杂度上升时整体上调。Leader 通常是主线程，配置可能不适用，见宿主适配。

## 解析规则

每个字段独立按以下顺序查找，先命中者胜：

1. 用户当前对话的明确指定。
2. `hosts.<host>.complexity.<level>.<role>.<field>`
3. `complexity.<level>.<role>.<field>`
4. `hosts.<host>.roles.<role>.<field>`
5. `roles.<role>.<field>`
6. `defaults.<field>`
7. 内置默认表。
8. 宿主继承（`inherit` / 省略字段）。

也就是：复杂度覆盖角色默认；同一层级内宿主专属覆盖通用段；最后才用内置默认和宿主继承。只有该字段在所有配置层都缺失时，才使用内置默认。

示例：

- 配置只写了 `complexity.large.reviewer.reasoning_effort = "xhigh"`，没写 model；reviewer 的 model 继续从 `hosts.<host>.roles.reviewer.model` 或 `roles.reviewer.model` 取。
- 配置写了 `roles.builder.model = "inherit"`；builder 的 model 直接交给宿主继承，不再向下查找；effort 仍按复杂度或默认解析。
- 配置写了 `complexity.small.builder.reasoning_effort = "low"`；small 的 builder 用 low，medium 和 large 继续用 `roles.builder` 的值。

## 复杂度

沿用 `agent-team` 的判断：

| 档位 | 适用场景 |
| --- | --- |
| `small` | 目标明确、范围局部、无关键取舍、低风险。 |
| `medium` | 涉及多文件/多模块联动、需方案取舍或有明确验收标准。 |
| `large` | 跨系统、高风险、高不确定性或需多方并行协作。 |

用户已指定复杂度时严格采用，不因“看起来改动很小”静默降级；现场事实与指定明显冲突时，先说明事实和影响，由用户确认是否调整。未指定时由 Leader 判断并记录依据。

同一任务的不同工作流可以有不同复杂度，按各自工作流分别解析。同一执行者跨复杂度工作时，在后续派发重新解析并说明变化，不追溯改变已经运行的任务。预算表不决定启用哪些角色；角色组合仍由 `agent-team` / 宿主决定。

## 宿主适配

### Claude Code

| 项目 | 规则 |
| --- | --- |
| 调用参数 `model` | 只接受 `sonnet`、`opus`、`haiku`、`fable` 四个别名；不接受完整模型 ID，也不接受 `inherit`。省略参数表示继承。 |
| agent 定义 `model` | `.claude/agents/<role>.md` 的 frontmatter 支持别名、完整模型 ID 和 `inherit`。 |
| 思考强度 | 字段和调用参数都是 `effort`，支持 `low`、`medium`、`high`、`xhigh`、`max`。不要写 `reasoning_effort` 或 `thinking`；Claude Code 没有 per-subagent thinking 字段，写错会被静默忽略。 |
| 继承 | agent 定义写 `model: inherit` / `effort: inherit`；调用参数只能省略。 |
| 模型优先级 | 调用参数 > agent 定义 > `CLAUDE_CODE_SUBAGENT_MODEL` > 主会话模型；嵌套子代理使用启动它的子代理模型。 |
| 思考强度优先级 | `CLAUDE_CODE_EFFORT_LEVEL` > 调用参数 > agent 定义 > 启动它的子代理或 skill > `CLAUDE_CODE_SUBAGENT_EFFORT` > 会话档位 > 模型默认。`maxEffortLevel` 另行封顶，多来源取最低。 |
| 覆盖与回退 | `CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1` 会忽略 agent 定义和调用参数的模型；`fork` 忽略 model/effort；`availableModels` 允许列表可能触发宿主回退。 |
| 完整模型 ID | 调用参数不能传完整 ID。先查找同名 agent 定义；没有定义时报告，并请用户选择“改用别名”或“创建定义”，不静默降级。 |
| 验证 | 较新版本的 `/tasks` 会显示子代理模型和 effort；否则只能说明“已提交，未确认”。 |

当前会话的 `Agent` 工具 schema 未必暴露 `effort` 参数；较新版本的 `AgentInput` 和 agent frontmatter 才有。派发前先核对实际 schema；调用参数不支持 `effort` 时，改用 agent 定义的 `effort` 字段，或报告不支持。

Claude Code 的 `--agents` JSON 可以在当前会话定义角色表，字段与 agent frontmatter 相同；它是会话级方案，不是持久配置。Agent teams 是实验特性，teammate 可以引用 agent 定义继承 model/effort，但 split-pane teammate 不一定应用 effort；不要把预算设计绑在实验特性上。

### Codex CLI

| 项目 | 规则 |
| --- | --- |
| agent 定义 | `~/.codex/agents/*.toml` 或 `.codex/agents/*.toml`；字段包括 `name`、`description`、`developer_instructions`、`model`、`model_reasoning_effort`。 |
| 全局默认 | `[agents]` 下的 `default_subagent_model`、`default_subagent_reasoning_effort`。 |
| 内置 agent | `default`、`worker`、`explorer`；自定义同名 agent 可以覆盖。 |
| 优先级 | 显式 spawn > `[agents]` 默认 > 父代理；agent 文件中的显式值优先；未设置的字段继承。 |
| 继承 | 省略字段，不使用 `inherit` 关键字。 |
| 思考强度 | `model_reasoning_effort`，常用 `low`、`medium`、`high`、`xhigh`；扩展档位按宿主版本校验。 |
| 版本差异 | per-spawn 传 model/effort 的支持随版本变化；稳定面是 per-agent TOML。派发前核对当前宿主能力，不支持时报告。 |
| 已知问题 | issue #13849 中父 profile 可能覆盖角色 effort；需要时在角色 TOML 中写明确的 profile/model_provider，或报告限制。 |

Codex agent TOML 模板：

```toml
name = "reviewer"
description = "独立审查当前成果"
developer_instructions = "只读审查，不自行修补。"
# 替换为当前宿主可用的模型名；不确定时省略 model 以继承。
model = "..."
model_reasoning_effort = "high"
```

### 其他宿主

- 支持 per-role model/effort 时按对应参数应用，并核对实际 schema。
- 只支持全局模型或全局档位时，报告“仅全局生效”，不声称按角色生效。
- 完全不支持时使用 `inherit`，报告一次，不阻塞其他工作。
- 宿主有自己的上限时，目标档位与上限取较低值，并说明实际值。

## 失败与报告

- **配置不存在**：使用内置默认，正常继续。
- **配置无效**：报告具体路径和键；受影响角色暂停派发，其他独立工作可继续；用户授权后才用内置默认。
- **宿主不支持指定值**：报告具体模型或档位、来源和不支持原因；不静默换模型、降档或忽略覆盖。用户已授权替代配置时说明变化。
- **环境变量覆盖**：报告“配置未生效”，例如 `CLAUDE_CODE_EFFORT_LEVEL` 或 `CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1`。
- **fork 忽略配置**：报告“该子代理为 fork，model/effort 不适用”。
- **完整模型 ID 无法按调用参数应用**：查找 agent 定义；没有定义时报告，不自动创建文件，不静默改用别名。
- **角色兼任**：同一执行者兼任多个角色时，按较高思考档位执行；模型冲突时报告并由 Leader 选择，不静默合并。
- **宿主确认**：分别说明计划值、实际提交值和宿主确认值；宿主不返回确认时写“已提交，未确认”。

## 人工核对

修改本技能后核对：

1. `assets/roles.json` 和 `assets/roles.example.json` 是合法 JSON，默认表与本文一致。
2. `SKILL.md`、本文和 `assets/` 的相对链接可访问。
3. 解析顺序、`inherit` 终止语义和各层覆盖关系没有互相矛盾。
4. Claude Code 与 Codex 的字段名没有混用：Claude Code 用 `effort`，Codex 用 `model_reasoning_effort`，配置统一用 `reasoning_effort`。
5. 实际宿主效果在新会话中验证；文件存在或配置可读不等于宿主已按预算执行。