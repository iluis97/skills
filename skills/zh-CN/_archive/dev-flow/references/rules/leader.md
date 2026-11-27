# 汇总规则

## L1 职责

只在 medium/large 流程末尾生成 `workflow-summary.md` 和 `stage-result.json`。最终状态由主线程运行 `workflow.py complete` 写入；small 由 solo-developer 汇总。

## L2 证据

从 `workflow-state.json` 读取阶段和产物路径，只汇总已验证结果。不得硬编码或猜测产物存在。

## L3 完成门禁

实际路由中的必需阶段必须 completed，CODE-REVIEW 必须 passed，TASK-04 的失败和阻塞必须已处理或明确披露。

## L4 不越权

不得修改方案、代码、测试、审查报告、知识条目、其他阶段产物或 `workflow-state.json`。发现问题时返回阻塞，不代写。
