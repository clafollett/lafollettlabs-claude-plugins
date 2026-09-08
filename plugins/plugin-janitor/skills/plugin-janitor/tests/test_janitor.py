#!/usr/bin/env python3
"""Tests for janitor. Stdlib only:

    python3 -m unittest discover -s tests -v
"""

from __future__ import annotations

import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import janitor as j  # noqa: E402


class CacheCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.cache = self.tmp / "cache"
        self.cache.mkdir()
        self.registry = {"plugins": {}}

    def version(self, marketplace, plugin, version, *, installed=False, size=100):
        d = self.cache / marketplace / plugin / version
        d.mkdir(parents=True)
        (d / "plugin.json").write_bytes(b"x" * size)
        if installed:
            key = f"{plugin}@{marketplace}"
            self.registry["plugins"].setdefault(key, []).append(
                {"installPath": str(d)})
        return d

    def write_registry(self):
        (self.tmp / j.REGISTRY).write_text(json.dumps(self.registry),
                                           encoding="utf-8")

    def run_it(self, **kw):
        self.write_registry()
        import argparse
        opts = dict(root=self.tmp, yes=False, json=False,
                    allow_unreachable_registry=False)
        opts.update(kw)
        buf = io.StringIO()
        with redirect_stdout(buf):
            j.main_with(argparse.Namespace(**opts))
        return buf.getvalue()


class TestStaleDetection(CacheCase):
    def test_an_uninstalled_version_is_stale(self) -> None:
        self.version("mk", "thing", "1.0.0")
        self.version("mk", "thing", "2.0.0", installed=True)
        out = self.run_it()
        self.assertIn("1.0.0", out)
        self.assertNotIn("2.0.0", out)

    def test_nothing_stale_says_so(self) -> None:
        self.version("mk", "thing", "2.0.0", installed=True)
        self.assertIn("nothing stale", self.run_it())

    def test_a_dry_run_deletes_nothing(self) -> None:
        d = self.version("mk", "thing", "1.0.0")
        self.version("mk", "thing", "2.0.0", installed=True)
        out = self.run_it()
        self.assertIn("dry run", out)
        self.assertTrue(d.is_dir())

    def test_yes_deletes_only_the_stale_one(self) -> None:
        old = self.version("mk", "thing", "1.0.0")
        live = self.version("mk", "thing", "2.0.0", installed=True)
        self.run_it(yes=True)
        self.assertFalse(old.exists())
        self.assertTrue(live.is_dir())

    def test_every_marketplace_and_plugin_is_swept(self) -> None:
        a = self.version("mk1", "one", "1.0.0")
        b = self.version("mk2", "two", "0.1.0")
        self.version("mk2", "two", "0.2.0", installed=True)
        self.run_it(yes=True)
        self.assertFalse(a.exists())
        self.assertFalse(b.exists())


class TestItRefusesToGuess(CacheCase):
    def test_a_missing_registry_stops_everything(self) -> None:
        """Without knowing what is installed, everything looks stale."""
        self.version("mk", "thing", "1.0.0")
        with self.assertRaises(SystemExit) as ctx:
            with redirect_stdout(io.StringIO()):
                import argparse
                j.main_with(argparse.Namespace(root=self.tmp, yes=True,
                                               json=False,
                                               allow_unreachable_registry=False))
        self.assertIn("refusing", str(ctx.exception))

    def test_a_corrupt_registry_stops_everything(self) -> None:
        self.version("mk", "thing", "1.0.0")
        (self.tmp / j.REGISTRY).write_text("{not json", encoding="utf-8")
        with self.assertRaises(SystemExit):
            with redirect_stdout(io.StringIO()):
                import argparse
                j.main_with(argparse.Namespace(root=self.tmp, yes=True,
                                               json=False,
                                               allow_unreachable_registry=False))

    def test_a_registry_that_is_not_an_object_stops_everything(self) -> None:
        self.version("mk", "thing", "1.0.0")
        (self.tmp / j.REGISTRY).write_text("[]", encoding="utf-8")
        with self.assertRaises(SystemExit):
            with redirect_stdout(io.StringIO()):
                import argparse
                j.main_with(argparse.Namespace(root=self.tmp, yes=True,
                                               json=False,
                                               allow_unreachable_registry=False))


