# 日志排查命令速查

面向人的命令速查，覆盖日志查询、过滤、统计与常见来源。**不属于技能执行规则**，Agent 不读取本文件。

约定：`<...>` 是需要替换的占位符；时间一律用绝对时间并确认时区；除明确标注外，命令都只读。

## 0. 先看规模

```bash
# 文件大小
ls -lh <file>

# 行数
wc -l <file>

# 候选文件数量
find <dir> -name '<pattern>' | wc -l

# 最新的几个文件
ls -lt <dir> | head
```

大文件或目录很多时先做这一步，再决定要不要加时间窗和范围限制。

## 1. 定位与上下文

```bash
# 字面量匹配（关键词含 . [ ] ( ) 等正则元字符时必须加 -F）
grep -n -F 'Error: timeout' <file>

# 忽略大小写
grep -n -i 'timeout' <file>

# 命中行及前 2 行、后 5 行
grep -n -A 5 -B 2 -F 'NullPointerException' <file>

# 最多取前 20 条（大文件先看样本）
grep -m 20 -F 'ERROR' <file>

# 只列出命中的文件名
grep -r -l -F 'OutOfMemoryError' <dir>

# 限定文件类型
grep -r -F 'ERROR' --include='*.log' <dir>
```

## 2. 过滤与组合

```bash
# 排除噪音后只看错误
grep -v -F 'healthcheck' <file> | grep -F 'ERROR'

# 多个关键词任一命中（OR）
grep -F -e 'ERROR' -e 'WARN' -e 'Exception' <file>

# 两个条件同时命中（AND）
grep -F 'order-123' <file> | grep -F 'timeout'

# 模式以 - 开头时必须用 -e
grep -e '-Xmx' <file>
```

## 3. 多行事件与堆栈

`grep -A N` 的问题是堆栈长度不固定：N 太小时事件被截断，N 太大会带进下一条。

```bash
# 粗略方式（已知堆栈长度上限）
grep -A 30 -F 'Exception' <file>

# 按事件边界合并：以时间戳开头为新事件，命中关键字的整块输出
awk '/^[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]/ { keep = ($0 ~ /(ERROR|Exception)/) } keep' <file>

# 从命中行输出到下一条时间戳为止
awk 'BEGIN{show=0} /^[0-9][0-9][0-9][0-9]-/ { if (show) exit } /NullPointerException/ { show=1 } show' <file>
```

Java 堆栈的续行通常以空白、`\tat `、`Caused by:`、`... 23 more` 开头，可按实际格式调整模式。

## 4. 关联 ID 追踪

```bash
# 整词匹配，避免 ID 是别的值的子串时误伤
grep -n -w -F '1f2e3d4c5b6a' <file>

# 常见几种 ID 字段名一起搜
grep -F -e 'traceId=1f2e3d4c5b6a' -e 'requestId=1f2e3d4c5b6a' <file>

# 跨目录批量搜
grep -r -n -w -F '1f2e3d4c5b6a' <dir>
```

## 5. 轮转与压缩日志

```bash
# zgrep 可直接读 .gz，也能读未压缩文件
zgrep -n -F 'ERROR' /var/log/app/app.log.*.gz

# 按顺序合并多个文件后再过滤
zcat app.log.2.gz app.log.1.gz | grep -F 'ERROR'

# 近两天变更过的日志文件
find /var/log/app -name 'app.log*' -mtime -2 | sort | xargs -r zgrep -F 'ERROR'

# 当前文件加全部轮转
zgrep -F 'ERROR' app.log app.log.*
```

## 6. 时间窗过滤

```bash
# 行首时间戳格式固定时，字符串比较即可（前提：同格式、同时区）
awk '$1 >= "2026-11-27T09:00" && $1 < "2026-11-27T10:00"' <file>

# 日期与时间以空格分隔
grep -E '^2026-11-27 (09|10):' <file>

# 精确到分钟
grep -E '^2026-11-27 09:[0-9][0-9]:' <file>
```

跨天或跨时区时不要用字符串前缀截取，先统一成同一格式再比较。

## 7. 统计与聚合

```bash
# 命中总数
grep -c -F 'ERROR' <file>

# Top 20 消息：去掉时间戳前缀后按消息聚合
awk '{ $1=""; $2=""; print }' <file> | sort | uniq -c | sort -rn | head -20

# 按分钟分桶，看趋势和拐点
awk '{ print substr($0, 1, 16) }' <file> | sort | uniq -c

# 按固定列聚合（例如第 7 列是接口名）
awk '{ print $7 }' <file> | sort | uniq -c | sort -rn | head -20

# JSON 行日志：按消息聚合
jq -r 'select(.level=="ERROR") | .message' <file> | sort | uniq -c | sort -rn | head -20

# JSON 行日志：按分钟聚合
jq -r 'select(.level=="ERROR") | ."@timestamp"[0:16]' <file> | sort | uniq -c

# 取某列的数值最大项（例如耗时）
awk '{ print $8 }' <file> | sort -n | tail -10
```

