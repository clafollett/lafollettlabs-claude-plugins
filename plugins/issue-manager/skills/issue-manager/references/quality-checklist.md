# Issue Quality Checklist

Use when reviewing existing issues or before creating new ones.

## Universal Checks (all issue types)

- [ ] **Intent, not implementation** — describes WHAT and WHY, not HOW
- [ ] **No code snippets** — no pseudocode, no implementation examples
- [ ] **No file paths** — unless an Epic-level architectural constraint
- [ ] **No library/framework prescriptions** — engineer decides tools
- [ ] **Domain language** — uses business terms, not technical jargon
- [ ] **Acceptance criteria are observable** — verifiable from outside the system

## Epic-Specific Checks

- [ ] **Current State -> Target State** — describes the transformation
- [ ] **Business value stated** — who benefits and why it matters
- [ ] **Scope boundaries** — what's explicitly excluded
- [ ] **Story breakdown** — child issues listed with dependency graph
- [ ] **Strategic constraints only** — no per-story implementation details

## Story-Specific Checks (INVEST)

- [ ] **Independent** — can be developed without other stories in progress
- [ ] **Negotiable** — details can be refined during implementation
- [ ] **Valuable** — delivers observable value to a user or the system
- [ ] **Estimable** — team can estimate the effort
- [ ] **Small** — completable in one sprint/cycle
- [ ] **Testable** ��� clear pass/fail criteria

## Key Rules Quality

- [ ] **Specific and testable** — "empty input returns empty, not error" (good)
- [ ] **Not vague** — "should be performant" (bad)
- [ ] **Violation = wrong** — if any rule is violated, implementation fails regardless of tests

## Dependency & Independence Checks

- [ ] **No hidden coupling** — if Story A modifies Story B's deliverable, they are not independent. Either fold the concern into one story or establish a contract (e.g., "Story B provides a filtering hook") so each story owns its own scope.
- [ ] **Dependency graph is explicit** — the Epic lists which stories can be parallelized and which are sequential. Don't leave ordering implicit.

## Anti-Patterns (reject if found)

- "Create a function called..." — implementation prescription
- "Use the X library to..." — tool prescription (even in Technical Notes)
- "In file path/to/thing.go..." — file path prescription
- "The database query should..." — internal implementation detail
- "Add a column called..." — schema prescription (belongs in ADR, not story)
- "Should be fast/clean/good" — unmeasurable vagueness
- **"How:"** section in Story description — the entire "How" is the engineer's job. Describe WHAT changes and WHY it matters. If you're explaining mechanism, it belongs in Behavior (observable) or not at all.
- "Write to `<dir>/<timestamp>-<id>.json`" — prescribing file formats, naming conventions, or internal data structures
- "Go binary" without citing an ADR — language choices must reference the decision that made them, not just state the preference
- "Follow the same architecture as X — SKILL.md with Y, Z tool" — prescribes internal file layout. Say "follow established conventions (reference: X)" instead