class TestDepthIsTheSignature(CacheCase):
    def test_only_three_levels_deep_is_a_version(self) -> None:
        """The cache root and the plugin directory above a version are not
        versions, and a directory inside one is not either."""
        self.version("mk", "thing", "1.0.0", installed=True)
        loose = self.cache / "mk" / "stray"          # two levels
        loose.mkdir(parents=True)
        found = {v.path for v in j.versions(self.cache)}
        self.assertNotIn(loose, found)
        self.assertNotIn(self.cache / "mk", found)

    def test_remove_re_derives_the_shape(self) -> None:
        """versions() proved it, but remove() is what deletes."""
        outside = self.tmp / "not-the-cache"
        outside.mkdir()
        entry = j.Version(path=outside, marketplace="m", plugin="p",
                          version="v", bytes=0)
        with redirect_stdout(io.StringIO()) as buf:
            self.assertFalse(j.remove(entry, self.cache))
        self.assertIn("skipped", buf.getvalue())
        self.assertTrue(outside.is_dir())

    def test_a_symlinked_version_is_not_followed(self) -> None:
        real = self.tmp / "elsewhere"
        real.mkdir()
        (real / "big").write_bytes(b"y" * 50_000)
        try:
            (self.cache / "mk" / "thing").mkdir(parents=True)
            (self.cache / "mk" / "thing" / "1.0.0").symlink_to(real)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        self.assertEqual(j.versions(self.cache), [])
        self.assertTrue(real.is_dir())


class TestDanglingInstalls(CacheCase):
    def test_a_registered_path_with_no_directory_is_reported(self) -> None:
        self.registry["plugins"]["ghost@mk"] = [
            {"installPath": str(self.cache / "mk" / "ghost" / "0.1.0")}]
        out = self.run_it()
        self.assertIn("registered but missing", out)
        self.assertIn("ghost", out)

    def test_it_is_not_counted_as_reclaimable(self) -> None:
        self.registry["plugins"]["ghost@mk"] = [
            {"installPath": str(self.cache / "mk" / "ghost" / "0.1.0")}]
        self.version("mk", "thing", "1.0.0", installed=True)
        self.assertIn("nothing stale", self.run_it())

    def test_a_pre_existing_dangle_is_not_reported_as_a_bug(self) -> None:
        """It was already missing; janitor must not claim it broke it."""
        self.registry["plugins"]["ghost@mk"] = [
            {"installPath": str(self.cache / "mk" / "ghost" / "0.1.0")}]
        self.version("mk", "thing", "1.0.0")
        self.version("mk", "thing", "2.0.0", installed=True)
        out = self.run_it(yes=True)
        self.assertNotIn("THIS IS A BUG", out)
        self.assertIn("removed 1", out)


class TestReport(CacheCase):
    def test_json_never_deletes(self) -> None:
        d = self.version("mk", "thing", "1.0.0")
        self.version("mk", "thing", "2.0.0", installed=True)
        out = self.run_it(json=True, yes=True)
        self.assertTrue(d.is_dir())
        self.assertEqual(json.loads(out)["stale"][0]["version"], "1.0.0")

    def test_control_characters_never_reach_the_table(self) -> None:
        """The plan is what a person reads before authorising a delete."""
        self.version("mk", "thing\x1b[2K", "1.0.0")
        self.version("mk", "keep", "2.0.0", installed=True)
        self.assertNotIn("\x1b", self.run_it())

    def test_bytes_freed_counts_only_what_went(self) -> None:
        self.version("mk", "thing", "1.0.0", size=1000)
        self.version("mk", "thing", "2.0.0", installed=True)
        out = self.run_it(yes=True)
        self.assertIn("removed 1", out)
        self.assertIn("verified", out)


