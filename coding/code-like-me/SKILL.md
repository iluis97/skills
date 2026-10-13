---
name: code-like-me
description: Apply personal coding preferences when implementing, modifying, or refactoring code. Emphasize clear responsibilities, readable main flows, composition, and reuse while following the target project's conventions. Includes Java-specific guidance.
---

# code-like-me

## Goal

Think and organize code like me: keep responsibilities clear, names intuitive, and reuse existing abstractions and tools so code remains easy to read, modify, and extend.

Complete the requested implementation and necessary verification; when asked only for analysis or advice, stay within that scope.

## 1. Rule Priority and Scope

- Priority: explicit task requirements → project conventions → well-maintained neighboring implementations in the same module → this skill's preferences. Always preserve correctness and interface compatibility.
- Apply general rules idiomatically in all languages. Apply a language section in addition only when using that language; follow project conventions for languages not listed.
- Follow local conventions in existing projects; design new modules for their requirements rather than copying reference package names, frameworks, or domain models.
- Infer personal habits from multiple consistent implementations, not isolated cases, generated code, or other authors' code. Quality rules are constraints, not claims that all historical code satisfies them.
- Preserve the user's changes and modify only necessary files. Do not expand scope, format the entire project, upgrade dependencies, or refactor unrelated modules merely to unify style.

## 2. Workflow

1. **Define scope**: Identify requirements, interfaces, compatibility constraints, and existing changes. Ask only when missing information affects business behavior and cannot be resolved from context.
2. **Read context**: Inspect project instructions, build and language versions, structure, relevant callers, implementations, and tests. When available, sample two or three similar implementations in the same module to confirm conventions relevant to the task; scale exploration to the change. Syntax and APIs must support the target version.
3. **Choose an implementation**: Reuse types, interfaces, and utilities before adding abstractions. Identify stable steps and variation points in complex flows; implement simple requirements directly.
4. **Make changes**: Organize logic by responsibility, keep methods or functions short and semantically complete, and implement boundary validation and failure handling alongside the main logic.
5. **Verify and review**: Choose compilation, static checks, existing tests, or focused new tests according to impact, covering branches, states, and boundaries. Review the diff using the final checklist before delivery.

## 3. General Coding Rules

### Design Principles and Patterns

- **Responsibilities and contracts**: Apply SOLID and the Law of Demeter to keep responsibilities clear, interfaces focused, and coupling low. Do not tighten interface input conditions or silently change return, exception, or side-effect semantics. Follow the project's injection approach for container-managed dependencies.
- **Reuse and abstraction**: Prefer existing components and extension mechanisms, composition, and delegation. Use inheritance for genuine substitutability or stable template flows. Introduce patterns or abstractions for identifiable variation, extension, or isolation needs; keep simple logic direct and avoid layers whose maintenance cost outweighs their benefit.
- **Component collaboration**: In complex flows, check dependency direction, resource ownership, lifecycle, ordering, concurrency, and failure propagation. Verify that substitution and extension preserve contracts.

### Naming and Logic Organization

- Names of types, methods, functions, and variables should express domain concepts and purpose. Follow the project's English naming, abbreviations, and type suffixes.
- Method or function names should identify actions and objects; follow project boolean naming conventions. Distinguish queries, conversions, validation, and execution; names must not conceal writes or external calls.
- Main flows should show the steps, with checks and conversions extracted into meaningful methods or functions. Keep coherent local logic together rather than creating many one-line wrappers.
- Use early returns for preconditions, no-op cases, and failure branches to reduce nesting, while preserving return contracts.
- Put repeated business rules in their owning domain or services. Reserve utility modules for stateless capabilities shared across domains.
- Use constants, enums, or idiomatic language types for meaningful fixed values; do not mechanically extract literals that occur once and are already clear.

### Data and State Modeling

- Data objects hold data and necessary local behavior; services orchestrate business logic. Follow layering conventions for entities and external contracts.
- Model finite, stable types, states, and operations centrally to reduce scattered values and repeated branches. Put reusable code lookup, description retrieval, and predicates in their owning types or conversion components.
- Define return, default, or exception contracts for null and unknown codes; do not silently treat them as valid states. Use stable codes in interfaces, persistence, and messages; do not arbitrarily change published codes.
- State types may encapsulate simple behavior tied to their attributes. Put complex behavior involving services, databases, or external calls in strategies or business components.

### Validation, Exceptions, and Logging

- Validate formats and required fields at entry points, and existence, permissions, states, and business constraints in services. Follow established boundaries and avoid duplication.
- Reuse validation tools, business exceptions, and error codes. Explain the business cause without exposing stack traces or internal details to callers.
- Catch exceptions only to recover, add context, or translate their semantics; otherwise use centralized handling. Do not hide failures behind empty collections, null values, or success results; handle permitted absence according to the contract.
- Follow logging frameworks and levels. Use parameterized logs for key changes, external failures, and diagnostic context; avoid meaningless high-frequency output.
- Retain business identifiers on frequent paths. Check the logging level before serialization or expensive computation. Avoid duplicate exception logs, retain stack traces when logging at the current layer, and omit credentials, tokens, and complete sensitive objects.

