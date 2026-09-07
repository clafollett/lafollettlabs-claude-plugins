#!/usr/bin/env python3
"""Tests for screenscribe. Stdlib only — run with:

    python3 -m unittest discover -s tests -v

Tests needing ffmpeg, Pillow, or imagehash skip themselves when those are
absent, so the pure-logic suite runs anywhere.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import screenscribe as sc  # noqa: E402

HAVE_FFMPEG = shutil.which("ffmpeg") is not None
try:
    import imagehash  # noqa: F401
    from PIL import Image  # noqa: F401
    HAVE_IMAGING = True
except ImportError:
    HAVE_IMAGING = False

try:
    import yt_dlp  # noqa: F401
    HAVE_YTDLP = True
except ImportError:
    HAVE_YTDLP = False


class TempDirCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)

    @staticmethod
    @contextmanager
    def silent():
        """Keep build progress out of the suite's own output."""
        buf = io.StringIO()
        with redirect_stdout(buf):
            yield buf


# --------------------------------------------------------------------------
class TestTime(unittest.TestCase):
    def test_hhmmss(self) -> None:
        self.assertEqual(sc.hhmmss(0), "00:00:00")
        self.assertEqual(sc.hhmmss(61.9), "00:01:01")
        self.assertEqual(sc.hhmmss(3661), "01:01:01")
        self.assertEqual(sc.hhmmss(45, sep="-"), "00-00-45")

    def test_parse_span_forms(self) -> None:
        self.assertEqual(sc.parse_span("45"), 45)
        self.assertEqual(sc.parse_span("12:30"), 750)
        self.assertEqual(sc.parse_span("01:02:03"), 3723)
        self.assertEqual(sc.parse_span(" 12:30 "), 750)

    def test_parse_span_rejects_garbage(self) -> None:
        for bad in ("abc", "", "1:2:3:4", "12:ab", "-5", "1.5"):
            with self.subTest(bad=bad), self.assertRaises(SystemExit):
                sc.parse_span(bad)

    def test_roundtrip(self) -> None:
        for s in ("00:00:00", "00:12:34", "02:03:04"):
            self.assertEqual(sc.hhmmss(sc.parse_span(s)), s)


# --------------------------------------------------------------------------
class TestParseVtt(TempDirCase):
    def parse(self, body: str) -> list[sc.Cue]:
        p = self.tmp / "s.vtt"
        p.write_text(body, encoding="utf-8")
        return sc.parse_vtt(p)

    def test_youtube_rolling_captions_are_not_duplicated(self) -> None:
        """The real regression: YouTube repeats the previous cue's tail.

        Whole-cue comparison catches only the exact repeats, leaving the
        transcript ~2.4x duplicated.
        """
        rolling = [
            "hey everyone welcome",
            "hey everyone welcome to another video",
            "to another video today we build",
            "today we build a small thing",
            "a small thing that reads frames",
            "that reads frames from the disk",
            "from the disk and prints them",
            "and prints them in order",
            "in order by their timestamp",
        ]
        body = "WEBVTT\nKind: captions\n\n" + "".join(
            f"00:00:{i*3:02d}.000 --> 00:00:{(i+1)*3:02d}.000\n{txt}\n\n"
            for i, txt in enumerate(rolling)
        )
        cues = self.parse(body)
        joined = " ".join(c.text for c in cues)
        self.assertEqual(joined.count("another"), 1, joined)
        self.assertEqual(joined.count("welcome"), 1, joined)
        self.assertEqual(joined.count("timestamp"), 1, joined)
        self.assertTrue(joined.startswith("hey everyone welcome to another video"), joined)

    def test_overlap_merge_is_word_based_not_character_based(self) -> None:
        """A tail ending in 'back' must not eat the 'back' of 'backend'."""
        cues = self.parse(
            "WEBVTT\n\n"
            "00:00:00.000 --> 00:00:02.000\nwe roll it back\n\n"
            "00:00:02.000 --> 00:00:04.000\nbackend routing comes next\n"
        )
        self.assertEqual(
            [c.text for c in cues], ["we roll it back", "backend routing comes next"]
        )

    def test_manual_track_keeps_legitimately_repeated_speech(self) -> None:
        """The overlap merge is only correct for rolling auto-captions, and
        find_vtt PREFERS the manual track, where cues never overlap. Running it
        unconditionally deleted real words."""
        for a, b, expect in [
            ("okay so that is the plan", "plan B is what we do next",
             ["okay so that is the plan", "plan B is what we do next"]),
            ("run the test", "run the test again",
             ["run the test", "run the test again"]),
            ("this is very", "very good indeed",
             ["this is very", "very good indeed"]),
        ]:
            with self.subTest(a=a):
                cues = self.parse(
                    f"WEBVTT\n\n00:00:00.000 --> 00:00:02.000\n{a}\n\n"
                    f"00:00:02.000 --> 00:00:04.000\n{b}\n"
                )
                self.assertEqual([c.text for c in cues], expect)

    def test_karaoke_markup_on_a_manual_track_does_not_trigger_merge(self) -> None:
        """Inline <00:00:01.500> timestamps are legal karaoke markup in
        hand-authored tracks, so detecting on markup swallowed real repeats:
        "run the test again now" came out as "again now"."""
        cues = self.parse(
            "WEBVTT\n\n"
            "00:00:00.000 --> 00:00:03.000\n"
            "we<00:00:00.500> are going to run the test\n\n"
            "00:00:03.000 --> 00:00:06.000\nrun the test again now\n\n"
            "00:00:06.000 --> 00:00:09.000\ncompletely fresh this time\n\n"
            "00:00:09.000 --> 00:00:12.000\nand then we commit\n\n"
            "00:00:12.000 --> 00:00:15.000\nthe change is staged\n\n"
            "00:00:15.000 --> 00:00:18.000\ngit status shows it\n\n"
            "00:00:18.000 --> 00:00:21.000\npush to origin main\n\n"
            "00:00:21.000 --> 00:00:24.000\ndone for today\n"
        )
        self.assertIn("run the test again now", [c.text for c in cues])

    def test_is_rolling_needs_substantial_overlap(self) -> None:
        """A one-word boundary match is ordinary speech, not a rolling repeat."""
        self.assertFalse(sc._is_rolling(
            ["ship it now", "now we wait", "wait for green", "green means go",
             "go and deploy", "deploy to prod", "prod is live", "live at last"]))

    def test_is_rolling_needs_enough_cues(self) -> None:
        """Too few cues to judge reports not-rolling, the safe answer."""
        self.assertFalse(sc._is_rolling(["run the test", "run the test again"]))

    def test_is_rolling_detects_a_real_rolling_track(self) -> None:
        texts = []
        tail = "the quick brown fox jumps over the lazy dog again and again".split()
        for i in range(10):
            texts.append(" ".join(tail[i:i + 6]))
        self.assertTrue(sc._is_rolling(texts))

    def test_rolling_track_still_merges(self) -> None:
        """Detecting on content must not disable the real dedupe."""
        rolling = [
            "okay so first we make the directory",
            "we make the directory then we init",
            "then we init the package json file",
            "the package json file and install",
            "and install express as a dependency",
            "express as a dependency then we write",
            "then we write the server file",
            "the server file and run it",
            "and run it on port three thousand",
        ]
        body = "WEBVTT\nKind: captions\n\n" + "".join(
            f"00:00:{i*3:02d}.000 --> 00:00:{(i+1)*3:02d}.000\n{txt}\n\n"
            for i, txt in enumerate(rolling)
        )
        joined = " ".join(c.text for c in self.parse(body))
        for word in ("directory", "express", "package", "thousand"):
            self.assertEqual(joined.count(word), 1, f"{word!r} duplicated in {joined!r}")

    def test_manual_track_keeps_genuine_repetition(self) -> None:
        """"no no no" is emphasis, not a caption artefact. The exact-repeat drop
        used to fire on manual tracks too and collapsed all three to one."""
        body = "WEBVTT\n\n" + "".join(
            f"00:00:{i*2:02d}.000 --> 00:00:{(i+1)*2:02d}.000\n{txt}\n\n"
            for i, txt in enumerate(
                ["no", "no", "no", "that is not what I meant at all",
                 "let me start over from the beginning", "open the config file",
                 "scroll down to the bottom", "add the missing key", "save it"])
        )
        self.assertEqual([c.text for c in self.parse(body)][:3], ["no", "no", "no"])

    def test_rolling_track_drops_exact_restatements(self) -> None:
        """A rolling track restates its own tail; those repeats are artefacts."""
        rolling = [
            "first we open the terminal window",
            "we open the terminal window and type",
            "and type the install command now",
            "the install command now and wait",
            "and wait for it to finish downloading",
            "for it to finish downloading the packages",
            "the packages then we can start",
            "then we can start the dev server",
            "the dev server on port three thousand",
        ]
        body = "WEBVTT\nKind: captions\n\n" + "".join(
            f"00:00:{i*3:02d}.000 --> 00:00:{(i+1)*3:02d}.000\n{txt}\n\n"
            for i, txt in enumerate(rolling)
        )
        joined = " ".join(c.text for c in self.parse(body))
        for word in ("terminal", "install", "downloading", "thousand"):
            self.assertEqual(joined.count(word), 1, f"{word!r} in {joined!r}")

    def test_strips_inline_timing_tags(self) -> None:
        cues = self.parse(
            "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\n"
            "npm<00:00:01.200><c> install</c><c.colorE5E5E5> express</c>\n"
        )
        self.assertEqual([c.text for c in cues], ["npm install express"])
        self.assertNotIn("<", cues[0].text)

    def test_timestamps_parsed(self) -> None:
        cues = self.parse(
            "WEBVTT\n\n01:02:03.500 --> 01:02:05.000\nlate in the video\n"
        )
        self.assertAlmostEqual(cues[0].start, 3723.5)

    def test_headers_and_notes_excluded(self) -> None:
        cues = self.parse(
            "WEBVTT\nKind: captions\nLanguage: en\nNOTE this is a comment\n\n"
            "00:00:01.000 --> 00:00:02.000\nreal content\n"
        )
        self.assertEqual([c.text for c in cues], ["real content"])

    def test_empty_and_cueless_files(self) -> None:
        self.assertEqual(self.parse(""), [])
        self.assertEqual(self.parse("WEBVTT\n\n"), [])

    def test_text_before_any_timestamp_is_ignored(self) -> None:
        self.assertEqual(self.parse("WEBVTT\n\nstray text\n"), [])


# --------------------------------------------------------------------------
class TestBundleRoot(TempDirCase):
    def setUp(self) -> None:
        super().setUp()
        self.prev = os.environ.pop(sc.BUNDLES_ENV, None)
        if self.prev is not None:
            self.addCleanup(os.environ.__setitem__, sc.BUNDLES_ENV, self.prev)

    def test_defaults_under_home_not_cwd(self) -> None:
        """A cwd-relative default drops 100-240 MB into whatever repo you are
        standing in, and obliges every one of them to gitignore it."""
        root = sc.bundles_root()
        self.assertTrue(root.is_absolute())
        self.assertNotIn("~", str(root))
        self.assertTrue(root.is_relative_to(Path.home()))

    def test_env_var_overrides_default(self) -> None:
        os.environ[sc.BUNDLES_ENV] = str(self.tmp / "lib")
        self.addCleanup(os.environ.pop, sc.BUNDLES_ENV, None)
        self.assertEqual(sc.bundles_root(), self.tmp / "lib")

    def test_env_var_expands_tilde(self) -> None:
        os.environ[sc.BUNDLES_ENV] = "~/vids"
        self.addCleanup(os.environ.pop, sc.BUNDLES_ENV, None)
        root = sc.bundles_root()
        self.assertTrue(root.is_absolute())
        self.assertNotIn("~", str(root))

    def test_blank_env_var_falls_back(self) -> None:
        os.environ[sc.BUNDLES_ENV] = "   "
        self.addCleanup(os.environ.pop, sc.BUNDLES_ENV, None)
        self.assertEqual(sc.bundles_root(), sc.DEFAULT_BUNDLES.expanduser())

    def make_bundle(self, root: Path, vid: str) -> Path:
        d = root / vid
        d.mkdir(parents=True)
        (d / "meta.json").write_text("{}", encoding="utf-8")
        return d

    def test_resolve_accepts_direct_path(self) -> None:
        d = self.make_bundle(self.tmp, "VID1")
        self.assertEqual(sc.resolve_bundle(d), d)

    def test_resolve_accepts_bare_id_under_env_root(self) -> None:
        lib = self.tmp / "lib"
        d = self.make_bundle(lib, "VID2")
        os.environ[sc.BUNDLES_ENV] = str(lib)
        self.addCleanup(os.environ.pop, sc.BUNDLES_ENV, None)
        self.assertEqual(sc.resolve_bundle(Path("VID2")), d)

    def test_resolve_prefers_direct_path_over_root(self) -> None:
        """An explicit path that IS a bundle must not be shadowed by the library."""
        lib = self.tmp / "lib"
        self.make_bundle(lib, "VID3")
        direct = self.make_bundle(self.tmp / "here", "VID3")
        os.environ[sc.BUNDLES_ENV] = str(lib)
        self.addCleanup(os.environ.pop, sc.BUNDLES_ENV, None)
        self.assertEqual(sc.resolve_bundle(direct), direct)

    def test_resolve_names_both_paths_on_failure(self) -> None:
        os.environ[sc.BUNDLES_ENV] = str(self.tmp / "lib")
        self.addCleanup(os.environ.pop, sc.BUNDLES_ENV, None)
        with self.assertRaises(SystemExit) as cm:
            sc.resolve_bundle(Path("NOPE"))
        msg = str(cm.exception)
        self.assertIn("NOPE", msg)
        self.assertIn("lib", msg)