class TestEmptyDirectories(CacheCase):
    """Removing a plugin's last version leaves the directory it lived in.

    Found by running it: the screenscribe -> watchwith rename emptied a plugin
    directory that no later sweep would ever name again, because `versions`
    only sees three levels down.
    """

    def test_a_plugin_directory_goes_with_its_last_version(self) -> None:
        old = self.version("mk", "gone", "1.0.0")
        self.version("mk", "kept", "2.0.0", installed=True)
        self.run_it(yes=True)
        self.assertFalse(old.exists())
        self.assertFalse((self.cache / "mk" / "gone").exists())
        self.assertTrue((self.cache / "mk" / "kept").is_dir())

    def test_a_plugin_with_a_surviving_version_keeps_its_directory(self) -> None:
        self.version("mk", "thing", "1.0.0")
        self.version("mk", "thing", "2.0.0", installed=True)
        self.run_it(yes=True)
        self.assertTrue((self.cache / "mk" / "thing").is_dir())

    def test_a_marketplace_goes_when_its_last_plugin_does(self) -> None:
        self.version("dead", "gone", "1.0.0")
        self.version("live", "kept", "2.0.0", installed=True)
        self.run_it(yes=True)
        self.assertFalse((self.cache / "dead").exists())
        self.assertTrue((self.cache / "live").is_dir())

    def test_an_already_empty_directory_is_swept(self) -> None:
        """The real case: the versions went in an earlier run, the shell stayed."""
        shell = self.cache / "mk" / "ghost"
        shell.mkdir(parents=True)
        self.version("mk", "kept", "2.0.0", installed=True)
        out = self.run_it(yes=True)
        self.assertFalse(shell.exists())
        self.assertIn("pruned 1", out)

    def test_it_is_reported_with_nothing_else_to_do(self) -> None:
        """No stale versions must not short-circuit past an empty directory."""
        shell = self.cache / "mk" / "ghost"
        shell.mkdir(parents=True)
        self.version("mk", "kept", "2.0.0", installed=True)
        out = self.run_it()
        self.assertNotIn("nothing stale", out)
        self.assertIn("mk/ghost", out)
        self.assertTrue(shell.is_dir())

    def test_a_dry_run_predicts_it_without_deleting(self) -> None:
        self.version("mk", "gone", "1.0.0")
        self.version("mk", "kept", "2.0.0", installed=True)
        out = self.run_it()
        self.assertIn("mk/gone", out)
        self.assertTrue((self.cache / "mk" / "gone").is_dir())

    def test_a_stray_file_keeps_the_directory(self) -> None:
        """`rmdir` would refuse anyway; the plan must not claim otherwise."""
        old = self.version("mk", "gone", "1.0.0")
        (self.cache / "mk" / "gone" / "NOTES.md").write_text("x")
        self.version("mk", "kept", "2.0.0", installed=True)
        out = self.run_it(yes=True)
        self.assertFalse(old.exists())
        self.assertTrue((self.cache / "mk" / "gone").is_dir())
        self.assertNotIn("pruned", out)

    def test_a_symlink_keeps_the_directory(self) -> None:
        self.version("mk", "kept", "2.0.0", installed=True)
        real = self.tmp / "elsewhere"
        real.mkdir()
        try:
            (self.cache / "mk" / "gone").mkdir(parents=True)
            (self.cache / "mk" / "gone" / "1.0.0").symlink_to(real)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        self.run_it(yes=True)
        self.assertTrue((self.cache / "mk" / "gone").is_dir())
        self.assertTrue(real.is_dir())

    def test_json_lists_it_and_deletes_nothing(self) -> None:
        shell = self.cache / "mk" / "ghost"
        shell.mkdir(parents=True)
        self.version("mk", "kept", "2.0.0", installed=True)
        out = self.run_it(json=True, yes=True)
        self.assertEqual(json.loads(out)["emptied"], [str(shell)])
        self.assertTrue(shell.is_dir())


