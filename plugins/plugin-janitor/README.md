# plugin-janitor

`/plugin marketplace update` copies each bumped plugin into
`cache/<marketplace>/<plugin>/<version>/`. It copies; it never sweeps. Every
version you have ever installed is still on disk.

```
/plugin install plugin-janitor
```

Standard library only — it runs on a bare `python3`, which matters because the
thing being repaired is your plugin install.

## Skills

| Skill | |
| - | - |
| `/plugin-janitor:plugin-janitor` | report unreachable cached versions, and delete them on request |

## Usage

```text
You: /plugin-janitor:plugin-janitor
You: clean up my plugin cache
You: why does ~/.claude/plugins keep growing?
```

It always reports first and stops. Nothing is deleted until you say so:

```text
remove screenscribe         0.7.2            225.7K  lafollett-labs-claude-plugins
remove screenscribe         0.7.5            228.7K  lafollett-labs-claude-plugins

2 of 19 versions, 454.4K
dry run — nothing removed. Re-run with --yes to delete.

You: --yes
```

## Tips

**Run it after a rename or an uninstall, not just when disk is tight.** That is
when whole plugins go unreachable at once — an uninstalled plugin leaves every
version it ever had, plus the empty directory they lived in.

**`installed_plugins.json` is the oracle.** A version directory that no
`installPath` resolves to is dead: nothing loads it, and no rollback consults
it. If that file is missing or corrupt the run aborts rather than guessing —
without it, *everything* looks unreachable.

**"Registered but missing" is a different problem, and janitor will not fix
it.** That is a plugin claiming to be installed with no files on disk. The fix
is a reinstall or removing the registry entry by hand. Janitor reports it and
stops, deliberately — editing the registry to make its own report clean is
exactly the wrong move.

**Nothing it deletes is recoverable from cache.** It is recoverable from the
marketplace, which is where versions come from anyway. There is no rollback that
reads an old cache directory.

**`--json` never deletes**, whatever else you pass it. Useful for scripting a
disk report.
