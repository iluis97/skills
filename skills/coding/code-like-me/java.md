# Java Coding Rules

Apply these rules only to Java. Rules for Lombok, MyBatis-Plus, and similar dependencies apply only when the project
already uses them.

## Lombok and Object Modeling

- Use Lombok to simplify ordinary beans, request/response and configuration objects, and enums. Select getter, setter,
  constructor, builder, and logging annotations as needed.
- Follow the `@Data` style for mutable beans; expose only read access for read-only objects. Check generated `equals`,
  `hashCode`, and `toString`; explicitly control inheritance, entity associations, and sensitive fields to prevent
  recursion or disclosure.
- Constructor annotations must meet framework instantiation requirements. Use `@Builder` only when it improves
  construction readability, not as a substitute for required-field validation or a default for every class.
- Follow the module's injection style; without an existing convention and when Lombok is used, consider
  `@RequiredArgsConstructor` with `private final`. Do not replace injection styles throughout existing code.
- Simple, stable response conversions may use `static of(...)` with explicit field mappings. Prefer an existing shared
  conversion component when available.
- Reuse common entity base fields and table mapping conventions. Before using `@EqualsAndHashCode(callSuper = true)`,
  confirm superclass fields belong in equality checks; do not apply it universally.

## Enums

- Store enum codes and descriptions in fields initialized by constructors. Never use `ordinal()` for external codes.
- When Lombok is used, consider `@Getter`, `@AllArgsConstructor`, and `private final` attributes. Follow project naming,
  code types, and dictionary annotations; do not mandate an `Enum` suffix, `Integer`, or constructor annotations.

## Collections, Numbers, and Data Access

- Use streams for simple conversions; prefer loops for complex branches or side effects. Simple nullable conversions may
  use `Optional`, and reusable conversions may accept a `Function`; avoid meaningless call layers.
- Use `BigDecimal` as required by the domain: compare numeric values with `compareTo`, and use `equals` only when both
  value and scale matter.
- Where duplicate keys are valid, provide a merge function for `Collectors.toMap` implementing the business conflict
  policy. Without a merge function, duplicate keys throw an exception. Do not arbitrarily keep the first or last entry
  merely to suppress the exception.
- Where MyBatis-Plus is already used, consider `LambdaQueryWrapper` and getter method references.
- For proxy-based transactions, verify that calls pass through the proxy and that the configured rollback rules cover
  the intended exception types.

## Javadoc

- Place Javadoc for classes, methods, constructors, and fields above the declaration's entire annotation block, or
  directly above the declaration when there are no annotations. Do not insert it between annotations or between
  annotations and the declaration.
