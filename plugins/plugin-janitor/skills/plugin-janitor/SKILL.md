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
# $CLAUDE_PLUGIN_ROOT is unset in some contexts, where it expands to /skills/...
JAN="${CLAUDE_PLUGIN_ROOT:-}/skills/plugin-janitor/scripts/janitor.py"
if [ ! -f "$JAN" ]; then
  JAN=$(python3 -c "
import json, pathlib, sys
reg = pathlib.Path.home() / '.claude/plugins/installed_plugins.json'
rel = 'skills/plugin-janitor/scripts/janitor.py'
try:
    plugins = json.loads(reg.read_text()).get('plugins') or {}
except Exception:
    plugins = {}
for key, entries in plugins.items() if isinstance(plugins, dict) else []:
    if key.partition('@')[0] != 'plugin-janitor':
        continue
    for entry in entries or []:
        script = pathlib.Path(entry.get('installPath', '')) / rel
        if script.is_absolute() and script.is_file():
            print(script); sys.exit(0)
sys.exit(1)
" || true)
fi

# `|| true` is load-bearing: find exits 1 with no ~/.claude/skills.
[ -f "$JAN" ] || JAN=$(find ~/.claude/skills -path "*/plugin-janitor/scripts/janitor.py" \
                        -print -quit 2>/dev/null || true)

[ -f "$JAN" ] || { echo "plugin-janitor: cannot resolve janitor.py" >&2; exit 1; }

python3 "$JAN"          # what would go, and what it frees
```

Stdlib only, so it runs on a bare `python3` with no venv.

| Flag | |
| - | - |
| `--root <path>` | a plugins directory other than `~/.claude/plugins` |
| `--yes` | actually delete |
| `--json` | machine-readable report; never deletes |
| `--allow-unreachable-registry` | delete when no install resolves to a real directory |

```
if the user asks to clean up or reclaim disk:
    run it with no flags, show the plan, stop
    # --yes deletes. It is the user's call, never yours to add
```

## What it will not do

Version deletion is limited to directories exactly three levels under `cache/`
(`<marketplace>/<plugin>/<version>`) that no `installPath` resolves to.
Symlinked version directories are skipped rather than followed.

A `<plugin>` or `<marketplace>` directory the sweep empties — or that was
already empty — goes too, by `rmdir` and never `rmtree`: one still holding
anything (a file, a symlink, a version that refused to go) survives, and so
does one some `installPath` still points into, including a dangling entry's.

`installed_plugins.json` decides what is reachable, so the run aborts rather
than guessing whenever it cannot be trusted:

| The registry | Result |
| - | - |
| missing, or not valid JSON | abort |
| not an object, or no `plugins` object | abort |
| an entry list that is not a list, or an entry that is not an object | abort |
| valid, but no install resolves to a directory that exists, beside a populated cache | abort on `--yes` unless `--allow-unreachable-registry`; the report still prints |

The last test is reachability, not emptiness: a registry naming sixteen plugins
whose paths all point at a home directory since renamed parses fine and is still
useless as an oracle.

## Registered but missing

The report also names plugins whose `installPath` has no directory. Janitor does
not create or delete those — it reports them.

```
if a plugin is registered but missing:
    say so; the fix is a reinstall, or removing the registry entry
    # do NOT edit installed_plugins.json to make the report clean
```
