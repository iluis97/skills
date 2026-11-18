# workflow-state.json 2.0 规范

`workflow-state.json` 是阶段交接、恢复和审计的唯一持久化状态。所有写入必须通过 `scripts/workflow.py`。

## 文件定位

- `ARTIFACTS_ROOT`：默认 `{PROJECT_ROOT}/artifacts`。
- `artifacts_dir`：`{ARTIFACTS_ROOT}/{TASK_SLUG}`。
- 状态路径：`{artifacts_dir}/workflow-state.json`。
- 生命周期：Phase 0 初始化，流程完成后保留。
- `size_class` 在 Phase 0 前可以为 `null`，运行 `classify` 后固定为 `small`、`medium` 或 `large`。

## 顶层结构

```json
{
  "version": "2.0",
  "contract_version": 2,
  "task_id": "",
  "task_slug": "",
  "run_mode": "auto",
  "host_adapter": "codex",
  "size_class": "medium",
  "current_stage": "TASK-02",
  "last_event": "TASK-02_in_progress",
  "next_target": "architect",
  "last_error": null,
  "last_error_class": null,
  "last_transition": null,
  "workspace_root": "",
  "artifacts_dir": "",
  "created_at": "",
  "updated_at": "",
  "project_config": {},
  "rules_loaded": {},
  "stages": {},
  "decisions": [],
  "summary": {
    "status": "not_started",
    "report_path": null,
    "completed_at": null
  }
}
```

## 阶段对象

每个 `stages.<stage>` 至少包含：

```json
{
  "status": "in_progress",
  "executor": "developer",
  "role_id": "developer",
  "result_path": "03-code/stage-result.json",
  "attempt": 1,
  "retry_count": 0,
  "validation": null,
  "artifact_path": null,
  "artifact_paths": [],
  "started_at": null,
  "finished_at": null,
  "completed_at": null,
  "self_check": null
}
```

可派发阶段还会记录：

```json
{
  "host": "codex",
  "agent_handle": "<handle>",
  "model": "inherit",
  "reasoning_effort": "high",
  "context_mode": "isolated",
  "model_source": "parent",
  "reasoning_effort_source": "role",
  "fallback": false,
  "host_metadata": {
    "fork_turns": "none"
  }
}
```

TASK-01 还记录：

```json
{
  "user_confirmed": true,
  "confirmed_at": "2026-11-18T00:00:00Z",
  "confirmation_note": "<用户确认摘要>"
}
```

## 状态枚举

```text
pending -> in_progress -> completed
pending / in_progress -> failed
pending / in_progress -> blocked
pending / in_progress -> cancelled
pending -> skipped
failed -> in_progress
blocked -> in_progress
```

`passed` 保留兼容读取，新流程使用 `completed`，审查结果放 `review_result`。

## 阶段结果

阶段角色写 `stage-result.json`，不写状态。示例：

```json
{
  "stage": "TASK-03",
  "role_id": "developer",
  "status": "passed",
  "artifacts": [
    "03-code/change-report.md"
  ],
  "files_changed": [
    "/abs/path/index.html"
  ],
  "checks": [
    {
      "name": "node --check script.js",
      "result": "passed",
      "evidence": "exit 0"
    }
  ],
  "api_docs_required": false,
  "risks": [],
  "last_error": null,
  "error_class": null
}
```

完整字段见 `assets/stage-result.schema.json`。

## 状态命令

```bash
python3 "$SKILL_DIR/scripts/workflow.py" init ...
python3 "$SKILL_DIR/scripts/workflow.py" classify --state "$STATE" --size medium --reason "..."
python3 "$SKILL_DIR/scripts/workflow.py" status --state "$STATE"
python3 "$SKILL_DIR/scripts/workflow.py" handoff --state "$STATE" --stage TASK-02
python3 "$SKILL_DIR/scripts/workflow.py" confirm --state "$STATE" --stage TASK-01 --note "..."
python3 "$SKILL_DIR/scripts/workflow.py" record-spawn --state "$STATE" --stage TASK-02 --handle "..." --host codex
python3 "$SKILL_DIR/scripts/workflow.py" validate --state "$STATE" --stage TASK-02
python3 "$SKILL_DIR/scripts/workflow.py" complete --state "$STATE" --stage TASK-02
python3 "$SKILL_DIR/scripts/workflow.py" fail --state "$STATE" --stage TASK-02 --error-class artifact_invalid --error "..."
python3 "$SKILL_DIR/scripts/workflow.py" abort --state "$STATE" --reason "..."
```

## 写入权限

- 主线程：初始化、Phase 0、TASK-01、派发审计、路由。
- 阶段角色：业务产物和 `stage-result.json`。
- `workflow.py`：唯一状态写入者。
- 不可变字段：`version` 升级除外，`task_id`、`task_slug`、`host_adapter`、`created_at` 不修改。
- `decisions[]` 只追加。

## 校验

`workflow.py validate` 检查：

1. 状态版本、阶段枚举、事件与当前阶段一致。
2. 前置阶段已完成，CODE-REVIEW 已通过。
3. 必需产物存在、非空、路径正确。
4. Markdown front matter 和必需章节。
5. 未填写占位符。
6. 阶段结果字段和角色一致。
7. 执行计划 PT 结构、绝对路径白名单、伪代码和验收项。
8. Acceptance 表、实际变更范围和 API 条件产物。
9. 审查报告结论与 `stage-result` 一致。

`complete` 在 `validate` 失败时不写状态。

## 失败分类

- `artifact_invalid`
- `scope_violation`
- `provider_error`
- `model_capability_error`
- `test_failed`
- `review_rejected`
- `user_gate`
- `agent_runtime_error`
- `unknown`

## 中断恢复

- `pending`：从该阶段开始。
- `in_progress`：`stage-result.json` 完整则校验，否则重做。
- `completed/passed`：按 `next_target` 继续。
- `failed`：`retry_count < max_retries` 时重试，否则暂停。
- `blocked`：等待阻塞解除。
- `cancelled`：默认保持中止。

## 禁止

- 手改 `workflow-state.json`。
- 跳过 `validate` 直接 `complete`。
- 修改或删除 `decisions[]` 历史。
- 删除既有阶段产物。
- 将未运行、失败或阻塞记为通过。
