# LaFollett Labs — Claude Plugins

Cross-project Claude Code commands and skills maintained by LaFollett Labs LLC.

## Structure

```
commands/           # Slash commands (install to ~/.claude/commands/)
  handoff-context.md    # /handoff-context — save session state for resumption
  resume-context.md     # /resume-context — load prior session state
skills/             # Skills (install to .claude/skills/ in target project)
  issue-manager/        # /issue-manager — GitHub Issue management with intent-over-implementation
```

## Installation

**Commands** (global, apply to all projects):
```sh
cp commands/handoff-context.md ~/.claude/commands/
cp commands/resume-context.md ~/.claude/commands/
```

**Skills** (per-project, copy into target repo):
```sh
# From the target project root
cp -r /path/to/lafollettlabs-claude-plugins/skills/issue-manager .claude/skills/
```

## Contributing

This repo is the source of truth. Edit here, commit, push.
After pulling updates, re-copy changed files to `~/.claude/commands/` or target project `.claude/skills/`.