class TestPruneRefuses(CacheCase):
    def test_it_will_not_touch_the_cache_root(self) -> None:
        with redirect_stdout(io.StringIO()) as buf:
            self.assertFalse(j.prune(self.cache, self.cache))
        self.assertIn("skipped", buf.getvalue())
        self.assertTrue(self.cache.is_dir())

    def test_it_will_not_go_outside_the_cache(self) -> None:
        outside = self.tmp / "not-the-cache"
        outside.mkdir()
        with redirect_stdout(io.StringIO()) as buf:
            self.assertFalse(j.prune(outside, self.cache))
        self.assertIn("skipped", buf.getvalue())
        self.assertTrue(outside.is_dir())

    def test_it_will_not_reach_version_depth(self) -> None:
        """A version directory is `remove`'s job, and it is not empty."""
        d = self.version("mk", "thing", "1.0.0")
        with redirect_stdout(io.StringIO()) as buf:
            self.assertFalse(j.prune(d, self.cache))
        self.assertIn("skipped", buf.getvalue())
        self.assertTrue(d.is_dir())

    def test_rmdir_is_the_backstop_for_a_non_empty_directory(self) -> None:
        """Even told to, it cannot take something that still holds a file."""
        self.version("mk", "thing", "1.0.0")
        with redirect_stdout(io.StringIO()) as buf:
            self.assertFalse(j.prune(self.cache / "mk" / "thing", self.cache))
        self.assertIn("skipped", buf.getvalue())
        self.assertTrue((self.cache / "mk" / "thing").is_dir())


