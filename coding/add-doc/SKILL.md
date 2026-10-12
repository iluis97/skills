---
name: add-doc
description: Add or improve code documentation and comments. If no files are specified, process all uncommitted code changes; otherwise, process only the specified files.
---

# add-doc

## Goal

Add clear, accurate, and concise documentation to code without changing existing business logic.

## 1. File Scope

- If no files are specified, inspect all uncommitted code changes in the Git working tree, including staged and unstaged changes.
- If files are specified, process only the files explicitly selected by the user. Do not expand the scope to other files.
- Preserve the user's existing changes. Do not overwrite, revert, or discard any uncommitted content.
- Do not modify code or files unrelated to the documentation task.

## 2. Workflow

1. Confirm the scope of files to process.
2. Read the relevant code to understand its actual functionality and logic.
3. Add or update documentation following the project's existing conventions.
4. Check that the documentation is accurate, concise, consistent with the implementation, and correctly positioned so documentation tools associate it with the intended declaration.
5. Review the final changes to ensure there are no unrelated modifications.

## 3. Writing Guidelines

- Prefer updating existing documentation over creating duplicate documentation.
- Focus on functionality, parameters, return values, exceptions, and complex logic.
- Follow the project's existing language, comment style, and documentation format.
- Place documentation comments where the language and documentation tools expect them, ensuring they document the intended class, method, or field. When updating existing comments, correct misplaced comments within the selected scope.
- Place implementation comments close to the code they explain, following the project's conventions.
- Do not invent code behavior or add redundant comments.
- Do not change business logic, interface behavior, or unrelated files.

## 4. Documentation Placement by Language

### Java — Javadoc

- Place Javadoc for a class, method, constructor, or field immediately above the declaration's entire annotation block.
- If the declaration has no annotations, place Javadoc directly above the declaration.
- Do not place Javadoc between annotations or between an annotation and the declaration.

```java
/**
 * Returns the user's display name.
 */
@Override
@Nullable
public String getDisplayName() {
    return displayName;
}
```

## 5. Output Requirements

After completion, briefly describe:

- Which files were modified.
- What documentation was added or improved.
- Which checks were performed and their results.

## 6. Core Principles

Keep the scope clear, documentation accurate, and changes minimal. Preserve existing code behavior.
