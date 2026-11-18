# service-troubleshooting

## 做什么

按场景排查服务问题：先根据症状归入场景（服务不可用、性能劣化、网络与连通、错误与行为异常、流媒体），再按该场景的决策树逐层验证，日志、运行时诊断（含 Arthas）、网络检测（含 ffmpeg/ffprobe）是场景内选用的手段，结论用可定位证据支撑。排查保持只读优先。

## 什么时候使用

按[安装与切换语言](../../../README.md#安装与切换语言)选择中文或英文技能包，调用名称均为 `$service-troubleshooting`。

通过 `$service-troubleshooting` 显式调用，描述症状及服务来源。服务、环境及症状起始时间需要能够确定；远程来源需已验证的 SSH 访问。

```text
$service-troubleshooting
192.0.2.10 上的 media 服务最近半小时拉流频繁花屏卡顿，排查原因。
```

日志、运行时诊断等细节按场景读取所选语言包内的 `references/` 手册：`performance.md`（Java 运行时与 Arthas）、`network.md`（连通与抓包）、`stream.md`（流媒体分层）、`docker.md`（容器环境）。可查看中文规则：[performance](../../../skills/zh-CN/operations/service-troubleshooting/references/performance.md) · [network](../../../skills/zh-CN/operations/service-troubleshooting/references/network.md) · [stream](../../../skills/zh-CN/operations/service-troubleshooting/references/stream.md) · [docker](../../../skills/zh-CN/operations/service-troubleshooting/references/docker.md)。

## 常见问题

- **和 log-analysis 什么关系？** 各自独立调用。本技能内做快速日志定位与分层判断；需要完整日志纪律（时间窗、轮转文件、统计口径）时，会提示显式调用 `$log-analysis`。
- **会用 Arthas 吗？** Java 服务日志解释不了的问题（CPU 高、偶发慢、死锁、内存）会用 JDK 工具与 Arthas 只读命令；`watch`/`trace` 带条件限时使用，改运行状态的操作需单独授权。
- **视频流卡顿怎么查？** 按链路分层：端口与流到达 → 协议握手（ffprobe）→ 传输方式对比（RTSP UDP/TCP）→ 解码与丢帧（ffmpeg `-v error`），先定位层再谈原因。
- **会重启服务修复吗？** 排查只读优先；重启、改配置属于处理动作，遵守用户已有授权，超出范围再确认。

## 如何判断执行符合预期

- 症状已归入明确场景，排查对象、时间范围与访问来源可复核。
- 每个结论的证据可定位（命令输出位置、文件行号、容器 ID），事实与推断分离。
- 覆盖缺口和未验证分支明确，未发现表述为“在已核验范围内未发现”。

[中文技能](../../../skills/zh-CN/operations/service-troubleshooting/SKILL.md) · [英文技能](../../../skills/en/operations/service-troubleshooting/SKILL.md)
