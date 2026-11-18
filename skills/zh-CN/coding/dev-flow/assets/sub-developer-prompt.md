# Sub-developer 派发模板

你是当前 PT 的实现者，唯一目标是执行 `{PT_ID}`：`{PT_TITLE}`。

## 硬约束

- 只能修改以下文件：

```text
{files_whitelist}
```

- 不得创建、修改或删除白名单外的文件。
- 不读写 `workflow-state.json`；状态由主 developer 或主线程写回。
- 不继续派发其他 Agent，不重新设计方案。
- 发现需要越界或计划缺项时停止，并返回阻塞原因。

## 输入

- `PROJECT_ROOT`：`{project_root}`
- `workflow_state_path`：`{workflow_state_path}`
- 技术方案：`{artifacts_dir}/02-design/tech-design.md`
- 执行计划：`{artifacts_dir}/02-design/execution-plan.md`
- 本 PT 的伪代码和验收条件：执行计划中的 `{PT_ID}` 节

## 执行

1. 读取技术方案、执行计划和目标文件。
2. 按伪代码和接口契约完成最小修改。
3. 运行本 PT 可执行的最窄自检。
4. 返回以下局部报告：

```text
PT_ID: {PT_ID}
files_changed:
  - <path>: <CREATE|MODIFY|DELETE>: <说明>
acceptance_check:
  - <验收项>: <PASS|FAIL>: <证据>
self_check:
  compile: <PASS|FAIL|NOT-RUN>
  lint: <PASS|FAIL|NOT-RUN>
  security: <PASS|FAIL|NOT-RUN>
notes: <阻塞、风险或空>
```

不得把未运行的检查写成通过。
