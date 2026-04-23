# Epic Template

## Core Principle: Intent Over Implementation

Epics define the **business goal**, **target state**, and **acceptance criteria** — not how to build it. Architectural decisions (language, platform, key patterns) belong here only when they're strategic constraints that affect all stories.

**The Epic defines:**
- Current state -> Target state (the transformation)
- Business value and who benefits
- Acceptance criteria (how we know the Epic is done)
- Architectural constraints that apply to ALL stories (only if strategic)
- Story dependency graph (what can be parallelized, what's sequential)
- What's explicitly out of scope

**The Epic does NOT define:**
- How individual stories are implemented
- Specific libraries, packages, or internal patterns
- Code structure or file organization

## Questions to Gather

1. **Business Goal** — What problem does this solve? Who benefits?
2. **Key Deliverables** — What are the main outputs/features?
3. **Dependencies** — What must exist before this can start?
4. **Acceptance Criteria** — How will we know this is done?
5. **Effort Estimate** — T-shirt size (S/M/L/XL)
6. **Scope Boundaries** — What is explicitly NOT included?
7. **Parallelism** — How do stories depend on each other?

## GitHub Issue Body Template

```markdown
## Description

### Current State

<What exists today, the problem or gap>

### Target State

<What will exist after completion — describe the end result, not the steps to get there>

### Business Value

<Why this matters, who benefits, what it enables>

## Acceptance Criteria

- [ ] <Observable outcome 1>
- [ ] <Observable outcome 2>
- [ ] <Observable outcome 3>

## Architecture (strategic constraints only)

<High-level constraints that affect ALL stories — platform decisions, key infrastructure choices. NOT implementation details.

State WHAT must be true, not HOW to achieve it:
- GOOD: "Event delivery must be compatible with Claude Code's existing tool surface"
- BAD: "File-based event delivery — listener writes events to a watched directory"
- GOOD: "Go — consistent with ADR: Production Language is Go" (cites decision)
- BAD: "Go binary — lightweight, runs as background process" (prescribes form)

Reference ADRs for decisions already made. Flag decisions that need an ADR before implementation.>

## Story Breakdown

- [ ] #NNN — Story title
- [ ] #NNN — Story title
- [ ] #NNN — Story title

## Dependencies

- <External dependency or "None">

## Out of Scope

- <Exclusion 1 — with brief rationale>
- <Exclusion 2 — with brief rationale>

**Priority:** <High/Medium/Low>
**Effort:** <S/M/L/XL>
**ADR:** <link to ADR if applicable>
```
