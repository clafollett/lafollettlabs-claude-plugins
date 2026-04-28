---
name: init-project
description: Scan the current project and generate a Stack Map + PE references for the code-reviewer skill. Detects languages, frameworks, test commands, and directory structure automatically.
---

# Initialize Project for Code Review

Bootstraps the `/code-reviewer` skill into any project by scanning the repo
and generating configuration automatically.

---

## Phase 1: Detect Stacks

Scan the repository for language markers, build files, and framework configs.

### Language Detection

| Marker | Stack | Default PE |
| - | - | - |
| `go.mod`, `*.go` | Go | PE-Backend |
| `package.json` + `*.vue` | Vue/Nuxt | PE-Frontend |
| `package.json` + `*.tsx`/`*.jsx` | React | PE-Frontend |
| `package.json` + `*.svelte` | Svelte | PE-Frontend |
| `cdk.json`, `*.ts` in `cdk/` or `infra/` | AWS CDK | PE-DevOps |
| `cdktf.json` | CDKTF | PE-DevOps |
| `*.tf` | Terraform | PE-DevOps |
| `Cargo.toml`, `*.rs` | Rust | PE-Backend |
| `pyproject.toml`, `requirements.txt`, `*.py` | Python | PE-Backend |
| `*.java`, `pom.xml`, `build.gradle` | Java | PE-Backend |
| `*.cs`, `*.csproj`, `*.sln` | C# / .NET | PE-Backend |
| `Dockerfile*`, `docker-compose*` | Docker | PE-DevOps |
| `.github/workflows/*.yml` | GitHub Actions CI/CD | PE-DevOps |
| `.gitlab-ci.yml` | GitLab CI/CD | PE-DevOps |

### Framework Detection

Dig deeper into detected stacks to identify frameworks:

| Indicator | Framework |
| - | - |
| `nuxt.config.*` | Nuxt 3 |
| `next.config.*` | Next.js |
| `astro.config.*` | Astro |
| `vite.config.*` | Vite |
| `angular.json` | Angular |
| `svelte.config.*` | SvelteKit |
| `tailwind.config.*` | Tailwind CSS |
| `.storybook/` | Storybook |
| `playwright.config.*` | Playwright |
| `vitest.config.*`, `jest.config.*` | Vitest / Jest |
| `testcontainers` in go.mod | Testcontainers (Go) |
| `pytest.ini`, `conftest.py` | Pytest |
| `Makefile` | Make build system |

---

## Phase 2: Map Directory Structure

Walk the repo and assign each top-level directory (and significant
subdirectories) to a stack and PE type.

```bash
# Get top-level directories
ls -d */ | head -30

# Get file extension distribution per directory
find <dir> -type f -name '*.*' | sed 's/.*\.//' | sort | uniq -c | sort -rn | head -10
```

Build a path → stack → PE mapping. Group directories that share the same
stack (e.g., `lambdas/` and `pkg/` are both Go → PE-Backend).

---

## Phase 3: Detect Test Commands

For each detected stack, identify the test commands:

| Stack | Look For | Default Test Command |
| - | - | - |
| Go | `go.mod` | `go vet ./... && go test ./... -count=1 -race` |
| Vue/Nuxt | `package.json` scripts | `npm run typecheck && npm test` |
| React | `package.json` scripts | `npm test` |
| CDK | `package.json` in cdk dir | `cd <dir> && npm test && npx cdk synth --all` |
| CDKTF | `package.json` in cdktf dir | `cd <dir> && npm test && npx cdktf synth` |
| Terraform | `*.tf` | `terraform validate` |
| Rust | `Cargo.toml` | `cargo test` |
| Python | `pyproject.toml` / `requirements.txt` | `pytest` |
| Java (Maven) | `pom.xml` | `mvn test` |
| Java (Gradle) | `build.gradle` | `./gradlew test` |
| C# | `*.sln` | `dotnet test` |
| Docker | `Dockerfile` | `docker build --target test` (if multi-stage) |

**Override from package.json:** If `package.json` exists, read `scripts` for
`test`, `typecheck`, `lint`, `build` — use actual script names, not defaults.

---

## Phase 4: Check for Existing CLAUDE.md

Read the project's `CLAUDE.md` (if it exists) for:
- Existing project structure documentation
- Team structure or review chain information
- Coding standards or conventions
- Any Stack Map already defined

If a Stack Map already exists, offer to update it rather than overwriting.

---

## Phase 5: Generate Output

### 5a: Stack Map

Generate a Stack Map table and prompt the user to add it to their `CLAUDE.md`:

```markdown
## Stack Map

| Path | Stack | PE | Test Command |
| - | - | - | - |
| lambdas/**, pkg/** | Go | PE-Backend | `go vet ./... && go test ./... -count=1 -race` |
| crew/** | Vue/Nuxt | PE-Frontend | `cd crew && npm run typecheck && npm test` |
| cdk/** | CDK TypeScript | PE-DevOps | `cd cdk && npm test && npx cdk synth --all` |
```

### 5b: PE Reference Files

For each detected PE type, generate a reference file at
`references/pe-<type>.md` with:

- Frontmatter (`name`, `activates_on` file extensions)
- Test commands (from Phase 3)
- Three-pass protocol skeleton (Architecture → Quality+Tests → Security)
- Framework-specific checklist items
- Domain expertise summary

**Do NOT overwrite existing PE references** — merge new patterns into existing
files, or offer the user a diff.

### 5c: Summary Report

Print a summary of what was detected and generated:

```
=== Project Initialized for Code Review ===

Stacks detected:
  - Go (PE-Backend): lambdas/, pkg/
  - Vue/Nuxt (PE-Frontend): crew/
  - CDK TypeScript (PE-DevOps): cdk/
  - CDKTF TypeScript (PE-DevOps): cloudflare/
  - GitHub Actions (PE-DevOps): .github/workflows/

PE references generated:
  - references/pe-backend.md (Go, SQL)
  - references/pe-frontend.md (Vue, Nuxt, Tailwind, Storybook)
  - references/pe-devops.md (CDK, CDKTF, GitHub Actions)

Stack Map ready — add to your CLAUDE.md or .code-reviewer.yml

Run /code-reviewer to start reviewing!
```

---

## Edge Cases

- **Monorepo with many stacks:** Generate one PE per unique stack, map all
  directories. The code-reviewer skill handles multi-PE diffs.
- **Unknown language:** Fall back to a generic review (Architecture → Quality →
  Security) without stack-specific test commands. Suggest the user create a
  custom PE reference.
- **No tests found:** Flag it as a finding in the summary — "No test command
  detected for <stack>. Consider adding tests."
- **Existing PE references:** Merge, don't overwrite. Show the user what would
  change and let them decide.