class TestARegistryItCannotReadStopsEverything(CacheCase):
    """The guard exists because an unreadable registry makes the whole cache
    look unreachable. Parsing is not reading: a file can be valid JSON and a
    dict and still name no installs, and the first version of this guard let
    every one of those through to `--yes`."""

    def shapes(self):
        return [
            ("plugins is null", {"plugins": None}),
            ("plugins is a list", {"plugins": []}),
            ("entries became an object", {"plugins": {"a@mk": {"installPath": "/x"}}}),
            ("entry is a bare string", {"plugins": {"a@mk": ["/x"]}}),
        ]

    def test_every_unrecognised_shape_aborts_with_the_cache_intact(self) -> None:
        for label, reg in self.shapes():
            with self.subTest(shape=label):
                d = self.version("mk", "thing", "1.0.0")
                (self.tmp / j.REGISTRY).write_text(json.dumps(reg), encoding="utf-8")
                import argparse
                with self.assertRaises(SystemExit) as ctx:
                    with redirect_stdout(io.StringIO()):
                        j.main_with(argparse.Namespace(
                            root=self.tmp, yes=True, json=False,
                            allow_unreachable_registry=False))
                self.assertIn("may be out of date with the registry format", str(ctx.exception))
                self.assertTrue(d.is_dir())
                shutil.rmtree(self.cache); self.cache.mkdir()

    def test_a_registry_whose_installs_all_dangle_is_refused(self) -> None:
        """Found in round 2: the first guard tested for zero entries, so a
        registry full of entries that all point at a home directory which has
        since been renamed sailed through and took the whole cache."""
        a = self.version("mk", "one", "1.0.0")
        b = self.version("mk", "two", "2.0.0")
        self.registry["plugins"]["one@mk"] = [
            {"installPath": "/moved/cache/mk/one/1.0.0"}]
        self.registry["plugins"]["two@mk"] = [
            {"installPath": "/moved/cache/mk/two/2.0.0"}]
        with self.assertRaises(SystemExit) as ctx:
            self.run_it(yes=True)
        self.assertIn("resolves to a directory that exists", str(ctx.exception))
        self.assertTrue(a.is_dir())
        self.assertTrue(b.is_dir())

    def test_one_resolvable_install_is_enough_to_proceed(self) -> None:
        """The guard must not fire on a healthy registry that merely also
        carries a dangling entry — that is the common case, not the alarming one."""
        old_ = self.version("mk", "gone", "1.0.0")
        self.version("mk", "kept", "2.0.0", installed=True)
        self.registry["plugins"]["ghost@mk"] = [
            {"installPath": "/nonexistent/0.1.0"}]
        out = self.run_it(yes=True)
        self.assertFalse(old_.exists())
        self.assertIn("removed 1", out)

    def test_a_relative_install_path_aborts(self) -> None:
        """It resolves against the process cwd, so reachability would depend on
        where janitor was run from. Beside one absolute entry — which keeps the
        reachability guard quiet — it deleted a live install, and the
        self-check stayed silent because the path was already counted as
        dangling."""
        rel = self.version("mk", "p", "2.0.0")
        keep = self.version("mk", "q", "1.0.0", installed=True)
        self.registry["plugins"]["p@mk"] = [
            {"installPath": "cache/mk/p/2.0.0"}]
        with self.assertRaises(SystemExit) as ctx:
            self.run_it(yes=True)
        self.assertIn("relative installPath", str(ctx.exception))
        self.assertTrue(rel.is_dir())
        self.assertTrue(keep.is_dir())

    def test_no_installs_beside_a_populated_cache_is_refused(self) -> None:
        """The wipe this guard was written for: registry says nothing is
        installed, so every version looks stale, so --yes takes all of them."""
        a = self.version("mk", "one", "1.0.0")
        b = self.version("mk", "two", "2.0.0")
        with self.assertRaises(SystemExit) as ctx:
            self.run_it(yes=True)
        self.assertIn("Refusing to delete", str(ctx.exception))
        self.assertTrue(a.is_dir())
        self.assertTrue(b.is_dir())

    def test_the_dry_run_still_reports_it(self) -> None:
        """The plan stays visible — only the deletion is gated."""
        self.version("mk", "one", "1.0.0")
        out = self.run_it()
        self.assertIn("1.0.0", out)
        self.assertIn("dry run", out)

    def test_the_escape_hatch_is_its_own_flag(self) -> None:
        """Someone who really did uninstall everything can still sweep."""
        a = self.version("mk", "one", "1.0.0")
        out = self.run_it(yes=True, allow_unreachable_registry=True)
        self.assertFalse(a.exists())
        self.assertIn("removed 1", out)

    def test_yes_alone_does_not_imply_it(self) -> None:
        self.version("mk", "one", "1.0.0")
        with self.assertRaises(SystemExit):
            self.run_it(yes=True, allow_unreachable_registry=False)


class TestItLeavesRegisteredDirectoriesAlone(CacheCase):
    def test_a_dangling_installs_empty_directory_survives(self) -> None:
        """The report names it as untouched in the same run. Deleting it made
        the tool contradict itself, and helped no reinstall."""
        shell = self.cache / "mk" / "ghost"
        shell.mkdir(parents=True)
        self.registry["plugins"]["ghost@mk"] = [
            {"installPath": str(shell / "0.1.0")}]
        self.version("mk", "kept", "2.0.0", installed=True)
        out = self.run_it(yes=True)
        self.assertIn("registered but missing", out)
        self.assertTrue(shell.is_dir())

    def test_an_unregistered_empty_directory_still_goes(self) -> None:
        shell = self.cache / "mk" / "orphan"
        shell.mkdir(parents=True)
        self.version("mk", "kept", "2.0.0", installed=True)
        self.run_it(yes=True)
        self.assertFalse(shell.exists())


