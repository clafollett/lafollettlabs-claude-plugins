# Task Template

## Core Principle: Intent Over Implementation

Even technical tasks describe **what needs to be accomplished** and **how we verify it** — not the step-by-step implementation.

**DO include:**
- Clear objective (what state should exist when done)
- Acceptance criteria (verifiable outcomes)
- Constraints and rules
- Dependencies

**DO NOT include:**
- Specific file paths to modify (the agent will find them)
- Code snippets or implementation approach
- Library or tool prescriptions
- "How:" sections — describe what should be true when done, not the steps to get there

## GitHub Issue Body Template

```markdown
Part of Epic #NNN

## Description

<What needs to be accomplished and why. 2-4 sentences.>

## Acceptance Criteria

- [ ] <Verifiable outcome 1>
- [ ] <Verifiable outcome 2>

## Key Rules

<Constraints, boundaries, or conventions that must be respected>

## Dependencies

- <Dependency or "None">

## Testing

<How to verify the task is complete — focus on observable outcomes>

## Technical Notes (optional, 1-3 bullets max)

<Lightweight hints only>

**Priority:** <High/Medium/Low>
**Effort:** <1/2/3/5/8/13 story points>
```
