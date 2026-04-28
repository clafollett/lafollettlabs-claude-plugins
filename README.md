# LaFollett Labs — Claude Code Plugins

Claude Code plugin marketplace for [LaFollett Labs LLC](https://lafollettlabs.com). Cross-project skills, commands, and developer workflow tools that work in any repository.

## Available Plugins

| Plugin | Purpose | Details |
| ------ | ------- | ------- |
| [code-reviewer](./plugins/code-reviewer/skills/code-reviewer/) | PE-powered code reviews + project bootstrapping | [README](./plugins/code-reviewer/skills/code-reviewer/README.md) |
| [context-handoff](./plugins/context-handoff/) | Session state handoff and resume with prior-session deduplication | [Commands](./plugins/context-handoff/commands/) |
| [issue-manager](./plugins/issue-manager/) | GitHub Issue management with intent-over-implementation templates | [Skill](./plugins/issue-manager/skills/issue-manager/SKILL.md) |
| [session-analyzer](./plugins/session-analyzer/) | Analyze and extract conversations from Claude Code session JSONL files | [Skill](./plugins/session-analyzer/skills/session-analyzer/SKILL.md) |

**code-reviewer** — PE-powered code reviews

- **`/code-reviewer`** — Three-pass review protocol: Architecture → Quality+Tests → Security
- **`/init-project`** — Auto-detect stacks, generate `.code-reviewer.yml` + PE references
- PE sub-agents per stack (Backend, Frontend, DevOps) with domain expertise and test execution
- Right-sized reviews (primary agent < 200 lines, PE sub-agents for larger)
- Scope discipline (In Scope vs Out of Scope findings)
- Strict verdicts: MEDIUM and above block merge
- Multi-round review support with appended findings
- Consolidated reports at `./docs/code-reviews/`
- Project-agnostic: works with Go, Vue, React, CDK, Terraform, Rust, Python, Java, C#, and more

### context-handoff

Save and restore session working state across `/clear` boundaries.

- **`/handoff-context`** — Serializes task goal, completed/in-progress/blocked items, decisions, constraints, modified files, and next steps to `.context/context-handoff.json`
- **`/resume-context`** — Loads the handoff, orients the session, verifies against live git state
- **Prior-session deduplication** — Diffs `next_steps` against archived handoffs' `completed` arrays to flag stale items and resolved blockers

### issue-manager

Create and manage GitHub Issues using intent-focused templates. All issues define **what** and **why** — engineers decide **how**.

- Epic, Story, Task, and Bug templates with quality gates
- CLI script for bulk creation, import, update, and sync status
- Markdown-first workflow: author locally in `docs/epics/`, push to GitHub Issues
- INVEST story validation and intent-over-implementation enforcement

### session-analyzer

Analyze and extract conversations from Claude Code session JSONL files. Python 3.10+, zero dependencies.

- **`list`** — Discover session files by project or across all projects
- **`extract`** — Human-readable conversation transcript with optional tool calls, thinking blocks, and timestamps
- **`analyze`** — Session statistics: duration, token usage, cache hit rate, tool breakdown, files modified
- Streaming parser handles arbitrarily large session files
- Markdown or JSON output formats

## Installation

### Add the Marketplace

In Claude Code, open the plugin manager and add this marketplace:

```
/plugins marketplace add https://github.com/clafollett/lafollettlabs-claude-plugins
```

### Install Plugins

```
/plugins install context-handoff
/plugins install issue-manager
/plugins install session-analyzer
```

### Manual Installation

If you prefer not to use the marketplace:

**context-handoff** (global commands):
```sh
cp plugins/context-handoff/commands/handoff-context.md ~/.claude/commands/
cp plugins/context-handoff/commands/resume-context.md ~/.claude/commands/
```

**issue-manager** (per-project skill):
```sh
# From the target project root
cp -r plugins/issue-manager/skills/issue-manager .claude/skills/
```

**session-analyzer** (per-project skill):
```sh
cp -r plugins/session-analyzer/skills/session-analyzer .claude/skills/
```

## Repository Structure

```
.claude-plugin/
  marketplace.json              # Marketplace registry
plugins/
  code-reviewer/                # Plugin: PE-powered code reviews
    .claude-plugin/plugin.json
    skills/
      code-reviewer/            # Review engine
        SKILL.md
        assets/                 # Report template
        references/             # PE reference files (pe-backend, pe-frontend, pe-devops)
      init-project/             # Project bootstrapper
        SKILL.md
        assets/                 # .code-reviewer.yml template
  context-handoff/              # Plugin: session handoff + resume
    .claude-plugin/plugin.json
    commands/
      handoff-context.md
      resume-context.md
  issue-manager/                # Plugin: GitHub Issue management
    .claude-plugin/plugin.json
    skills/
      issue-manager/
        SKILL.md
        references/             # Issue templates + quality checklist
        scripts/                # gh-issues.js CLI
  session-analyzer/             # Plugin: session JSONL analysis
    .claude-plugin/plugin.json
    skills/
      session-analyzer/
        SKILL.md
        scripts/                # session-analyzer.py CLI
```

## Contributing

1. Edit plugin files in this repo (source of truth)
2. Bump `version` in the plugin's `.claude-plugin/plugin.json`
3. Commit and push
4. Consumers pull updates via `/plugins update`

### Adding a New Plugin

1. Create `plugins/<name>/.claude-plugin/plugin.json` with name, description, version, author
2. Add commands, skills, agents, or hooks under the plugin directory
3. Add an entry to `.claude-plugin/marketplace.json`
4. Update this README with the plugin description

## License

MIT — LaFollett Labs LLC
