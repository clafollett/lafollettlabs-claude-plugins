# LaFollett Labs — Claude Plugins

Cross-project Claude Code plugins maintained by LaFollett Labs LLC.
Marketplace-installable via `/plugins`.

## Structure

```
.claude-plugin/
  marketplace.json          # Marketplace registry — lists all plugins
plugins/
  context-handoff/          # /handoff-context + /resume-context
    .claude-plugin/plugin.json
    commands/
      handoff-context.md
      resume-context.md
  issue-manager/            # /issue-manager — GitHub Issue management
    .claude-plugin/plugin.json
    skills/
      issue-manager/
        SKILL.md
        references/
        scripts/
```

## Installation

Add the marketplace, then install individual plugins:
```
/plugins marketplace add https://github.com/clafollett/lafollettlabs-claude-plugins
/plugins install context-handoff
/plugins install issue-manager
```

## Contributing

This repo is the source of truth. Each plugin is independently versioned.
Edit here, commit, push. Consumers pull updates via `/plugins update`.