### Collections, Conversion, and Data Access

- Prefer existing collection, string, conversion, and data access utilities. Do not add dependencies when the standard library suffices.
- Use clear, idiomatic constructs for filtering, mapping, and grouping; prefer loops for complex branches, side effects, or early termination.
- Define semantics for empty collections, null elements, duplicate keys, and ordering. Use domain-specific conflict policies when merging data rather than arbitrarily retaining one entry.
- Specify numeric defaults, precision, rounding, and comparison semantics; do not rely on implicit utility behavior or treat zero as missing without domain justification.
- Follow existing conversion and field mapping approaches. Check required fields, types, and meaning; do not let generic copying obscure differences.
- Reuse data access components or service queries and avoid querying each item in a loop. Consider batch size and transaction semantics.
- Define transaction boundaries by business atomicity and honor framework transaction and rollback rules. Follow existing compensation mechanisms for external calls, caches, and messages.
- When maintaining caches after database writes, check and reuse after-commit callbacks to avoid cache changes surviving a rollback. Define behavior without a transaction and when callbacks fail.
- Cache repeated intermediate results on hot paths when they can be reliably invalidated. Prefer existing components and define keys, lifecycle, invalidation after writes, and concurrency semantics; do not copy capacities or TTLs blindly.
- Define the scope and repeat-execution behavior of updates, deletes, and batches. Retain necessary conditions, result checks, and concurrency controls.

### Comments and Formatting

- Follow indentation, imports, line breaks, declaration metadata ordering, and comment language; use existing formatting tools.
- Chinese business comments should explain intent, constraints, algorithm steps, and tradeoffs, not translate code line by line. Document actual parameters, returns, and exceptions for public capabilities, complex methods or functions, and key fields as the project requires.
- Place documentation comments where the language and documentation tools require, and local explanations near the implementation. Update comments when behavior changes; do not invent authors, dates, performance guarantees, or unimplemented capabilities.

## 4. Language-Specific Rules

### Java

Apply these rules only to Java. Rules for Lombok, MyBatis-Plus, and similar dependencies apply only when the project already uses them.

#### Lombok and Object Modeling

- Use Lombok to simplify ordinary beans, request/response and configuration objects, and enums. Select getter, setter, constructor, builder, and logging annotations as needed.
- Follow the `@Data` style for mutable beans; expose only read access for read-only objects. Check generated `equals`, `hashCode`, and `toString`; explicitly control inheritance, entity associations, and sensitive fields to prevent recursion or disclosure.
- Constructor annotations must meet framework instantiation requirements. Use `@Builder` only when it improves construction readability, not as a substitute for required-field validation or a default for every class.
- Follow the module's injection style; without an existing convention and when Lombok is used, consider `@RequiredArgsConstructor` with `private final`. Do not replace injection styles throughout existing code.
- Simple, stable response conversions may use `static of(...)` with explicit field mappings. Prefer an existing shared conversion component when available.
- Reuse common entity base fields and table mapping conventions. Before using `@EqualsAndHashCode(callSuper = true)`, confirm superclass fields belong in equality checks; do not apply it universally.

#### Enums

- Store enum codes and descriptions in fields initialized by constructors. Never use `ordinal()` for external codes.
- When Lombok is used, consider `@Getter`, `@AllArgsConstructor`, and `private final` attributes. Follow project naming, code types, and dictionary annotations; do not mandate an `Enum` suffix, `Integer`, or constructor annotations.

#### Collections, Numbers, and Data Access

- Use streams for clear filtering, mapping, and grouping. Simple nullable conversions may use `Optional`, and reusable conversions may accept a `Function`; keep them readable.
- Use `BigDecimal` as required by the domain: compare numeric values with `compareTo`, and use `equals` only when both value and scale matter.
- `Collectors.toMap` without a merge function throws on duplicate keys; where duplicates are valid, provide a merge function implementing the domain policy.
- Where MyBatis-Plus is already used, consider `LambdaQueryWrapper` and getter method references.
- For proxy-based transactions, verify that calls pass through the proxy and that the configured rollback rules cover the intended exception types.

#### Javadoc

- Place Javadoc for classes, methods, constructors, and fields above the declaration's entire annotation block, or directly above the declaration when there are no annotations. Do not insert it between annotations or between annotations and the declaration.

## 5. Final Review and Delivery

- [ ] The diff fulfills the requested scope and applicable conventions, with no unintended changes to behavior or user edits.
- [ ] Verification covers the affected contracts, boundaries, and failure paths; comments match the final implementation.

Briefly report changes, verification results, and relevant checks not run or blocked. Explain only key tradeoffs affecting use or maintenance; do not restate the skill's rules.
