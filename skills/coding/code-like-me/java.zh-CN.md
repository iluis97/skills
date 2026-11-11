# Java 补充规则

以下规则仅应用于 Java；Lombok、MyBatis-Plus 等规则仅在项目已使用对应依赖时生效。

## Lombok 与对象建模

- 用 Lombok 简化普通 Bean、请求/响应、配置对象与枚举；按需选择 getter、setter、构造器、builder 和日志注解。
- 可变 Bean 沿用 `@Data` 风格，只读对象仅开放读取；确认生成的 `equals`、`hashCode`、`toString`
  合适。涉及继承、实体关联或敏感字段时显式控制，避免递归或泄露。
- 构造器注解满足框架实例化要求；`@Builder` 用于改善构建可读性，不要用它替代必填校验，也不要默认用于所有类。
- 注入方式沿用目标模块；无约定且使用 Lombok 时可用 `@RequiredArgsConstructor` 配合 `private final`，不要因此批量替换存量代码。
- 简单稳定的响应转换可用 `static of(...)` 显式逐字段映射；已有统一转换组件时优先沿用。
- 复用实体公共基类字段与表映射约定；仅在父类字段应参与相等性判断时使用 `@EqualsAndHashCode(callSuper = true)`，不要统一套用。

## 枚举

- 枚举的编码与描述存入由构造器初始化的字段，对外使用显式定义的稳定编码。禁止使用 `ordinal()` 作为对外编码。
- 使用 Lombok 时，可用 `@Getter`、`@AllArgsConstructor` 与 `private final` 属性；命名、编码类型、字典注解沿用项目，不要强制
  `Enum` 后缀、`Integer` 或构造器注解。

## 集合、数值与数据访问

- 简单转换可用 Stream，复杂分支或副作用优先用循环；简单可空转换可用 `Optional`，复用的转换可传入 `Function`
  。不要为使用这些写法增加无意义的调用层次。
- 按业务使用 `BigDecimal`，数值比较用 `compareTo`，需同时比较数值与标度才用 `equals`。
- 业务允许重复键时，为 `Collectors.toMap` 提供实现业务冲突策略的合并函数；未提供合并函数时，重复键会抛出异常。不要仅为消除异常而随意保留第一条或最后一条。
- 已使用 MyBatis-Plus 时，可用 `LambdaQueryWrapper` 和 getter 方法引用。
- 使用代理式事务时，确认调用经过代理，且配置的回滚规则覆盖预期异常类型。

## Javadoc

- 类、方法、构造器与字段的 Javadoc 放在声明整个注解块上方；无注解时直接放在声明上方。不要插在注解之间或注解与声明之间。
