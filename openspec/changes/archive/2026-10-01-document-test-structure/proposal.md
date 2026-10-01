# Proposal: Document the Test Structure

## Why

Readers ask why tests live inside each package (for example `libs/sales_common/tests/`) rather than under the root `tests/` folder. The README lists test commands but not the layout or the reasoning.

## What Changes

- README "Tests" section gains a test-structure table: per-package unit tests, gateway tests, root cross-service tests, golden evals, and E2E. It explains why unit tests sit next to their package.

BASELINE.md sections affected: none.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `service-operations`: README documents the test layout.

## Non-goals

- Moving any tests.

## Impact

- **Docs:** README.md only.
