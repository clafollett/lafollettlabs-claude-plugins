# code-reviewer

Lean, pragmatic code reviews with scope discipline. Uses right-sized approach — primary agent handles small changes directly, sub-agents for larger reviews.

## Features

- **Right-sized reviews** — < 200 lines: primary agent; ≥ 200 lines: sub-agents
- **Scope discipline** — In Scope (blocks PR) vs Out of Scope (tech debt)
- **Finding validation** — All CRITICAL/HIGH/MEDIUM verified before publishing
- **Multiple review types** — Branch diff, PR review, staged changes, specific files, ad-hoc
- **Branch discipline** — Auto-checkouts PR source branch, commits review to working branch
- **Multi-round reviews** — Appends findings to existing review files instead of overwriting
- **PR comment + approval** — Prompts reviewer to post summary comment and approve/request changes
- **Project-specific references** — Drop `.md` files in `references/` for domain-specific review rules

## Triggers

This skill auto-activates when you mention:

- Code review, PR review
- Review changes, review my branch
- Review staged changes, review these files

## Review Types

| Request | What Gets Reviewed |
| ------- | ------------------ |
| "Review my branch" | `git diff main...HEAD` |
| PR URL or "Review PR #17" | Fetch source branch, diff against target |
| "Review staged changes" | `git diff --cached` |
| "Review these files: X, Y" | Entire file contents |
| "Review this code" + paste | The provided code |

## Expert Domains

All reviews cover three domains (via sub-agents for large changes, primary for small):

| Domain | Focus |
| ------ | ----- |
| **Security** | OWASP Top 10, auth, secrets, injection |
| **Architecture** | SOLID, patterns, coupling, cohesion |
| **Code Quality** | Readability, maintainability, DRY |

### Project-Specific References

Add `.md` files to the `references/` directory for domain-specific review
rules your project needs. The skill scans the diff for patterns and loads
matching reference files before reviewing.

## Scope Discipline

**In Scope** — Issues in changed code:

- Report all severities (CRITICAL → INFO)
- CRITICAL/HIGH block the PR

**Out of Scope** — Pre-existing issues:

- Note for awareness
- Don't block PR
- Log to backlog

## Severity Levels

| Level | Criteria | Action |
| ----- | -------- | ------ |
| 🔴 CRITICAL | Security vulnerabilities, data loss | Must fix |
| 🟠 HIGH | Bugs, significant design issues | Should fix |
| 🟡 MEDIUM | Code quality, maintainability | Consider |
| 🟢 LOW | Style, minor improvements | Optional |
| ℹ️ INFO | Observations | Awareness |

## Report Output

Review reports are written to `./docs/code-reviews/`. See SKILL.md Phase 6 for naming conventions.

## Usage Examples

### Branch Review

```text
You: "Review my branch"
Claude: [Analyzes diff, validates findings, generates report]
```

### Staged Changes

```text
You: "Review my staged changes"
Claude: [Reviews git diff --cached]
```

### PR Review

```text
You: "Review PR #984"
Claude: [Checks out source branch, reviews diff, writes/appends report, prompts for PR comment]
```

### Ad-hoc Review

```text
You: "Review this code" + paste code
Claude: [Reviews provided code]
```

---

*Part of [LaFollett Labs Claude Plugins](../../../../README.md)*
