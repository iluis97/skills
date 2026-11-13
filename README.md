# Personal Skills

个人技能库。

## 技能列表

| 分类 | 技能入口                                                | 能力                            | 使用说明                                |
|------|---------------------------------------------------------|---------------------------------|-----------------------------------------|
| 编码 | [add-doc](skills/coding/add-doc/SKILL.md)               | 在指定范围内完善代码文档与注释  | [说明](docs/coding/add-doc/README.md)          |
| 编码 | [code-like-me](skills/coding/code-like-me/SKILL.md)     | 遵循项目约定应用个人编码偏好    | [说明](docs/coding/code-like-me/README.md)     |
| 运维 | [log-analysis](skills/operations/log-analysis/SKILL.md) | 按范围分析日志并提供可定位证据  | [说明](docs/operations/log-analysis/README.md) |
| 运维 | [ssh](skills/operations/ssh/SKILL.md)                   | 验证 SSH 访问并指导用户配置公钥 | [说明](docs/operations/ssh/README.md)          |

## 文件职责

- `skills/<分类>/<技能名>/SKILL.md`：面向 Agent 的唯一英文执行入口。
- 技能包内 `AGENTS.md`：按需设置的英文技能维护约定，与执行入口同级。
- 技能包内 `references/`：按条件读取的英文补充资料，如 `java.md`、`docker.md`、`commands.md`。
- 技能包内 `agents/openai.yaml`：技能展示信息和 Codex 手动调用策略。
- 技能包内 `scripts/`：可执行脚本；`assets/`：模板、图片等资源，按需创建。
- `docs/<分类>/<技能名>/README.md`：供人阅读的中文使用说明及资料索引。
- 同一文档目录内 `SKILL.zh-CN.md`、`references/*.zh-CN.md`、可选的 `AGENTS.zh-CN.md`：对应英文文件的中文阅读版，不注册为技能，也不是运行时依赖。

每个技能包根目录只允许 `SKILL.md` 和可选的 `AGENTS.md` 两种文件；其他文件放入包内对应子目录，不创建空目录占位。`skills/` 保留 Agent 执行和维护所需资料，中文阅读版集中在 `docs/`；执行资料中的中文示例和用户提示按需要保留。

每个技能包都设置 `disable-model-invocation: true`，以及 `policy.allow_implicit_invocation: false`。安装时复制完整文件夹，保留补充资料和元数据。

## 双语维护

英文和中文对应版按分类、技能名和包内相对路径配对，例如：

- `skills/coding/code-like-me/SKILL.md` ↔ `docs/coding/code-like-me/SKILL.zh-CN.md`。
- `skills/coding/code-like-me/references/java.md` ↔ `docs/coding/code-like-me/references/java.zh-CN.md`。

已有双语版本的内容，修改任一份时在同一批改动中同步另一份，保持含义、规则强度、边界、例外和示例行为一致；新增、删除、重命名时同步配对资料和链接。用户明确要求分阶段验收时，先按指定版本修改，列明待同步项，再在后续阶段完成同步。无需为仅有单一语言的资料额外建立译本。

Agent 执行技能时读取英文入口及所需的包内补充资料；维护双语文档时才按需对照两份内容。未读取的中文文件不会作为正文占用模型上下文。

## 维护检查

修改后人工核对名称、手动配置、中英文语义、包内链接及文档索引，不添加校验脚本或测试类。宿主实际调用效果在新会话中确认。
