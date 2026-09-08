#!/usr/bin/env python3
"""
janitor — remove plugin versions the installer left behind.

`/plugin marketplace update` fetches the whole marketplace repo, then copies
each plugin whose version changed into `cache/<marketplace>/<plugin>/<version>/`.
It copies; it does not sweep. Every bump you have ever shipped is still on disk:
measured on one machine, 72 version bumps across six plugins, each one its own
directory, none of them reachable.

Reachability is the whole question, and `installed_plugins.json` answers it: it
records one `installPath` per installed plugin. A version directory that no
`installPath` points at is dead — nothing loads it, and no rollback consults it.

Removing those leaves a second kind of litter: uninstall or rename a plugin and
the `<plugin>` directory its versions lived in survives them, empty. So does a
`<marketplace>` whose last plugin went. Both get swept, by `rmdir` alone.

Stdlib only. This runs before any venv exists, and on a machine whose plugins
are the thing being repaired.

Usage:
    ./janitor.py            # what would go, and what it would free
    ./janitor.py --yes      # actually remove it
    ./janitor.py --json     # machine-readable, never deletes

A registry in which no install resolves to a directory that exists is refused
rather than treated as "every version is stale" — pass
--allow-unreachable-registry when the cache really is all stale.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

PLUGINS = Path("~/.claude/plugins")
CACHE = "cache"
REGISTRY = "installed_plugins.json"

# Every shape check below exits with this. Failing closed is right for something
# that deletes — but a bare "refusing to guess" reads as a bug in the registry
# when the likelier cause is that this tool is a version behind the format.
SCHEMA_DRIFT = ("This tool may be out of date with the registry format. It "
                "deletes nothing until it\n  can read it — update plugin-janitor, "
                "or report the shape above.")

# Names come off the filesystem and out of a JSON manifest, and land in a table
# a person reads before authorising a delete. ESC is not whitespace, so
# `str.split` leaves it and a crafted name could rewrite rows in that table.
CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")


@dataclass
class Version:
    """One `cache/<marketplace>/<plugin>/<version>` directory."""
    path: Path
    marketplace: str
    plugin: str
    version: str
    bytes: int


def clean(text: str, width: int = 0) -> str:
    text = " ".join(CONTROL.sub("", str(text)).split())
    if width and len(text) > width:
        return text[:width - 1] + "…"
    return text


def human(n: float) -> str:
    for unit in ("B", "K", "M", "G"):
        if n < 1024:
            return f"{n:.0f}{unit}" if unit == "B" else f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}T"


def dir_bytes(path: Path) -> int:
    """Bytes under `path`, counting symlinks as links.

    Never follows them: a link pointing out of the cache would inflate the
    figure this tool reports as reclaimable, and a link loop would hang the walk.
    """
    total = 0
    for root, _dirs, files in os.walk(path, followlinks=False):
        for name in files:
            try:
                total += os.lstat(os.path.join(root, name)).st_size
            except OSError:
                continue
    return total


def installed(root: Path) -> tuple[set[str], list[tuple[str, str, str]]]:
    """Resolved `installPath`s, and the ones whose directory is gone.

    The second list is not this tool's problem to fix — it is a plugin that
    claims to be installed and has no files — but finding it while walking the
    same registry costs nothing, and silence would be the wrong report.
    """
    try:
        data = json.loads((root / REGISTRY).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        sys.exit(f"cannot read {root / REGISTRY}: {e}\n"
                 f"  refusing to delete anything without knowing what is installed")
    if not isinstance(data, dict):
        sys.exit(f"{root / REGISTRY} is not a JSON object — refusing to guess")

    # Every branch below exits rather than skipping. A shape this function does
    # not recognise is indistinguishable from a schema it has not been taught,
    # and the failure mode of guessing is that `live` comes back empty and every
    # cached version looks unreachable — which is the whole cache.
    plugins = data.get("plugins")
    if not isinstance(plugins, dict):
        sys.exit(f"{root / REGISTRY} has no 'plugins' object.\n"
                 f"  {SCHEMA_DRIFT}")

    live, dangling = set(), []
    for key, entries in plugins.items():
        if not isinstance(entries, list):
            sys.exit(f"{root / REGISTRY}: {key!r} is not a list of installs.\n"
                     f"  {SCHEMA_DRIFT}")
        for entry in entries:
            if not isinstance(entry, dict):
                sys.exit(f"{root / REGISTRY}: {key!r} holds a non-object entry.\n"
                         f"  {SCHEMA_DRIFT}")
            raw = entry.get("installPath")
            if not raw:
                continue
            # An installPath is absolute. A relative one resolves against the
            # process working directory, so whether an install looks reachable
            # would depend on where janitor was run from — and beside one
            # absolute entry, which keeps the reachability guard quiet, that
            # deletes a live install with the self-check none the wiser,
            # because the path is already accounted for as dangling.
            if not Path(raw).is_absolute():
                sys.exit(f"{root / REGISTRY}: {key!r} has a relative "
                         f"installPath {raw!r}.\n  {SCHEMA_DRIFT}")
            path = Path(raw)
            resolved = str(path.resolve())
            live.add(resolved)
            # `is_dir` on the RESOLVED path, not the raw one. `resolve()`
            # normalises `..` lexically; `stat` cannot walk through a missing
            # intermediate component, so testing the raw string classed a real
            # install as dangling and the reachability guard then refused the
            # whole run over it.
            if not Path(resolved).is_dir():
                # Carried as (key, raw, resolved), not as a formatted string.
                # The final self-check compares against `live`, which holds
                # RESOLVED paths, and re-parsing a display line to recover one
                # got it wrong wherever the two differ — /var vs /private/var on
                # macOS was enough to make janitor accuse itself of deleting a
                # plugin that had been missing before it ran.
                dangling.append((key, raw, resolved))
    return live, dangling


def ident(path: str | Path) -> tuple[int, int] | None:
    """`(st_dev, st_ino)` — what actually identifies a directory.

    `str(Path(p).resolve())` was the test, and it is wrong on the filesystem
    this most often runs on. macOS is case-insensitive by default, so a registry
    that recorded `.../cache/MKT/plug/1.0.0` for a directory on disk at
    `.../cache/mkt/plug/1.0.0` passes `is_dir()` — the install is reachable and
    the guard is correctly silent — and then fails string equality, so the
    version is classed stale and the live install is deleted. The self-check
    catches it, loudly, after the fact.

    Identity settles case, symlinks, trailing separators and `..` in one move.
    """
    try:
        # `.resolve()` first, because `os.stat` cannot walk a path whose
        # intermediate component is missing (`a/x/../b` with no `x`) while the
        # string comparison this replaced normalised it lexically. Losing that
        # would turn such an entry unreachable and refuse the whole run.
        st = os.stat(Path(path).resolve())
    except OSError:
        return None
    return (st.st_dev, st.st_ino)


def versions(cache: Path) -> list[Version]:
    """Every version directory, at exactly `<marketplace>/<plugin>/<version>`.

    Depth is the signature. Anything shallower or deeper is not something this
    tool put a name to, so it is not something this tool removes.
    """
    found = []
    for marketplace in sorted(_dirs(cache)):
        for plugin in sorted(_dirs(marketplace)):
            for version in sorted(_dirs(plugin)):
                found.append(Version(
                    path=version,
                    marketplace=marketplace.name,
                    plugin=plugin.name,
                    version=version.name,
                    bytes=dir_bytes(version),
                ))
    return found


def _dirs(path: Path) -> list[Path]:
    try:
        return [p for p in path.iterdir() if p.is_dir() and not p.is_symlink()]
    except OSError:
        return []


def claimed(path: Path, registered: set[str]) -> bool:
    """True when some `installPath` still points inside `path`.

    A registered-but-missing plugin has an entry and no files, and its
    `<plugin>` directory is empty for that reason. `janitor does not touch
    these` is what the report says while naming it, so the sweep has to agree:
    the fix for a dangling entry is a reinstall or removing the entry, and
    neither is helped by deleting the directory the reinstall wants.
    """
    root = str(path.resolve())
    return any(r == root or r.startswith(root + os.sep) for r in registered)


def emptied(cache: Path, going: list[Version], registered: set[str]) -> list[Path]:
    """Plugin and marketplace directories holding nothing once `going` is gone.

    `versions` names things exactly three levels down, so the `<plugin>`
    directory above a plugin's last version is invisible to it. Uninstall or
    rename a plugin and the shell it lived in outlives every future sweep —
    the same litter this tool exists to remove, in the one shape it could not
    see. A `<marketplace>` whose last plugin goes has the same problem.

    Directories that were already empty count too — `_holds_only` is vacuously
    true on them. They got that way by the same route, and nothing else is ever
    going to mention them.

    Plugin directories lead the returned list. A marketplace is not empty until
    they are gone, and `prune` walks the list in order.
    """
    doomed = {v.path for v in going}
    plugins = sorted(p for m in _dirs(cache) for p in _dirs(m)
                     if _holds_only(p, doomed) and not claimed(p, registered))
    doomed |= set(plugins)
    markets = sorted(m for m in _dirs(cache)
                     if _holds_only(m, doomed) and not claimed(m, registered))
    return plugins + markets


def _holds_only(path: Path, doomed: set[Path]) -> bool:
    """True when every entry in `path` is already on its way out.

    `iterdir`, not `_dirs`: a stray file or a symlink is a reason to keep the
    directory, and filtering them out of the question would delete around them.
    """
    try:
        return all(kid in doomed for kid in path.iterdir())
    except OSError:
        return False


def prune(path: Path, cache: Path) -> bool:
    """rmdir one emptied directory, at one or two levels under the cache.

    `rmdir` rather than `rmtree`, and not merely as a matter of taste: it fails
    on a directory that still holds something, so an error in the arithmetic
    above costs a printed refusal instead of a plugin. The depth check bounds
    it from the other side — the cache root itself has no parents under `root`
    and is refused with everything deeper than a plugin.
    """
    resolved = path.resolve()
    root = cache.resolve()
    if root not in resolved.parents or len(resolved.relative_to(root).parts) > 2:
        print(f"   ! skipped {resolved}: not a <marketplace>[/<plugin>] "
              f"directory under {root}")
        return False
    try:
        resolved.rmdir()
    except OSError as e:
        print(f"   ! skipped {resolved}: {e}")
        return False
    return True


def remove(entry: Version, cache: Path) -> bool:
    """Delete one version directory, having re-derived that it is one.

    `versions` already proved the shape and `stale` already proved nothing
    points at it, but this is the function that deletes, so it re-checks
    containment instead of trusting its caller. A refusal is reported and the
    sweep continues — exiting here would leave the job half done and unsummarised.
    """
    path = entry.path.resolve()
    root = cache.resolve()
    if root not in path.parents or len(path.relative_to(root).parts) != 3:
        print(f"   ! skipped {path}: not a <marketplace>/<plugin>/<version> "
              f"directory under {root}")
        return False
    try:
        shutil.rmtree(path)
    except OSError as e:
        print(f"   ! skipped {path}: {e}")
        return False
    return True


def main() -> None:
    ap = argparse.ArgumentParser(
        description="remove plugin versions no install points at")
    ap.add_argument("--root", type=Path, default=None,
                    help=f"plugins directory (default {PLUGINS})")
    ap.add_argument("--yes", action="store_true",
                    help="actually delete; without it this is a dry run")
    ap.add_argument("--json", action="store_true",
                    help="machine-readable report; never deletes")
    ap.add_argument("--allow-unreachable-registry", action="store_true",
                    help="delete even when no install in the registry "
                         "resolves to a directory that exists; refused "
                         "without it")
    main_with(ap.parse_args())


def main_with(args: argparse.Namespace) -> None:
    root = (args.root or PLUGINS).expanduser()
    cache = root / CACHE
    if not cache.is_dir():
        sys.exit(f"no plugin cache at {cache}")

    live, dangling = installed(root)
    every = versions(cache)
    installed_ids = {i for i in (ident(r) for r in live) if i is not None}
    # `is not None` before the membership test, not just when building the set:
    # filtering None out of `installed_ids` protects the set, and the predicate
    # is what decides. A version whose stat fails between the walk above and
    # here — ESTALE on a network home, an autofs timeout, a concurrent
    # `marketplace update` — has an identity of None, None is in no set, and it
    # would fall straight through to stale and be deleted. Not knowing what a
    # directory is cannot be grounds for removing it.
    stale = [v for v in every
             if (i := ident(v.path)) is not None and i not in installed_ids]
    freed = sum(v.bytes for v in stale)
    empty = emptied(cache, stale, live)

    if args.json:
        print(json.dumps({
            "cache": str(cache),
            "installed": len(live),
            "versions": len(every),
            "stale": [{"marketplace": v.marketplace, "plugin": v.plugin,
                       "version": v.version, "bytes": v.bytes,
                       "path": str(v.path)} for v in stale],
            "reclaimable": freed,
            "emptied": [str(p) for p in empty],
            "dangling": [{"plugin": k, "path": raw} for k, raw, _ in dangling],
        }, indent=2))
        return

    if dangling:
        print("registered but missing from disk "
              "(reinstall, or remove the entry — janitor does not touch these):")
        for key, raw, _ in dangling:
            print(f"  ? {clean(key)} -> {clean(raw)}")
        print()

    if not stale and not empty:
        print(f"nothing stale — {len(every)} version"
              f"{'s' if len(every) != 1 else ''} on disk, all installed")
        return

    if stale:
        for v in stale:
            print(f"remove {clean(v.plugin, 20):<20} {clean(v.version, 14):<14} "
                  f"{human(v.bytes):>8}  {clean(v.marketplace, 30)}")
        print(f"\n{len(stale)} of {len(every)} versions, {human(freed)}")

    if empty:
        if stale:
            print()
        print(f"{len(empty)} empty "
              f"director{'y' if len(empty) == 1 else 'ies'} "
              f"left behind by plugins that are gone:")
        for path in empty:
            print(f"  - {clean(str(path.relative_to(cache)))}")

    if not args.yes:
        print("dry run — nothing removed. Re-run with --yes to delete.")
        return

    # Deliberately below the dry run and the --json report, so the plan is
    # always visible and only the deletion is gated.
    #
    # The test is whether ANY install resolves to a directory that is really
    # there — not whether the registry has entries. A registry listing sixteen
    # plugins whose paths all point at a home directory that has been renamed
    # parses fine, has entries, and is still useless as an oracle: every version
    # on disk looks unreachable and the sweep takes the whole cache. That state
    # is what "the user uninstalled everything" looks like, and equally what a
    # moved cache, a restored backup or a changed path scheme looks like. Only
    # the first is recoverable by the person who would have to notice, so the
    # rest decide the default.
    reachable = live - {resolved for _, _, resolved in dangling}
    if every and not reachable and not args.allow_unreachable_registry:
        sys.exit(f"no install in {root / REGISTRY} resolves to a directory that "
                 f"exists, but {cache}\n"
                 f"  holds {len(every)} version{'s' if len(every) != 1 else ''} — "
                 f"so every one of them looks unreachable, which is also exactly\n"
                 f"  how a moved cache or a registry this tool cannot read would "
                 f"look. Refusing to delete\n"
                 f"  the whole cache on that basis. If it really is all stale, "
                 f"re-run with --allow-unreachable-registry.")

    done = [v for v in stale if remove(v, cache)]
    if stale:
        # Recomputed from what actually went, not from the plan: a refusal must
        # not be reported as bytes freed.
        print(f"removed {len(done)}, freed {human(sum(v.bytes for v in done))}")

    # Recomputed against the filesystem the removals just left, so a version
    # that refused to go keeps the directory above it.
    swept = [d for d in emptied(cache, done, live) if prune(d, cache)]
    if swept:
        print(f"pruned {len(swept)} empty "
              f"director{'y' if len(swept) == 1 else 'ies'}")
    if len(swept) < len(empty):
        # The plan named these; a refusal above means they still hold something.
        # Saying nothing would leave the printed plan quietly unfulfilled.
        print(f"{len(empty) - len(swept)} planned "
              f"director{'y' if len(empty) - len(swept) == 1 else 'ies'} kept — "
              f"still holding something the sweep could not take")

    gone = [p for p in sorted(live) if not Path(p).is_dir()]
    already = {resolved for _, _, resolved in dangling}
    fresh = [g for g in gone if g not in already]
    if fresh:
        sys.exit("\n".join(["", "THIS IS A BUG — janitor removed a live install:"]
                           + [f"  {g}" for g in fresh]))
    print(f"verified: {len(live) - len(gone)}/{len(live)} installs intact")


if __name__ == "__main__":
    main()
