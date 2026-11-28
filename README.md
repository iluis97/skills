# Personal Skills

个人技能库，按语言划分技能包，目前主要维护中文版本（`zh-CN`）。每个语言包可独立安装和使用；其他语言以仓库中实际提供的目录为准，同一技能在不同语言下保持相同的调用名称。

## 文件职责

```text
skills/
└── zh-CN/
    ├── coding/          # 代码实现与文档质量
    │   └── code-like-me/
    ├── workflow/        # 多角色编排与任务推进
    │   ├── agent-team/
    │   ├── role-model-budget/
    │   ├── dev-workflow/
    │   └── restate-goal/
    ├── git/             # 提交与分支等版本控制操作
    │   ├── commit-cleanup/
    │   └── commit-organize/
    ├── operations/      # 运维与故障排查
    │   ├── java-troubleshooting/
    │   ├── log-analysis/
    │   └── ssh/
    ├── productivity/    # 个人效率与辅助工具
    │   ├── axure-reader/
    │   └── work-summary/
    └── _archive/        # 已被取代、不再分发的归档技能
        └── dev-flow/
docs/
├── coding/
├── workflow/
├── git/
├── operations/
└── productivity/
```

- `skills/<语言>/<分类>/<技能名>/SKILL.md`：所选语言的技能执行入口。
- 项目根目录 [AGENTS.md](AGENTS.md)：通用维护要求；维护具体技能前，自行阅读对应的 `docs/<分类>/<技能名>/README.md`。
- 技能包内 `references/`：按条件读取的补充资料，如 `java.md`、`docker.md`、`commands.md`。
- 技能包内 `agents/openai.yaml`：所选语言的技能展示信息和调用策略。
- 技能包内 `scripts/`：可执行脚本；`assets/`：模板、图片等资源，按需创建。
- `docs/<分类>/<技能名>/README.md`：中文使用说明及已有语言包的资料索引。例如，[code-like-me 使用说明](docs/coding/code-like-me/README.md)介绍编码偏好的应用方式，开发场景与改动边界、通用流程、编码偏好、类型与领域建模、读者负担、实现决策的三问、适用规则读取、注释和完成判定集中在技能入口；异常与日志、数据与事务、缓存与并发、资源与性能（含量化结论的基线与波动）四份运行时资料及 Java（含类型建模与 Javadoc）资料由入口按任务直接选择；用户可按[实际场景验收流程](docs/coding/code-like-me/acceptance-workflow.md)选择场景、执行验证并记录 Agent 的实际表现。
- [agent-team 使用说明](docs/workflow/agent-team/README.md)：维护一版宿主无关的角色职责契约（Leader、Designer、Builder、Reviewer），具体调度与执行实现交由各 Agent Harness 完成。
- [role-model-budget 使用说明](docs/workflow/role-model-budget/README.md)：按 small/medium/large 复杂度解析 Leader、Designer、Builder、Reviewer 的模型与思考强度，读取用户配置并在 Claude Code / Codex 能力内应用，缺失时使用内置默认；只输出预算表，不改变角色职责和调度。
- [dev-workflow 使用说明](docs/workflow/dev-workflow/README.md)：按规模组织调研、规划、实现和核验；独立的 [progression.md](skills/zh-CN/workflow/dev-workflow/references/progression.md) 是推进规则来源，使用稳定编号描述条件和动作，供当前人工执行及后续小型规则引擎映射；缺陷修复、重构、功能、只读调查和性能的任务类型方法见 [playbooks.md](skills/zh-CN/workflow/dev-workflow/references/playbooks.md)；真实调用验收见[场景资料](docs/workflow/dev-workflow/acceptance.md)。
- [restate-goal 使用说明](docs/workflow/restate-goal/README.md)：用自己的话复述用户的目标、要解决的问题和满足目标的最小改动，区分事实与推断，确认理解一致后再继续。
- [commit-cleanup 使用说明](docs/git/commit-cleanup/README.md)：整理提交历史，拆分混合提交、合并碎片提交、重排顺序并补全信息，只改组织方式并校验树哈希。
- [commit-organize 使用说明](docs/git/commit-organize/README.md)：把工作区未提交改动按变更单元分组提交，生成符合项目风格的提交信息，直接产出清晰历史；含缺陷修复时失败用例或复现证据先于修复提交。
- [work-summary 使用说明](docs/productivity/work-summary/README.md)：按完整需求整理每日工作记录，默认省略测试内容和未执行事项声明，确认后保存。
- [axure-reader 使用说明](docs/productivity/axure-reader/README.md)：读取 Axure、Axhub 原型链接，逐链接提取页面内容、批注与交互并整理需求。
- [java-troubleshooting 使用说明](docs/operations/java-troubleshooting/README.md)：排查运行中 Java 服务的响应变慢、无响应、内存增长等异常，按宿主机资源、容器限额、JVM、代码逐层归因；资源和性能结论带基线与波动范围；优先 Arthas，不可用时回退 JDK 原生工具。
- [log-analysis 使用说明](docs/operations/log-analysis/README.md)：根据日志排查服务问题，结合代码与近期变更定位原因，以可复核证据支撑结论。
- [ssh 使用说明](docs/operations/ssh/README.md)：验证并连接服务器，连不上时指导完成连接，连接后按用户要求在授权范围内执行远程操作。

