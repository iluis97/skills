---
name: code-like-me
description: Apply personal coding preferences while preserving project conventions and interface contracts.
disable-model-invocation: true
---

# code-like-me

## Goal

Think and organize code like me: keep responsibilities clear, names intuitive, and reuse existing abstractions and tools
so code remains easy to read, modify, and extend.

Complete the requested implementation and necessary verification; when asked only for analysis or advice, stay within
that scope.

## 1. Rule Priority and Scope

- Priority: explicit task requirements → project conventions → well-maintained neighboring implementations in the same
  module → this skill's preferences. Always preserve correctness and interface compatibility.
- Apply general rules idiomatically in all languages. Apply a language section in addition only when using that
  language; follow project conventions for languages not listed.
- Follow local conventions in existing projects; design new modules for their requirements rather than copying reference
  package names, frameworks, or domain models.
- Infer personal habits from multiple consistent implementations, not isolated cases, generated code, or other authors'
  code. Quality rules are constraints, not claims that all historical code satisfies them.
- Preserve the user's changes and modify only necessary files. Do not expand scope, format the entire project, upgrade
  dependencies, or refactor unrelated modules merely to unify style.

## 2. Workflow

1. **Define scope**: Identify requirements, interfaces, compatibility constraints, and existing changes. Ask only when
   missing information affects business behavior and cannot be resolved from context.
2. **Read context**: Inspect project instructions, build and language versions, structure, relevant callers,
   implementations, and tests. When available, sample two or three similar implementations in the same module to confirm
   conventions relevant to the task; scale exploration to the change. Syntax and APIs must support the target version.
3. **Choose an implementation**: Reuse types, interfaces, and utilities first, then decide whether current requirements
   justify new abstractions. Identify stable steps and variation points in complex flows; implement simple requirements
   directly.
4. **Make changes**: Organize methods or functions around a single responsibility and complete logic; implement
   necessary boundary validation and failure handling according to contracts.
5. **Verify and review**: Choose compilation, static checks, existing tests, or focused new tests according to impact,
   covering branches, states, and boundaries. Review the diff using the final checklist before delivery.

## 3. General Coding Rules

### Design Principles and Patterns

- **Responsibilities and contracts**: Aim for clear responsibilities, focused interfaces, and low coupling; apply SOLID
  and the Law of Demeter as needed. Follow the project's injection approach for container-managed dependencies. Preserve
  interface contracts when modifying existing capabilities; do not tighten input conditions or silently change return,
  exception, or side-effect semantics.
- **Reuse and collaboration**: Prefer existing components and extension mechanisms, composition, and delegation. Use
  inheritance for genuine substitutability or stable template flows.
- Implement current requirements directly. New abstractions should address existing duplicated business knowledge,
  identifiable variation points, or isolation needs, with maintenance costs proportionate to their benefits.
- **Do not**: Introduce interfaces, abstract base classes, strategies, factories, or configuration layers solely for
  possible future extensions. A single implementation or a few lines of logic is not sufficient justification for an
  abstraction; existing project conventions and concrete isolation needs can justify one.
- **Component collaboration**: In complex flows, check dependency direction, resource ownership, lifecycle, ordering,
  concurrency, and failure propagation. Verify that substitution and extension preserve contracts.

### Naming and Logic Organization

- Names of types, methods, functions, and variables should express domain concepts and purpose. Follow the project's
  English naming, abbreviations, and type suffixes.
- Method or function names should identify actions and objects; follow project boolean naming conventions. Distinguish
  queries, conversions, validation, and execution; names must not conceal writes or external calls.
- **Single responsibility, complete logic**: Each method or function should fulfill one clear responsibility through a
  semantically complete piece of logic. Keep the checks, calculations, and processing belonging to that responsibility
  coherent; do not mix in unrelated responsibilities.
- Organize main flows by business steps at a consistent level of abstraction. Extract methods for independent meaning,
  reuse, or a material improvement in main-flow readability. Orchestration methods may coordinate multiple steps that
  jointly fulfill their responsibility.
- **Do not**: Split methods mechanically just to shorten them, or add forwarding calls and wrappers without independent
  responsibilities. Judge framework adapters and delegation with explicit isolation responsibilities by their actual
  purpose.
- Express boolean results directly, without equivalent `if/else` wrappers or repeated checks of conditions that still
  hold in the current branch. Retain branches with distinct processing or side effects.
- Prefer early exits for unmet preconditions, legitimate no-op cases, and failure branches so normal processing unfolds
  sequentially. Preserve resource cleanup, transactions, and necessary side effects on exit.
- **Do not**: Silently exit instead of reporting business failure, or force normal business branches that should be
  compared side by side into scattered early returns. Return without action only when the contract allows it; clear
  `if/else` structures may remain.
- Put repeated business rules in their owning domain or services. Reserve utility modules for stateless capabilities
  shared across domains.

### Fixed Values and Business Codes

- For business values such as status codes, type codes, thresholds, and defaults, prefer existing constants, enums,
  configuration, or capabilities of their owning types. When no suitable definition exists, name the value within its
  owning scope.
- **Do not**: Scatter business magic values in conditions, assignments, queries, or calculations, such as `status == 2`,
  or redefine existing constants. Express the business meaning even when a value appears only once.
- Clear local literals such as the zero in `count > 0` need no extraction. Do not mechanically extract every literal or
  turn fixed business definitions into configuration options without a configuration requirement.

### Data and State Modeling

