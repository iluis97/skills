# Java 运行期排查命令速查

面向人的命令速查，覆盖宿主机资源、容器限额、JVM 与 Arthas。**不属于技能执行规则**，Agent 不读取本文件。

约定：`<...>` 是需要替换的占位符；`<pid>` 为 **Java 进程 pid**（容器内执行时用容器内的 pid）；除标注外均为只读；高风险命令单独标记。

## 0. 先确认环境与进程

```bash
jps -l                                  # 当前用户的 Java 进程
ps -ef | grep -v grep | grep java       # 全部 Java 进程，看启动参数

java -version
cat /proc/<pid>/cmdline | tr '\0' ' '   # 实际启动命令与 JVM 参数
cat /proc/<pid>/limits                  # 进程级 ulimit（句柄、栈、内存）

# 容器内执行时，先确认目标容器与容器内 pid
docker exec -it <container> jps -l
```

判断进程是否还活着、是否在反复重启：

```bash
docker inspect --format '{{.RestartCount}} exit={{.State.ExitCode}} oom={{.State.OOMKilled}} started={{.State.StartedAt}}' <container>
docker ps -a --filter "name=<container>"
```

## 1. 宿主机资源

```bash
# CPU 总体：负载、使用率
uptime
top -b -n 1 | head -20
mpstat -P ALL 1 3

# 单个进程
pidstat -u 1 -p <pid>
pidstat -d 1 -p <pid>                   # 磁盘 IO
pidstat -w 1 -p <pid>                   # 上下文切换

# 内存与 swap
free -m
vmstat 1 5                              # si/so 非零说明在换页

# 磁盘 IO
iostat -x 1 5                           # %util 接近 100、await 高 = IO 瓶颈
df -h
du -sh /var/log/*

# 网络
ss -s
ss -tnp | head -50                      # 连接数与状态分布
netstat -s | grep -iE 'retrans|drop'    # 重传与丢包
sar -n DEV 1 3

# 内核压力（PSI，较新内核）：avg10 高说明资源正被挤占
cat /proc/pressure/cpu /proc/pressure/memory /proc/pressure/io
```

判断要点：**load 高但 CPU 不高**，通常是有进程卡在 IO 或不可中断状态（D 状态），先看 `iostat` 和 `pidstat -d`。

## 2. 容器限额

宿主机资源充足、容器内却慢，优先查限额。

```bash
docker stats --no-stream <container>

# cgroup v1
cat /sys/fs/cgroup/cpu/cpu.stat | grep -E 'nr_throttled|throttled_time'
cat /sys/fs/cgroup/memory/memory.limit_in_bytes
cat /sys/fs/cgroup/memory/memory.usage_in_bytes
cat /sys/fs/cgroup/memory/memory.failcnt

# cgroup v2
cat /sys/fs/cgroup/cpu.stat | grep -E 'nr_throttled|throttled_usec'
cat /sys/fs/cgroup/memory.max /sys/fs/cgroup/memory.current
cat /sys/fs/cgroup/memory.events          # 有 oom_kill 说明曾被 OOM 杀

# 限额配置
docker inspect --format '{{.HostConfig.CpuQuota}} {{.HostConfig.CpuPeriod}} {{.HostConfig.Memory}} {{.HostConfig.MemorySwap}}' <container>
```

`nr_throttled` 持续增长 = 容器被 CPU 限流，此时 JVM 内部怎么看都「不忙」，但响应确实慢。

JVM 视角的核数与内存：

```bash
jcmd <pid> VM.info | grep -iE 'cpu|memory|container'
jcmd <pid> VM.flags | tr ' ' '\n' | grep -iE 'ActiveProcessorCount|MaxHeapSize|UseContainer'
```

## 3. JVM 概况

```bash
jcmd <pid> VM.version
jcmd <pid> VM.flags -all
jcmd <pid> VM.system_properties
jcmd <pid> VM.uptime
jcmd <pid> GC.heap_info                 # 各区容量与使用量
jcmd <pid> help                         # 当前 JVM 支持的全部诊断命令
```

