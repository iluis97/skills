# 阶段契约说明

`assets/stage-contracts.json` 是阶段产物、校验器、状态字段和路由的机器可读来源。

## 顶层字段

- `version`：契约版本。
- `max_retries`：同一阶段自动重试上限。
- `max_parallel_sub_developers`：执行计划 PT 上限。
- `stages`：按阶段 ID 索引的契约。

## 阶段字段

```json
{
  "role_id": "developer",
  "executor": "developer",
  "result_path": "03-code/stage-result.json",
  "result_required": true,
  "artifacts": [],
  "inputs": [],
  "validators": [],
  "state_paths": {},
  "pass_event": "TASK-03_completed",
  "next_on_pass": "code-reviewer",
  "next_on_fail": "developer",
  "requires_user_confirmation": false
}
```

`requires_user_confirmation=true` 的阶段必须先运行 `workflow.py confirm`，否则 `validate` 和 `complete` 均失败。

### artifacts

```json
{
  "path": "03-code/change-report.md",
  "required": true,
  "conditional": "api_docs_required",
  "markdown": true,
  "min_chars": 400,
  "sections": [
    "实际变更文件",
    "Acceptance"
  ]
}
```

- 相对路径基于 `artifacts_dir`。
- `{artifacts_root}`、`{project_root}`、`{task_slug}` 可用于动态路径。
- `conditional` 当前支持 `api_docs_required`。
- `sections` 按 Markdown 标题中的关键字匹配。

### validators

| 名称 | 作用 |
|---|---|
| `stage_result` | 校验 `stage-result.json` |
| `execution_plan` | 校验 `parallel_tasks` 结构 |
| `acceptance_table` | 校验每个 PT 的 PASS 证据行 |
| `plan_scope` | 校验 `files_changed` 位于白名单并集 |
| `api_conditional` | 校验 API 条件文档 |
| `review_report` | 校验审查结论与 P0/P1 |
| `summary` | 校验 summary 状态和最终报告 |

### state_paths

完成阶段时把契约路径写入阶段对象：

```json
{
  "artifact_path": "03-code/change-report.md",
  "api_docs_path": "03-code/api-docs.md"
}
```

可选文件不存在时不会写入。

## 目录边界

| 目录 | 写入者 |
|---|---|
| `01-requirement/` | main |
| `02-design/` | architect |
| `03-code/` | developer、code-reviewer |
| `04-e2e/` | test-engineer |
| `05-knowledge/` | knowledge-engineer |
| `01-solo/` | solo-developer |
| `{artifacts_root}/knowledge/` | solo-developer、knowledge-engineer |

阶段结果文件写入对应阶段目录。SUMMARY 的阶段结果写入 `artifacts_dir/stage-result.json`。

## 扩展

新增阶段时：

1. 在 `stages` 增加契约。
2. 在 `assets/roles.json` 增加角色映射。
3. 在 `references/roles/` 增加角色提示。
4. 在 `references/rules/` 增加阶段规则。
5. 如需新校验器，在 `scripts/workflow.py` 注册实现并加回归测试。
6. 更新 `STAGE_DEPENDENCIES` 和 routing 文档。

## 回归测试

```bash
python3 -m unittest discover -s scripts/tests -v
```

测试至少覆盖：

- 缺少设计产物
- 报告写错目录
- 文件变更越过计划白名单
- 状态事件和当前阶段不一致
- 模型推理档不兼容
- 无效状态版本被拒绝
