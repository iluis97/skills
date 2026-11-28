# dev-workflow 维护设计

初版日期：2026-11-19；本次改造：2026-11-20；2026-11-28 补充任务类型方法。

## 目标与本次问题

技能围绕用户目标组织调研、规划、实现和核验。真实成果、必要证据和有效用户决定支撑交付，组织形式服务于目标。当前仅提供中文包，旧 `dev-flow` 和安装副本独立维护。

试用复盘暴露了：规模已明确但组织要求缺少落实；方案参数和验收条款冲突流入实现；未运行混入通过；工程问题转交用户；负责人仅报告差距；记录与现场脱节。部分行为已经违反旧规则，也暴露了规则分散、停止出口不一致、委派约束传递和行为验收不足。

本次改造收束推进语义，明确角色交接、规模基线与证据范围，并保留后续搭建小型规则引擎的依据。本次不实现引擎、宿主适配器、数据库、锁或自动调度。

## 文件职责与权威来源

| 文件 | 维护职责 |
| --- | --- |
| [SKILL.md](../../../skills/zh-CN/workflow/dev-workflow/SKILL.md) | 范围、操作入口、读取时机与主流程摘要 |
| [progression.md](../../../skills/zh-CN/workflow/dev-workflow/references/progression.md) | 推进语义的唯一权威来源：输入含义、事件次序、条件、动作及影响 |
| [scale.md](../../../skills/zh-CN/workflow/dev-workflow/references/scale.md) | 规模来源与调研、规划、组织、验证的工作基线 |
| [playbooks.md](../../../skills/zh-CN/workflow/dev-workflow/references/playbooks.md) | 缺陷修复、重构、功能、只读调查和性能的任务类型方法 |
| [roles.md](../../../skills/zh-CN/workflow/dev-workflow/references/roles.md) | 四种职责、模型与思考强度解析和播报方式 |
| [tasks-and-delegation.md](../../../skills/zh-CN/workflow/dev-workflow/references/tasks-and-delegation.md) | 任务消息、执行者所需资料及成果交接方式 |
| [clarification.md](../../../skills/zh-CN/workflow/dev-workflow/references/clarification.md) | 识别已有决定、工程判断与真实用户取舍的方法 |
| [verification.md](../../../skills/zh-CN/workflow/dev-workflow/references/verification.md) | 目标关联、检查方法、证据覆盖及感知成果观察 |
| [task-record.md](../../../skills/zh-CN/workflow/dev-workflow/references/task-record.md)及模板 | 唯一记录的组织方式与所需信息 |
| [acceptance.md](acceptance.md) | 面向维护者的规则示例、场景输入、观察要求和验证状态 |

是否允许开始、接受、等待或完成，在 progression.md 中定义。其他文件说明如何完成职责，并以规则编号引用推进条件；改变规模或核验要求时同步检查对应推进规则。playbooks.md 只补充任务类型的具体做法，不新增开始、完成或核验条件；类型方法与其他资料冲突时，以 progression.md 的推进条件为准。本目录不作为运行时依赖，不另存第三份执行规范。

## 推进规则的组织

progression.md 使用 PR-01 至 PR-16 稳定编号，每条规则具有六个明确要素：触发事件、判断依据、成立条件、处理动作、不成立或未知、结果影响。编号用于追踪与映射，不作为业务任务的固定执行阶段。

规则按事件评估，区分成立、不成立、未知；在工作开始、成果交接、等待及完成等决策处综合适用条件。事件次序说明先处理取消、现场及依据变化，再判断交接和下一步，避免用局部通过覆盖否决条件。

当前输入可以用简短文本表达。后续引擎实现时，可将这些概念映射为明确字段与操作接口；应先确定输入契约及可信来源，再实现条件判断。新增机器格式须与本文件所链接的规则一致，不能因便于解析改变原有授权和质量要求。

## 判断、推进与运行能力的边界

| 层面 | 负责内容 | 所需依据 |
| --- | --- | --- |
| 负责人和各角色 | 理解目标、判断质量与证据充分性、分类问题、分析变更影响、选择工作 | 原始要求、实际成果、工具观察及专业判断 |
| 推进规则及未来引擎 | 基于有依据的输入判断允许动作、必要处理和受影响工作 | 各规则明确的输入及条件，未知保持未知 |
| 宿主或项目能力 | 派发、查询、取消、实际读写、权限及必要的冲突和幂等保障 | 真实调用及返回、现场和外部结果 |

规则通过不证明成果真实或操作已完成，记录状态也不提供锁和恢复保障。后续引擎应能关联条件依据和允许动作，但成果质量仍需观察和判断；操作结果不明时查证，不能盲目重放。

## 组织与成本控制

保留 owner、planner、builder、verifier 四种职责，实际人数由任务需要及能力决定。用户说明规模是组织输入，中等任务的实际规划与核验安排可被追踪；复用已有充分成果时记录来源和复核依据。

轻量任务减少独立产物与交接，仍保留真实核对和必要独立核验；常规及复杂任务通过稳定目标标识连接方案、成果和证据。按关键事件同步一个任务记录，方案、截图和日志按需引用，不逐操作新增文件。

角色模型配置继续使用 [roles.json](../../../skills/zh-CN/workflow/dev-workflow/assets/roles.json)，保留字段优先级、直接委派者继承及配置事实分层。配置缺口依赖真实宿主处理，不能通过改角色名称或口头声明补足。

技能包不内置语言或数据库专项，也不主动调用其他手动技能。`grilling` 作为可选能力按用户显式授权衔接；项目另有必需技能时按对应要求落实。

## 验证与后续建设

先核对规则结构、语义、引用和文件职责，再按 acceptance.md 的原始输入进行实际场景执行，最后在安装后的新会话观察完整宿主行为。场景推演不能冒充真实运行，真实运行也只支持已观察的配置和场景。

每批修改后用对应场景检查，并关注是否仍有可执行工作却停下、未运行误标通过、工程缺陷转交用户、旧结果覆盖新依据等行为。代码或引擎建设应以实际缺口和具体收益为前提。当前阶段和未验证内容见 [roadmap.md](roadmap.md)。

## 设计来源

初版借鉴 CrewAI 的任务优先、显式上下文、按需委派、结果反馈及依赖处理思路，不依赖 CrewAI 运行时，不照搬角色履历、字数门槛或框架 API。

来源：[CrewAI skills 仓库](https://github.com/crewAIInc/skills)、[design-agent](https://github.com/crewAIInc/skills/blob/main/skills/design-agent/SKILL.md)、[design-task](https://github.com/crewAIInc/skills/blob/main/skills/design-task/SKILL.md)、[build-flow](https://github.com/crewAIInc/skills/blob/main/skills/build-flow/SKILL.md)；CrewAI v1.15.43 的 [Tasks 与 Guardrails](https://docs.crewai.com/v1.15.43/en/concepts/tasks.md)、[Flows](https://docs.crewai.com/v1.15.43/en/concepts/flows.md) 及 [Processes](https://docs.crewai.com/v1.15.43/en/concepts/processes.md)。这些是设计资料，不是技能运行时依赖。
