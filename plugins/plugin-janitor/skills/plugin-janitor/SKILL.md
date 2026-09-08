---
name: plugin-janitor
description: Remove cached plugin versions that no install points at. Use when the user asks to clean up the plugin cache, reclaim disk from ~/.claude/plugins, prune old or stale plugin versions, or asks why the cache keeps growing after marketplace updates. Also use to report plugins that are registered as installed but whose files are missing.
argument-hint: "[nothing, to report | --yes, to delete]"
---

# Plugin Janitor

`/plugin marketplace update` copies each bumped plugin into
`cache/<marketplace>/<plugin>/<version>/`. It never sweeps, so every version
ever installed is still on disk.

`installed_plugins.json` records one `installPath` per plugin. A version
directory no `installPath` points at is unreachable — nothing loads it.

## Run it

```bash
JAN="$CLAUDE_PLUGIN_ROOT/skills/plugin-janitor/scripts/janitor.py"
python3 "$JAN"          # what would go, and what it frees
python3 "$JAN" --yes    # delete it
python3 "$JAN" --json   # machine-readable; never deletes
```

Stdlib only, so it runs on a bare `python3` with no venv.

| Flag | |
| - | - |
| `--root <path>` | a plugins directory other than `~/.claude/plugins` |
| `--yes` | actually delete |
| `--json` | report only |

```
if the user asks to clean up or reclaim disk:
    run it with no flags, show the plan, stop
    # --yes deletes. It is the user's call, never yours to add
```

## What it will not do

Version deletion is limited to directories exactly three levels under `cache/`
(`<marketplace>/<plugin>/<version>`) that no `installPath` resolves to.
Symlinked version directories are skipped rather than followed. A missing or
unparseable `installed_plugins.json` aborts the run — without it every version
looks unreachable.

A `<plugin>` or `<marketplace>` directory left empty by that sweep goes too, by
`rmdir` and never `rmtree`: one still holding anything — a file, a symlink, a
version that refused to go — survives.

## Registered but missing

The report also names plugins whose `installPath` has no directory. Janitor does
not create or delete those — it reports them.

```
if a plugin is registered but missing:
    say so; the fix is a reinstall, or removing the registry entry
    # do NOT edit installed_plugins.json to make the report clean
```
