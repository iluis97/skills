# Personal Skills

个人技能库。

## 技能列表

| 分类 | 技能入口                                                | 能力                            | 使用说明                                |
|------|---------------------------------------------------------|---------------------------------|-----------------------------------------|
| 编码 | [add-doc](skills/coding/add-doc/SKILL.md)               | 在指定范围内完善代码文档与注释  | [说明](docs/coding/add-doc.md)          |
| 编码 | [code-like-me](skills/coding/code-like-me/SKILL.md)     | 遵循项目约定应用个人编码偏好    | [说明](docs/coding/code-like-me.md)     |
| 运维 | [log-analysis](skills/operations/log-analysis/SKILL.md) | 按范围分析日志并提供可定位证据  | [说明](docs/operations/log-analysis.md) |
| 运维 | [ssh](skills/operations/ssh/SKILL.md)                   | 验证 SSH 访问并指导用户配置公钥 | [说明](docs/operations/ssh.md)          |

## 文件职责

- `skills/<分类>/<技能名>/SKILL.md`：默认英文执行入口。
- `SKILL.zh-CN.md`：对应中文版本，用于阅读和维护。
- `java.md`、`docker.md`、`commands.md`：技能包内按条件读取的补充规则；对应中文文件同步维护。
- `agents/openai.yaml`：技能展示信息和 Codex 手动调用策略。
- `docs/`：供人阅读的使用说明，不是执行依赖。

每个技能包都设置 `disable-model-invocation: true`，以及 `policy.allow_implicit_invocation: false`。安装时复制完整文件夹，保留补充资料和元数据。

## 维护检查

修改后人工核对名称、手动配置、中英文语义、包内链接及文档索引，不添加校验脚本或测试类。宿主实际调用效果在新会话中确认。
