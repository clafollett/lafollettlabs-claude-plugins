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
# Symlink into your global commands directory
ln -sf "$(pwd)/commands/handoff-context.md" ~/.claude/commands/handoff-context.md
ln -sf "$(pwd)/commands/resume-context.md" ~/.claude/commands/resume-context.md
```

**Skills** (per-project, copy or symlink into target repo):
```sh
# From the target project root
cp -r /path/to/lafollettlabs-claude-plugins/skills/issue-manager .claude/skills/
# Or symlink
ln -sf /path/to/lafollettlabs-claude-plugins/skills/issue-manager .claude/skills/issue-manager
```

## Contributing

Edit files here, commit, push. Pull updates in consuming projects.
Commands symlinked to `~/.claude/commands/` update automatically on `git pull`.