JFR（低开销，推荐先用）：

```bash
jcmd <pid> JFR.start name=diag duration=60s filename=/tmp/diag.jfr settings=profile
jcmd <pid> JFR.dump name=diag filename=/tmp/diag.jfr
jcmd <pid> JFR.stop name=diag
```

## 4. 线程

```bash
# 线程快照；多次采样比单次更有价值
jstack <pid> > /tmp/js.1.txt
sleep 5; jstack <pid> > /tmp/js.2.txt
sleep 5; jstack <pid> > /tmp/js.3.txt

# 状态统计
grep -c 'java.lang.Thread.State: BLOCKED' /tmp/js.1.txt
grep -c 'java.lang.Thread.State: WAITING' /tmp/js.1.txt
grep -c 'java.lang.Thread.State: RUNNABLE' /tmp/js.1.txt

# 找阻塞源头（-b 直接打印持锁线程与调用栈）
jstack -l <pid> | grep -A 30 'Found one Java-level deadlock'

# 线程总数与命名分布
jcmd <pid> Thread.print | grep '^"' | sed 's/".*//' | head
jcmd <pid> Thread.print | grep -c '^"'
```

CPU 高的线程如何对应到代码：

```bash
top -H -p <pid>                         # 记下高 CPU 的线程 ID（十进制）
printf '%x\n' <tid>                     # 转成十六进制
grep -A 30 'nid=0x<hex>' /tmp/js.1.txt  # 在 jstack 快照里定位
```

容器内注意 pid 命名空间：`top -H` 和 `jstack` 必须在同一个命名空间里执行（都用 `docker exec`），宿主机的 tid 与容器内不对应。

## 5. GC 与内存

```bash
# 每 1 秒输出一次 GC 统计
jstat -gcutil <pid> 1000 10
# 列：S0 S1 E O M CCS YGC YGCT FGC FGCT CGC CGCT GCT
# 重点：FGC 增长快、FGCT 占比高、O 长期接近 100

jstat -gc <pid> 1000 10                 # 各区容量（KB）
jstat -gccapacity <pid>                 # 各代容量与最大容量

# 堆与对象分布
jcmd <pid> GC.class_histogram | head -30
jmap -histo <pid> | head -30            # 注意：-histo:live 会触发 Full GC
```

GC 日志（需启动时开启，不能事后补）：

```bash
# JDK 8
-Xloggc:/var/log/gc.log -XX:+PrintGCDetails -XX:+PrintGCDateStamps
# JDK 9+
-Xlog:gc*:file=/var/log/gc.log:time,uptime,level,tags
```

堆快照：

```bash
jcmd <pid> GC.heap_dump /tmp/heap.hprof     # 会 STW，先确认磁盘余量
jmap -dump:format=b,file=/tmp/heap.hprof <pid>

# 对象数量对比（排查内存持续增长）：间隔一段再取一次
jcmd <pid> GC.class_histogram > /tmp/h1.txt
sleep 300
jcmd <pid> GC.class_histogram > /tmp/h2.txt
diff <(head -20 /tmp/h1.txt) <(head -20 /tmp/h2.txt)
```

## 6. Arthas

优先使用。容器内执行时用 `docker exec -it <container>` 进入后运行，**需与目标 JVM 同用户或 root**。

```bash
docker exec -it <container> sh
java -jar /opt/arthas/arthas-boot.jar     # 列出 JVM，输入序号附加
# 或直接指定
java -jar /opt/arthas/arthas-boot.jar <pid>
```

常用命令：