每个技能包根目录只保留 `SKILL.md` 文件；其他文件放入包内对应子目录，不创建空目录占位。每个语言包包含执行所需的完整资料和资源，包内引用指向当前语言包中的文件。通用维护约定在根目录，专属维护说明在各技能对应的中文 README，包内不另设 `AGENTS.md`。

## 安装与切换语言

1. 在 `skills/` 下选择实际存在的语言包，目前维护 `zh-CN` 中文目录；其他语言包提供后按相同结构安装。
2. 将所选语言、分类下的完整技能文件夹复制到宿主的技能目录，保持技能文件夹名称不变。例如，将 `skills/zh-CN/coding/code-like-me/` 复制到 `<宿主技能目录>/code-like-me/`。
3. 在新会话中可通过原名称显式调用，例如 `$code-like-me`；是否允许自动触发以该技能的配置为准。技能读取所安装语言包的规则和配套资料。

每个宿主默认只安装同一技能的一种语言。有其他语言包可用时，先核对安装目标并备份已有副本，再用所选语言的完整包更新同一位置，保留已有扩展配置；不要留下两套同名技能或混用两种语言的文件。不同技能可以分别选择语言。

新增技能默认手动触发，设置 `disable-model-invocation: true` 和 `policy.allow_implicit_invocation: false`；用户明确指定其他触发方式时按其要求配置。维护已有技能时保留其触发配置，除非用户明确要求调整，不统一改写。仓库源码与已安装副本独立，仓库变更后需另行同步安装副本。

## 语言版本维护

优先维护中文包，不为凑齐语言目录创建英文占位包。同一技能的不同语言包共用技能名称；不同技能名称唯一，每个语言目录内名称唯一。提供中英文版本时，按分类、技能名和包内相对路径配对，例如：

- `skills/en/coding/code-like-me/SKILL.md` ↔ `skills/zh-CN/coding/code-like-me/SKILL.md`。
- `skills/en/coding/code-like-me/references/java.md` ↔ `skills/zh-CN/coding/code-like-me/references/java.md`。

已有双语版本的内容，修改任一份时在同一批改动中同步另一份，保持含义、规则强度、边界、例外和示例行为一致；新增、删除、重命名时同步配对资料和链接。用户明确要求分阶段验收时，先按指定版本修改，列明待同步项，再在后续阶段完成同步。

已有的两种语言包保持相同的格式、结构和内容，包括 frontmatter、宿主元数据和所需资源；翻译自然语言，保留字段名、技能名和配置值。中文包不额外添加英文来源、阅读用途、技能入口等说明，也不将 frontmatter 中的描述重复放入正文；原文已有的说明照常翻译。

Agent 执行时仅读取已安装语言包的入口及所需的包内补充资料；维护双语内容时按需对照双方。`docs/` 保留使用说明，不另存第三份执行规则。

## 维护检查

修改后人工核对名称、调用配置、语言包完整性、中英文语义、包内链接及文档索引，不添加校验脚本或测试类。宿主实际调用效果在新会话中确认。
