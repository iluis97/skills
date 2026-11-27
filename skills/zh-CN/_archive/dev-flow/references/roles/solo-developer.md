# Solo Developer

仅当 `size_class = "small"` 时执行。由主线程内联完成需求理解、简化设计、编码、验证、知识沉淀和总结。

## 启动

1. 从派发消息或主线程上下文读取 `PROJECT_ROOT`、`SKILL_DIR`、`workflow_state_path`。
2. 读取 `{SKILL_DIR}/references/workflow-state-spec.md`。
3. 读取 `workflow-state.json`，强制校验 `size_class = "small"`。
4. 读取：
   - `{artifacts_dir}/01-requirement/requirement-report.md`
   - `{SKILL_DIR}/assets/stage-contracts.json`
   - `{SKILL_DIR}/assets/stage-result.schema.json`
   - `{SKILL_DIR}/references/rules/global.md`
   - `{SKILL_DIR}/references/rules/developer.md`
   - 适用时读取 `lang-golang.md` 和 `sql-standard.md`
5. 不得修改 `workflow-state.json`。

主线程进入本阶段时先通过 `workflow.py record-execution --state "$workflow_state_path" --stage SOLO --mode main_thread` 登记并展示单行 `notice`，不将角色配置的推理等级当成已切换的会话等级。

## 1. 需求理解

读取 Phase 0 需求报告，确认目标、影响文件、成功标准和排除项。small 不重新进入多轮需求澄清；发现范围明显超出 small 时进入升级回退。

## 2. 简化设计

在 `{artifacts_dir}/01-solo/solo-report.md` 写入以下标题：

```markdown
## 需求理解
## 简化设计
## 编码摘要
## 实际改动文件
## 验证命令
## 未运行项
```

简化设计部分必须列出最多 5 个文件的白名单。

如果需要修改白名单外文件、预计超过 5 个文件、涉及公共接口或数据模型变化，立即升级回退。

## 3. 实现

按简化设计逐文件做最小修改。不得扩大范围、格式化无关代码或升级依赖。

## 4. 验证

按项目现有体系运行最窄验证：

- 编译或语法检查
- 静态检查
- 受影响测试
- 安全边界检查

失败先修复。连续失败 2 次或无法在 small 边界内完成时，回滚本次业务代码并返回 `SOLO_overflow`。

## 5. 产物

在 `solo-report.md` 中补充：

- 需求理解
- 简化设计
- 编码摘要
- 实际改动文件
- 验证命令和真实结果
- 未运行项和风险

涉及 HTTP API 新增、修改或删除时，生成 `{artifacts_dir}/01-solo/api-docs.md`，内容与 developer 阶段要求一致。

知识沉淀写入 `{ARTIFACTS_ROOT}/knowledge/{task_slug}.md`，遵循 `{SKILL_DIR}/references/knowledge-capture.md`。没有可复用知识时在报告中说明。

## 6. 最终总结

生成 `{artifacts_dir}/workflow-summary.md`，至少包含：

- 任务
- 阶段产物
- 代码变更
- 代码审查（SOLO 明确说明未启用独立审查）
- 测试
- 知识沉淀
- 风险

在阶段产物中链接任务的 `workflow-state.json` 供按需追溯，不在最终对话默认附执行配置表。

## 7. 阶段结果

成功时写入 `{artifacts_dir}/01-solo/stage-result.json`：

```json
{
  "stage": "SOLO",
  "role_id": "solo-developer",
  "status": "passed",
  "artifacts": [
    "01-solo/solo-report.md",
    "workflow-summary.md"
  ],
  "checks": [
    {
      "name": "solo verification",
      "result": "passed",
      "evidence": "<实际命令和结果>"
    }
  ],
  "risks": [],
  "last_error": null,
  "error_class": null
}
```

有全局知识文件时，把其绝对路径加入 `artifacts`。涉及 HTTP API 变化时设置 `api_docs_required=true`，并把 `01-solo/api-docs.md` 加入 `artifacts`。

然后运行：

```bash
python3 "$SKILL_DIR/scripts/workflow.py" validate \
  --state "$workflow_state_path" --stage SOLO
```

升级回退时写 `status=failed`、`error_class=scope_violation`、`last_error`，保留诊断产物，不自行改状态。

## 返回

```text
event: workflow_completed | SOLO_overflow
stage: SOLO
status: passed | failed
next_target: main
artifact_paths:
  - 01-solo/solo-report.md
  - 01-solo/stage-result.json
  - workflow-summary.md
checks: <验证真实结果>
risks: <未运行项、风险或回退原因>
```

## 边界

只处理 small 任务。不得启动 medium/large 流程，不得修改白名单外文件，不得修改状态，不得跳过验证或将未运行项写成通过。
