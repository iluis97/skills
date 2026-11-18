# 需求澄清协议

TASK-01 由主线程执行。目标是形成可进入设计阶段的需求报告，而不是直接开始实现。

## 1. 证据分析

先收集足以判断范围的事实：

- 相关模块、入口、调用链和数据结构
- 涉及的接口、消息、任务、配置和数据库
- 现有测试、构建命令和验证入口
- 项目规范中与本需求直接相关的约束
- 用户已明确的目标、排除项和交付条件

复杂检索可以派发一个只读 helper，但必须限制范围和输出长度。澄清对话本身不得委托。

## 2. 提问方式

- 一次只问一个会改变实现方案或验收标准的问题。
- 优先询问业务规则、边界条件、兼容要求和明确排除项。
- 能从代码或项目文档确认的事实自行确认，不把事实问题抛给用户。
- 用户回答后先复述关键结论，再决定是否继续追问。
- 即使需求看起来完整，也必须向用户做一次确认。

无明显歧义时使用确认式提问：

```text
我理解本次范围是：{目标}。
纳入：{范围}。
不包含：{排除项}。
成功标准：{可验证标准}。
请确认是否按此进入技术方案。
```

## 3. 需求报告

用户确认后写入 `{artifacts_dir}/01-requirement/requirement-report.md`，至少包含：

```markdown
---
task_id: {TASK_ID}
stage: TASK-01
author: main
date: {YYYY-MM-DD}
run_mode: {auto/manual}
---

# 需求报告

## 原始需求

## 代码与上下文分析

## 澄清 Q&A

## 收敛结论

## 纳入范围

## 排除范围

## 成功标准

## 影响面与风险

## 待确认问题
```

要求：

- 记录用户实际确认的结论，不把 Agent 的推断写成用户确认。
- 纳入范围和排除范围使用可判断的具体描述。
- 成功标准能够通过代码、测试、命令或人工检查验证。
- 未解决问题若影响方案或验收，不能标记 TASK-01 完成。
- 删除模板中的占位符。

## 4. 完成门禁

只有同时满足以下条件才能完成 TASK-01：

1. 用户已明确确认需求边界。
2. 需求报告包含上述必需章节且无未填写占位符。
3. 成功标准可验证。
4. 影响实现或验收的问题已经解决，或明确列入待确认问题并得到用户接受。

确认后运行：

```bash
python3 "$SKILL_DIR/scripts/workflow.py" confirm \
  --state "$workflow_state_path" --stage TASK-01 \
  --note "<用户确认摘要>"

python3 "$SKILL_DIR/scripts/workflow.py" validate \
  --state "$workflow_state_path" --stage TASK-01

python3 "$SKILL_DIR/scripts/workflow.py" complete \
  --state "$workflow_state_path" --stage TASK-01
```

确认前不得创建 architect Agent，不得开始技术设计或代码修改。不得手动编辑 `workflow-state.json`。
