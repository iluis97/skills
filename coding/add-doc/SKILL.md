---
name: add-doc
description: Add or improve code documentation and comments. Use when asked to document code, explain complex logic in comments, or correct existing documentation. Defaults to uncommitted code changes unless files are specified.
---

# add-doc

## 1. Scope and Constraints

- If no files are specified, inspect staged and unstaged code changes and untracked code files not excluded by Git's ignore rules. Limit documentation edits to declarations and logic affected by those changes.
- If files are specified, review documentation within those files only; changes need not be limited to uncommitted code.
- Skip deleted files. If there are no applicable code changes or existing target files, report that there is nothing to process and stop. Outside a Git repository, ask for target files if none were specified.
- Preserve the user's existing changes. Modify documentation and comments only; do not change executable code, interface behavior, or unrelated files.

## 2. Workflow

1. Determine the target scope using the rules above.
2. Read the relevant code and context to understand actual behavior and the project's documentation conventions.
3. Add or update documentation using the guidelines below.
4. Review the diff for accuracy, placement, and scope. Use available documentation checks when warranted by the changes, and ensure there are no unrelated modifications.

## 3. Writing Guidelines

- Prefer updating existing documentation over creating duplicates.
- Document intent, contracts, constraints, and non-obvious logic. Describe parameters, return values, and exceptions when they add information beyond names and types.
- Follow the project's existing language, comment style, and documentation format.
- Place documentation comments where the language and documentation tools associate them with the intended declaration. Correct misplaced comments within the target scope; keep implementation comments close to the code they explain.
- Do not invent behavior or add comments that merely restate the code.

## 4. Java Javadoc Placement

- Place Javadoc for a class, method, constructor, or field immediately above the declaration's entire annotation block, or directly above the declaration if there are no annotations. Do not insert it between annotations or between an annotation and the declaration.

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

## 5. Delivery

Briefly report which files changed, what documentation was improved, and the checks performed with their results. State any relevant checks that could not be run.
