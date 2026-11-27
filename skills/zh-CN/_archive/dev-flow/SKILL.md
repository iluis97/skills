---
name: dev-flow
description: 以可校验、可恢复的多 Agent 流程完成软件交付，覆盖需求确认、设计、实现、审查、测试、知识沉淀和总结。
disable-model-invocation: true
---

# DevFlow

用于需要结构化交付、阶段隔离、可恢复状态和独立审查的软件开发任务。单文件小修或简单问答直接处理。

## 路径

- `PROJECT_ROOT`：用户当前工作目录，也是流程运行的根目录。
- `SKILL_DIR`：本技能包根目录。
- `ARTIFACTS_ROOT`：默认 `{PROJECT_ROOT}/artifacts`。
- `artifacts_dir`：`{ARTIFACTS_ROOT}/{TASK_SLUG}`。
- `workflow_state_path`：`{artifacts_dir}/workflow-state.json`。

启动前检查仓库、分支、工作区状态和项目指令。保留用户已有改动，不自动 stash、commit、push 或部署。

## 命令

```text
$dev-flow start <需求描述>
$dev-flow resume <TASK_SLUG>
$dev-flow status <TASK_SLUG>
$dev-flow abort <TASK_SLUG>
```

- `start`：初始化并执行新任务。
- `resume`：读取 `workflow-state.json`，从最近未完成或失败的阶段继续。
- `status`：只读汇总，不修改文件。
- `abort`：中止流程，保留全部产物并取消可控子 Agent。

## 权威资料

- 启动与调度：`references/start-workflow.md`
- 状态结构与命令：`references/workflow-state-spec.md`
- 阶段产物契约：`assets/stage-contracts.json`
- 阶段结果格式：`assets/stage-result.schema.json`
- 机器契约说明：`references/stage-contracts.md`
- 角色配置：`assets/roles.json`
- 宿主适配：`references/host-adapters.md`
- 执行记录与对话播报：阶段启动前读取 `references/execution-reporting.md`
- 当前角色：`references/roles/<role>.md`
- 当前阶段规则：`references/rules/`
- 代码审查门禁：`references/checklists/gate-code-review.md`

## 状态命令

所有状态变更必须通过 `scripts/workflow.py`，阶段角色不得直接编辑 `workflow-state.json`。

```bash
python3 "$SKILL_DIR/scripts/workflow.py" init \
  --workspace "$PROJECT_ROOT" --slug "$TASK_SLUG"

python3 "$SKILL_DIR/scripts/workflow.py" classify \
  --state "$workflow_state_path" --size medium \
  --reason "<Phase 0 规模判定依据>"

python3 "$SKILL_DIR/scripts/workflow.py" status \
  --state "$workflow_state_path"

python3 "$SKILL_DIR/scripts/workflow.py" handoff \
  --state "$workflow_state_path" --stage TASK-02

python3 "$SKILL_DIR/scripts/workflow.py" record-spawn \
  --state "$workflow_state_path" --stage TASK-02 \
  --handle "<agent-handle>" --host codex \
  --dispatch-id "<handoff 的 dispatch_id>" \
  --request-file "<本次实际提交参数 JSON>"

python3 "$SKILL_DIR/scripts/workflow.py" validate \
  --state "$workflow_state_path" --stage TASK-02

python3 "$SKILL_DIR/scripts/workflow.py" complete \
  --state "$workflow_state_path" --stage TASK-02

python3 "$SKILL_DIR/scripts/workflow.py" confirm \
  --state "$workflow_state_path" --stage TASK-01 \
  --note "<用户确认摘要>"

python3 "$SKILL_DIR/scripts/workflow.py" fail \
  --state "$workflow_state_path" --stage TASK-02 \
  --error-class artifact_invalid --error "<具体错误>"
```

## 主流程

1. Phase 0：主线程分析需求、代码、测试入口和影响面，判定 `small`、`medium` 或 `large`，并运行 `classify` 记录结果。
2. `small`：初始化后进入 SOLO，用 `record-execution --mode main_thread` 登记主线程执行，再完成实现、验证、知识沉淀和总结。
3. `medium` / `large`：TASK-01 用 `record-execution --mode main_thread` 登记后，由主线程完成需求澄清和用户确认。
4. TASK-02 起：
   - 用 `handoff` 生成阶段任务卡。
   - 解析角色配置并用宿主原生子 Agent 能力派发。
   - 成功后用 `record-spawn` 登记本次快照、真实句柄、实际提交参数及可用的宿主回报。
   - 子 Agent 写业务产物和 `stage-result.json`，不写状态。
   - 主线程运行 `validate`，通过后运行 `complete`。
