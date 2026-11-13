# Personal Skills

个人技能库。每个技能提供可独立安装和使用的中文、英文语言包，安装时选择语言，调用名称保持一致。

## 技能列表

| 分类 | 技能 | 中文入口 | 英文入口 | 能力 | 使用说明 |
|------|------|----------|----------|------|----------|
| 编码 | add-doc | [中文](skills/zh-CN/coding/add-doc/SKILL.md) | [English](skills/en/coding/add-doc/SKILL.md) | 在指定范围内完善代码文档与注释 | [说明](docs/coding/add-doc/README.md) |
| 编码 | code-like-me | [中文](skills/zh-CN/coding/code-like-me/SKILL.md) | [English](skills/en/coding/code-like-me/SKILL.md) | 遵循项目约定应用个人编码偏好 | [说明](docs/coding/code-like-me/README.md) |
| 运维 | log-analysis | [中文](skills/zh-CN/operations/log-analysis/SKILL.md) | [English](skills/en/operations/log-analysis/SKILL.md) | 按范围分析日志并提供可定位证据 | [说明](docs/operations/log-analysis/README.md) |
| 运维 | ssh | [中文](skills/zh-CN/operations/ssh/SKILL.md) | [English](skills/en/operations/ssh/SKILL.md) | 验证 SSH 访问并指导用户配置公钥 | [说明](docs/operations/ssh/README.md) |

## 文件职责

```text
skills/
├── en/
│   ├── coding/
│   │   ├── add-doc/
│   │   └── code-like-me/
│   └── operations/
│       ├── log-analysis/
│       └── ssh/
└── zh-CN/
    ├── coding/
    │   ├── add-doc/
    │   └── code-like-me/
    └── operations/
        ├── log-analysis/
        └── ssh/
docs/
├── coding/
└── operations/
```

- `skills/<语言>/<分类>/<技能名>/SKILL.md`：所选语言的技能执行入口。
- 项目根目录 `AGENTS.md`：通用维护要求及按技能划分的[特定技能维护约定](AGENTS.md#特定技能维护约定)。
- 技能包内 `references/`：按条件读取的补充资料，如 `java.md`、`docker.md`、`commands.md`。
- 技能包内 `agents/openai.yaml`：所选语言的技能展示信息和手动调用策略。
- 技能包内 `scripts/`：可执行脚本；`assets/`：模板、图片等资源，按需创建。
- `docs/<分类>/<技能名>/README.md`：中文使用说明及中英文技能包的资料索引。

每个技能包根目录只保留 `SKILL.md` 文件；其他文件放入包内对应子目录，不创建空目录占位。每个语言包包含执行所需的完整资料和资源，包内引用指向当前语言包中的文件。维护约定集中在项目根目录，包内不另设 `AGENTS.md`。

## 安装与切换语言

1. 选择语言：`zh-CN` 为中文，`en` 为英文。
2. 将所选语言、分类下的完整技能文件夹复制到宿主的技能目录，保持技能文件夹名称不变。例如，将 `skills/zh-CN/coding/code-like-me/` 复制到 `<宿主技能目录>/code-like-me/`。
3. 在新会话中通过原名称显式调用，例如 `$code-like-me`。安装中文版时执行中文规则，安装英文版时执行英文规则。

每个宿主默认只安装同一技能的一种语言。切换语言时，先核对安装目标并备份已有副本，再用另一语言的完整包更新同一位置，保留已有扩展配置；不要留下两套同名技能或混用两种语言的文件。不同技能可以分别选择语言。

每个技能包均设置 `disable-model-invocation: true` 和 `policy.allow_implicit_invocation: false`。仓库源码与已安装副本独立，仓库变更后需另行同步安装副本。

## 双语维护

同一技能的中英文包共用技能名称；不同技能名称唯一，每个语言目录内名称唯一。两种语言按分类、技能名和包内相对路径配对，例如：

- `skills/en/coding/code-like-me/SKILL.md` ↔ `skills/zh-CN/coding/code-like-me/SKILL.md`。
- `skills/en/coding/code-like-me/references/java.md` ↔ `skills/zh-CN/coding/code-like-me/references/java.md`。

已有双语版本的内容，修改任一份时在同一批改动中同步另一份，保持含义、规则强度、边界、例外和示例行为一致；新增、删除、重命名时同步配对资料和链接。用户明确要求分阶段验收时，先按指定版本修改，列明待同步项，再在后续阶段完成同步。

两种语言包保持相同的格式、结构和内容，包括 frontmatter、宿主元数据和所需资源；翻译自然语言，保留字段名、技能名和配置值。中文包不额外添加英文来源、阅读用途、技能入口等说明，也不将 frontmatter 中的描述重复放入正文；原文已有的说明照常翻译。

Agent 执行时仅读取已安装语言包的入口及所需的包内补充资料；维护双语内容时按需对照双方。`docs/` 保留使用说明，不另存第三份执行规则。

## 维护检查

修改后人工核对名称、手动配置、语言包完整性、中英文语义、包内链接及文档索引，不添加校验脚本或测试类。宿主实际调用效果在新会话中确认。
