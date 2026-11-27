# 全局规则

适用于主线程和所有阶段角色。

## G1 路径与资产边界

- `PROJECT_ROOT` 是用户当前工作目录。
- `SKILL_DIR` 是已安装技能包根目录。
- 只读取当前技能包内资料和当前项目所需文件。
- 不依赖其他宿主导出的临时工作流目录、仓库源码路径或其他手动技能。

## G2 配置优先

执行前读取 `workflow-state.json`。默认值以 `assets/devflow.defaults.yaml` 为准，角色配置以 `assets/roles.json` 为准，阶段产物、校验器和路由以 `assets/stage-contracts.json` 为准。

## G3 产物本地化

所有阶段产物写入 `{artifacts_dir}`。全局知识写入 `{ARTIFACTS_ROOT}/knowledge/`。禁止跨任务复用目录。

阶段目录所有权：

| 目录 | 写入者 |
|------|--------|
| `01-requirement/` | main |
| `02-design/` | architect |
| `03-code/` | developer、code-reviewer |
| `04-e2e/` | test-engineer |
| `05-knowledge/` | knowledge-engineer |
| `01-solo/` | solo-developer |

TASK-03 需要给后续阶段准备素材时写入 `03-code/*-draft.md` 或 `03-code/*-source.md`。
主线程可在当前阶段目录写入任务卡和 `spawn-request-<dispatch_id>.json` 执行审计文件；阶段角色不得改写这些记录。

每个阶段同时在拥有目录中写入 `stage-result.json` 或契约指定的结果文件，格式遵循 `assets/stage-result.schema.json`。

## G4 模式与确认

- `auto` / `manual` 决定非需求门禁的自动流转。
- TASK-01 的用户确认门禁在两种模式下都必须执行。
- 用户明确要求先看方案时，在指定门禁前暂停。
- 不擅自扩大用户授权范围。

## G5 角色不越权

每个角色只执行自己的阶段职责。上一阶段未完成或产物未校验前，下一阶段不得开始。角色不得修改其他阶段正式产物，也不得修改 `workflow-state.json`。

## G6 状态交接

`workflow-state.json` 是唯一持久化状态。阶段角色只写业务产物和阶段结果；主线程通过 `scripts/workflow.py` 写状态。`decisions[]` 只追加。

## G7 主线程调度

主线程通过 `workflow.py complete/fail` 路由。只有子 Agent 能力不存在或明确 unavailable 时才允许内联降级；模型或推理强度不兼容时先用 `model_profiles` 修正档位，再记录降级。两种降级分别记录。

## G8 产物质量

所有 Markdown 产物包含 YAML front matter，删除模板占位符。阶段完成前必须运行 `workflow.py validate`；未运行、失败和阻塞必须明确区分。

## G9 安全与授权

- 保留用户已有改动。
- 不自动 stash、commit、push、部署或执行未授权外部写操作。
- 不记录完整敏感信息和凭据。
- 不通过修改测试或删除证据掩盖失败。