5. 校验失败：`complete` 不写状态；主线程根据错误摘要重试或运行 `fail`。
6. CODE-REVIEW 失败回 TASK-03；测试失败回责任阶段。
7. 完成后由 leader 生成 `workflow-summary.md`。

## 阶段产物

| 阶段 | 角色 | 正式产物 |
|---|---|---|
| SOLO | solo-developer | `01-solo/solo-report.md`、`workflow-summary.md`、`01-solo/stage-result.json` |
| TASK-01 | main | `01-requirement/requirement-report.md` |
| TASK-02 | architect | `02-design/tech-design.md`、`02-design/execution-plan.md`、`02-design/stage-result.json` |
| TASK-03 | developer | `03-code/change-report.md`、条件产物 `03-code/api-docs.md`、`03-code/stage-result.json` |
| CODE-REVIEW | code-reviewer | `03-code/review-report.md`、`03-code/code-review-result.json` |
| TASK-04 | test-engineer | `04-e2e/test-report.md`、`04-e2e/added-cases.md`、`04-e2e/stage-result.json` |
| TASK-05 | knowledge-engineer | `05-knowledge/knowledge-report.md`、全局知识文件、`05-knowledge/stage-result.json` |
| SUMMARY | leader | `workflow-summary.md`、`stage-result.json` |

完整规则以 `assets/stage-contracts.json` 为准。

## 派发

派发前执行：

```bash
python3 "$SKILL_DIR/scripts/role_registry.py" validate
python3 "$SKILL_DIR/scripts/role_registry.py" resolve TASK-02
```

派发消息必须包含：

- `PROJECT_ROOT`、`SKILL_DIR`、`workflow_state_path`。
- 当前阶段、角色 ID、任务卡或任务卡路径。
- 允许写入的目录和文件。
- `stage-result.json` 路径。
- 完成后运行 `workflow.py validate`。
- “不得修改 `workflow-state.json`，不得覆盖其他 Agent 或用户改动”。

只有 `model != "inherit"` 时才传模型，只有 `reasoning_effort != "inherit"` 时才传推理强度。覆盖任一配置时使用隔离上下文。

模型不支持配置的推理档时，优先使用 `model_profiles` 的兼容档位并保留用户指定模型；不要静默换模型。

## 简洁播报

- 主线程在阶段启动后展示登记命令返回的 `notice`：一行说明角色、真实 Agent 或主线程、模型、推理等级及确认依据。
- 配置要求、实际提交和宿主回报分别落盘；只有宿主明确回报的字段才标“已确认”，仅提交参数标“已提交”，继承或缺少依据时如实显示未知。
- 普通进度不重复身份；重试或降级补充一句配置变化与原因。结束简述结果，最终回复不默认附执行配置表。
- TASK-01、SOLO 和内联降级不得宣称已按角色配置切换主线程模型或推理等级。
- 详情按用户查询范围读取 `status`，历史尝试与证据按需使用 `status --details`。完整规则见 `references/execution-reporting.md`。

## 错误分类

| 类型 | 默认处理 |
|---|---|
| `artifact_invalid` | 同角色重试一次，只回传校验错误摘要 |
| `scope_violation` | 立即阻塞 |
| `provider_error` | 记录，按宿主能力重试或切换模型 |
| `model_capability_error` | 保留模型，改用兼容推理档 |
| `test_failed` | 返回 developer |
| `review_rejected` | 返回 developer |
| `user_gate` | 暂停并等待用户 |
| `agent_runtime_error` | 同角色重试一次 |

自动重试上限读取 `stage-contracts.json.max_retries`。

## TASK-01 门禁

- TASK-01 必须由主线程与用户实际交互，不得委托。
- 存在歧义时一次只问一个会影响实现或验收的问题。
- 没有明显歧义时复述目标、范围、排除项和成功标准，并请求确认。
- 用户明确确认后写入需求报告，运行 `workflow.py confirm --stage TASK-01`，再运行 `validate` 和 `complete`。

## 完成与中止

完成：

1. SUMMARY 阶段校验通过并运行 `complete --stage SUMMARY`。
2. 确认 `summary.status = "completed"`。
3. 保留全部产物、状态和 decisions。

中止：

```bash
python3 "$SKILL_DIR/scripts/workflow.py" abort \
  --state "$workflow_state_path" --reason "<原因>"
```

## 不可绕过

- 不直接手改 `workflow-state.json`。
- 不跳过阶段完成前的 `validate`。
- 不让下一阶段在上一阶段完成前开始。
- 不把未运行检查记为通过。
- 不删除已有阶段产物或改写 `decisions[]` 历史。
- 不在未获用户确认时把 `auto` 模式当作需求确认。
