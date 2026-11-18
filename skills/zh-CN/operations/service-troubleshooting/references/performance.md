# Java 运行时性能排查

仅用于性能劣化场景中的 Java 服务。按主技能的证据纪律执行：限制回传量，结论引用可定位的输出。

前提：

- attach 需要与目标 JVM 同用户；容器内进容器执行。权限不足或无法 attach 时报告限制，不擅自换用侵入手段。
- 优先 JDK 自带工具；Arthas 用于 JDK 工具解释不了的问题（方法级耗时、运行时代码核对、调用现场回放）。

按症状选择：

- CPU 高：`top -Hp <pid>` 找热点线程，`printf '%x' <tid>` 转十六进制，`jstack <pid>` 中按 `nid=0x…` 定位栈；或 Arthas `dashboard` → `thread -n 5`。栈落在 GC 线程时转内存分支。
- 接口慢：Arthas `trace 全限定类名 方法 '#cost > 200'` 逐层展开耗时最大的子调用；无 Arthas 时用慢日志、链路追踪或分段计时分层，定位增量最大的一层（应用内、依赖、网络）再深入。
- 内存增长或频繁 GC：`jstat -gcutil <pid> 1000 10` 看回收趋势；`jmap -histo:live <pid> | head -20` 看对象排行；必要时 `jmap -dump:live,format=b,file=<获准路径> <pid>` 离线分析，注意文件大小与磁盘余量。OOM 先从日志确认类型（heap、metaspace、direct memory）再选工具。
- 死锁与线程池：`jstack <pid>` 检查 BLOCKED 线程与 "Found one Java-level deadlock"；Arthas `thread` 自带死锁检测。对比线程总数与池配置，确认是否池耗尽。
- 行为与代码不符：Arthas `sc -d <类名>` 查类来源与加载器，`jad <类名> <方法>` 确认运行时代码版本。

Arthas 约束：

- `watch`/`trace`/`tt` 增加运行时开销：带耗时或条件表达式、限定观察时长、用完 `stop` 退出，不在生产环境无条件常开。
- `ognl` 修改字段或调用写方法改变运行状态，需用户单独授权；未授权不执行。
- heapdump 与栈输出可能含敏感数据，最终证据脱敏，保留线程名、类名与定位行。
