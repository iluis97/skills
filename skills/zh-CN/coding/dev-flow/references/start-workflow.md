# 启动与编排协议

主线程是唯一 orchestrator。状态写入由 `scripts/workflow.py` 完成，阶段角色只写业务产物和 `stage-result.json`。

## 路径

- `PROJECT_ROOT`：用户当前工作目录。
- `SKILL_DIR`：已安装技能包根目录。
- `ARTIFACTS_ROOT`：默认 `{PROJECT_ROOT}/artifacts`。
- `artifacts_dir`：`{ARTIFACTS_ROOT}/{TASK_SLUG}`。
- `workflow_state_path`：`{artifacts_dir}/workflow-state.json`。

## Step 0 读取配置

读取：

1. `assets/devflow.defaults.yaml`
2. `assets/roles.json`
3. `assets/stage-contracts.json`
4. `references/workflow-state-spec.md`
5. `references/stage-contracts.md`
6. `references/rules/global.md`
7. `references/host-adapters.md`
8. 当前宿主适配器

检查仓库根、分支、工作区状态和项目指令。不要切换项目，不清理用户改动。

## Step 1 初始化

从需求生成 `TASK_SLUG`，只允许字母、数字、点、下划线和连字符。

```bash
python3 "$SKILL_DIR/scripts/workflow.py" init \
  --workspace "$PROJECT_ROOT" \
  --slug "$TASK_SLUG"
```

已有状态时拒绝覆盖，改用 `status` 或 `resume`。

初始化会创建：

```text
artifacts/{task_slug}/
  01-requirement/
  02-design/
  03-code/
  04-e2e/
  05-knowledge/
  01-solo/
  workflow-state.json
```

## Step 2 Phase 0

主线程直接完成：

1. 解析需求标题、目标、已知约束和用户指定范围。
2. 扫描相关代码、接口、数据模型、文档、构建命令和测试入口。
3. 判定 `size_class`：
   - `small`：单模块，预计不超过 3 个文件，无接口、数据模型或架构影响。
   - `medium`：跨模块，或预计约 4–10 个文件，存在局部接口或行为变化。
   - `large`：更大范围，或涉及公共接口、数据模型、迁移、架构、高风险发布。
4. 将 Phase 0 结论写入：
   - `small`：`01-requirement/requirement-report.md`
   - `medium/large`：`01-requirement/phase0-scan.md`
5. Phase 0 完成后记录规模判定：

```bash
python3 "$SKILL_DIR/scripts/workflow.py" classify \
  --state "$workflow_state_path" \
  --size "$SIZE_CLASS" \
  --reason "<判定依据>"
```

范围发生变化时用新的任务重新初始化，不静默改写历史。

## Step 3 路由

- `small`：进入 SOLO。
- `medium/large`：进入 TASK-01。
- 用户明确要求先确认方案时，在 TASK-02 或 TASK-03 前暂停。

## Step 4 TASK-01 需求门禁

1. 主线程读取 `references/requirement-clarification.md`。
2. 可派发一个只读调研 helper，但需求对话必须由主线程完成。
3. 存在歧义时一次只问一个具体问题。
4. 无明显歧义时复述目标、纳入、排除和成功标准，并请求确认。
5. 用户明确确认后写入需求报告。
6. 记录用户确认：

```bash
python3 "$SKILL_DIR/scripts/workflow.py" confirm \
  --state "$workflow_state_path" --stage TASK-01 \
  --note "<用户确认摘要>"
```

7. 运行：

```bash
python3 "$SKILL_DIR/scripts/workflow.py" validate \
  --state "$workflow_state_path" --stage TASK-01

python3 "$SKILL_DIR/scripts/workflow.py" complete \
  --state "$workflow_state_path" --stage TASK-01
```

未记录用户确认或未通过 TASK-01 校验时不得派发 architect。

## Step 5 阶段派发

### 5.1 校验注册表

```bash
python3 "$SKILL_DIR/scripts/role_registry.py" validate
python3 "$SKILL_DIR/scripts/role_registry.py" resolve TASK-02
```

### 5.2 生成任务卡

```bash
python3 "$SKILL_DIR/scripts/workflow.py" handoff \
  --state "$workflow_state_path" \
  --stage TASK-02
```

任务卡只包含当前阶段必要信息和写入边界。优先直接使用任务卡作为派发消息主体。

### 5.3 派发

