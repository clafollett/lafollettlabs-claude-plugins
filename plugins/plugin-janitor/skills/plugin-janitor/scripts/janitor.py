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

Stdlib only. This runs before any venv exists, and on a machine whose plugins
are the thing being repaired.

Usage:
    ./janitor.py            # what would go, and what it would free
    ./janitor.py --yes      # actually remove it
    ./janitor.py --json     # machine-readable, never deletes
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

    live, dangling = set(), []
    for key, entries in (data.get("plugins") or {}).items():
        for entry in entries or []:
            if not isinstance(entry, dict):
                continue
            raw = entry.get("installPath")
            if not raw:
                continue
            path = Path(raw)
            resolved = str(path.resolve())
            live.add(resolved)
            if not path.is_dir():
                # Carried as (key, raw, resolved), not as a formatted string.
                # The final self-check compares against `live`, which holds
                # RESOLVED paths, and re-parsing a display line to recover one
                # got it wrong wherever the two differ — /var vs /private/var on
                # macOS was enough to make janitor accuse itself of deleting a
                # plugin that had been missing before it ran.
                dangling.append((key, raw, resolved))
    return live, dangling


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
    main_with(ap.parse_args())


def main_with(args: argparse.Namespace) -> None:
    root = (args.root or PLUGINS).expanduser()
    cache = root / CACHE
    if not cache.is_dir():
        sys.exit(f"no plugin cache at {cache}")

    live, dangling = installed(root)
    every = versions(cache)
    stale = [v for v in every if str(v.path.resolve()) not in live]
    freed = sum(v.bytes for v in stale)

    if args.json:
        print(json.dumps({
            "cache": str(cache),
            "installed": len(live),
            "versions": len(every),
            "stale": [{"marketplace": v.marketplace, "plugin": v.plugin,
                       "version": v.version, "bytes": v.bytes,
                       "path": str(v.path)} for v in stale],
            "reclaimable": freed,
            "dangling": [{"plugin": k, "path": raw} for k, raw, _ in dangling],
        }, indent=2))
        return

    if dangling:
        print("registered but missing from disk "
              "(reinstall, or remove the entry — janitor does not touch these):")
        for key, raw, _ in dangling:
            print(f"  ? {clean(key)} -> {clean(raw)}")
        print()

    if not stale:
        print(f"nothing stale — {len(every)} version"
              f"{'s' if len(every) != 1 else ''} on disk, all installed")
        return

    for v in stale:
        print(f"remove {clean(v.plugin, 20):<20} {clean(v.version, 14):<14} "
              f"{human(v.bytes):>8}  {clean(v.marketplace, 30)}")
    print(f"\n{len(stale)} of {len(every)} versions, {human(freed)}")

    if not args.yes:
        print("dry run — nothing removed. Re-run with --yes to delete.")
        return

    done = [v for v in stale if remove(v, cache)]
    # Recomputed from what actually went, not from the plan: a refusal must not
    # be reported as bytes freed.
    print(f"removed {len(done)}, freed {human(sum(v.bytes for v in done))}")

    gone = [p for p in sorted(live) if not Path(p).is_dir()]
    already = {resolved for _, _, resolved in dangling}
    fresh = [g for g in gone if g not in already]
    if fresh:
        sys.exit("\n".join(["", "THIS IS A BUG — janitor removed a live install:"]
                           + [f"  {g}" for g in fresh]))
    print(f"verified: {len(live) - len(gone)}/{len(live)} installs intact")


if __name__ == "__main__":
    main()
