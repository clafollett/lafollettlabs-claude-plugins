---
name: code-reviewer
description: This skill should be used when performing code reviews, PR reviews, reviewing code changes, or analyzing code quality. Routes by Stack Map — dispatches stack-specific PE sub-agents (pe-backend, pe-frontend, pe-devops) per matched stack regardless of diff size; falls back to a generic three-pass review only when no PE matches. Focuses only on changed code with scope discipline. Locks each round to the reviewed SHA so post-approval commits invalidate prior approval. Produces de-duplicated, actionable findings in ./docs/code-reviews/.
---

# Expert Code Review

Lean, pragmatic code reviews with scope discipline. Stack-specific PE sub-agents do the heavy lifting; the parent skill orchestrates dispatch and consolidates findings.

---

## Phase 1: Scope Analysis

Determine review type from the user's request:

| User Request | Review Type | What to Review |
| --- | --- | --- |
| "Review my branch" / "Review this PR" | Branch Diff | `git diff main...HEAD` |
| GitHub PR URL or "Review PR #N" | PR Review | `git diff <target>...<source>` (auto-checkouts source branch) |
| "Review staged changes" | Staged Diff | `git diff --cached` |
| "Review these files: X, Y, Z" | Specific Files | Read and review entire files |
| "Review the src/services folder" | Folder | Read and review all files in folder |
| "Review this code" + pasted code | Ad-hoc | Review the provided code |

### Branch / Staged

```bash
git diff main...HEAD      # branch diff
git diff --cached         # staged changes
```

```
if current_branch == "main":
  ask user which branch to review (do NOT proceed)
```

### PR

```bash
gh pr view <PR_NUMBER> --json number,url,headRefName,baseRefName,author
git checkout <source_branch>
git pull
git diff <target_branch>...<source_branch>
```

Capture: source branch, target branch, PR number, PR URL, author. Store for Phase 6.

**Critical:** Review files MUST be committed to the source branch, never to main.

### Files / Folders / Ad-hoc

Read the files directly. No diff context — review entire content.

### Review Name (used for output filename)

```
if branch matches "<type>/<issue-id>-<description>":
  name = issue_id                 # e.g., "983"
elif on a branch (no issue ID):
  name = slugify(branch)          # e.g., "fix-code-reviewer-cleanup"
else:
  ask user for a short descriptive name
```

### PE Routing

```bash
git diff main...HEAD --stat | tail -1          # branch reviews (informational)
git diff <target>...<source> --stat | tail -1  # PR reviews (informational)
```

```
matching_pes = PEs whose Stack Map paths intersect with files in the diff

if matching_pes is empty:
  approach = "generic"     # primary runs generic three-pass (no PE expertise available)
elif len(matching_pes) == 1:
  approach = "single_pe"   # dispatch the one matching PE
else:
  approach = "multi_pe"    # dispatch all matching PEs in parallel
```

Diff size is informational only. Domain expertise is the constant — every review touching a stack with a matching PE dispatches that PE, regardless of line count.

---

## PE Agent Selection

The plugin ships four built-in PE sub-agents:

| Subagent | Domain | File patterns |
| --- | --- | --- |
| `code-reviewer:pe-backend` | Go / PostgreSQL / AWS Lambda | `*.go`, `go.mod`, `go.sum`, `*.sql` |
| `code-reviewer:pe-frontend` | Vue 3 / Nuxt 3 / TS / Tailwind / Storybook | `*.vue`, `*.tsx`, `*.jsx`, `tailwind.config.*`, `nuxt.config.*`, `vite.config.*`, `*.stories.*` |
| `code-reviewer:pe-devops` | AWS CDK / Cloudflare CDKTF / Terraform / Docker / GH Actions | `cdk.json`, `*.tf`, `*.tfvars`, `Dockerfile*`, `docker-compose*`, `.github/workflows/*.yml` |
| `code-reviewer:pe-governance` | Agent definitions, skills, plugin instructions, CLAUDE.md | `.claude/agents/*.md`, `**/SKILL.md`, `plugins/**/agents/*.md`, `**/CLAUDE.md`, `.claude/rules/*.md`, `docs/rules/*.md` |

Each agent has its own model (`claude-opus-4-7`), tools, and self-contained three-pass protocol — they do NOT need a reference file at runtime.

`pe-governance` reviews documents whose audience is the model (agent governance markdown). It does NOT review documents whose audience is humans (ADRs at `docs/architecture/*.md`, runbooks at `docs/runbooks/*.md`, review docs at `docs/code-reviews/*.md`, READMEs). Those fall to generic three-pass review.

### Selection Priority

```
1. .code-reviewer.yml (project config) — if it exists, read `stacks` array;
   match changed files against each stack's `paths` globs; map to subagent.
2. CLAUDE.md Stack Map — parse the table; map paths → stack → subagent.
3. File pattern fallback — match diff file extensions against the table above.
4. No match — generic three-pass review (Architecture → Quality → Security)
   without stack-specific test commands or domain checklists.
```

**Mixed diffs:** If the diff spans multiple stacks, dispatch ALL matching PE subagents in parallel (single message, multiple Agent calls). Each PE reviews only the portion of the diff relevant to its domain.

