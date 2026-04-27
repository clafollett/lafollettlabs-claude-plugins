# LaFollett Labs — Claude Plugins

Cross-project Claude Code plugins maintained by LaFollett Labs LLC.
Marketplace-installable via `/plugins`.

## Structure

```
.claude-plugin/
  marketplace.json          # Marketplace registry — lists all plugins
plugins/
  context-handoff/          # /handoff-context + /resume-context + context monitoring
    .claude-plugin/plugin.json
    commands/
      handoff-context.md
      resume-context.md
    hooks/
      hooks.json              # Stop hook — context usage monitor
    scripts/
      context-monitor.sh      # Token tracking + threshold warnings
  issue-manager/            # /issue-manager — GitHub Issue management
    .claude-plugin/plugin.json
    skills/
      issue-manager/
        SKILL.md
        references/
        scripts/
  session-analyzer/         # /session-analyzer — JSONL session analysis
    .claude-plugin/plugin.json
    skills/
      session-analyzer/
        SKILL.md
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

### Version bumping (required on every edit)

**Every change to a plugin's content MUST include a patch version bump** in the `.claude-plugin/marketplace.json` and that plugin's `.<plugin-name>/plugin.json`. Without a version bump, downstream consumers running `/plugins update` may not pick up the change — the marketplace uses the version field to detect updates.

- Bug fix or text change → bump patch (e.g., `1.0.0` → `1.0.1`)
- New feature or command → bump minor (e.g., `1.0.1` → `1.1.0`)
- Breaking change → bump major (e.g., `1.1.0` → `2.0.0`)