统计口径要写明：过滤条件是什么、覆盖了哪些文件、是否包含轮转。

## 8. systemd（journalctl）

```bash
# 指定时间窗，非交互必须加 --no-pager
journalctl -u <service> --since '2026-11-27 09:00' --until '2026-11-27 10:00' --no-pager

# 只看 err 及以上，最近 200 条
journalctl -u <service> -p err -n 200 --no-pager

# 实时跟随
journalctl -u <service> -f

# 相对时间
journalctl -u <service> --since '30 min ago' --no-pager

# 结构化输出后按优先级过滤
journalctl -u <service> -o json --no-pager | jq -r 'select((.PRIORITY|tonumber) <= 3) | .MESSAGE'
```

非交互执行必须加 `--no-pager`，否则会卡在分页器里。

## 9. 容器日志

```bash
# Docker：固定时间窗
docker logs --since '2026-11-27T09:00:00' --until '2026-11-27T10:00:00' --timestamps <container>

# 最近 200 行（不代表覆盖时间窗）
docker logs --tail 200 -t <container>

# 实时跟随近 10 分钟
docker logs -f --since 10m <container>

# 日志文件实际路径
docker inspect --format '{{.LogPath}}' <container>

# 重启次数、退出码、是否被 OOM 杀
docker inspect --format '{{.RestartCount}} exit={{.State.ExitCode}} oom={{.State.OOMKilled}}' <container>

# k8s：指定时间窗
kubectl logs <pod> --since=1h --timestamps

# k8s：上一个容器实例（重启前的日志）
kubectl logs <pod> -p

# k8s：多容器 Pod 指定容器
kubectl logs <pod> -c <container>

# k8s：按标签取全部副本
kubectl logs -l app=<name> --since=1h --all-containers
```

容器已删除时，历史日志只能从宿主机挂载的日志目录或外部日志系统找；`docker logs` 读的是日志驱动，容器不存在就读不到。

## 10. 性能与大文件

```bash
# C locale 显著提速
LC_ALL=C grep -F 'ERROR' <big-file>

# 只要前 100 条时尽早截断
LC_ALL=C grep -m 100 -F 'ERROR' <big-file>

# 解压加过滤，降低优先级
zcat <big>.gz | nice -n 10 grep -F 'ERROR' | head -50

# 实时观察时才需要行缓冲
tail -f <file> | grep --line-buffered -F 'ERROR'
```

## 11. 兼容性差异

| 项目 | GNU（Linux） | BSD（macOS） | busybox（Alpine 等） |
| :--- | :--- | :--- | :--- |
| `grep -P` | 支持 | 不支持 | 不支持 |
| 正则区间 `{2}` | 支持 | 基本支持 | 支持有限 |
| `sed -i` | `sed -i` | `sed -i ''` | `sed -i` |
| `date -d` | 支持 | 不支持 | 支持有限 |
| `awk` | gawk/mawk | BSD awk | busybox awk，功能少 |
| `zgrep` | 有 | 有 | 可能没有，用 `zcat \| grep` |

跨环境时优先用 POSIX 通用子集：用 `grep -E` 代替 `-P`，避免 `[0-9]{2}` 这类区间写法（改写成 `[0-9][0-9]`）。

## 12. 易错点

- **`grep -A N` 会截断堆栈**：N 是固定行数，多行事件应按起止模式合并。
- **关键词含正则元字符不加 `-F`**：`.` `[` `(` 会被当正则，误报或漏报。
- **`docker logs --tail` 不等于覆盖时间窗**：它只给最后 N 行，不能据此宣称“这段时间没错误”。
- **`journalctl` 不加 `--no-pager`**：脚本或非交互环境会挂住。
- **直接 `grep` 压缩文件**：会提示 binary file matches，必须用 `zgrep`/`zcat`。
- **用展示样本推算总量**：展示可以截断，统计必须覆盖完整范围并注明口径。
- **输出重定向覆盖原日志**：`>` 会清空目标文件，保存结果只用新文件名或临时目录。
- **过滤后当成全量**：排除条件要记录，否则“没找到”只是“在当前过滤条件下没找到”。

## 13. 常用组合

```bash
# 一次请求全链路：先定位
grep -n -w -F '<traceId>' app.log*

# 再看该请求的完整上下文
grep -A 40 -w -F '<traceId>' app.log

# 看它出现在哪些时间点
grep -w -F '<traceId>' app.log | awk '{print substr($0,1,19)}' | sort | uniq -c

# 错误突增：先看每分钟趋势
grep -F 'ERROR' app.log | awk '{print substr($0,1,16)}' | sort | uniq -c

# 再取拐点前后的事件
awk '$1 >= "2026-11-27T09:40" && $1 < "2026-11-27T09:50"' app.log | grep -F 'ERROR'

# 最慢的 20 条请求（最后一列为耗时）
awk '{print $NF, $0}' app.log | sort -n | tail -20
```
