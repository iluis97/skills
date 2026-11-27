# JVM 诊断工具参考

仅在进入 JVM 层排查时阅读。按主技能确定的表现特征选择命令，不逐项执行全量检查。

## 工具选择

- **有 Arthas → 优先使用**：非侵入挂载，命令覆盖完整。Docker 内经 `docker exec` 进入容器后运行 `java -jar arthas-boot.jar` 选择目标 JVM 进程；宿主机部署直接执行。多容器、多进程时先确认目标，不猜。
- **Arthas 不可用 → 改用 JDK 原生工具**：宿主机直接执行，Docker 内经 `docker exec` 执行；不为排查主动安装 Arthas。

## 表现 → 命令映射

按表现选择对应方向与命令，不逐行跑完全部：

| 表现特征 | 方向 | Arthas（优先） | JDK 原生（回退） |
| :--- | :--- | :--- | :--- |
| 全部请求变慢、CPU 高 | 热点线程/方法 | `thread -n` 找高 CPU 线程；`profiler start` 后 `profiler stop --format html` 生成火焰图 | `top -H -p <pid>` 找线程，线程 id 转十六进制后对照 `jstack <pid>` |
| 全部请求变慢、CPU 低 | 锁等待/阻塞 | `thread --state BLOCKED`；`thread -b` 查死锁 | `jstack <pid>` 多次采样比对 BLOCKED/WAITING |
| 间歇性停顿 | GC 停顿 | `dashboard` 看 GC 次数与耗时；结合 `memory` 看堆压力 | `jstat -gcutil <pid> 1000` 持续观察；核对已开启的 GC 日志 |
| 单接口/单方法慢 | 方法分段耗时 | `trace <类名> <方法名>` 逐层定位耗时段；`watch` 观察入参与返回值 | 无直接等价；可申请挂 async-profiler（需授权） |
| 内存持续增长 | 堆与对象分布 | `memory` 看各分区用量；`heapdump /tmp/heap.hprof` 导出快照 | `jmap -histo <pid>` 看对象分布；`jcmd <pid> GC.heap_dump /tmp/heap.hprof` 导出 |
| 线程数异常增长 | 线程状态分布 | `thread` 查看所有线程；`thread -n` 与状态统计 | `jcmd <pid> Thread.print` 多次采样比对 |

## Docker 环境补充

宿主机资源充足但容器内服务仍异常时，先核对容器限额再进 JVM 层：

```bash
# 实时资源用量
docker stats <container>

# CPU throttling（值持续非零说明被限流）
cat /sys/fs/cgroup/cpu/cpu.stat | grep throttled

# 内存 limit
docker inspect <container> --format '{{.HostConfig.Memory}}'
```

JVM 对容器 CPU 核数的感知：JDK 8u191 之前默认以宿主机核数计算线程池和 GC 线程数，可能导致资源争抢；核对 JVM 版本与 `-XX:ActiveProcessorCount` 配置。

## 生产安全

- `trace`/`watch`/`profiler` 有运行时开销：短时观察，用完执行 `stop`，不在高峰期长时间挂载。
- `heapdump` 是全量堆快照：先确认磁盘余量与用户授权，导出期间有短暂 STW。
- Arthas 不改 JVM 参数、不重启服务；诊断结束确认 `stop` 退出，避免残留 Agent。
- JDK 原生工具（`jstack`/`jmap`）同样有短暂停顿风险，高峰期谨慎使用；单次快照适合时间点观察，建议间隔多次采样提高命中率。