1. 使用宿主原生子 Agent 能力。
2. `context_mode = isolated` 时使用隔离上下文。
3. 只有非 `inherit` 的模型或推理强度才传覆盖参数。
4. 派发消息必须包含：
   - `PROJECT_ROOT`、`SKILL_DIR`、`workflow_state_path`
   - 当前阶段、角色 ID、任务卡
   - 允许写入的目录和文件
   - `stage-result.json` 路径
   - “不得修改 workflow-state.json”
   - 完成后运行 `validate`

### 5.4 登记真实句柄

```bash
python3 "$SKILL_DIR/scripts/workflow.py" record-spawn \
  --state "$workflow_state_path" \
  --stage TASK-02 \
  --handle "<agent-handle>" \
  --host codex
```

只有宿主真实返回句柄后才登记。

### 5.5 阶段角色工作

角色必须：

1. 读取 `handoff` 任务卡和角色提示。
2. 只写自己阶段目录、任务卡允许的代码文件。
3. 写必需业务产物。
4. 写 `stage-result.json`，格式见 `assets/stage-result.schema.json`。
5. 运行：

```bash
python3 "$SKILL_DIR/scripts/workflow.py" validate \
  --state "$workflow_state_path" --stage "$STAGE"
```

角色不得修改 `workflow-state.json`，不得修改其他阶段产物。

### 5.6 主线程完成阶段

```bash
python3 "$SKILL_DIR/scripts/workflow.py" complete \
  --state "$workflow_state_path" --stage "$STAGE"
```

- 校验失败时不写状态，返回结构化错误。
- 校验通过后脚本原子更新状态、事件、路由和 decisions。

## Step 6 失败与重试

### 产物或范围失败

```bash
python3 "$SKILL_DIR/scripts/workflow.py" fail \
  --state "$workflow_state_path" --stage "$STAGE" \
  --error-class artifact_invalid \
  --error "<压缩后的校验错误>"
```

错误类型：

- `artifact_invalid`
- `scope_violation`
- `provider_error`
- `model_capability_error`
- `test_failed`
- `review_rejected`
- `user_gate`
- `agent_runtime_error`
- `unknown`

### 模型不兼容

先检查：

```bash
python3 "$SKILL_DIR/scripts/role_registry.py" check-model \
  --model "<model>" --reasoning-effort "<effort>"
```

存在兼容 fallback 时保留模型、调整推理档。显式指定的推理档不受支持时停止并向用户报告。

### 子 Agent 不可用

只有工具不存在或明确返回 unavailable/not found 时，才允许主线程内联执行，并记录：

```json
{
  "kind": "agent_spawn_unavailable",
  "stage": "TASK-02",
  "role_id": "architect",
  "reason": "<实际错误>"
}
```

主线程内联执行仍需遵守当前阶段角色提示和全部校验。

## Step 7 恢复

`$dev-flow resume <TASK_SLUG>`：

1. 读取最新状态。
2. 运行 `status`。
3. 按以下规则恢复：
   - `pending`：从该阶段开始。
   - `in_progress`：检查 `stage-result.json`，有则校验，无则重新派发。
   - `completed/passed`：按 `next_target` 继续。
   - `failed`：`retry_count < max_retries` 时重试，否则暂停报告。
   - `blocked`：等待阻塞解除。
   - `cancelled`：默认保持中止；用户明确要求继续时重新初始化或记录恢复决策。
4. 保留现有产物和不可变字段。

## Step 8 状态

```bash
python3 "$SKILL_DIR/scripts/workflow.py" status \
  --state "$workflow_state_path"
```

只读汇总当前阶段、角色、模型、推理强度、事件、下一目标、产物存在性、失败次数、错误和 summary。

## Step 9 完成

1. SUMMARY 角色写 `workflow-summary.md` 和 `stage-result.json`。
2. 运行：

```bash
python3 "$SKILL_DIR/scripts/workflow.py" validate \
  --state "$workflow_state_path" --stage SUMMARY

python3 "$SKILL_DIR/scripts/workflow.py" complete \
  --state "$workflow_state_path" --stage SUMMARY
```

3. 确认 `summary.status = "completed"`、`last_event = "workflow_completed"`。
4. 保留全部中间产物和状态。

## Step 10 中止

```bash
python3 "$SKILL_DIR/scripts/workflow.py" abort \
  --state "$workflow_state_path" \
  --stage TASK-03 \
  --reason "<原因>"
```

中止会取消可控制子 Agent、标记当前阶段 `cancelled`、写入 `workflow_aborted` 并保留产物。