**Stacks not covered by built-in agents** (Rust, Python, Java, C#, etc.): primary agent runs the generic three-pass review directly. CLAUDE.md's Stack Map still tells the parent which paths are which stack and what test commands to run.

---

## Phase 2: Scope Discipline

### Diff-based reviews (Branch / Staged / PR)

```
in_scope = issue is in lines added/modified by the diff
            OR in functions/types/components containing changes

# Report ALL severities (CRITICAL → INFO) for awareness.
# Verdict is based on highest severity that has in_scope = true.
# Pre-existing issues (in_scope = false) → awareness, do NOT block PR.
```

### File / Folder / Ad-hoc reviews

```
in_scope = true for everything provided
# Use judgment on severity — focus on security and architecture; don't nitpick
# style on existing code unless explicitly asked.
```

---

## Phase 3: Review Execution

### Three-Pass Protocol (every review)

```
Pass 1 — Architecture: SOLID, patterns, coupling, cohesion, separation of
                       concerns, package/component boundaries, migration safety.

Pass 2 — Quality + Tests: code quality + RUN THE TEST SUITE. Test failures
                          are CRITICAL. Lint/vet/typecheck warnings are HIGH.

Pass 3 — Security: top 1% strict. OWASP Top 10, auth, secrets, injection,
                   supply chain. "Would this survive a pentest?", not "is this
                   probably fine?". Assume an attacker is reading the diff.

                   Cross-file claim verification: when the diff includes
                   documentation that describes runtime security posture
                   (IAM/RBAC/permissions/auth claims), verify the doc's
                   claim against the actual runtime artifact (CDK stack,
                   IAM policy file, workflow YAML, role trust policy).
                   Doc-vs-artifact drift is a security-grade finding —
                   readers and operators trust the doc.
```

### Dispatch

```
match approach:
  case "generic":
    # No matching PE — primary runs all three passes directly
    # using its own judgment + Stack Map's test commands.
    no sub-agent dispatch

  case "single_pe":
    Agent(
      subagent_type: "code-reviewer:pe-{stack}",
      prompt: <dispatch input — see below>
    )

  case "multi_pe":
    # Dispatch all matching PEs in parallel — single message, multiple Agent calls.
    for each pe in matching_pes:
      Agent(
        subagent_type: "code-reviewer:pe-{stack}",
        prompt: <dispatch input filtered to this PE's domain>
      )
```

### Dispatch Input

Each PE subagent expects the following inputs in its prompt. The agent's system prompt carries the three-pass protocol, test commands, checklist, and YAML output contract — the dispatch only provides inputs:

```
You are reviewing changes for {ISSUE_ID}.

DIFF (filtered to your domain):
{paste git diff output for files matching this PE's patterns}

SCOPE: {Branch Diff | Staged Diff | PR Review}
TARGET BRANCH: {main | etc.}
SOURCE BRANCH: {current branch}
WORKTREE: {absolute path to repo root}
{optional} PROJECT SUBDIR: {e.g., "crew/" for frontend in monorepo, "cdk/" for CDK subdir}

Run your three-pass protocol. Return YAML findings.
```

The PE returns ONLY a YAML block — see "YAML Finding Structure" below.

---

## Phase 4: De-duplication

When consolidating sub-agent findings:

```
1. Merge duplicates:        same issue from multiple PEs = ONE finding
2. Tag domains:             merged finding gets `domains: [Security, Architecture]`
3. Keep highest severity:   if PEs disagree, use the higher severity
```

---

## Phase 5: Finding Validation

Before writing the final report:

```
if sub-agents were used:
  for each finding:
    verify severity given full context
    dismiss false positives with brief rationale
    adjust severity if PE over/under-rated

elif primary reviewed directly:
  for each CRITICAL/HIGH finding:
    re-examine with full context
    confirm actionable and accurate
    downgrade if initial assessment was too harsh
```

**Validation checklist for any CRITICAL/HIGH:**

- [ ] Actually exploitable / broken?
- [ ] Does full context change the severity?
- [ ] Real risk, not theoretical?
- [ ] Would a senior engineer agree this blocks the PR?

Never publish a CRITICAL/HIGH without a second look.

---

## Phase 6: Output

### Step 1: Output Path

```
./docs/code-reviews/{name}-code-review.md
```

`{name}` resolution from Phase 1.

### Step 2: Write or Append

```
reviewed_sha = git rev-parse HEAD     # capture BEFORE writing

if file does NOT exist:
  write full report using assets/summary-report-template.md
  populate:
    Reviewer       (`git config user.name`)
    Review Round   (1)
    Reviewed SHA   (reviewed_sha)
    PR fields      (number, URL, author — PR reviews only)

elif file exists (previous review):
  read existing file
  prior_sha = SHA recorded in latest round's "Reviewed SHA" field
  prior_verdict = top-level Verdict of latest round

  if prior_sha == reviewed_sha:
    # No new commits since last review.
    REFUSE: "No changes since round N (SHA {prior_sha}). Re-running adds no signal — abort."

  else:
    # New commits since last review.
    count `## Review Round` headings → next_round_number = N + 1
    if prior_verdict == "✅ APPROVED":
      round_header_note = "🚫 PRIOR ROUND INVALIDATED — re-reviewing post-approval changes"
    else:
      round_header_note = (none — standard remediation round)
    append new Review Round section before the `Generated with Claude Code` footer
    populate Reviewed SHA = reviewed_sha
    update top-level Verdict to reflect latest round
```

See `assets/summary-report-template.md` for exact format.

### Step 3: Commit

```bash
git add ./docs/code-reviews/{name}-code-review.md
git commit -m "docs: {name} code review"
```

Commit to the **current branch** (source branch for PR reviews, feature branch for branch reviews). Never commit review files to main.

### Step 4: PR Comment (PR Reviews Only)

```
Prompt: "Review complete and committed to {source_branch}.
         Would you like to post a summary comment on PR #{number}?"

if yes:
  post condensed summary via `gh pr comment`:
    - Verdict, finding counts by severity, link to review file
    - Key findings (CRITICAL/HIGH only, one line each)
    - Action items (Must Fix and Should Fix only)

  approve or request changes per Verdict:
    APPROVED          → gh pr review <PR> --approve
    CHANGES REQUESTED → gh pr review <PR> --request-changes
    BLOCKED           → gh pr review <PR> --request-changes
```

### Step 5: External Review Consolidation (PR Reviews Only, optional)

External reviewers (Copilot, third-party bots, human reviewers via GitHub UI)
post review comments asynchronously. Their comments are pinned to a specific
commit SHA. When HEAD advances past that SHA, some comments may already be
addressed by remediation commits.

```
Prompt: "Pull external PR review comments and consolidate against current HEAD?"

if yes:
  fetch open review threads:
    gh api graphql -f query='
      query { repository(owner, name) {
        pullRequest(number) {
          reviewThreads(first: 50) {
            nodes { id isResolved comments(first: 1) {
              nodes { databaseId author { login } path line body
                      commit { oid } }
            } }
          }
        }
      }'

  for each thread where isResolved == false:
    comment_sha = thread.comments[0].commit.oid
    if HEAD == comment_sha:
      status = "current"          # comment matches HEAD; full review needed
    else:
      # HEAD advanced — verify the comment's claim still holds
      grep the comment's claimed-missing or claimed-broken pattern against
      current HEAD's file at the comment's path.
      if pattern not found at HEAD:
        status = "stale"          # already addressed; reply with pointer to fixing commit
      else:
        status = "current"        # claim still holds at HEAD

  for each thread:
    if status == "stale":
      reply via gh api repos/{owner}/{repo}/pulls/{N}/comments/{commentId}/replies:
        "Already resolved in {sha} ({short message of fixing commit}). ✅"
      resolve thread via GraphQL resolveReviewThread mutation
    if status == "current":
      evaluate finding; if agree, fix in a remediation commit; reply with
      "Fixed in {sha}. ✅" and resolve thread; if disagree, reply with
      reasoning and leave thread open for author response.
```

External-review consolidation is optional — skip when reviewing pure branch
diffs or when no external reviews exist.

---

## Severity Definitions

| Level | Criteria | Action |
| --- | --- | --- |
| 🔴 CRITICAL | Security vulnerabilities, data loss, breaking changes, test failures | Must fix — blocks merge |
| 🟠 HIGH | Bugs, vet/typecheck warnings, significant design issues | Must fix — blocks merge |
| 🟡 MEDIUM | Code quality, maintainability | Required — changes requested |
| 🟢 LOW | Style, minor improvements | Optional |
| ℹ️ INFO | Observations | Awareness |

---

## Verdict Logic

```
if any CRITICAL with in_scope == true:    🚫 BLOCKED
elif any HIGH with in_scope == true:      🚫 BLOCKED
elif any MEDIUM with in_scope == true:    ⚠️  CHANGES REQUESTED
else:                                      ✅ APPROVED
```

If it's worth reporting, it's worth fixing. LOW and INFO are awareness items — everything above requires remediation before merge.

---

## YAML Finding Structure

PE sub-agents return findings in this exact format. Primary agent parses YAML blocks and consolidates into the final report.

```yaml
expert: PE-Backend|PE-Frontend|PE-DevOps|Primary
findings:
  - id: "CRITICAL-001"
    severity: CRITICAL
    in_scope: true
    title: "XSS via unsanitized HTML injection"
    location: "src/components/email-viewer.ts:207"
    description: |
      Email content is written to iframe using document.write()
      without any sanitization, allowing arbitrary script execution.
    recommendation: |
      Use DOMPurify to sanitize HTML before injection:
      ```typescript
      import DOMPurify from 'dompurify';
      const clean = DOMPurify.sanitize(emailContent);
      ```

  - id: "HIGH-001"
    severity: HIGH
    in_scope: true
    title: "Memory leak — event listener not removed"
    location: "src/components/email-viewer.ts:210"
    description: |
      Click event listener added to iframe but never removed
      when component is destroyed.
    recommendation: |
      Implement cleanup and remove the listener on unmount.
```
