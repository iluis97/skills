# 代码形态示例

示例只说明本技能期望的形态，不替代项目规范、接口契约和相邻实现；语言仅作示意。

## 缺陷修复：根因 + 最小改动

现象：`format_name` 在中间名首尾有空格时产生双空格。

```diff
 def format_name(first, middle, last):
     parts = [first]
     if middle:
-        parts.append(middle)
+        parts.append(middle.strip())
     parts.append(last)
     return " ".join(p for p in parts if p)
```

- 只改产生错误的一行；不重命名函数、不删除相邻未引用的 `legacy_format`、不调整无关格式。
- 在同一入口补回归用例：`("Ada", "  Lovelace  ", "King") -> "Ada Lovelace King"`。
- 交付说明根因、修改点和未覆盖的边界。

## 功能实现：先定数据形状与接口

需求：新增租户订单导出，方案只给字段和权限范围，接口未定。

```text
ExportRequest: tenant_id, date_from, date_to, fields
ExportResult: file_ref, row_count
ExportService.export(request) -> ExportResult
契约：无权限 -> 业务异常；无数据 -> 空结果或空文件，按现有接口约定
```

- 先确认字段、空值、日期范围、权限来源和失败契约，再写导出逻辑。
- 复用项目已有文件、权限和查询组件；不为单一实现新增 `ExporterFactory` 或配置层。
- 真实入口验证正常、无数据、无权限和导出失败路径。

## 性能优化：基线 + 瓶颈路径结构性改造

现象：订单列表按订单逐条查询明细，P95 约 800ms，目标是 200ms。

```text
改动前：for order in orders: detail = repo.find_detail(order.id)
改动后：ids = [o.id for o in orders]; details = repo.find_details(ids); 按 order.id 分组
```

- 先记录基线、运行次数、数据规模和波动范围，再确认瓶颈在 N+1 查询。
- 允许改查询方式和数据结构；范围限于列表查询及必要调用方，不顺手重构无关模块。
- 前后在相同负载、数据和环境下对比；功能回归覆盖无明细、重复键和空结果。
- 报告实际数据、波动和限制；未达标时不声称提升。