| 目的 | 命令 |
| :--- | :--- |
| 总览（线程、内存、GC、运行时） | `dashboard` |
| 全部线程 / 最忙的 5 个 | `thread` / `thread -n 5` |
| 阻塞其他线程的源头、死锁 | `thread -b` |
| 指定状态线程 | `thread --state BLOCKED` |
| JVM 与系统属性 | `jvm` / `sysprop` / `sysenv` |
| 内存分区 | `memory` |
| 堆快照 | `heapdump /tmp/heap.hprof` |
| 方法调用链耗时 | `trace <类名> <方法名>` |
| 入参与返回值 | `watch <类名> <方法名> '{params, returnObj}' -x 3` |
| 调用栈来源 | `stack <类名> <方法名>` |
| 方法调用统计（QPS、RT） | `monitor -c 10 <类名> <方法名>` |
| CPU 火焰图 | `profiler start` → `profiler stop --format html` |
| 查找类与已加载方法 | `sc <类名通配>` / `sm <类名> <方法名>` |
| 读取静态字段 | `ognl '@<类全名>@<字段名>'` |

退出与恢复：

```text
stop          # 断开当前会话，增强类会在下次调用时还原
shutdown      # 彻底关闭 Arthas 服务端
```

注意：`trace`/`watch`/`stack`/`monitor`/`profiler` 都有运行时开销，观察完立即 `stop`，不要在高峰期长时间挂着。

## 7. 兼容性差异

| 项目 | JDK 8 | JDK 9+ |
| :--- | :--- | :--- |
| `jcmd` | 有，子命令较少 | 完整，首选入口 |
| `jhsdb` | 无 | 有（替代旧版 `jmap -F`） |
| JFR | 视发行版，可能需商业特性或未开放 | 默认内置 |
| GC 日志参数 | `-Xloggc` + `-XX:+PrintGCDetails` | `-Xlog:gc*` |
| 容器感知 | 8u191 之前不感知 CPU/内存限额 | 默认感知 |

容器镜像常见问题：精简镜像只有 JRE，`jstack`/`jmap`/`jcmd` 可能缺失；此时只能靠 Arthas，或临时挂载带 JDK 的镜像，不在生产上随意安装工具。

## 8. 易错点

- **`jmap -histo:live` 和 heap dump 都会触发停顿**，在高峰期执行会放大故障。
- **单次 `jstack` 看不出问题**：锁竞争和死循环要靠多次采样比对。
- **容器内外 pid/tid 不通用**：`top -H` 得到的 tid 必须在同一命名空间内转 hex 再对 `jstack`。
- **`nr_throttled` 非零不等于一定有问题**：短时突发被限流属正常，要看持续增长与 `throttled_time` 占比。
- **JVM 看到的核数可能不是宿主机核数**：JDK 8u191 之前按宿主机计算，线程池和 GC 线程数会超配。
- **NMT 需要启动参数**：`-XX:NativeMemoryTracking=summary` 不能事后开启，没开就只能看 `/proc/<pid>/status` 和 `pmap`。
- **Arthas 增强过的方法在 `stop` 后才会还原**：诊断完不要直接关终端走人。
- **`profiler` 产物落在容器内**：需要 `docker cp` 取出来，且注意磁盘空间。

## 9. 常用组合

```bash
# CPU 高：找线程 → 转 hex → 对栈
top -H -p <pid>
jstack <pid> > /tmp/js.txt
grep -A 30 "nid=0x$(printf '%x' <tid>)" /tmp/js.txt

# CPU 不高但响应慢：先排除限流与 IO，再看阻塞与 GC
cat /sys/fs/cgroup/cpu.stat | grep throttled
iostat -x 1 3
jstack <pid> | grep -c 'BLOCKED'
jstat -gcutil <pid> 1000 5

# 内存持续增长：看趋势 → 对比对象分布 → 必要时导堆
jcmd <pid> GC.heap_info
jcmd <pid> GC.class_histogram | head -20
jcmd <pid> GC.heap_dump /tmp/heap-$(date +%H%M).hprof

# 间歇性停顿：低开销先抓 JFR
jcmd <pid> JFR.start name=stall duration=120s filename=/tmp/stall.jfr settings=profile
# 结束后用 JDK Mission Control 打开，看 GC 停顿与长线程
```
