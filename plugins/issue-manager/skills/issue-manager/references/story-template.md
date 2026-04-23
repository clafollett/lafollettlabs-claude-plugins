# Story Template

## Core Principle: Intent Over Implementation

Stories define **WHAT** the system should do and **HOW WE VERIFY** it works — never **HOW** to build it. The implementing agent decides the approach.

**DO include:**
- Clear behavioral descriptions (what the system does from the user's perspective)
- Testable acceptance criteria (observable outcomes, not internal state)
- Domain specifications and formats (API contracts, data structures the system processes)
- Key rules and constraints (boundaries the implementation must respect)
- Dependencies between stories

**DO NOT include:**
- Code snippets or pseudocode showing implementation
- Specific library or framework choices (unless architecturally mandated at the Epic level)
- Class names, function signatures, or file paths
- Internal data structures or algorithms

## Description Formats

**User Story format** — for user-facing features:
> **As a** <persona>
> **I want** <capability>
> **So that** <business value>

**What/Why format** — for technical or system-level stories:
> **What:** What is changing or being added (the observable difference)
> **Why:** Why this matters (the consequence or value)

**Rule of thumb:** If the story has a clear human user, use User Story format. If it's about system internals — use What/Why.

**WARNING:** Never include a "How:" section in the description. "How" is the engineer's decision. If you catch yourself writing "How:" — stop and ask whether you're describing observable behavior (belongs in Behavior section) or prescribing implementation (delete it).

## GitHub Issue Body Template

```markdown
Part of Epic #NNN

## Description

<Use User Story or What/How/Why format. 2-4 clear sentences.>

## Acceptance Criteria

- [ ] <Observable outcome 1>
- [ ] <Observable outcome 2>
- [ ] <Observable outcome 3>

## Behavior

<Show what the system does through concrete examples:
- Input/output examples with real data formats
- Step-by-step flows: "User does X -> System does Y -> Result is Z"
- Before/after comparisons when changing existing behavior
Domain specs (API contracts, data formats) belong here — they are intent, not implementation.>

## Key Rules

<Non-negotiable constraints. If any rule is violated, the implementation is wrong regardless of whether tests pass.

Good rules are specific and testable:
- "Existing data without the new field still validates"
- "Concurrent requests must not corrupt shared state"
- "Empty inputs produce no output, not an error"

Bad rules are vague: "Should be performant" or "Handle errors gracefully">

## Dependencies

- <Story dependency or "None">

## Testing

<Concrete test scenarios covering:
- Happy path — primary success scenarios
- Error cases — invalid inputs, constraint violations
- Boundary cases ��� empty collections, max values
- Backward compatibility — existing behavior preserved>

## Technical Notes (optional, 1-3 bullets max)

<Lightweight hints — what existing patterns to follow, gotchas.
This is a hint, not a design doc. The implementing agent decides the approach.

NEVER name specific libraries, frameworks, or packages here. "Reference: the Telegram plugin pattern" is OK. "Use the slack-go library" is NOT.
NEVER include file paths. The engineer discovers the codebase.>

**Priority:** <High/Medium/Low>
**Effort:** <1/2/3/5/8/13 story points>
```