- Data objects hold data and necessary local behavior; services orchestrate business logic. Follow layering conventions
  for entities and external contracts.
- Model finite, stable types, states, and operations centrally to reduce scattered values and repeated branches. Put
  reusable code lookup, description retrieval, and predicates in their owning types or conversion components.
- Define return, default, or exception contracts for null and unknown codes; do not silently treat them as valid states.
  Use stable codes in interfaces, persistence, and messages; do not arbitrarily change published codes.
- State types may encapsulate simple behavior tied to their attributes. Put complex behavior involving services,
  databases, or external calls in strategies or business components.

### Validation and Defensive Programming Boundaries

- Base validation on input sources, types, contracts, and business rules. Entry points validate formats and required
  fields; services validate existence, permissions, states, and business constraints. Follow established responsibility
  boundaries.
- **Do not**: Recheck conditions already guaranteed upstream and still intact along the same call path, including
  required dependencies, validated parameters, and return values guaranteed non-null by contract. Do not add null checks
  at every layer merely because null is theoretically possible, or fallbacks for impossible cases.
- Retain necessary checks at new entry points, new trust boundaries, for query results that may be absent, and where
  state can change. Preserve authorization, business-state, write-scope, concurrency, and consistency safeguards when
  simplifying code.

### Exceptions and Logging

- Report failures according to established exception contracts. Reuse validation tools, business exceptions, and error
  codes, and explain the business cause in messages. Catch exceptions to recover, add context, or translate semantics;
  otherwise use centralized handling.
- **Do not**: Return empty collections, null, default objects, zero, or success results, skip invalid data, or swallow
  errors and continue without a business or interface basis. Preserve contractually permitted empty results, recovery,
  and degradation.
- Error messages for callers must not expose stack traces or internal details.
- **Logs support diagnosis**: Follow logging frameworks and levels. Use parameterized logs for key changes, external
  failures, and diagnostic context. Check the logging level before serialization or expensive computation.
- **Consistent business logs**: Use a consistent, searchable business keyword prefix across all stages of the same
  business flow. Retain key business identifiers and state the processing step or outcome to connect the flow and locate
  problems.
- **Avoid duplicate exception logs and sensitive output**: Avoid meaningless high-frequency output and duplicate
  exception logs. Retain stack traces when logging exceptions at the current layer; do not log credentials, tokens, or
  complete sensitive objects.

### Collections, Conversion, and Data Access

- Prefer existing collection, string, conversion, and data access utilities. Do not add dependencies when the standard
  library suffices.
- Use clear, idiomatic constructs for filtering, mapping, and grouping; prefer loops for complex branches, side effects,
  or early termination.
- Define semantics for empty collections, null elements, duplicate keys, and ordering. Use domain-specific conflict
  policies when merging data; do not arbitrarily retain one entry to eliminate a conflict.
- Specify numeric defaults, precision, rounding, and comparison semantics. Do not rely on unverified implicit utility
  behavior or treat zero as missing without domain justification.
- Follow existing conversion and field mapping approaches. Check required fields, types, and meaning; do not let generic
  copying obscure differences.
- Reuse data access components or service queries. Do not query items individually in a loop when they can be queried in
  a batch; consider batch size and transaction semantics.
- Define transaction boundaries by business atomicity and honor framework transaction and rollback rules. Follow
  existing compensation mechanisms for external calls, caches, and messages.
- When maintaining caches after database writes, check and reuse after-commit callbacks to avoid cache changes surviving
  a rollback. Define behavior without a transaction and when callbacks fail.
- Cache repeated intermediate results on hot paths when they can be reliably invalidated. Prefer existing components and
  define keys, lifecycle, invalidation after writes, and concurrency semantics; do not copy capacities or TTLs blindly.
- Define the scope and repeat-execution behavior of updates, deletes, and batches. Retain necessary conditions, result
  checks, and concurrency controls.

### Comments and Formatting

- Follow indentation, imports, line breaks, declaration metadata ordering, and comment language; use existing formatting
  tools.
- Reference classes via imports; do not use fully qualified class names inline. Use a fully qualified name only when
  same-named classes conflict or an import would be ambiguous, keeping such usages consistent within the file.
- Chinese business comments should explain intent, constraints, algorithm steps, and tradeoffs, not translate code line
  by line. Document actual parameters, returns, and exceptions for public capabilities, complex methods or functions,
  and key fields as the project requires.
- Place documentation comments where the language and documentation tools require, and local explanations near the
  implementation. Update comments when behavior changes; do not invent authors, dates, performance guarantees, or
  unimplemented capabilities.

## 4. Language-Specific Rules

For Java work, read [java.md](java.md) before choosing an implementation and making changes. For other languages, follow
project conventions without loading the Java rules.

## 5. Final Review and Delivery

- [ ] The diff fulfills the requested scope and applicable conventions, with no unintended changes to behavior or user
  edits.
- [ ] Methods or functions have a single responsibility and complete logic, with meaningful extraction. Business fixed
  values use existing definitions or are named within their owning scope, without scattered business magic values.
- [ ] New abstractions, validation, fallbacks, and early exits have a current requirement or contractual basis, without
  redundant conditions, duplicate defenses, or silently swallowed errors. Necessary safeguards remain intact.
- [ ] Verification covers the affected contracts, boundaries, and failure paths; comments match the final
  implementation.

Briefly report changes, verification results, and relevant checks not run or blocked. Explain only key tradeoffs
affecting use or maintenance; do not restate the skill's rules.