# --------------------------------------------------------------------------
class TestFetchOptions(unittest.TestCase):
    """fetch() cannot be run without network, but its opts dict is the defect
    surface: a missing flag there is what makes a &list= URL pull a playlist."""

    def opts(self) -> dict:
        import inspect
        src = inspect.getsource(sc.fetch)
        ns: dict = {}
        body = src[src.index("opts = {"):src.index("with yt_dlp")]
        exec(body, {"workdir": Path("/tmp/x")}, ns)
        return ns["opts"]

    def test_noplaylist_is_set(self) -> None:
        """Without it, watch?v=X&list=PL... downloads every entry into one path."""
        self.assertIs(self.opts()["noplaylist"], True)

    def test_progress_bar_suppressed(self) -> None:
        """`quiet` alone does not; the bar writes to stdout and garbles output."""
        self.assertIs(self.opts()["noprogress"], True)

    def test_caps_at_1080p(self) -> None:
        self.assertIn("height<=1080", self.opts()["format"])

    def test_prefers_the_smallest_1080p_encode(self) -> None:
        """Resolution is load-bearing (1280-wide sources get upscaled to
        FRAME_WIDTH and small text mushes); bitrate is not. `bestvideo` alone
        picked YouTube's premium stream and paid ~40% more for pixels that are
        identical after the pipeline."""
        sort = self.opts()["format_sort"]
        self.assertEqual(sort[0], "res:1080", "resolution must outrank size")
        self.assertIn("+size", sort)

    def sub_opts(self) -> dict:
        import inspect
        src = inspect.getsource(sc.fetch_subtitles)
        ns: dict = {}
        body = src[src.index("opts = {"):src.index("try:")]
        exec(body, {"workdir": Path("/tmp/x"), "lang": "en"}, ns)
        return ns["opts"]

    def test_prefers_json3_over_vtt(self) -> None:
        """json3 is YouTube's own format and arrives already de-duplicated; the
        rolling repetition is an artefact of VTT's scrolling display model."""
        o = self.sub_opts()
        self.assertEqual(o["subtitlesformat"], "json3/vtt")
        self.assertIs(o["writesubtitles"], True)

    def test_video_pass_requests_no_subtitles(self) -> None:
        """Subtitles ride in their own pass so a 429 there cannot kill the
        video download — yt-dlp writes subs BEFORE the media file."""
        o = self.opts()
        self.assertNotIn("writesubtitles", o)
        self.assertNotIn("subtitleslangs", o)

    def test_subtitle_pass_skips_the_download(self) -> None:
        self.assertIs(self.sub_opts()["skip_download"], True)

    def test_subtitle_pass_requests_one_language_at_a_time(self) -> None:
        """Three langs x manual+auto is up to six hits on the endpoint that
        rate-limits hardest; they are tried in order and the first wins."""
        self.assertEqual(len(self.sub_opts()["subtitleslangs"]), 1)


@unittest.skipUnless(HAVE_YTDLP, "yt-dlp not installed")
class TestSubtitleFailureIsNotFatal(TempDirCase):
    """Two consecutive 58-minute builds died on HTTP 429 at _write_subtitles."""

    def run_with(self, side_effect):
        import yt_dlp
        calls = {"n": 0}

        class FakeYDL:
            def __init__(self, opts): pass
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def extract_info(self, url, download=False):
                calls["n"] += 1
                side_effect()

        real, sleep = yt_dlp.YoutubeDL, sc.time.sleep
        yt_dlp.YoutubeDL = FakeYDL
        sc.time.sleep = lambda _: None
        self.addCleanup(setattr, yt_dlp, "YoutubeDL", real)
        self.addCleanup(setattr, sc.time, "sleep", sleep)
        buf = io.StringIO()
        with redirect_stdout(buf):
            ok = sc.fetch_subtitles("u", self.tmp)
        return ok, calls["n"], buf.getvalue()

    def test_a_429_returns_false_instead_of_raising(self) -> None:
        def boom():
            raise Exception("ERROR: Unable to download video subtitles for 'en': "
                            "HTTP Error 429: Too Many Requests")
        ok, _, out = self.run_with(boom)
        self.assertFalse(ok)
        self.assertIn("continuing without narration", out)
        self.assertIn("429", out)

    def test_it_retries_before_giving_up(self) -> None:
        def boom():
            raise Exception("HTTP Error 429: Too Many Requests")
        _, n, _ = self.run_with(boom)
        self.assertEqual(n, 9, "3 attempts x 3 languages")

    def test_original_language_track_is_tried_first(self) -> None:
        """`en` is YouTube's PROCESSED English; `en-orig` is the real ASR.

        Requesting `en` first returned a paraphrase of the video: disfluencies
        and `>>` markers stripped, words inserted, acronyms expanded. That is
        derived evidence, which is the one thing this tool must not cite.
        """
        import inspect
        src = inspect.getsource(sc.fetch_subtitles)
        line = next(l for l in src.splitlines() if "for lang in" in l)
        order = [x.strip().strip('"\'') for x in
                 line[line.index("(") + 1:line.rindex(")")].split(",") if x.strip()]
        self.assertEqual(order[0], "en-orig",
                         f"original track must be tried first, got {order}")
        self.assertIn("en", order)

    def test_success_stops_after_the_first_language(self) -> None:
        (self.tmp / "video.en.json3").write_text('{"events":[]}', encoding="utf-8")
        ok, n, _ = self.run_with(lambda: None)
        self.assertTrue(ok)
        self.assertEqual(n, 1)


# --------------------------------------------------------------------------
class TestPathContainment(TempDirCase):
    """yt-dlp's id is network-derived. For a generic-extractor URL it is
    `unquote(last path segment)`, so `https://h/..%2f..%2fw.mp4` -> `../../w`.
    Unsanitized that escaped --out: frames and meta.json written outside it, an
    existing BUNDLE.md there overwritten, a `frames` directory there deleted.
    """

    def test_youtube_ids_pass_through_untouched(self) -> None:
        for vid in ("3sHNpzgNCYY", "dQw4w9WgXcQ", "aqz-KE-bpKQ", "_-xyz_ABC12"):
            with self.subTest(vid=vid):
                self.assertEqual(sc.safe_dest(self.tmp, vid).name, vid)

    def test_relative_traversal_is_flattened(self) -> None:
        d = sc.safe_dest(self.tmp, "../victim")
        self.assertEqual(d.parent, self.tmp.resolve())
        self.assertNotIn("..", d.parts)

    def test_deep_traversal_is_flattened(self) -> None:
        d = sc.safe_dest(self.tmp, "../../../../tmp/pwn")
        self.assertEqual(d.parent, self.tmp.resolve())

    def test_absolute_path_is_flattened(self) -> None:
        d = sc.safe_dest(self.tmp, "/etc/passwd")
        self.assertEqual(d.parent, self.tmp.resolve())
        self.assertEqual(d.name, "_etc_passwd")

    def test_encoded_separator_is_flattened(self) -> None:
        d = sc.safe_dest(self.tmp, "a/b/c")
        self.assertEqual(d.parent, self.tmp.resolve())

    def test_result_is_always_inside_root(self) -> None:
        for vid in ("../x", "../../x", "/x", "a/b", "..", ".", "~/x", "a\\b", "..."):
            with self.subTest(vid=vid):
                d = sc.safe_dest(self.tmp, vid)
                self.assertEqual(d.parent, self.tmp.resolve(), vid)

    def test_underscore_bearing_ids_are_preserved(self) -> None:
        """Underscore is legal in a YouTube id; stripping it renames the bundle
        away from the id a spec's `Watch:` line cites."""
        for vid in ("_-xyz_ABC12", "__leading", "trailing__", "_"):
            with self.subTest(vid=vid):
                self.assertEqual(sc.safe_dest(self.tmp, vid).name, vid)

    def test_empty_id_is_rejected(self) -> None:
        with self.assertRaises(SystemExit):
            sc.safe_dest(self.tmp, "")

    def test_long_id_is_truncated(self) -> None:
        self.assertLessEqual(len(sc.safe_dest(self.tmp, "z" * 300).name), 64)


