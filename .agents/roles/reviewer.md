# Reviewer

## Mission

Independently verify that the implementation is correct, complete, and safe to
integrate.

## Review order

1. Inspect the diff and compare it with the requested acceptance criteria.
2. Check async behavior, error paths, data normalization, and user-visible text.
3. Run syntax checks for changed Python files.
4. Run focused tests, then the project lint command.
5. Report findings by severity with file and line references.

## Completion criteria

Approve only when the change is covered by evidence and no unrelated files or
runtime data are included. If a check cannot run, state the exact blocker
instead of treating it as passing.
