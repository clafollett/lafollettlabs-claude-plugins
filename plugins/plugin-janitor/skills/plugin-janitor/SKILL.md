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

`$CLAUDE_PLUGIN_ROOT` is not set in every context this runs in, and unset it
expands to `/skills/...`, which does not exist. Fall back to the registry, which
records an `installPath` per install:

```bash
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

[ -f "$JAN" ] || { echo "plugin-janitor: cannot resolve janitor.py" >&2; exit 1; }

python3 "$JAN"          # what would go, and what it frees
python3 "$JAN" --yes    # delete it
```

Stdlib only, so it runs on a bare `python3` with no venv.

| Flag | |
| - | - |
| `--root <path>` | a plugins directory other than `~/.claude/plugins` |
| `--yes` | actually delete |
| `--json` | machine-readable report; never deletes |
| `--allow-empty-registry` | delete when the registry lists no installs at all |

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
| valid, but naming no installs at all, beside a populated cache | abort unless `--allow-empty-registry` |

The last one is the whole cache. An install-less registry is what "the user
uninstalled everything" looks like, and equally what "this tool can no longer
read the registry" looks like; the second is unrecoverable by the person who
would have to notice it, so it decides the default.

## Registered but missing

The report also names plugins whose `installPath` has no directory. Janitor does
not create or delete those — it reports them.

```
if a plugin is registered but missing:
    say so; the fix is a reinstall, or removing the registry entry
    # do NOT edit installed_plugins.json to make the report clean
```