@unittest.skipUnless(HAVE_FFMPEG, "ffmpeg not on PATH")
class TestFrameDirGuard(TempDirCase):
    def make_video(self) -> Path:
        p = self.tmp / "v.mp4"
        subprocess.run(
            ["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i",
             "testsrc=size=320x180:rate=10:duration=3",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", str(p), "-y"], check=True)
        return p

    def test_refuses_to_clear_a_directory_holding_non_frames(self) -> None:
        out = self.tmp / "frames"
        out.mkdir()
        (out / "THESIS.txt").write_text("irreplaceable", encoding="utf-8")
        with self.assertRaises(SystemExit) as cm:
            sc.sample_frames(self.make_video(), out, 1.0)
        self.assertIn("refusing to clear", str(cm.exception))
        self.assertTrue((out / "THESIS.txt").is_file())

    def test_clears_a_real_frames_directory(self) -> None:
        out = self.tmp / "frames"
        out.mkdir()
        (out / "00-99-99.jpg").write_bytes(b"stale")
        sc.sample_frames(self.make_video(), out, 1.0)
        self.assertFalse((out / "00-99-99.jpg").exists())


# --------------------------------------------------------------------------
class TestFileDiscovery(TempDirCase):
    def test_find_video_ignores_subtitle_track(self) -> None:
        """glob('video.*') also matches video.en.vtt, which then reaches ffmpeg."""
        (self.tmp / "video.en.vtt").touch()
        (self.tmp / "video.mp4").touch()
        self.assertEqual(sc.find_video(self.tmp).name, "video.mp4")

    def test_find_video_accepts_other_containers(self) -> None:
        (self.tmp / "video.en.vtt").touch()
        (self.tmp / "video.webm").touch()
        self.assertEqual(sc.find_video(self.tmp).name, "video.webm")

    def test_find_video_exits_when_only_subtitles(self) -> None:
        (self.tmp / "video.en.vtt").touch()
        with self.assertRaises(SystemExit):
            sc.find_video(self.tmp)

    def test_find_vtt_prefers_plain_en(self) -> None:
        for n in ("video.en-US.vtt", "video.en.vtt", "video.es.vtt"):
            (self.tmp / n).touch()
        self.assertEqual(sc.find_vtt(self.tmp).name, "video.en.vtt")

    def test_find_vtt_falls_back(self) -> None:
        (self.tmp / "video.es.vtt").touch()
        self.assertEqual(sc.find_vtt(self.tmp).name, "video.es.vtt")

    def test_find_vtt_none(self) -> None:
        self.assertIsNone(sc.find_vtt(self.tmp))


# --------------------------------------------------------------------------
class TestRename(TempDirCase):
    def test_names_are_timestamps(self) -> None:
        frames = []
        for i, ts in enumerate((0.0, 65.0, 3661.0)):
            p = self.tmp / f"s_{i:06d}.jpg"
            p.write_bytes(b"x")
            frames.append(sc.Frame(ts, p))
        out = sc.rename_by_timestamp(frames, self.tmp)
        self.assertEqual(
            [f.path.name for f in out],
            ["00-00-00.jpg", "00-01-05.jpg", "01-01-01.jpg"],
        )

    def test_subsecond_collision_does_not_overwrite(self) -> None:
        """At fps>1 two frames round into the same second; rename would clobber."""
        frames = []
        for i, ts in enumerate((10.0, 10.4, 10.8)):
            p = self.tmp / f"s_{i:06d}.jpg"
            p.write_bytes(bytes([i]))
            frames.append(sc.Frame(ts, p))
        out = sc.rename_by_timestamp(frames, self.tmp)
        self.assertEqual(len({f.path.name for f in out}), 3)
        for f in out:
            self.assertTrue(f.path.is_file())

    def test_rejects_are_deleted(self) -> None:
        keep = self.tmp / "s_000001.jpg"
        keep.write_bytes(b"x")
        (self.tmp / "s_000002.jpg").write_bytes(b"y")
        sc.rename_by_timestamp([sc.Frame(1.0, keep)], self.tmp)
        self.assertEqual(list(self.tmp.glob("s_*.jpg")), [])
        self.assertTrue((self.tmp / "00-00-01.jpg").is_file())


# --------------------------------------------------------------------------
class TestBundleAndWindow(TempDirCase):
    def build_bundle(self) -> Path:
        dest = self.tmp / "VID1"
        (dest / "frames").mkdir(parents=True)
        frames = []
        for ts in (0, 30, 90, 150, 600):
            p = dest / "frames" / f"{sc.hhmmss(ts, sep='-')}.jpg"
            p.write_bytes(b"x")
            frames.append(sc.Frame(float(ts), p))
        cues = [sc.Cue(5.0, "intro words"), sc.Cue(95.0, "middle words"),
                sc.Cue(605.0, "late words")]
        meta = {
            "id": "VID1", "title": "T", "channel": "C", "duration": 700,
            "url": "https://youtu.be/VID1", "chapters": [{"title": "Setup", "start": 0}],
            "transcript": [{"start": c.start, "text": c.text} for c in cues],
        }
        (dest / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
        sc.build_bundle(meta, cues, frames, dest)
        return dest

    def test_bundle_does_not_inline_frames(self) -> None:
        """Markdown image refs render nowhere and load nothing when Read."""
        text = (self.build_bundle() / "BUNDLE.md").read_text(encoding="utf-8")
        self.assertNotIn("![", text)
        self.assertIn("Chapters", text)
        self.assertIn("intro words", text)
        self.assertIn("00:00:05", text)

    def test_bundle_reports_frame_count(self) -> None:
        text = (self.build_bundle() / "BUNDLE.md").read_text(encoding="utf-8")
        self.assertIn("**Frames:** 5", text)

    def test_bundle_without_subtitles(self) -> None:
        dest = self.tmp / "V2"
        dest.mkdir()
        meta = {"id": "V2", "title": "T", "channel": "C", "duration": 10,
                "url": "u", "chapters": []}
        sc.build_bundle(meta, [], [], dest)
        self.assertIn("No subtitle track", (dest / "BUNDLE.md").read_text())

    def window(self, dest: Path, a: float, b: float) -> str:
        buf = io.StringIO()
        with redirect_stdout(buf):
            sc.emit_window(dest, a, b)
        return buf.getvalue()

    def test_window_filters_to_span(self) -> None:
        out = self.window(self.build_bundle(), 30, 150)
        self.assertIn("00-00-30.jpg", out)
        self.assertIn("00-02-30.jpg", out)
        self.assertNotIn("00-10-00.jpg", out)   # 600s is outside
        self.assertIn("middle words", out)
        self.assertNotIn("late words", out)

    def test_window_emits_bare_readable_paths(self) -> None:
        out = self.window(self.build_bundle(), 0, 200)
        frame_lines = [ln for ln in out.splitlines() if ln.startswith("FRAME")]
        self.assertTrue(frame_lines)
        for ln in frame_lines:
            p = Path(ln.split(maxsplit=2)[2])
            self.assertTrue(p.is_absolute(), ln)
            self.assertTrue(p.is_file(), ln)

    def test_window_orders_frame_before_narration(self) -> None:
        """Screen state first, then what was said about it — for EVERY pair, not
        just the first line."""
        out = self.window(self.build_bundle(), 0, 200)
        seq = []
        for ln in out.splitlines():
            if ln.startswith("FRAME"):
                seq.append((sc.parse_span(ln.split()[1]), 0))
            elif ln.startswith("      0"):
                seq.append((sc.parse_span(ln.split()[0]), 1))
        self.assertTrue(seq)
        self.assertEqual(seq, sorted(seq), "frame/cue stream is not time-ordered")

    def test_window_refuses_an_oversized_span(self) -> None:
        """The old code warned and then printed the payload anyway."""
        dest = self.tmp / "BIG"
        (dest / "frames").mkdir(parents=True)
        n = sc.WINDOW_TOKEN_CAP // sc.TOKENS_PER_FRAME + 10
        for i in range(n):
            (dest / "frames" / f"{sc.hhmmss(i, sep='-')}.jpg").write_bytes(b"x")
        (dest / "meta.json").write_text(
            json.dumps({"title": "T", "transcript": []}), encoding="utf-8")
        with self.assertRaises(SystemExit) as cm:
            self.window(dest, 0, n)
        self.assertIn("Narrow the span", str(cm.exception))
        buf = io.StringIO()
        with redirect_stdout(buf):
            sc.emit_window(dest, 0, n, force=True)
        self.assertIn("FRAME", buf.getvalue())

    def test_window_cap_counts_transcript_text_too(self) -> None:
        """Few frames plus a huge transcript is exactly the shape of a heavily
        deduped long video; a frames-only estimate let it walk past the cap."""
        dest = self.tmp / "TALKY"
        (dest / "frames").mkdir(parents=True)
        for i in range(20):
            (dest / "frames" / f"{sc.hhmmss(i, sep='-')}.jpg").write_bytes(b"x")
        cues = [{"start": float(i), "text": "word " * 60} for i in range(20000)]
        (dest / "meta.json").write_text(
            json.dumps({"title": "T", "transcript": cues}), encoding="utf-8")
        with self.assertRaises(SystemExit):
            self.window(dest, 0, 20000)

    def test_window_survives_corrupt_meta(self) -> None:
        dest = self.tmp / "BAD"
        (dest / "frames").mkdir(parents=True)
        (dest / "meta.json").write_text("not json at all", encoding="utf-8")
        with self.assertRaises(SystemExit) as cm:
            self.window(dest, 0, 10)
        self.assertIn("corrupt bundle", str(cm.exception))

    def test_window_rejects_non_bundle(self) -> None:
        with self.assertRaises(SystemExit):
            sc.emit_window(self.tmp / "nope", 0, 10)

    def test_window_ignores_unparseable_frame_names(self) -> None:
        dest = self.build_bundle()
        (dest / "frames" / "thumbnail.jpg").write_bytes(b"x")
        out = self.window(dest, 0, 3600)
        self.assertNotIn("thumbnail", out)


# --------------------------------------------------------------------------
@unittest.skipUnless(HAVE_FFMPEG, "ffmpeg not on PATH")
class TestSampling(TempDirCase):
    def make_video(self, seconds: int = 6) -> Path:
        p = self.tmp / "video.mp4"
        subprocess.run(
            ["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i",
             f"testsrc=size=320x180:rate=10:duration={seconds}",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", str(p), "-y"],
            check=True,
        )
        return p

    def test_timestamps_are_arithmetic(self) -> None:
        """Frame N lands at (N-1)/fps — no stderr parsing, nothing to misalign."""
        frames = sc.sample_frames(self.make_video(6), self.tmp / "f", 1.0)
        self.assertEqual([f.ts for f in frames], [float(i) for i in range(len(frames))])

    def test_first_frame_is_t_zero(self) -> None:
        """Scene detection never fired on frame 0, losing the opening screen."""
        frames = sc.sample_frames(self.make_video(4), self.tmp / "f", 1.0)
        self.assertEqual(frames[0].ts, 0.0)

    def test_fps_controls_density(self) -> None:
        sparse = sc.sample_frames(self.make_video(6), self.tmp / "a", 1.0)
        dense = sc.sample_frames(self.make_video(6), self.tmp / "b", 2.0)
        self.assertGreater(len(dense), len(sparse))

    def test_stale_frames_cleared_between_runs(self) -> None:
        out = self.tmp / "f"
        out.mkdir()
        (out / "00-99-99.jpg").write_bytes(b"stale")
        sc.sample_frames(self.make_video(3), out, 1.0)
        self.assertFalse((out / "00-99-99.jpg").exists())

    def test_non_video_input_fails_loudly(self) -> None:
        junk = self.tmp / "video.mp4"
        junk.write_text("WEBVTT\n\nnot a video")
        with self.assertRaises(SystemExit):
            sc.sample_frames(junk, self.tmp / "f", 1.0)

    @unittest.skipUnless(HAVE_IMAGING, "imagehash/Pillow not installed")
    def test_dedupe_keeps_distinct_screens(self) -> None:
        """phash(hash_size=8) scores different terminal commands 0-6 apart.

        The library default cannot separate them from identical frames, so the
        old distance-6 threshold discarded real content.
        """
        clips = []
        for i, txt in enumerate(("alpha one", "bravo two", "charlie three")):
            c = self.tmp / f"c{i}.mp4"
            subprocess.run(
                ["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i",
                 f"color=c=black:size=640x360:rate=5:duration=2,"
                 f"drawtext=text='{txt}':fontcolor=white:fontsize=48:x=20:y=20",
                 "-c:v", "libx264", "-pix_fmt", "yuv420p", str(c), "-y"],
                check=True,
            )
            clips.append(c)
        lst = self.tmp / "l.txt"
        lst.write_text("".join(f"file '{c.name}'\n" for c in clips))
        joined = self.tmp / "video.mp4"
        subprocess.run(
            ["ffmpeg", "-loglevel", "error", "-f", "concat", "-safe", "0",
             "-i", str(lst), "-c", "copy", str(joined), "-y"],
            check=True, cwd=self.tmp,
        )
        frames = sc.sample_frames(joined, self.tmp / "f", 1.0)
        kept = sc.dedupe(frames, sc.PHASH_DISTANCE)
        self.assertEqual(len(kept), 3, f"expected 3 distinct screens, kept {len(kept)}")

    @unittest.skipUnless(HAVE_IMAGING, "imagehash/Pillow not installed")
    def test_dedupe_collapses_a_static_screen(self) -> None:
        frames = sc.sample_frames(self.make_static(5), self.tmp / "f", 1.0)
        self.assertGreater(len(frames), 1)
        self.assertEqual(len(sc.dedupe(frames, sc.PHASH_DISTANCE)), 1)

    def make_static(self, seconds: int) -> Path:
        p = self.tmp / "static.mp4"
        subprocess.run(
            ["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i",
             f"color=c=0x1e1e2e:size=320x180:rate=5:duration={seconds}",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", str(p), "-y"],
            check=True,
        )
        return p


# --------------------------------------------------------------------------
@unittest.skipUnless(HAVE_FFMPEG and HAVE_IMAGING, "needs ffmpeg + Pillow")
class TestCmdBuild(TempDirCase):
    """cmd_build is testable by stubbing only the network call. Every defect
    found in review except the VTT merge lived in this previously-uncovered band.
    """

    def setUp(self) -> None:
        super().setUp()
        self.fixture = self.tmp / "src.mp4"
        subprocess.run(
            ["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i",
             "testsrc=size=320x180:rate=10:duration=6",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", str(self.fixture), "-y"],
            check=True)
        self.real_fetch = sc.fetch
        self.addCleanup(setattr, sc, "fetch", self.real_fetch)

    def stub(self, vid: str = "VID123", vtt: str | None = None):
        def fake(url: str, workdir: Path) -> dict:
            shutil.copy(self.fixture, workdir / "video.mp4")
            if vtt is not None:
                (workdir / "video.en.vtt").write_text(vtt, encoding="utf-8")
            return {"id": vid, "title": "T", "channel": "C", "duration": 6,
                    "url": url, "description": "", "chapters": []}
        sc.fetch = fake

    def run_build(self, out: Path, **kw):
        ns = dict(url="u", out=out, fps=1.0, phash_distance=sc.PHASH_DISTANCE,
                  crop=None, keep_video=False, whole_frame_hash=False,
                  content_flatness=sc.CONTENT_FLATNESS)
        ns.update(kw)
        with self.silent() as buf:
            sc.cmd_build(argparse.Namespace(**ns))
        return buf.getvalue()

    def test_produces_a_complete_bundle(self) -> None:
        self.stub(vtt="WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nhello there\n")
        out = self.tmp / "b"
        self.run_build(out)
        dest = out / "VID123"
        self.assertTrue((dest / "BUNDLE.md").is_file())
        meta = json.loads((dest / "meta.json").read_text())
        on_disk = sorted((dest / "frames").glob("*.jpg"))
        self.assertTrue(on_disk)
        self.assertEqual(meta["frame_count"], len(on_disk),
                         "meta.json disagrees with the frames actually written")
        self.assertEqual([c["text"] for c in meta["transcript"]], ["hello there"])
        for f in on_disk:
            self.assertRegex(f.stem, r"^\d{2}-\d{2}-\d{2}(_\d{2})?$")

    def test_staging_is_removed(self) -> None:
        self.stub()
        out = self.tmp / "b"
        self.run_build(out)
        self.assertFalse((out / "_staging").exists())

    def test_keep_video_retains_staging(self) -> None:
        self.stub()
        out = self.tmp / "b"
        self.run_build(out, keep_video=True)
        self.assertTrue((out / "_staging" / "video.mp4").is_file())

    def test_failed_rebuild_preserves_the_previous_bundle(self) -> None:
        """Sampling used to clear dest/frames before knowing the run would
        succeed, leaving BUNDLE.md and meta.json describing deleted frames."""
        out = self.tmp / "b"
        self.stub()
        self.run_build(out)
        dest = out / "VID123"
        before = sorted(p.name for p in (dest / "frames").glob("*.jpg"))
        self.assertTrue(before)

        def broken(url: str, workdir: Path) -> dict:
            (workdir / "video.mp4").write_text("not a video", encoding="utf-8")
            return {"id": "VID123", "title": "T", "channel": "C", "duration": 6,
                    "url": url, "description": "", "chapters": []}
        sc.fetch = broken
        with self.assertRaises(SystemExit):
            self.run_build(out)

        after = sorted(p.name for p in (dest / "frames").glob("*.jpg"))
        self.assertEqual(before, after, "a failed rebuild destroyed the good frames")
        self.assertFalse((dest / "frames.new").exists(), "work dir left behind")

    def test_rejects_bad_fps_including_nan(self) -> None:
        self.stub()
        for bad in (0, -1, float("nan"), float("inf")):
            with self.subTest(fps=bad), self.assertRaises(SystemExit):
                self.run_build(self.tmp / "b", fps=bad)

    def test_traversal_id_stays_inside_out(self) -> None:
        self.stub(vid="../escaped")
        out = self.tmp / "b"
        out.mkdir()
        self.run_build(out)
        self.assertFalse((self.tmp / "escaped").exists())
        self.assertEqual([p.name for p in out.iterdir() if p.is_dir()], ["___escaped"])

    def test_no_subtitles_still_builds(self) -> None:
        self.stub(vtt=None)
        out = self.tmp / "b"
        self.run_build(out)
        text = (out / "VID123" / "BUNDLE.md").read_text()
        self.assertIn("No subtitle track", text)


class TestCmdBuildPreflight(TempDirCase):
    """The three guards that run before any download."""

    def ns(self, **kw):
        d = dict(url="u", out=self.tmp, fps=1.0, phash_distance=sc.PHASH_DISTANCE,
                 crop=None, keep_video=False, whole_frame_hash=False,
                 content_flatness=sc.CONTENT_FLATNESS)
        d.update(kw)
        return argparse.Namespace(**d)

    def test_missing_ffmpeg_exits(self) -> None:
        real = sc.shutil.which
        sc.shutil.which = lambda _: None
        self.addCleanup(setattr, sc.shutil, "which", real)
        with self.assertRaises(SystemExit) as cm:
            sc.cmd_build(self.ns())
        self.assertIn("ffmpeg not found", str(cm.exception))

    @unittest.skipUnless(HAVE_FFMPEG, "ffmpeg not on PATH")
    def test_missing_python_dependency_is_named(self) -> None:
        import builtins
        real = builtins.__import__

        def fake(name, *a, **k):
            if name == "imagehash":
                raise ImportError(name="imagehash")
            return real(name, *a, **k)

        builtins.__import__ = fake
        self.addCleanup(setattr, builtins, "__import__", real)
        with self.assertRaises(SystemExit) as cm:
            sc.cmd_build(self.ns())
        msg = str(cm.exception)
        self.assertIn("missing dependency", msg)
        self.assertIn("imagehash", msg)

    def test_bad_crop_rejected_before_download(self) -> None:
        """An invalid crop used to die inside ffmpeg, after paying for the video.

        Checked before the environment probes, so a typo is named as a typo even
        on a machine that is also missing a dependency."""
        for bad in ("not-a-crop", "100:100:0", "a:b:c:d", "100x100"):
            with self.subTest(crop=bad), self.assertRaises(SystemExit) as cm:
                sc.cmd_build(self.ns(crop=bad))
            self.assertIn("--crop must be", str(cm.exception))


@unittest.skipUnless(HAVE_FFMPEG and HAVE_IMAGING, "needs ffmpeg + Pillow")
class TestRetentionWarning(TempDirCase):
    def test_warns_when_dedupe_is_a_no_op(self) -> None:
        """A webcam overlay defeats whole-frame hashing; the run must say so
        rather than silently keeping every frame."""
        fixture = self.tmp / "v.mp4"
        subprocess.run(
            ["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i",
             "testsrc=size=320x180:rate=10:duration=70",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", str(fixture), "-y"], check=True)
        real_fetch, real_dedupe = sc.fetch, sc.dedupe
        self.addCleanup(setattr, sc, "fetch", real_fetch)
        self.addCleanup(setattr, sc, "dedupe", real_dedupe)
        sc.fetch = lambda url, wd: (shutil.copy(fixture, wd / "video.mp4"),
                                    {"id": "V", "title": "T", "channel": "C",
                                     "duration": 70, "url": url, "description": "",
                                     "chapters": []})[1]
        sc.dedupe = lambda frames, d, whole=False: frames        # nothing culled
        buf = io.StringIO()
        with redirect_stdout(buf):
            sc.cmd_build(argparse.Namespace(
                url="u", out=self.tmp / "b", fps=1.0,
                phash_distance=sc.PHASH_DISTANCE, crop=None, keep_video=False,
                whole_frame_hash=False, content_flatness=sc.CONTENT_FLATNESS))
        out = buf.getvalue()
        self.assertIn("dedupe kept", out)
        self.assertIn("--fps", out)


class TestCmdWindow(TempDirCase):
    def test_rejects_reversed_span(self) -> None:
        with self.assertRaises(SystemExit) as cm:
            sc.cmd_window(argparse.Namespace(
                bundle=self.tmp, start="5:00", end="2:00", force=False, every=False))
        self.assertIn("must be after", str(cm.exception))

    def test_rejects_equal_span(self) -> None:
        with self.assertRaises(SystemExit):
            sc.cmd_window(argparse.Namespace(
                bundle=self.tmp, start="2:00", end="2:00", force=False, every=False))

    def test_rejects_bad_timestamp(self) -> None:
        with self.assertRaises(SystemExit):
            sc.cmd_window(argparse.Namespace(
                bundle=self.tmp, start="abc", end="2:00", force=False, every=False))


@unittest.skipUnless(HAVE_IMAGING, "imagehash/Pillow not installed")
class TestArtifactSelection(TempDirCase):
    """The page must spend its 16 MB on screens, not webcam stills."""

    def bundle(self, flat):
        from PIL import Image, ImageDraw
        dest = self.tmp / "VID"
        (dest / "frames").mkdir(parents=True)
        names = []
        for i in range(len(flat)):
            img = Image.new("RGB", (1408, 792), (18, 20, 30))
            d = ImageDraw.Draw(img)
            d.rectangle([60, 120, 190 + i * 60, 620], fill=(220, 220, 210))
            n = f"{sc.hhmmss(i, sep='-')}.jpg"
            img.save(dest / "frames" / n, "JPEG")
            names.append(n)
        (dest / "meta.json").write_text(json.dumps({
            "id": "VID", "title": "T", "channel": "C", "duration": len(flat),
            "url": "u", "fps": 1.0, "frame_count": len(flat), "chapters": [],
            "description": "", "transcript": [],
            "flatness": {n: flat[i] for i, n in enumerate(names)},
            "content_threshold": sc.CONTENT_FLATNESS,
        }), encoding="utf-8")
        return dest

    def screens(self, dest):
        out = self.tmp / "p.html"
        tpl = Path(__file__).resolve().parent.parent / "assets" / "artifact-template.html"
        buf = io.StringIO()
        with redirect_stdout(buf):
            sc.build_artifact(dest, 0, 99, out, tpl, sc.DISPLAY_DISTANCE)
        import re
        m = re.search(r"^var D = (\{.*\});$", out.read_text(encoding="utf-8"),
                      re.M | re.S)
        return json.loads(m.group(1))["frames"]

    def test_camera_frames_are_left_out_of_the_page(self) -> None:
        got = self.screens(self.bundle([0.9, 0.01, 0.9, 0.01, 0.01, 0.9]))
        self.assertEqual(sorted(int(f["t"]) for f in got), [0, 2, 5],
                         "only the flat frames belong on the page")

    def test_a_span_with_no_screen_still_renders(self) -> None:
        """A conversational stretch must not produce an empty page."""
        self.assertTrue(self.screens(self.bundle([0.01] * 6)))

    def test_a_bundle_without_scores_uses_every_frame(self) -> None:
        dest = self.bundle([0.01] * 5)
        meta = json.loads((dest / "meta.json").read_text())
        del meta["flatness"]
        (dest / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
        self.assertTrue(self.screens(dest))


@unittest.skipUnless(HAVE_IMAGING, "imagehash/Pillow not installed")
class TestDisplayDedupeIgnoresCorners(TempDirCase):
    """Whole-frame hashing here kept 2072 of 2771 frames -> a 94 MB page."""

    def frames(self, n=6):
        from PIL import Image, ImageDraw
        import random
        out = []
        for i in range(n):
            random.seed(i)
            img = Image.new("RGB", (1408, 792), (20, 22, 30))
            d = ImageDraw.Draw(img)
            d.rectangle((200, 100, 1200, 400), fill=(240, 240, 240))
            for y in range(792 - 230, 792, 25):
                for x in range(0, 300, 25):
                    v = random.choice((0, 255))
                    d.rectangle((x, y, x + 25, y + 25), fill=(v, v, v))
            f = self.tmp / f"{sc.hhmmss(i, sep='-')}.jpg"
            img.save(f)
            out.append(sc.Frame(float(i), f))
        return out

    def test_corner_motion_does_not_multiply_screens(self) -> None:
        self.assertEqual(len(sc.pick_for_display(self.frames(), sc.DISPLAY_DISTANCE)), 1)

    def test_whole_frame_mode_keeps_them_all(self) -> None:
        got = sc.pick_for_display(self.frames(), sc.DISPLAY_DISTANCE, whole=True)
        self.assertEqual(len(got), 6)


@unittest.skipUnless(HAVE_IMAGING, "imagehash/Pillow not installed")
class TestArtifact(TempDirCase):
    TEMPLATE = Path(__file__).resolve().parent.parent / "assets" / "artifact-template.html"

    def make_bundle(self, n: int = 12, silent_from: int = 8) -> Path:
        from PIL import Image, ImageDraw
        dest = self.tmp / "VID"
        (dest / "frames").mkdir(parents=True)
        for i in range(n):
            # Structural difference, not just colour: phash is a luminance DCT,
            # so a flat fill has no frequency content and every solid image
            # hashes alike no matter its colour.
            img = Image.new("RGB", (1408, 792), (18, 20, 30))
            d = ImageDraw.Draw(img)
            for k in range(i + 1):
                d.rectangle([60 + k * 100, 120, 190 + k * 100, 620], fill=(220, 220, 210))
            img.save(dest / "frames" / f"{sc.hhmmss(i * 5, sep='-')}.jpg", "JPEG")
        transcript = [{"start": float(i * 5) + 1, "text": f"line {i}"}
                      for i in range(silent_from)]
        (dest / "meta.json").write_text(json.dumps({
            "id": "VID", "title": "A Title", "channel": "Chan", "duration": n * 5,
            "url": "https://youtu.be/VID", "fps": 1.0, "frame_count": n,
            "chapters": [{"title": "One", "start": 0}, {"title": "Two", "start": 25}],
            "description": "Setup notes\nhttps://github.com/o/repo\nbuy https://amzn.to/x",
            "transcript": transcript,
        }), encoding="utf-8")
        return dest

    def payload(self, html: str) -> dict:
        import re
        m = re.search(r"^var D = (\{.*\});$", html, re.M | re.S)
        self.assertIsNotNone(m, "payload was not injected")
        return json.loads(m.group(1))

    def build(self, **kw) -> tuple[Path, dict]:
        dest = kw.pop("bundle", None) or self.make_bundle()
        out = self.tmp / "page.html"
        with self.silent():
            sc.build_artifact(dest, 0, 60, out, self.TEMPLATE,
                              kw.pop("distance", 0))
        html = out.read_text(encoding="utf-8")
        return out, self.payload(html)

    def test_emits_a_self_contained_page(self) -> None:
        out, d = self.build()
        html = out.read_text(encoding="utf-8")
        self.assertNotIn("__TITLE__", html)
        self.assertNotIn("window.__SCRIBE__", html)
        self.assertIn("<title>A Title</title>", html)
        self.assertEqual(d["title"], "A Title")

    def test_frames_embed_as_data_uris(self) -> None:
        """The artifact runtime serves no asset store, so nothing may reference
        a local path — every image has to be inline."""
        _, d = self.build()
        self.assertTrue(d["frames"])
        for f in d["frames"]:
            self.assertTrue(f["img"].startswith("data:image/jpeg;base64,"), f["label"])

    def test_frames_are_downscaled_for_the_page(self) -> None:
        import base64 as b64, io
        from PIL import Image
        _, d = self.build()
        raw = b64.b64decode(d["frames"][0]["img"].split(",", 1)[1])
        with Image.open(io.BytesIO(raw)) as img:
            self.assertEqual(img.width, sc.ARTIFACT_WIDTH)

    def test_narration_pairs_with_the_frame_it_covers(self) -> None:
        _, d = self.build()
        by_label = {f["label"]: f["said"] for f in d["frames"]}
        self.assertEqual(by_label["00:00:00"], "line 0")
        # the cue at t=36 falls inside this frame's window, not the next one
        self.assertEqual(by_label["00:00:35"], "line 7")
        self.assertEqual(by_label["00:00:40"], "")   # past the transcript

    def test_silent_frames_are_marked_not_dropped(self) -> None:
        _, d = self.build()
        self.assertTrue(any(not f["said"] for f in d["frames"]))
        self.assertEqual(len(d["frames"]), 12)

    def test_affiliate_links_filtered_description_verbatim(self) -> None:
        _, d = self.build()
        self.assertIn("https://github.com/o/repo", d["links"])
        self.assertFalse([u for u in d["links"] if "amzn.to" in u])
        self.assertIn("buy https://amzn.to/x", d["description"])

    def test_display_dedupe_culls_harder(self) -> None:
        from PIL import Image, ImageDraw
        dest = self.tmp / "SAME"
        (dest / "frames").mkdir(parents=True)
        for i in range(10):
            img = Image.new("RGB", (1408, 792), (18, 20, 30))
            ImageDraw.Draw(img).rectangle([100, 100, 700, 500], fill=(220, 220, 210))
            img.save(dest / "frames" / f"{sc.hhmmss(i * 5, sep='-')}.jpg", "JPEG")
        (dest / "meta.json").write_text(json.dumps({
            "id": "S", "title": "T", "channel": "C", "duration": 50,
            "url": "u", "chapters": [], "description": "", "transcript": []}),
            encoding="utf-8")
        out = self.tmp / "p.html"
        with self.silent():
            sc.build_artifact(dest, 0, 60, out, self.TEMPLATE, sc.DISPLAY_DISTANCE)
        self.assertEqual(len(self.payload(out.read_text())["frames"]), 1)

    def test_empty_span_fails_loudly(self) -> None:
        dest = self.make_bundle()
        with self.assertRaises(SystemExit) as cm, self.silent():
            sc.build_artifact(dest, 9000, 9600, self.tmp / "p.html",
                              self.TEMPLATE, 0)
        self.assertIn("no frames", str(cm.exception))

    def test_missing_template_fails_loudly(self) -> None:
        with self.assertRaises(SystemExit) as cm, self.silent():
            sc.build_artifact(self.make_bundle(), 0, 60, self.tmp / "p.html",
                              self.tmp / "nope.html", 0)
        self.assertIn("template not found", str(cm.exception))

    def test_closing_script_tag_in_data_cannot_break_out(self) -> None:
        """A title containing </script> would otherwise terminate the block."""
        dest = self.make_bundle()
        meta = json.loads((dest / "meta.json").read_text())
        meta["title"] = "evil </script><script>alert(1)</script>"
        (dest / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
        out = self.tmp / "p.html"
        with self.silent():
            sc.build_artifact(dest, 0, 60, out, self.TEMPLATE, 0)
        html = out.read_text(encoding="utf-8")
        body = html[html.index("var D = "):]
        self.assertNotIn("</script><script>alert", body[:body.index("\n")])

    def test_template_is_pure_ascii(self) -> None:
        """Non-ASCII literals render as mojibake wherever the charset is guessed."""
        text = self.TEMPLATE.read_text(encoding="utf-8")
        bad = sorted({c for c in text if ord(c) > 127})
        self.assertEqual(bad, [], f"non-ASCII in template: {bad}")

# --------------------------------------------------------------------------
# Content classification: screens vs camera footage
# --------------------------------------------------------------------------
@unittest.skipUnless(HAVE_IMAGING, "imagehash/Pillow not installed")
class TestFlatness(TempDirCase):
    """Flatness separates a screen from a face. See CONTENT_FLATNESS."""

    def img(self, fill):
        from PIL import Image
        return Image.new("RGB", (1408, 792), fill)

    def test_solid_dark_is_flat(self) -> None:
        self.assertGreater(sc.flatness(self.img((5, 5, 8))), 0.99)

    def test_solid_white_is_flat(self) -> None:
        self.assertGreater(sc.flatness(self.img((250, 250, 250))), 0.99)

    def test_midtone_is_not_flat(self) -> None:
        """Skin and walls sit in the midrange — the band flatness ignores."""
        self.assertLess(sc.flatness(self.img((128, 120, 110))), 0.01)

    def test_threshold_sits_between_them(self) -> None:
        flat = sc.flatness(self.img((250, 250, 250)))
        mid = sc.flatness(self.img((128, 120, 110)))
        self.assertLess(mid, sc.CONTENT_FLATNESS < flat)

    def test_hash_box_excludes_the_corners(self) -> None:
        """A webcam parked bottom-left must fall outside the hash region."""
        box = sc.hash_box(self.img((0, 0, 0)))
        self.assertEqual(box.size, (int(1408 * 0.72), int(792 * 0.66)))

    def test_score_frames_keys_on_filename(self) -> None:
        from PIL import Image
        f = self.tmp / "00-00-01.jpg"
        Image.new("RGB", (640, 360), (250, 250, 250)).save(f)
        scores = sc.score_frames([sc.Frame(1.0, f)])
        self.assertIn("00-00-01.jpg", scores)
        self.assertGreater(scores["00-00-01.jpg"], 0.9)


@unittest.skipUnless(HAVE_IMAGING, "imagehash/Pillow not installed")
class TestCornerMotionDedupe(TempDirCase):
    """The regression that made dedupe a no-op on a 58-minute podcast.

    A static screen with a moving webcam in the corner hashed as a new screen
    every single frame: whole-frame phash retained 99.8% of them.
    """

    def frames(self, n=8):
        """Static screen, webcam-shaped block noise in the bottom-left corner.

        Blocks, not scattered pixels: phash downscales to 64x64 before the DCT,
        and single pixels average away to nothing at that size.
        """
        from PIL import Image, ImageDraw
        import random
        out = []
        for i in range(n):
            random.seed(i)
            im = Image.new("RGB", (1408, 792), (20, 22, 30))
            d = ImageDraw.Draw(im)
            d.rectangle((200, 100, 1200, 400), fill=(240, 240, 240))
            for y in range(792 - 230, 792, 25):      # outside HASH_BOX
                for x in range(0, 300, 25):
                    v = random.choice((0, 255))
                    d.rectangle((x, y, x + 25, y + 25), fill=(v, v, v))
            p = self.tmp / f"s_{i:03d}.jpg"
            im.save(p)
            out.append(sc.Frame(float(i), p))
        return out

    def test_corner_motion_moves_a_whole_frame_hash(self) -> None:
        """Measured 54-88 apart on a 256-bit hash — far past the threshold."""
        import imagehash
        from PIL import Image
        a, b = self.frames(2)
        with Image.open(a.path) as ia, Image.open(b.path) as ib:
            d = imagehash.phash(ia, hash_size=sc.PHASH_SIZE) - imagehash.phash(
                ib, hash_size=sc.PHASH_SIZE)
        self.assertGreater(d, sc.PHASH_DISTANCE)

    def test_corner_motion_does_not_move_a_centre_hash(self) -> None:
        import imagehash
        from PIL import Image
        a, b = self.frames(2)
        with Image.open(a.path) as ia, Image.open(b.path) as ib:
            d = imagehash.phash(sc.hash_box(ia), hash_size=sc.PHASH_SIZE) - \
                imagehash.phash(sc.hash_box(ib), hash_size=sc.PHASH_SIZE)
        self.assertEqual(d, 0)

    def test_whole_frame_hashing_keeps_every_frame(self) -> None:
        kept = sc.dedupe(self.frames(), sc.PHASH_DISTANCE, whole=True)
        self.assertEqual(len(kept), 8, "this is the 99.8%-retention bug")

    def test_centre_hashing_collapses_the_static_screen(self) -> None:
        self.assertEqual(len(sc.dedupe(self.frames(), sc.PHASH_DISTANCE)), 1)


class TestSegments(unittest.TestCase):
    def frames(self, times):
        return [sc.Frame(float(t), Path(f"{sc.hhmmss(t, sep='-')}.jpg")) for t in times]

    def scores(self, frames, content):
        return {f.path.name: (0.9 if f.ts in content else 0.01) for f in frames}

    def test_merges_across_a_short_gap(self) -> None:
        fr = self.frames(range(0, 60))
        spans = sc.segments(fr, self.scores(fr, set(range(0, 25)) | set(range(35, 60))))
        self.assertEqual(spans, [(0, 59)])

    def test_splits_on_a_long_gap(self) -> None:
        fr = self.frames(list(range(0, 30)) + list(range(120, 150)))
        spans = sc.segments(fr, self.scores(fr, set(range(0, 30)) | set(range(120, 150))))
        self.assertEqual(spans, [(0, 29), (120, 149)])

    def test_drops_a_run_shorter_than_the_minimum(self) -> None:
        fr = self.frames(range(0, 10))
        self.assertEqual(sc.segments(fr, self.scores(fr, set(range(0, 5)))), [])

    def test_no_content_means_no_spans(self) -> None:
        fr = self.frames(range(0, 60))
        self.assertEqual(sc.segments(fr, self.scores(fr, set())), [])


class TestDerivedSections(unittest.TestCase):
    def test_labels_from_the_opening_words(self) -> None:
        cues = [sc.Cue(2.0, "context engineering"), sc.Cue(6.0, "is the whole game")]
        got = sc.derive_sections([(0, 90)], cues)
        self.assertEqual(got[0]["title"], "context engineering is the whole game")
        self.assertEqual((got[0]["start"], got[0]["end"]), (0, 90))

    def test_silent_span_is_labelled_not_dropped(self) -> None:
        self.assertEqual(sc.derive_sections([(0, 90)], [])[0]["title"], "(silent)")

    def test_long_label_is_truncated_on_a_word(self) -> None:
        cues = [sc.Cue(1.0, "word " * 60)]
        title = sc.derive_sections([(0, 90)], cues)[0]["title"]
        self.assertLessEqual(len(title), 71)
        self.assertTrue(title.endswith("\u2026"))

    def test_only_the_lead_seconds_are_used(self) -> None:
        cues = [sc.Cue(1.0, "early"), sc.Cue(400.0, "much later")]
        self.assertEqual(sc.derive_sections([(0, 500)], cues)[0]["title"], "early")


class TestWindowContentFilter(TempDirCase):
    def bundle(self, flat):
        dest = self.tmp / "VID"
        (dest / "frames").mkdir(parents=True)
        frames = []
        for ts in range(0, 5):
            p = dest / "frames" / f"{sc.hhmmss(ts, sep='-')}.jpg"
            p.write_bytes(b"x")
            frames.append(p.name)
        meta = {"id": "VID", "title": "T", "duration": 10, "transcript": [],
                "flatness": {n: flat[i] for i, n in enumerate(frames)},
                "content_threshold": sc.CONTENT_FLATNESS}
        (dest / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
        return dest

    def emit(self, dest, **kw):
        buf = io.StringIO()
        with redirect_stdout(buf):
            sc.emit_window(dest, 0, 10, **kw)
        return buf.getvalue()

    @staticmethod
    def n_frames(out):
        """Count FRAME *lines* — the instruction header names FRAME too."""
        return sum(1 for ln in out.splitlines() if ln.startswith("FRAME "))

    def test_camera_frames_are_hidden(self) -> None:
        out = self.emit(self.bundle([0.9, 0.01, 0.9, 0.01, 0.01]))
        self.assertEqual(self.n_frames(out), 2)
        self.assertIn("3 camera frames hidden", out)

    def test_all_shows_every_frame(self) -> None:
        out = self.emit(self.bundle([0.9, 0.01, 0.9, 0.01, 0.01]), every=True)
        self.assertEqual(self.n_frames(out), 5)

    def test_a_span_with_no_screen_falls_back_to_camera(self) -> None:
        """Showing nothing reads as 'no footage', not 'no screen shared'."""
        out = self.emit(self.bundle([0.01] * 5))
        self.assertEqual(self.n_frames(out), 5)
        self.assertIn("No screen was shared", out)

    def test_a_bundle_without_scores_shows_everything(self) -> None:
        dest = self.bundle([0.01] * 5)
        meta = json.loads((dest / "meta.json").read_text())
        del meta["flatness"]
        (dest / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
        self.assertEqual(self.n_frames(self.emit(dest)), 5)


class TestBundleScribe(TempDirCase):
    """BUNDLE.md is the scribe: greppable transcript with frame pointers."""

    def build(self, chapters):
        dest = self.tmp / "VID"
        (dest / "frames").mkdir(parents=True)
        frames, flat = [], {}
        for ts in range(0, 40):
            p = dest / "frames" / f"{sc.hhmmss(ts, sep='-')}.jpg"
            p.write_bytes(b"x")
            frames.append(sc.Frame(float(ts), p))
            flat[p.name] = 0.9 if ts < 30 else 0.01
        cues = [sc.Cue(1.0, "first words here"), sc.Cue(35.0, "later words")]
        meta = {"id": "VID", "title": "T", "channel": "C", "duration": 40,
                "url": "u", "description": "", "chapters": chapters,
                "flatness": flat, "content_threshold": sc.CONTENT_FLATNESS,
                "segments": [[0, 29]],
                "transcript": [{"start": c.start, "text": c.text} for c in cues]}
        sc.build_bundle(meta, cues, frames, dest)
        return (dest / "BUNDLE.md").read_text(encoding="utf-8")

    def test_screen_lines_point_at_frames(self) -> None:
        text = self.build([])
        self.assertIn("`00:00:00` FRAME frames/00-00-00.jpg", text)
        self.assertEqual(text.count("FRAME frames/"), 30)

    def test_camera_frames_get_no_pointer(self) -> None:
        self.assertNotIn("frames/00-00-35.jpg", self.build([]))

    def test_transcript_interleaves_with_frames(self) -> None:
        text = self.build([])
        self.assertIn("`00:00:01` first words here", text)

    def test_derived_sections_when_the_author_published_none(self) -> None:
        text = self.build([])
        self.assertIn("Derived sections", text)
        self.assertIn("first words here", text)

    def test_real_chapters_win_over_derived(self) -> None:
        text = self.build([{"title": "Setup", "start": 0}])
        self.assertIn("## Chapters", text)
        self.assertNotIn("Derived sections", text)

    def test_segment_table_is_present(self) -> None:
        self.assertIn("Screen-share segments", self.build([]))

    def test_an_unclassified_bundle_still_points_at_every_frame(self) -> None:
        """Declining to classify must not leave the scribe with no pointers."""
        dest = self.tmp / "U"
        (dest / "frames").mkdir(parents=True)
        frames = []
        for ts in range(0, 6):
            f = dest / "frames" / f"{sc.hhmmss(ts, sep='-')}.jpg"
            f.write_bytes(b"x")
            frames.append(sc.Frame(float(ts), f))
        meta = {"id": "U", "title": "T", "channel": "C", "duration": 6, "url": "u",
                "description": "", "chapters": [], "flatness": {}, "segments": [],
                "transcript": []}
        sc.build_bundle(meta, [], frames, dest)
        text = (dest / "BUNDLE.md").read_text(encoding="utf-8")
        self.assertEqual(text.count("FRAME frames/"), 6)


class TestSeparationGate(unittest.TestCase):
    """A threshold is only meaningful if the frames fall into two groups.

    Measured within +/-0.05 of 0.19: 0.19% of the podcast's frames, 6.89% of the
    overlay screencast's.
    """

    def test_a_clear_valley_separates(self) -> None:
        scores = {f"a{i}": 0.02 for i in range(500)}
        scores.update({f"b{i}": 0.90 for i in range(500)})
        self.assertTrue(sc.separates(scores))

    def test_a_continuous_spread_does_not(self) -> None:
        scores = {f"c{i}": i / 1000 for i in range(1000)}
        self.assertFalse(sc.separates(scores))

    def test_mass_sitting_on_the_threshold_does_not(self) -> None:
        """The git-diagram-over-b-roll case: content lands mid-scale."""
        scores = {f"a{i}": 0.02 for i in range(900)}
        scores.update({f"m{i}": 0.19 for i in range(100)})
        self.assertFalse(sc.separates(scores))

    def test_empty_scores_do_not_separate(self) -> None:
        self.assertFalse(sc.separates({}))



class TestBootstrap(TempDirCase):
    """A fresh plugin install has no venv and no third-party packages.

    `bootstrap` runs on a bare system python3, so it may import only the
    standard library, and it prints exactly one thing on stdout — the
    interpreter path a caller binds with PY=$(... bootstrap).
    """

    def test_venv_python_path(self) -> None:
        got = sc.venv_python(Path("/x/venv"))
        self.assertEqual(got.parent.name, "Scripts" if os.name == "nt" else "bin")
        self.assertEqual(got.parent.parent, Path("/x/venv"))

    def test_missing_modules_names_what_is_absent(self) -> None:
        got = sc.missing_modules(Path(sys.executable), ["json", "nope_not_real_xyz"])
        self.assertEqual(got, ["nope_not_real_xyz"])

    def test_missing_modules_on_a_dead_interpreter_reports_everything(self) -> None:
        """A venv that failed to build must not read as fully provisioned."""
        got = sc.missing_modules(self.tmp / "nope" / "python", ["json", "os"])
        self.assertEqual(got, ["json", "os"])

    def fake_venv(self):
        venv = self.tmp / "v"
        py = sc.venv_python(venv)
        py.parent.mkdir(parents=True)
        py.write_text("#!/bin/sh\n")
        py.chmod(0o755)
        return venv, py

    def test_stdout_carries_only_the_interpreter_path(self) -> None:
        """A pip upgrade notice leaking into stdout would corrupt $PY."""
        venv, py = self.fake_venv()
        real = sc.missing_modules
        sc.missing_modules = lambda *a, **k: []
        self.addCleanup(setattr, sc, "missing_modules", real)
        buf = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(io.StringIO()):
            sc.cmd_bootstrap(argparse.Namespace(venv=str(venv)))
        self.assertEqual(buf.getvalue().strip(), str(py))

    def test_an_existing_venv_is_not_rebuilt(self) -> None:
        venv, py = self.fake_venv()
        marker = py.read_text()
        real = sc.missing_modules
        sc.missing_modules = lambda *a, **k: []
        self.addCleanup(setattr, sc, "missing_modules", real)
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            sc.cmd_bootstrap(argparse.Namespace(venv=str(venv)))
        self.assertEqual(py.read_text(), marker, "venv was recreated")

    def test_a_still_missing_required_package_fails_loudly(self) -> None:
        venv, _ = self.fake_venv()
        real, run = sc.missing_modules, sc.subprocess.run
        sc.missing_modules = lambda p, names: [n for n in names if n in sc.REQUIRED_DEPS]
        sc.subprocess.run = lambda *a, **k: argparse.Namespace(returncode=0)
        self.addCleanup(setattr, sc, "missing_modules", real)
        self.addCleanup(setattr, sc.subprocess, "run", run)
        with self.assertRaises(SystemExit) as cm, \
                redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            sc.cmd_bootstrap(argparse.Namespace(venv=str(venv)))
        self.assertIn("still missing", str(cm.exception))

    def test_an_optional_package_does_not_fail_the_bootstrap(self) -> None:
        """curl_cffi may not build everywhere; that must not block a build."""
        venv, py = self.fake_venv()
        real, run = sc.missing_modules, sc.subprocess.run
        sc.missing_modules = lambda p, names: [n for n in names if n in sc.OPTIONAL_DEPS]
        sc.subprocess.run = lambda *a, **k: argparse.Namespace(returncode=0)
        self.addCleanup(setattr, sc, "missing_modules", real)
        self.addCleanup(setattr, sc.subprocess, "run", run)
        buf = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(io.StringIO()):
            sc.cmd_bootstrap(argparse.Namespace(venv=str(venv)))
        self.assertEqual(buf.getvalue().strip(), str(py))



class TestUsefulLinksAnchoring(unittest.TestCase):
    """Substring matching ate the technical links the filter exists to keep."""

    DESC = """
    https://docs.aws.amazon.com/lambda/latest/dg/welcome.html
    https://phoenix.com/engineering/blog
    https://s3.amazonaws.com/bucket/spec.pdf
    https://github.com/real/repo
    https://amzn.to/affiliate
    https://www.amazon.com/dp/B0123456
    https://x.com/someone
    https://patreon.com/creator
    https://youtube.com/watch?v=abc&sub_confirmation=1
    """

    def links(self):
        return sc.useful_links(self.DESC)

    def test_aws_docs_survive(self) -> None:
        """`amazon.` matched docs.aws.amazon.com — an AWS docs link."""
        self.assertIn("https://docs.aws.amazon.com/lambda/latest/dg/welcome.html",
                      self.links())

    def test_a_host_merely_ending_in_x_com_survives(self) -> None:
        """`x.com/` matched phoenix.com/."""
        self.assertIn("https://phoenix.com/engineering/blog", self.links())

    def test_real_affiliate_and_social_still_dropped(self) -> None:
        got = self.links()
        for dead in ("https://amzn.to/affiliate",
                     "https://www.amazon.com/dp/B0123456",
                     "https://x.com/someone",
                     "https://patreon.com/creator",
                     "https://youtube.com/watch?v=abc&sub_confirmation=1"):
            self.assertNotIn(dead, got, f"{dead} should be filtered")

    def test_subdomains_of_a_noise_host_are_dropped(self) -> None:
        self.assertEqual(sc.useful_links("https://open.spotify.com/show/xyz"), [])

    def test_a_bare_youtube_link_is_kept(self) -> None:
        """A description linking a prerequisite video is context worth keeping."""
        self.assertEqual(sc.useful_links("https://youtube.com/watch?v=abc"),
                         ["https://youtube.com/watch?v=abc"])


@unittest.skipUnless(HAVE_IMAGING, "imagehash/Pillow not installed")
class TestArtifactSafety(TempDirCase):
    TEMPLATE = Path(__file__).resolve().parent.parent / "assets" / "artifact-template.html"

    def bundle(self, title="T", transcript=(), frame_secs=(0, 5, 10)):
        from PIL import Image, ImageDraw
        dest = self.tmp / "VID"
        (dest / "frames").mkdir(parents=True)
        for i in frame_secs:
            im = Image.new("RGB", (1408, 792), (18, 20, 30))
            d = ImageDraw.Draw(im)
            d.rectangle([60, 120, 190 + i * 60, 620], fill=(230, 230, 225))
            im.save(dest / "frames" / f"{sc.hhmmss(i, sep='-')}.jpg", "JPEG")
        (dest / "meta.json").write_text(json.dumps({
            "id": "VID", "title": title, "channel": "C", "duration": 40,
            "url": "u", "fps": 1.0, "frame_count": len(frame_secs),
            "chapters": [], "description": "",
            "transcript": [{"start": t, "text": x} for t, x in transcript],
        }), encoding="utf-8")
        return dest

    def build(self, dest, start=0, end=30):
        out = self.tmp / "p.html"
        with redirect_stdout(io.StringIO()):
            sc.build_artifact(dest, start, end, out, self.TEMPLATE, sc.DISPLAY_DISTANCE)
        return out.read_text(encoding="utf-8")

    def test_a_hostile_title_cannot_break_out_of_the_title_element(self) -> None:
        """The title is network-derived metadata landing in raw markup."""
        html = self.build(self.bundle(
            title="</title><script>alert(document.domain)</script>"))
        self.assertNotIn("<script>alert(document.domain)</script>", html)
        self.assertIn("&lt;/title&gt;", html)

    def test_narration_before_the_first_frame_reaches_the_page(self) -> None:
        """Anchoring row 0 at its own ts dropped every earlier cue, silently."""
        dest = self.bundle(frame_secs=(10, 15, 20),
                           transcript=((3.0, "BEFORE_FIRST_FRAME"),
                                       (12.0, "during")))
        html = self.build(dest, 0, 30)
        D = json.loads(re.search(r"^var D = (\{.*\});$", html, re.M | re.S).group(1))
        said = " ".join(f["said"] for f in D["frames"])
        self.assertIn("BEFORE_FIRST_FRAME", said)
        self.assertIn("during", said)

    def test_payload_cannot_close_the_script_element(self) -> None:
        html = self.build(self.bundle(transcript=((1.0, "</script><b>x</b>"),)))
        self.assertNotIn("</script><b>x</b>", html)



# --------------------------------------------------------------------------
class LibraryCase(TempDirCase):
    """A library of hand-built bundles, so the maintenance commands can be
    driven without downloading anything."""

    def bundle(self, vid, *, frames=3, title=None, cues=(), used=None,
               url=None, channel="chan"):
        dest = self.tmp / vid
        (dest / "frames").mkdir(parents=True)
        for ts in range(frames):
            (dest / "frames" / f"{sc.hhmmss(ts, sep='-')}.jpg").write_bytes(b"x" * 100)
        meta = {
            "id": vid,
            "title": title or f"title of {vid}",
            "channel": channel,
            "duration": 60,
            "url": url or f"https://example.test/{vid}",
            "transcript": [{"start": float(t), "text": txt} for t, txt in cues],
        }
        (dest / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
        (dest / "BUNDLE.md").write_text("# scribe\n", encoding="utf-8")
        if used is not None:
            marker = dest / sc.USED_MARKER
            marker.touch()
            os.utime(marker, (used, used))
        return dest

    def invoke(self, fn, **kw):
        """Call a cmd_* with a namespace, capturing stdout.

        Not `run` — that is TestCase.run, and shadowing it makes the whole
        class silently un-runnable."""
        buf = io.StringIO()
        with redirect_stdout(buf):
            fn(argparse.Namespace(**kw))
        return buf.getvalue()

    def index(self, **kw):
        return self.invoke(sc.cmd_index, root=self.tmp, json=False, **kw)

    def search(self, term, **kw):
        opts = dict(root=self.tmp, id=[], context=0, regex=False,
                    case=False, limit=40)
        opts.update(kw)
        return self.invoke(sc.cmd_search, term=term, **opts)

    def prune(self, **kw):
        opts = dict(root=self.tmp, id=[], older_than=None, keep=None,
                    over=None, yes=False)
        opts.update(kw)
        return self.invoke(sc.cmd_prune, **opts)


class TestSize(unittest.TestCase):
    def test_units(self) -> None:
        self.assertEqual(sc.parse_size("512"), 512)
        self.assertEqual(sc.parse_size("2K"), 2048)
        self.assertEqual(sc.parse_size("1.5G"), int(1.5 * 1024 ** 3))
        self.assertEqual(sc.parse_size(" 4 GB "), 4 * 1024 ** 3)
        self.assertEqual(sc.parse_size("300m"), 300 * 1024 ** 2)

    def test_garbage_is_refused(self) -> None:
        for bad in ("", "big", "2X", "-5G", "1.2.3M"):
            with self.assertRaises(SystemExit):
                sc.parse_size(bad)

    def test_human_round_trips_readably(self) -> None:
        self.assertEqual(sc.human(0), "0B")
        self.assertEqual(sc.human(2048), "2.0K")
        self.assertEqual(sc.human(3 * 1024 ** 3), "3.0G")


class TestLibraryScan(LibraryCase):
    def test_only_directories_with_meta_are_bundles(self) -> None:
        """The bundle root also collects _staging and whatever Finder drops in
        it. `.DS_Store` really is sitting in the author's library."""
        self.bundle("AAA")
        (self.tmp / ".DS_Store").write_bytes(b"junk")
        (self.tmp / "_staging").mkdir()
        (self.tmp / "notes.txt").write_text("hi")
        self.assertEqual([e.id for e in sc.library(self.tmp)], ["AAA"])

    def test_corrupt_meta_is_skipped_not_fatal(self) -> None:
        self.bundle("AAA")
        broken = self.tmp / "BBB"
        broken.mkdir()
        (broken / "meta.json").write_text("{not json", encoding="utf-8")
        self.assertEqual([e.id for e in sc.library(self.tmp)], ["AAA"])

    def test_a_json_scalar_is_not_a_bundle(self) -> None:
        odd = self.tmp / "CCC"
        odd.mkdir()
        (odd / "meta.json").write_text("42", encoding="utf-8")
        self.assertEqual(sc.library(self.tmp), [])

    def test_most_recently_read_first(self) -> None:
        self.bundle("OLD", used=1_000_000)
        self.bundle("MID", used=2_000_000)
        self.bundle("NEW", used=3_000_000)
        self.assertEqual([e.id for e in sc.library(self.tmp)],
                         ["NEW", "MID", "OLD"])

    def test_missing_frames_dir_counts_zero(self) -> None:
        d = self.bundle("AAA", frames=2)
        shutil.rmtree(d / "frames")
        (entry,) = sc.library(self.tmp)
        self.assertEqual(entry.frames, 0)

    def test_a_symlink_is_measured_as_a_link(self) -> None:
        """Following one out of the library would inflate the number
        `prune --over` acts on, and a loop would hang the walk."""
        d = self.bundle("AAA", frames=1)
        big = self.tmp / "outside.bin"
        big.write_bytes(b"y" * 50_000)
        try:
            (d / "frames" / "link.jpg").symlink_to(big)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        (entry,) = sc.library(self.tmp)
        self.assertLess(entry.bytes, 5_000)


class TestIndex(LibraryCase):
    def test_lists_every_bundle_with_a_total(self) -> None:
        self.bundle("AAA", frames=2)
        self.bundle("BBB", frames=5)
        out = self.index()
        self.assertIn("AAA", out)
        self.assertIn("BBB", out)
        self.assertIn("2 bundles", out)

    def test_a_bundle_with_no_frames_shows_zero(self) -> None:
        """An interrupted build, not a state prune can produce — a pruned
        bundle is not in the library at all."""
        d = self.bundle("AAA")
        shutil.rmtree(d / "frames")
        self.assertRegex(self.index(), r"AAA\s+0\s")

    def test_empty_library_says_so_without_crashing(self) -> None:
        self.assertIn("no bundles", self.index())

    def test_json_form_carries_the_url_to_rebuild_from(self) -> None:
        self.bundle("AAA", frames=2)
        rows = json.loads(self.invoke(sc.cmd_index, root=self.tmp, json=True))
        self.assertEqual(rows[0]["id"], "AAA")
        self.assertEqual(rows[0]["url"], "https://example.test/AAA")
        self.assertEqual(rows[0]["frames"], 2)


class TestSearch(LibraryCase):
    def library(self):
        self.bundle("AAA", frames=3, title="Alpha talk",
                    cues=((0.0, "we tried Mermaid diagrams"),
                          (1.5, "and then a call stack"),
                          (2.0, "nothing to see here")))
        self.bundle("BBB", frames=3, title="Beta talk",
                    cues=((1.0, "no mermaid in this one"),))

    def test_finds_a_phrase_across_bundles(self) -> None:
        self.library()
        out = self.search("mermaid")
        self.assertIn("AAA", out)
        self.assertIn("BBB", out)
        self.assertIn("2 hits in 2 of 2 bundles", out)

    def test_case_sensitivity_is_opt_in(self) -> None:
        self.library()
        self.assertIn("1 hit in 1 of 2", self.search("Mermaid", case=True))

    def test_hits_name_the_frame_that_was_on_screen(self) -> None:
        """The cue at 1.5s falls between frames, so the frame still up is the
        one sampled at 1s — not the next one."""
        self.library()
        out = self.search("call stack")
        self.assertIn("frames/00-00-01.jpg", out)

    def test_a_pruned_bundle_still_searches(self) -> None:
        self.library()
        shutil.rmtree(self.tmp / "AAA" / "frames")
        out = self.search("call stack")
        self.assertIn("00:00:01", out)
        self.assertIn(" -  ", out)

    def test_restricting_to_one_id(self) -> None:
        self.library()
        out = self.search("mermaid", id=["BBB"])
        self.assertIn("BBB", out)
        self.assertNotIn("Alpha talk", out)

    def test_an_unknown_id_is_an_error(self) -> None:
        self.library()
        with self.assertRaises(SystemExit):
            self.search("mermaid", id=["ZZZ"])

    def test_context_shows_neighbouring_cues(self) -> None:
        self.library()
        out = self.search("call stack", context=1)
        self.assertIn("we tried Mermaid", out)
        self.assertIn("nothing to see here", out)

    def test_a_term_is_literal_unless_regex_is_asked_for(self) -> None:
        self.bundle("AAA", cues=((0.0, "a.b"), (1.0, "axb")))
        self.assertIn("1 hit", self.search("a.b"))
        self.assertIn("2 hits", self.search("a.b", regex=True))

    def test_a_broken_pattern_is_an_error_not_a_traceback(self) -> None:
        self.library()
        with self.assertRaises(SystemExit):
            self.search("(unclosed", regex=True)

    def test_no_match_says_so(self) -> None:
        self.library()
        self.assertIn("no match", self.search("kubernetes"))

    def test_a_title_only_match_still_surfaces_the_bundle(self) -> None:
        self.library()
        out = self.search("Alpha")
        self.assertIn("AAA", out)
        self.assertIn("(title)", out)


class TestPruneSelection(LibraryCase):
    def setUp(self) -> None:
        super().setUp()
        self.bundle("OLD", frames=4, used=1_000_000)
        self.bundle("MID", frames=4, used=2_000_000)
        self.bundle("NEW", frames=4, used=3_000_000)

    def select(self, **kw):
        opts = dict(id=[], older_than=None, keep=None, over=None)
        opts.update(kw)
        return [e.id for e in sc.prune_targets(sc.library(self.tmp),
                                               argparse.Namespace(**opts))]

    def test_keep_n_evicts_the_least_recently_read(self) -> None:
        self.assertEqual(self.select(keep=1), ["MID", "OLD"])
        self.assertEqual(self.select(keep=0), ["NEW", "MID", "OLD"])
        self.assertEqual(self.select(keep=9), [])

    def test_older_than_uses_last_read(self) -> None:
        self.bundle("FRESH", used=time.time())
        self.bundle("STALE", used=time.time() - 40 * 86400)
        picked = self.select(older_than=30)
        self.assertIn("STALE", picked)
        self.assertNotIn("FRESH", picked)

    def test_over_evicts_lru_first_and_stops_at_the_budget(self) -> None:
        total = sum(e.bytes for e in sc.library(self.tmp))
        self.assertEqual(self.select(over=str(total - 1)), ["OLD"])

    def test_over_takes_nothing_when_the_library_already_fits(self) -> None:
        self.assertEqual(self.select(over="10G"), [])

    def test_explicit_ids_win_over_every_policy(self) -> None:
        self.assertEqual(self.select(id=["NEW"], keep=0, over="1"), ["NEW"])

    def test_an_unknown_id_is_an_error(self) -> None:
        with self.assertRaises(SystemExit):
            self.select(id=["NOPE"])

    def test_a_bundle_whose_build_left_no_frames_is_still_prunable(self) -> None:
        """An interrupted build leaves the directory; prune still takes it."""
        stripped = self.bundle("GONE", frames=2, used=500_000)
        shutil.rmtree(stripped / "frames")
        self.assertIn("GONE", self.select(id=["GONE"]))


class TestPruneExecution(LibraryCase):
    def test_a_dry_run_deletes_nothing(self) -> None:
        d = self.bundle("AAA", frames=3)
        out = self.prune(keep=0)
        self.assertIn("dry run", out)
        self.assertTrue((d / "frames").is_dir())

    def test_prune_removes_the_whole_bundle(self) -> None:
        """"Prune a scribed video" means the video leaves the library —
        frames, scribe, meta, directory. There is no half-pruned state."""
        d = self.bundle("AAA", frames=3)
        self.prune(keep=0, yes=True)
        self.assertFalse(d.exists())

    def test_a_half_finished_build_leaves_nothing_behind(self) -> None:
        d = self.bundle("AAA", frames=1)
        (d / "frames.new").mkdir()
        (d / "frames.old").mkdir()
        self.prune(keep=0, yes=True)
        self.assertFalse(d.exists())

    def test_a_dry_run_says_what_goes(self) -> None:
        out = self.bundle("AAA", frames=3) and self.prune(keep=0)
        self.assertIn("scribe, frames, directory", out)
        self.assertIn("dry run", out)

    def test_a_removed_bundle_leaves_the_library_empty(self) -> None:
        self.bundle("AAA", frames=3)
        self.prune(keep=0, yes=True)
        with self.assertRaises(SystemExit):
            self.prune(keep=0)

    def test_nonsense_selectors_are_refused(self) -> None:
        self.bundle("AAA")
        for kw in ({"keep": -1}, {"older_than": 0}, {"older_than": -3}):
            with self.assertRaises(SystemExit):
                self.prune(**kw)

    def test_drop_refuses_a_path_outside_the_root(self) -> None:
        """`library` cannot produce one, but this is the only command that
        deletes, so it re-derives containment rather than trusting a caller."""
        d = self.bundle("AAA", frames=1)
        (entry,) = sc.library(self.tmp)
        with redirect_stdout(io.StringIO()) as buf:
            refused = sc.drop(entry, self.tmp / "elsewhere")
        self.assertFalse(refused)
        self.assertIn("skipped", buf.getvalue())
        self.assertTrue((d / "frames").is_dir())

    def test_one_refusal_does_not_abandon_the_rest(self) -> None:
        """It reports and moves on: exiting mid-loop left a prune half applied
        and unsummarised."""
        self.bundle("AAA", frames=1)
        self.bundle("BBB", frames=1)
        out = self.prune(keep=0, yes=True)
        self.assertIn("removed 2", out)

    def test_an_empty_library_is_an_error(self) -> None:
        with self.assertRaises(SystemExit):
            self.prune(keep=0)


class TestFrameStamp(unittest.TestCase):
    def test_names_that_are_timestamps(self) -> None:
        self.assertEqual(sc.frame_stamp(Path("00-01-05.jpg")), 65.0)
        self.assertEqual(sc.frame_stamp(Path("01-00-00.jpg")), 3600.0)
        self.assertEqual(sc.frame_stamp(Path("00-00-07_2.jpg")), 7.0)

    def test_names_that_are_not(self) -> None:
        for name in ("frame.jpg", "00-01.jpg", "a-b-c.jpg", "00-01-05-9.jpg",
                     "٠٠-٠١-٠٥.jpg"):
            self.assertIsNone(sc.frame_stamp(Path(name)))


class TestFrameFor(unittest.TestCase):
    def frames(self):
        return [sc.Frame(t, Path(f"{t}.jpg")) for t in (0.0, 10.0, 25.0)]

    def test_picks_the_last_frame_at_or_before_the_cue(self) -> None:
        fs = self.frames()
        keys = [f.ts for f in fs]
        self.assertEqual(sc.frame_for(fs, keys, 10.0).ts, 10.0)
        self.assertEqual(sc.frame_for(fs, keys, 24.9).ts, 10.0)
        self.assertEqual(sc.frame_for(fs, keys, 99.0).ts, 25.0)

    def test_a_cue_before_every_frame_has_none(self) -> None:
        fs = [sc.Frame(10.0, Path("a.jpg"))]
        self.assertIsNone(sc.frame_for(fs, [10.0], 5.0))

    def test_no_frames_at_all(self) -> None:
        self.assertIsNone(sc.frame_for([], [], 5.0))


class TestNamingAVideo(LibraryCase):
    """An 11-character YouTube id is not how anyone refers to a video."""

    def setUp(self) -> None:
        super().setUp()
        self.bundle("xgkjtF89-44", title="Ex-NASA dev reveals his workflow")
        self.bundle("XV2PAHWnJN0", title="I Left 10 AI Agents Alone")

    def one(self, needle):
        return sc.pick_one(needle, sc.library(self.tmp)).id

    def test_a_word_from_the_title(self) -> None:
        self.assertEqual(self.one("NASA"), "xgkjtF89-44")
        self.assertEqual(self.one("left 10"), "XV2PAHWnJN0")

    def test_case_does_not_matter(self) -> None:
        self.assertEqual(self.one("nasa"), "xgkjtF89-44")
        self.assertEqual(self.one("ex-nasa"), "xgkjtF89-44")

    def test_the_channel(self) -> None:
        self.bundle("ZZZ1", title="something else", channel="Matt Pocock")
        self.assertEqual(self.one("pocock"), "ZZZ1")

    def test_a_url_in_any_shape(self) -> None:
        """The stored URL contains the id; a short link contains it too, so the
        match has to run in both directions."""
        for url in ("https://example.test/xgkjtF89-44",
                    "https://youtu.be/xgkjtF89-44",
                    "https://www.youtube.com/watch?v=xgkjtF89-44&t=90s"):
            self.assertEqual(self.one(url), "xgkjtF89-44", url)

    def test_the_id_itself(self) -> None:
        self.assertEqual(self.one("xgkjtF89-44"), "xgkjtF89-44")

    def test_an_exact_id_beats_a_title_that_mentions_it(self) -> None:
        """Otherwise a real id turns ambiguous because another video names it."""
        self.bundle("ZZZ2", title="a talk about xgkjtF89-44 and its ideas")
        self.assertEqual(self.one("xgkjtF89-44"), "xgkjtF89-44")

    def test_ambiguity_is_refused_and_lists_the_candidates(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            self.one("e")
        msg = str(ctx.exception)
        self.assertIn("matches", msg)
        self.assertIn("xgkjtF89-44", msg)
        self.assertIn("XV2PAHWnJN0", msg)

    def test_no_match_points_at_index(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            self.one("kubernetes")
        self.assertIn("index", str(ctx.exception))

    def test_an_empty_needle_matches_nothing(self) -> None:
        for needle in ("", "   "):
            with self.assertRaises(SystemExit):
                self.one(needle)

    def test_window_resolves_a_title_word(self) -> None:
        os.environ[sc.BUNDLES_ENV] = str(self.tmp)
        self.addCleanup(os.environ.pop, sc.BUNDLES_ENV, None)
        self.assertEqual(sc.resolve_bundle(Path("NASA")).name, "xgkjtF89-44")

    def test_a_bundle_directory_still_wins_over_any_matching(self) -> None:
        os.environ[sc.BUNDLES_ENV] = str(self.tmp)
        self.addCleanup(os.environ.pop, sc.BUNDLES_ENV, None)
        direct = self.tmp / "XV2PAHWnJN0"
        self.assertEqual(sc.resolve_bundle(direct), direct)

    def test_prune_takes_a_title_word(self) -> None:
        out = self.prune(id=["NASA"])
        self.assertIn("xgkjtF89-44", out)
        self.assertNotIn("XV2PAHWnJN0", out)

    def test_prune_counts_one_video_once(self) -> None:
        """Two needles naming the same video must not double-count its bytes."""
        out = self.prune(id=["NASA", "xgkjtF89-44"])
        self.assertIn("1 bundle,", out)

    def test_prune_refuses_an_ambiguous_name_rather_than_guessing(self) -> None:
        with self.assertRaises(SystemExit):
            self.prune(id=["e"], yes=True)
        self.assertTrue((self.tmp / "xgkjtF89-44").is_dir())
        self.assertTrue((self.tmp / "XV2PAHWnJN0").is_dir())

    def test_search_takes_a_title_word(self) -> None:
        self.bundle("QQQ", title="Q talk", cues=((0.0, "a word about oracles"),))
        out = self.search("oracles", id=["Q talk"])
        self.assertIn("QQQ", out)


class TestBundleSignature(LibraryCase):
    """Round-1 HIGH: `prune --yes` rmtree'd directories that were never
    bundles, because a `meta.json` was the whole test and that filename is
    everywhere. An npm package and a photo folder were destroyed proving it."""

    def foreign(self, name, meta):
        d = self.tmp / name
        d.mkdir()
        (d / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
        (d / "keep-me.txt").write_text("not yours", encoding="utf-8")
        return d

    def test_a_foreign_meta_json_is_not_a_bundle(self) -> None:
        self.foreign("some-node-package", {"name": "thing", "version": "1.0.0"})
        self.foreign("my-photos", {"camera": "X100V"})
        self.assertEqual(sc.library(self.tmp), [])

    def test_prune_will_not_delete_one(self) -> None:
        d = self.foreign("some-node-package", {"name": "thing"})
        self.bundle("AAA", frames=1)
        self.prune(keep=0, yes=True)
        self.assertTrue((d / "keep-me.txt").is_file())

    def test_a_meta_without_an_id_is_not_a_bundle(self) -> None:
        d = self.foreign("odd", {"title": "no id here"})
        (d / "BUNDLE.md").write_text("# not really", encoding="utf-8")
        self.assertEqual(sc.library(self.tmp), [])

    def test_a_directory_without_a_scribe_is_not_a_bundle(self) -> None:
        d = self.bundle("AAA", frames=1)
        (d / "BUNDLE.md").unlink()
        self.assertEqual(sc.library(self.tmp), [])

    def test_drop_re_derives_the_signature_it_was_handed(self) -> None:
        """library() is the gate, but drop() is what deletes."""
        d = self.bundle("AAA", frames=1)
        (entry,) = sc.library(self.tmp)
        (d / "BUNDLE.md").unlink()
        with redirect_stdout(io.StringIO()):
            self.assertFalse(sc.drop(entry, self.tmp))
        self.assertTrue(d.is_dir())

    def test_a_real_bundle_still_qualifies(self) -> None:
        self.bundle("AAA", frames=1)
        self.assertEqual([e.id for e in sc.library(self.tmp)], ["AAA"])


class TestSizesAreLazy(LibraryCase):
    """Round-1 MEDIUM: the comment claimed frames were walked only for a
    matching bundle; library() had already walked every one of them."""

    def test_a_scan_measures_nothing_until_asked(self) -> None:
        self.bundle("AAA", frames=3)
        (entry,) = sc.library(self.tmp)
        self.assertIsNone(entry._bytes)
        self.assertGreater(entry.bytes, 0)
        self.assertIsNotNone(entry._bytes)

    def test_search_never_walks_the_frames_for_sizes(self) -> None:
        self.bundle("AAA", frames=3, cues=((0.0, "a widget"),))
        walked = []
        real = os.walk
        os.walk = lambda p, **kw: (walked.append(str(p)), real(p, **kw))[1]
        try:
            self.search("widget")
        finally:
            os.walk = real
        self.assertEqual(walked, [])

    def test_index_still_reports_real_sizes(self) -> None:
        self.bundle("AAA", frames=3)
        self.assertNotIn("0B on disk", self.index())

    def test_reading_a_bundle_marks_it_used(self) -> None:
        d = self.bundle("AAA", frames=2, cues=((0.0, "hi"),))
        marker = d / sc.USED_MARKER
        self.assertFalse(marker.exists())
        with redirect_stdout(io.StringIO()):
            sc.emit_window(d, 0, 10)
        self.assertTrue(marker.is_file())


class TestClipStripsControlCharacters(unittest.TestCase):
    """A title is network-derived, and `prune`'s plan is what a person reads
    before authorising a delete. ESC is not whitespace, so split() leaves it."""

    def test_escape_sequences_do_not_survive(self) -> None:
        hostile = "Safe Video\x1b[2K\r  VID9  Totally Different"
        out = sc.clip(hostile, 80)
        self.assertNotIn("\x1b", out)
        self.assertIn("Safe Video", out)

    def test_other_control_characters_go_too(self) -> None:
        for ch in ("\x00", "\x07", "\x1b", "\x7f", "\x9b"):
            self.assertNotIn(ch, sc.clip(f"a{ch}b", 80))

    def test_ordinary_text_is_untouched(self) -> None:
        self.assertEqual(sc.clip("  a   b  ", 80), "a b")
        self.assertEqual(sc.clip("héllo — wörld", 80), "héllo — wörld")

    def test_it_still_clips(self) -> None:
        self.assertEqual(sc.clip("abcdef", 4), "abc…")


class TestSearchOutput(LibraryCase):
    def many(self, n=3, per=4):
        for i in range(n):
            self.bundle(f"VID{i}", frames=2, title=f"talk {i}",
                        cues=tuple((float(t), "the word widget here")
                                   for t in range(per)))

    def test_the_limit_never_prints_an_empty_header(self) -> None:
        """A header over no rows reads as "matched, nothing to show"."""
        self.many()
        out = self.search("widget", limit=2)
        bodies = {}
        current = None
        for line in out.splitlines():
            if line.startswith("VID"):
                current = line.split()[0]
                bodies[current] = 0
            elif current and line.strip().startswith(">"):
                bodies[current] += 1
        self.assertTrue(bodies)
        for vid, rows in bodies.items():
            self.assertGreater(rows, 0, f"{vid} printed a header with no rows")

    def test_the_count_of_what_was_withheld_is_honest(self) -> None:
        self.many(n=3, per=4)          # 12 hits total
        out = self.search("widget", limit=2)
        self.assertIn("12 hits in 3 of 3 bundles", out)
        self.assertIn("10 more", out)
        self.assertIn("--limit 0", out)

    def test_limit_zero_shows_everything(self) -> None:
        self.many(n=2, per=3)
        out = self.search("widget", limit=0)
        self.assertNotIn("stopped at", out)
        self.assertEqual(sum(1 for ln in out.splitlines()
                             if ln.strip().startswith(">")), 6)

    def test_adjacent_hits_do_not_repeat_their_context(self) -> None:
        self.bundle("AAA", frames=1, cues=((0.0, "before"), (1.0, "widget one"),
                                           (2.0, "widget two"), (3.0, "after")))
        out = self.search("widget", context=1)
        self.assertEqual(out.count("widget one"), 1)
        self.assertEqual(out.count("widget two"), 1)
        self.assertEqual(out.count("before"), 1)

    def test_every_hit_keeps_its_marker_inside_shared_context(self) -> None:
        """Two hits closer together than --context share a window. Keying the
        marker on the loop index left the second one unmarked and
        indistinguishable from a line that never matched — the footer said two
        hits and only one carried `>`."""
        self.bundle("AAA", frames=1, cues=((0.0, "before"), (1.0, "widget one"),
                                           (2.0, "widget two"), (3.0, "after")))
        out = self.search("widget", context=1)
        marked = [ln for ln in out.splitlines() if ln.strip().startswith(">")]
        self.assertEqual(len(marked), 2)
        self.assertTrue(any("widget one" in ln for ln in marked))
        self.assertTrue(any("widget two" in ln for ln in marked))
        for ln in marked:
            self.assertNotIn("before", ln)
            self.assertNotIn("after", ln)

    def test_the_marker_count_matches_the_reported_count(self) -> None:
        self.bundle("BBB", frames=1, cues=tuple(
            (float(t), "widget" if t % 2 else "filler") for t in range(10)))
        out = self.search("widget", context=2)
        marked = sum(1 for ln in out.splitlines() if ln.strip().startswith(">"))
        self.assertIn(f"{marked} hits", out)

    def test_a_cue_missing_start_is_skipped_not_a_traceback(self) -> None:
        d = self.tmp / "AAA"
        (d / "frames").mkdir(parents=True)
        (d / "BUNDLE.md").write_text("# scribe", encoding="utf-8")
        (d / "meta.json").write_text(json.dumps({
            "id": "AAA", "title": "T", "duration": 60,
            "url": "https://example.test/AAA",
            "transcript": [{"text": "a widget with no start"},
                           {"start": 1.0, "text": "a widget with one"}],
        }), encoding="utf-8")
        out = self.search("widget")
        self.assertIn("1 hit", out)


if __name__ == "__main__":
    unittest.main()