class TestIdentityNotSpelling(CacheCase):
    def test_a_case_differing_install_path_is_not_stale(self) -> None:
        """macOS is case-insensitive by default, so a registry recording
        cache/MKT/... for a directory on disk at cache/mkt/... passed is_dir()
        — reachable, guard silent — then failed string equality and the live
        install was deleted. The self-check caught it after the fact."""
        d = self.version("mkt", "plug", "1.0.0")
        odd = str(self.cache / "MKT" / "plug" / "1.0.0")
        if not (self.cache / "MKT").is_dir():
            self.skipTest("case-sensitive filesystem")
        self.registry["plugins"]["plug@mkt"] = [{"installPath": odd}]
        out = self.run_it(yes=True)
        self.assertNotIn("THIS IS A BUG", out)
        self.assertTrue(d.is_dir())

    def test_a_path_with_dot_dot_segments_is_not_stale(self) -> None:
        """`os.stat` cannot walk through a missing intermediate component, so
        `<cache>/mk/nothere/../keep/1.0.0` failed where the string comparison
        this replaced normalised it lexically — the install was classed dangling
        and the reachability guard refused the whole run over it."""
        d = self.version("mk", "keep", "1.0.0")
        odd = str(self.cache / "mk" / "nothere" / ".." / "keep" / "1.0.0")
        self.registry["plugins"]["keep@mk"] = [{"installPath": odd}]
        out = self.run_it(yes=True)
        self.assertIn("nothing stale", out)
        self.assertTrue(d.is_dir())

    def test_a_trailing_separator_is_not_stale(self) -> None:
        d = self.version("mkt", "plug", "1.0.0")
        self.registry["plugins"]["plug@mkt"] = [{"installPath": str(d) + os.sep}]
        self.run_it(yes=True)
        self.assertTrue(d.is_dir())

    def test_a_genuinely_different_directory_is_still_stale(self) -> None:
        """Identity must not make everything look installed."""
        old = self.version("mkt", "plug", "1.0.0")
        self.version("mkt", "plug", "2.0.0", installed=True)
        self.run_it(yes=True)
        self.assertFalse(old.exists())


class TestNotKnowingIsNotGroundsForDeleting(CacheCase):
    def test_a_version_whose_identity_is_unknown_is_not_stale(self) -> None:
        """A stat that fails between the walk and the staleness test yields an
        identity of None. None is in no set, so the version fell through to
        stale and --yes deleted a live install — the self-check said so, after
        the deletion."""
        live = self.version("mk", "keep", "2.0.0", installed=True)
        # A second reachable install, so the unreachable-registry guard cannot
        # fire and mask the behaviour under test.
        self.version("mk", "other", "1.0.0", installed=True)
        real = j.ident
        victim = os.path.realpath(live)
        self.addCleanup(setattr, j, "ident", real)

        def blind(path):
            try:
                unknown = os.path.realpath(path) == victim
            except OSError:
                unknown = False
            return None if unknown else real(path)

        j.ident = blind
        out = self.run_it(yes=True)
        self.assertNotIn("THIS IS A BUG", out)
        self.assertTrue(live.is_dir())


class TestThePlanIsReconciled(CacheCase):
    def test_a_directory_the_plan_promised_but_kept_is_reported(self) -> None:
        """A refusal used to leave the printed plan quietly unfulfilled."""
        old = self.version("mk", "gone", "1.0.0")
        self.version("mk", "kept", "2.0.0", installed=True)
        (old / "NOTES.md").write_text("x")
        os.chmod(old, 0o555)
        self.addCleanup(os.chmod, old, 0o755)
        out = self.run_it(yes=True)
        self.assertIn("mk/gone", out)
        self.assertIn("kept", out)
        self.assertTrue((self.cache / "mk" / "gone").is_dir())


class TestHuman(unittest.TestCase):
    def test_units(self) -> None:
        self.assertEqual(j.human(0), "0B")
        self.assertEqual(j.human(2048), "2.0K")
        self.assertEqual(j.human(3 * 1024 ** 3), "3.0G")


if __name__ == "__main__":
    unittest.main()
