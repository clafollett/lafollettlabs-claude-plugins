#!/usr/bin/env python3
"""
watchwith — turn a tutorial video into a bundle Claude can actually *watch*.

Transcripts drop the payload. In a screencast the information lives in the pixels
(terminal, file tree, IDE state, diagrams), so we sample frames at a fixed rate,
drop the visually-identical ones, and keep the survivors named by timestamp.

Nothing here summarizes. Density is the product; compression happens later, with
the user in the loop.

Two modes:

    build   video -> bundle/          sample densely, store everything
    window  bundle + span -> stdout   read back a slice that fits in context

`build` is deliberately greedy — disk is cheap, and a frame you culled at
extraction time is gone. `window` is where the context budget is enforced,
because that is the only place that knows what you are looking for.

Output tree:
    out/<video_id>/
        BUNDLE.md      <- nav map: meta, chapters, full transcript, frame index
        frames/        <- deduped frames, named HH-MM-SS.jpg
        meta.json      <- title, channel, duration, chapters, frame inventory

Install:
    pip install yt-dlp imagehash pillow
    ffmpeg must be on PATH

Usage:
    ./watchwith.py build "https://youtu.be/VIDEO_ID"
    ./watchwith.py build "<url>" --fps 2 --phash-distance 4
    ./watchwith.py window bundles/VIDEO_ID 12:00 18:00

Bundles are written to --out, else $WATCHWITH_BUNDLES, else ~/.watchwith/bundles.
`window` also accepts a bare video id, resolved against that root:

    ./watchwith.py window VIDEO_ID 12:00 18:00

Pass `-o ./bundles` when you want the bundle to live with the project instead.
"""

from __future__ import annotations

import argparse
import base64
import bisect
import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

# --------------------------------------------------------------------------
# Config defaults.
#
# FRAME_WIDTH is not a taste call. Claude downscales anything over ~1.15
# megapixels, so 1408x792 (1.12 MP, ~1487 tokens) is the last width whose
# pixels survive the trip. 1568 and 1920 cost more bytes and arrive identical.
#
# FPS 1.0 matches the granularity transcripts are already cut at, and is dense
# enough to catch a command between the moment it is typed and the moment it
# scrolls away.
# --------------------------------------------------------------------------
FPS = 1.0
FRAME_WIDTH = 1408
TOKENS_PER_FRAME = 1487  # 1408*792/750, for the window budget estimate
WINDOW_TOKEN_CAP = 400_000   # above this `window` refuses without --force

# An artifact page embeds its frames as data: URIs — the artifact runtime serves
# no asset store — so the page budget is the constraint. 900px is ample for
# reading a terminal on screen, and DISPLAY_DISTANCE culls harder than the build
# pass: a moving webcam leaves a hundred near-identical frames that make the page
# heavy without making it clearer.
ARTIFACT_WIDTH = 900
ARTIFACT_QUALITY = 72
DISPLAY_DISTANCE = 40
ARTIFACT_SOFT_LIMIT = 12 * 1024 * 1024   # page cap is 16 MB; leave headroom

# phash at the library default (hash_size=8, a 32x32 grayscale DCT) cannot see
# screencast text at all. Measured on a 6-scene terminal recording, frames
# showing entirely different commands scored 0, 0, 4, 6, 14 apart — three of the
# five real transitions fell under the old default of 6, so half the video was
# discarded while the run reported success.
#
# hash_size=16 (256-bit) separates cleanly on the same input: 26 minimum between
# distinct scenes, 0 between identical ones. 10 sits well inside that gap.
PHASH_SIZE = 16
PHASH_DISTANCE = 10      # hamming distance below which two frames are "the same"

# Hash a centre box, not the whole frame. A screen-share layout parks webcams in
# the corners, and a face moves every single frame, so whole-frame phash reports
# "new screen" forever and dedupe silently no-ops. Measured on a 58-minute
# podcast: whole-frame hashing kept 99.8% of the screen-share frames; hashing
# this box kept 55%. The full frame is still what gets saved and read — only the
# similarity decision ignores the corners.
HASH_BOX = (0.14, 0.0, 0.86, 0.66)   # l, t, r, b as fractions of the frame

# Camera footage and screen content separate on flatness: UI is flat white or
# flat dark with sharp text, a face is continuous midtone. Flatness is the
# fraction of near-white/near-black pixels in HASH_BOX.
#
# Measured over 3165 frames of that podcast the distribution is bimodal with an
# empty valley — 1991 frames below 0.05, 10 frames in 0.10-0.25, 940 above — so
# any threshold in the valley gives the same answer within 6 frames. Labelled
# spot-checks: every real screen scored >= 0.256, every face <= 0.126.
#
# Edge density and colour saturation were both measured and both rejected: the
# corner webcams contaminate every whole-frame metric, and saturation false-
# positived on faces against pale walls.
CONTENT_FLATNESS = 0.19
FLAT_HI, FLAT_LO = 225, 30       # luminance bands counted as "flat"

# The threshold is only meaningful when this video's frames actually fall into
# two groups. They do not always: a tutorial that draws diagrams over blurred
# b-roll produces one continuous spread, and cutting it anywhere hides real
# content — a git branch diagram over a photo scored 0.14 and would have been
# filed as camera footage. So measure the valley before trusting the cut, and
# when it is not there, classify nothing and show every frame.
#
# Measured within +/-0.05 of the threshold: 0.19% of the podcast's frames, 6.89%
# of the overlay screencast's — a 36x gap, with 2% sitting an order of magnitude
# clear of both. Otsu's method was measured and rejected for the cut itself: it
# picks 0.41 on the podcast, which files a hand-verified screen at 0.243 as
# camera footage.
VALLEY_HALF_WIDTH = 0.05
VALLEY_MAX_OCCUPANCY = 0.02
SEGMENT_GAP = 15                 # merge content runs separated by <= this many s
SEGMENT_MIN = 20                 # drop runs shorter than this

VIDEO_EXTS = (".mp4", ".mkv", ".webm", ".mov", ".m4v", ".flv", ".avi")
URL_RE = re.compile(r"https?://[^\s<>\")\]]+")

# Affiliate, social and channel-promo links crowd out the technical ones. Note
# what is NOT here: youtube.com/watch and youtu.be stay, because a description
# linking a prerequisite video is exactly the context worth keeping — only the
# subscribe call-to-action is filtered.
# Matched against the parsed hostname — exactly, or as a subdomain of it.
#
# NOT as a substring of the URL, which is what this used to do and which ate the
# technical links the list exists to protect: "amazon." dropped
# `docs.aws.amazon.com/lambda/...`, and "x.com/" dropped
# `phoenix.com/engineering/blog`.
NOISE_HOSTS = (
    # affiliate / storefront
    "amzn.to", "bit.ly", "linktr.ee", "epidemicsound.com", "skl.sh",
    "brilliant.org", "squarespace.com", "nordvpn.com", "joinhoney.com",
    "impact.com",
    # tip jars
    "patreon.com", "buymeacoffee.com", "ko-fi.com", "paypal.com",
    # social and chat
    "twitter.com", "x.com", "instagram.com", "tiktok.com", "facebook.com",
    "discord.gg", "t.me", "threads.net", "bsky.app", "mastodon.social",
    # channel promo
    "buzzsprout.com", "anchor.fm", "podcasts.apple.com",
)

# Promotional paths on hosts that also serve real content. amazon.com is here
# rather than in NOISE_HOSTS precisely so `docs.aws.amazon.com` survives.
NOISE_HOST_PATHS = (
    ("amazon.com", "/dp/"), ("amazon.com", "/gp/"),
    ("spotify.com", "/show"),
)

# Substrings anywhere in the URL. Only for markers that are unambiguous.
NOISE_MARKERS = ("sub_confirmation",)

# Where bundles live: --out, then $WATCHWITH_BUNDLES, then ~/.watchwith/bundles.
#
# The default is under $HOME, not ./bundles, for two reasons. A bundle runs
# 100-240 MB, so a cwd-relative default drops that into whatever repo you happen
# to be standing in and obliges every one of them to carry its own gitignore
# entry. And one video often informs several projects, so a single library means
# one download instead of one per checkout. Pass `-o ./bundles` when you do want
# the bundle to live with the work.
BUNDLES_ENV = "WATCHWITH_BUNDLES"
DEFAULT_BUNDLES = Path("~/.watchwith/bundles")

# The runtime venv, and the packages that go in it. Never inside
# ~/.claude/plugins/cache/ — that directory is replaced on every plugin update.
#
# Import name -> pip name, because three of the four differ. REQUIRED is what
# the script imports; OPTIONAL is what yt-dlp picks up when it is there:
# curl_cffi supplies the impersonation target whose absence draws rate limits
# sooner. `deno` is the other optional piece and cannot be pip-installed.
DEFAULT_VENV = Path("~/.watchwith/venv")
REQUIRED_DEPS = {"yt_dlp": "yt-dlp", "imagehash": "imagehash", "PIL": "pillow"}
OPTIONAL_DEPS = {"curl_cffi": "curl_cffi"}

# yt-dlp's id is network-derived, not a constrained token. For a URL that falls
# through to the generic extractor it is `unquote(last path segment)`, so
# `https://host/..%2f..%2fwork.mp4` yields the id `../../work` — real separators.
# Unsanitized that reaches `out / id`, and every write below it escapes: frames
# and meta.json land outside --out, an existing BUNDLE.md there is overwritten,
# and a directory named `frames` there is deleted. YouTube ids are
# [A-Za-z0-9_-]{11} and pass through this untouched.
ID_SAFE = re.compile(r"[^A-Za-z0-9_-]")

# Auto-captions are the common case — most videos have no author-uploaded track.
# The overlap merge below is only correct for the rolling form, and `find_vtt`
# prefers the manual track, so running it unconditionally deletes legitimately
# repeated speech ("run the test" / "run the test again" -> "run the test",
# "again").
#
# Detected on content, not markup. Inline <00:00:01.500> cue timestamps look like
# a rolling marker but are legal karaoke markup in hand-authored tracks too, so a
# manual track carrying them tripped the merge and swallowed real repeats. What
# actually distinguishes a rolling track is behaviour: it repeats the previous
# cue's tail at most boundaries, and nothing else does.
ROLLING_THRESHOLD = 0.5
ROLLING_MIN_CUES = 8   # below this there is not enough signal; assume not rolling
MIN_OVERLAP = 3        # a 1-2 word coincidence is speech, not a rolling repeat


@dataclass
class Cue:
    """One transcript cue: when it was said, and what was said."""
    start: float
    text: str


@dataclass
class Frame:
    """One sampled frame and the timestamp it was pulled from."""
    ts: float
    path: Path


def bundles_root() -> Path:
    """Default bundle root. `--out` overrides this; it does not consult it."""
    env = os.environ.get(BUNDLES_ENV, "").strip()
    if env:
        return Path(env).expanduser()
    try:
        return DEFAULT_BUNDLES.expanduser()
    except RuntimeError:
        sys.exit(f"cannot resolve {DEFAULT_BUNDLES} — "
                 f"set ${BUNDLES_ENV} or pass --out")


def safe_dest(root: Path, video_id: str) -> Path:
    """One directory under `root`, named after the video. Never outside it."""
    # No .strip("_") — underscore is a legal YouTube id character, and stripping
    # it renames the bundle away from the id the spec's Watch: line cites.
    # A pathological id like ".." sanitizes to the literal dirname "__", which is
    # contained and harmless.
    name = ID_SAFE.sub("_", video_id)[:64]
    if not name:
        sys.exit(f"unusable video id {video_id!r} — cannot name a bundle directory")
    dest = (root / name).resolve()
    if dest != root.resolve() and root.resolve() not in dest.parents:
        sys.exit(f"refusing to write outside {root}: {dest}")
    return dest


def matches(entry: Entry, needle: str) -> bool:
    """Whether `needle` plausibly names this bundle.

    Nobody remembers `xgkjtF89-44`. They remember "the NASA one", the channel,
    or they still have the URL on the clipboard — so id, title, channel and URL
    all match, case-insensitively, as substrings.

    The URL case runs the other way round: `youtu.be/xgkjtF89-44` contains the
    id rather than being contained by any field, so a long enough id is looked
    for inside the needle too.
    """
    want = needle.strip().casefold()
    if not want:
        return False
    fields = [str(entry.meta.get(k) or "")
              for k in ("id", "title", "channel", "url")]
    fields.append(entry.path.name)
    return (any(want in f.casefold() for f in fields)
            or (len(entry.id) >= 6 and entry.id.casefold() in want))


def pick_one(needle: str, entries: list[Entry]) -> Entry:
    """Exactly one bundle, or a refusal that names the candidates.

    Ambiguity is never settled by taking the first hit. `prune` deletes, and a
    guess there deletes the wrong video.
    """
    hits = [e for e in entries if matches(e, needle)]
    # An exact id beats a title that happens to contain it, so a real id never
    # turns ambiguous just because another video mentions it.
    exact = [e for e in hits if e.id.casefold() == needle.strip().casefold()]
    for shortlist in (exact, hits):
        if len(shortlist) == 1:
            return shortlist[0]
    if len(hits) > 1:
        sys.exit(f"{needle!r} matches {len(hits)} videos — name one:\n" +
                 "\n".join(f"  {e.id}  {clip(e.meta.get('title') or '', 60)}"
                            for e in hits))
    sys.exit(f"no video matching {needle!r} — run `index` to see the library")


def resolve_bundle(arg: Path) -> Path:
    """A bundle directory, a bare video id, a URL, or words from the title.

    `window <id>` is the common case once a central library exists — the user
    knows the video, not where the library happens to be mounted. And usually
    not the id either, hence the fuzzy tail.
    """
    if (arg / "meta.json").is_file():
        return arg
    root = bundles_root()
    candidate = root / arg
    if (candidate / "meta.json").is_file():
        return candidate

    entries = library(root)
    if not entries:
        sys.exit(f"not a bundle: no meta.json at {arg} or {candidate}\n"
                 f"set ${BUNDLES_ENV} or pass the bundle directory directly")
    return pick_one(str(arg), entries).path


# --------------------------------------------------------------------------
# Time helpers
# --------------------------------------------------------------------------
def hhmmss(seconds: float, sep: str = ":") -> str:
    s = int(seconds)
    return f"{s // 3600:02d}{sep}{(s % 3600) // 60:02d}{sep}{s % 60:02d}"


def parse_span(text: str) -> float:
    """Accept SS, MM:SS, or HH:MM:SS. Rejects anything else loudly."""
    parts = text.strip().split(":")
    if not 1 <= len(parts) <= 3 or not all(p.isascii() and p.isdigit() for p in parts):
        sys.exit(f"bad timestamp {text!r} — expected SS, MM:SS, or HH:MM:SS")
    total = 0.0
    for p in parts:
        total = total * 60 + int(p)
    return total


def frame_stamp(path: Path) -> float | None:
    """Seconds from a frame filename, or None when it is not one.

    Frames are named HH-MM-SS.jpg, with a `_N` suffix where one second yielded
    more than one keeper. The name IS the index — there is no sidecar that can
    fall out of sync with the directory.
    """
    parts = path.stem.split("_")[0].split("-")
    if len(parts) != 3 or not all(p.isascii() and p.isdigit() for p in parts):
        return None
    return float(int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2]))


def bundle_frames(bundle: Path) -> list[Frame]:
    """Every frame on disk, in timestamp order.

    One reader for the frames directory. `window`, `artifact` and `search` all
    resolve timestamps through this: three separate copies of the same parse is
    how the artifact filter drifted from the window filter in the first place.
    """
    found = []
    for p in sorted((bundle / "frames").glob("*.jpg")):
        ts = frame_stamp(p)
        if ts is not None:
            found.append(Frame(ts, p.resolve()))
    found.sort(key=lambda f: f.ts)
    return found


def frame_for(stamps: list[Frame], keys: list[float],
              ts: float) -> Frame | None:
    """The frame that was on screen when `ts` was spoken.

    The last frame sampled at or before it: frames are deduped, so a cue rarely
    lands on one exactly, and the nearest earlier frame is the screen that was
    still up. `keys` is `[f.ts for f in stamps]`, built once per bundle instead
    of once per hit.
    """
    i = bisect.bisect_right(keys, ts)
    return stamps[i - 1] if i else None


def require_frames(bundle: Path) -> None:
    """Stop before reporting an empty span as a fact about the video.

    A bundle without frames is a failed or interrupted build, not a video with
    nothing on screen, and the two read identically once the span comes back
    empty.
    """
    if not (bundle / "frames").is_dir():
        sys.exit(f"not a bundle: {bundle / 'frames'} missing\n"
                 f"  rebuild it:  build {bundle.name}")


# --------------------------------------------------------------------------
# 1. Acquisition
# --------------------------------------------------------------------------
def fetch_subtitles(url: str, workdir: Path, attempts: int = 3) -> bool:
    """Fetch the subtitle track in its own pass. Never fatal.

    Subtitles are downloaded separately from the video, and a failure here is
    warned about rather than raised, because YouTube rate-limits the caption
    endpoint far harder than the media one: two consecutive 58-minute builds
    died on `HTTP 429` at `_write_subtitles` — which yt-dlp runs *before* the
    media download — and took the whole run with them. A transcript is worth
    much less than the video it annotates, and the pipeline already handles a
    bundle that has no cues.

    Requesting three language variants of both the manual and automatic track
    is up to six hits on that endpoint per build, so the langs are tried in
    priority order and the first that lands wins.
    """
    import yt_dlp

    # `en-orig` FIRST, and this order is load-bearing. YouTube publishes two
    # English tracks on a video whose audio it auto-captions: `en-orig`
    # ("English (Original)") is the ASR of what was actually said, and `en` is a
    # processed/translated rendering of it. Requesting `en` first returned a
    # paraphrase — disfluencies and `>>` speaker markers stripped, words the
    # speaker never said inserted ("Of course"), acronyms expanded to
    # "reinforcement learning (RL)" — 3333 cues against the original's 1980, and
    # 10k fewer characters. A transcript that rewrites the speaker is derived
    # evidence, which is the whole thing this tool refuses to cite.
    # A video with author-uploaded subtitles has no `en-orig` and falls through.
    for lang in ("en-orig", "en", "en-US"):
        for attempt in range(attempts):
            opts = {
                "skip_download": True,
                "writesubtitles": True,
                "writeautomaticsub": True,   # fallback when no manual track exists
                "subtitleslangs": [lang],
                # json3 is YouTube's own format and arrives already de-duplicated.
                # The rolling repetition is an artefact of VTT, which is built for
                # on-screen display where lines scroll. Measured across five
                # videos: json3 matches the VTT-plus-merge output 97.9-100%, and
                # every difference is a residual duplicate the merge left behind.
                "subtitlesformat": "json3/vtt",
                "outtmpl": str(workdir / "video.%(ext)s"),
                "quiet": True,
                "no_warnings": True,
                "noprogress": True,
                "noplaylist": True,
            }
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    ydl.extract_info(url, download=True)
            except Exception as e:                      # noqa: BLE001
                last = str(e).strip().splitlines()[-1] if str(e) else type(e).__name__
                if attempt + 1 < attempts:
                    time.sleep(2 ** attempt * 5)        # 5s, 10s
                    continue
                print(f"   ! subtitles ({lang}): {last}")
                break
            if find_subs(workdir):
                return True
            break

    print("   ! no subtitle track downloaded — continuing without narration")
    return False


def fetch(url: str, workdir: Path) -> dict:
    """Pull the video via yt-dlp, then the subtitles in a separate pass.

    Caps at 1080p — below that, small terminal text turns to mush and the frames
    become useless.
    """
    import yt_dlp

    opts = {
        # Video only. Nothing here decodes audio — sample_frames runs -vf and
        # the narration comes from the subtitle track — so pulling +bestaudio
        # downloaded roughly a quarter of the bytes to throw them away.
        "format": "bestvideo[height<=1080]/best[height<=1080]",
        # Resolution is load-bearing; bitrate is not. Frames are scaled to
        # FRAME_WIDTH, so a 1920-wide source is downscaled — a low-pass filter
        # that discards exactly the detail a high bitrate buys — while a
        # 1280-wide source is UPSCALED and small text turns to mush. Measured on
        # a 1080p screen-share: av01 at 587 MB and YouTube's premium vp9 at over
        # 1 GB are character-for-character identical after the pipeline, and
        # 720p loses the filename and the test output entirely.
        #
        # So: prefer the resolution, then the smallest encode of it. `bestvideo`
        # alone picked the premium stream and paid ~40% more for nothing.
        "format_sort": ["res:1080", "+size", "+br"],
        "merge_output_format": "mp4",
        "outtmpl": str(workdir / "video.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        # `quiet` alone does not suppress the progress bar; it writes straight
        # to stdout and garbles this script's own output.
        "noprogress": True,
        # A URL copied from the address bar while a video plays inside a playlist
        # carries &list=. Without this yt-dlp downloads every entry, and every
        # entry renders to the same outtmpl path — N videos overwrite one file,
        # and meta["id"] becomes the playlist id.
        "noplaylist": True,
    }

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)

    fetch_subtitles(url, workdir)

    if info.get("_type") == "playlist":
        sys.exit("that URL is a playlist — pass a single video URL")

    if not info.get("id"):
        sys.exit("yt-dlp returned no video id — cannot name the bundle")

    return {
        "id": info["id"],
        "title": info.get("title") or info["id"],
        "channel": info.get("uploader") or "unknown",
        "duration": info.get("duration") or 0,
        "url": info.get("webpage_url") or url,
        # Verbatim, uncut. The description routinely carries what neither the
        # frames nor the narration do — repo URLs, tool versions, prerequisites —
        # and truncating it is compression at the wrong layer: nothing in stage 1
        # summarizes. A 2000-char cap was severing real descriptions mid-link.
        "description": info.get("description") or "",
        "tags": (info.get("tags") or [])[:30],
        "upload_date": info.get("upload_date"),
        # Chapters are the author's own outline — useful scaffolding for a spec.
        "chapters": [
            {"title": c.get("title"), "start": c.get("start_time") or 0}
            for c in (info.get("chapters") or [])
        ],
    }


def find_video(staging: Path) -> Path:
    """Pick the downloaded video out of staging.

    Explicitly extension-matched. `glob("video.*")` also matches `video.en.vtt`,
    and on at least one filesystem scandir hands back the subtitle track first —
    which then goes to ffmpeg as if it were a video.
    """
    hits = sorted(p for p in staging.glob("video.*") if p.suffix.lower() in VIDEO_EXTS)
    if not hits:
        sys.exit(f"no video file in {staging} (looked for {', '.join(VIDEO_EXTS)})")
    return hits[0]


# --------------------------------------------------------------------------
# 2. Transcript
# --------------------------------------------------------------------------
def _is_rolling(texts: list[str], thresh: float = ROLLING_THRESHOLD) -> bool:
    """Do most cue boundaries repeat a substantial tail of the previous cue?

    Only overlaps of MIN_OVERLAP words or more count: a one-word match at a
    boundary ("...now" / "now...") is ordinary speech, and on a short track a
    couple of those are enough to fake a rolling signature. Tracks with too few
    cues to judge are reported not-rolling, which is the safe answer — the merge
    stays off and no speech can be deleted.
    """
    if len(texts) < ROLLING_MIN_CUES:
        return False
    words = [t.split() for t in texts]
    pairs = [(a, b) for a, b in zip(words, words[1:]) if a and b]
    if not pairs:
        return False
    hits = sum(
        any(a[-n:] == b[:n]
            for n in range(min(len(a), len(b)), MIN_OVERLAP - 1, -1))
        for a, b in pairs
    )
    return hits / len(pairs) >= thresh


def parse_vtt(path: Path) -> list[Cue]:
    """Minimal WebVTT parser, tolerant of YouTube's rolling auto-captions.

    Auto-generated VTT carries inline <00:00:04.719><c> word timings and a
    rolling window: each cue repeats the tail of the previous one and appends a
    few new words. Comparing whole cues catches only the exact repeats, so the
    transcript still comes out ~3x duplicated — measured across four real
    auto-captioned videos, which removed 65-67% of words each.

    Instead each cue is merged against the running tail on a word basis, and only
    the words not already emitted are kept. Word-based rather than character-
    based so a tail ending in "back" does not eat the "back" of "backend".

    Applied only when `_is_rolling` says the track actually rolls. Manual tracks
    pass through unmerged: their cues do not overlap, so any match there is real
    repeated speech.
    """
    time_re = re.compile(r"(\d{2}):(\d{2}):(\d{2})\.(\d{3})\s*-->")
    tag_re = re.compile(r"<[^>]+>")

    raw = path.read_text(encoding="utf-8", errors="ignore")

    # Pre-pass: read the cue texts plainly so `rolling` is decided from what the
    # track does, before any merging changes it.
    plain: list[str] = []
    _start: float | None = None
    _buf: list[str] = []
    for line in raw.splitlines():
        if time_re.match(line.strip()):
            if _start is not None:
                s = re.sub(r"\s+", " ", tag_re.sub("", " ".join(_buf))).strip()
                if s:
                    plain.append(s)
            _start, _buf = 0.0, []
        elif line.strip() and not line.startswith(("WEBVTT", "Kind:", "Language:", "NOTE")):
            _buf.append(line.strip())
    if _start is not None:
        s = re.sub(r"\s+", " ", tag_re.sub("", " ".join(_buf))).strip()
        if s:
            plain.append(s)
    rolling = _is_rolling(plain)

    cues: list[Cue] = []
    tail: list[str] = []
    start: float | None = None
    buf: list[str] = []

    def flush() -> None:
        nonlocal tail
        if start is None:
            return
        # Collapse whitespace *after* tag removal — stripping <c> tags leaves
        # double spaces, which would split one word into two empty-separated ones.
        text = re.sub(r"\s+", " ", tag_re.sub("", " ".join(buf))).strip()
        if not text:
            return
        words = text.split()
        if rolling and cues and cues[-1].text == text:
            return                      # a rolling track's exact restatement
        new = words
        if rolling:
            for n in range(min(len(tail), len(words)), MIN_OVERLAP - 1, -1):
                if tail[-n:] == words[:n]:
                    new = words[n:]
                    break
        if new:
            cues.append(Cue(start, " ".join(new)))
            # Bounded tail: overlap never spans more than a cue or two.
            tail = (tail + new)[-60:]

    for line in raw.splitlines():
        m = time_re.match(line.strip())
        if m:
            flush()
            h, mnt, s, ms = map(int, m.groups())
            start, buf = h * 3600 + mnt * 60 + s + ms / 1000, []
        elif line.strip() and not line.startswith(("WEBVTT", "Kind:", "Language:", "NOTE")):
            buf.append(line.strip())

    flush()
    return cues


def parse_json3(path: Path) -> list[Cue]:
    """Parse YouTube's json3 captions. No de-duplication needed or performed.

    Events alternate between real text and empty spacers; the empties are the
    only thing to drop.
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except json.JSONDecodeError as e:
        sys.exit(f"malformed caption file {path}: {e}")

    cues: list[Cue] = []
    for event in data.get("events") or []:
        text = "".join(
            seg.get("utf8", "") for seg in (event.get("segs") or [])
        ).replace("\n", " ").strip()
        if text:
            cues.append(Cue((event.get("tStartMs") or 0) / 1000, text))
    return cues


def find_subs(staging: Path) -> tuple[Path, str] | None:
    """Locate the caption file, preferring json3 over vtt.

    Returns the path and which parser to use. vtt remains the fallback for a
    source that does not serve json3.
    """
    for suffix, kind in ((".json3", "json3"), (".vtt", "vtt")):
        hits = sorted(staging.glob(f"video*{suffix}"))
        if not hits:
            continue
        for preferred in (f"video.en{suffix}", f"video.en-US{suffix}",
                          f"video.en-orig{suffix}"):
            for h in hits:
                if h.name == preferred:
                    return h, kind
        return hits[0], kind
    return None


def find_vtt(staging: Path) -> Path | None:
    """Prefer a manual track over an auto-generated one.

    yt-dlp names manual subs `video.en.vtt` and auto-generated ones with the
    same shape, so there is no reliable filename signal. Plain `en` is the most
    likely manual track; fall back to whatever exists.
    """
    hits = sorted(staging.glob("video*.vtt"))
    if not hits:
        return None
    for preferred in ("video.en.vtt", "video.en-US.vtt", "video.en-orig.vtt"):
        for h in hits:
            if h.name == preferred:
                return h
    return hits[0]


# --------------------------------------------------------------------------
# 3. Frame sampling — the part that actually matters
# --------------------------------------------------------------------------
def sample_frames(video: Path, outdir: Path, fps: float,
                  crop: str | None = None) -> list[Frame]:
    """Sample at a fixed rate. Frame N lands at (N-1)/fps, exactly.

    The previous implementation used `select='gt(scene,N)'` and recovered each
    timestamp by parsing pts_time out of ffmpeg's stderr, then zipping that list
    against the written files. That pairing was the load-bearing assumption of
    the whole script and had three problems: an ffmpeg version difference or a
    stray warning line silently shifted every timestamp, scene detection never
    fires on frame 0 so the opening screen was always missing, and the selection
    was content-blind — it could not tell a new terminal command from a scroll.

    Fixed-rate sampling makes the timestamp arithmetic instead of parsed. There
    is nothing left to misalign.
    """
    if outdir.exists():
        # A stale frame from a prior run is a wrong frame, so this directory gets
        # cleared — which makes it worth proving it is ours before deleting it.
        strays = [p.name for p in outdir.iterdir() if p.suffix.lower() != ".jpg"]
        if not outdir.is_dir() or strays:
            sys.exit(
                f"refusing to clear {outdir}: not a frames directory "
                f"(contains {', '.join(sorted(strays)[:5])})"
            )
        shutil.rmtree(outdir)
    outdir.mkdir(parents=True)

    cmd = [
        "ffmpeg", "-nostdin", "-i", str(video),
        "-vf", (f"fps={fps}" + (f",crop={crop}" if crop else "")
                + f",scale={FRAME_WIDTH}:-2:flags=lanczos"),
        "-q:v", "3",
        str(outdir / "s_%06d.jpg"),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        sys.exit(f"ffmpeg failed:\n{proc.stderr[-2000:]}")

    files = sorted(outdir.glob("s_*.jpg"))
    if not files:
        sys.exit("ffmpeg wrote no frames — is the input actually a video?")

    return [Frame((i) / fps, f) for i, f in enumerate(files)]


def hash_box(img):
    """Crop to HASH_BOX — the region a similarity decision should look at."""
    w, h = img.size
    l, t, r, b = HASH_BOX
    return img.crop((int(w * l), int(h * t), int(w * r), int(h * b)))


def flatness(img) -> float:
    """Fraction of near-white/near-black pixels in HASH_BOX.

    High on a document, terminal or slide; low on camera footage, whose skin and
    background tones sit in the midrange. Computed on a 320x180 downscale — the
    ratio is a population statistic, so full resolution buys nothing and costs 10x.
    """
    from PIL import Image

    box = hash_box(img.convert("L").resize((320, 180), Image.BILINEAR))
    hist = box.histogram()
    total = sum(hist)
    if not total:
        return 0.0
    return (sum(hist[FLAT_HI + 1:]) + sum(hist[:FLAT_LO])) / total


def dedupe(frames: list[Frame], distance: int, whole: bool = False) -> list[Frame]:
    """Drop frames visually identical to the last one kept.

    Compared against the last *kept* frame so a gradual change accumulates
    against a fixed reference and registers once it crosses the threshold.
    Comparing against the immediate predecessor would let the reference drift
    alongside the change and drop the transition entirely.

    The hash covers HASH_BOX, not the whole frame, so corner webcams cannot hold
    every frame alive. `whole=True` restores whole-frame hashing for footage
    where the edges are the content.
    """
    import imagehash
    from PIL import Image

    kept: list[Frame] = []
    last_hash = None
    for f in frames:
        with Image.open(f.path) as img:
            h = imagehash.phash(img if whole else hash_box(img),
                                hash_size=PHASH_SIZE)
        if last_hash is None or (h - last_hash) > distance:
            kept.append(f)
            last_hash = h
    return kept


def score_frames(frames: list[Frame]) -> dict[str, float]:
    """Flatness per frame, keyed by filename. Recorded, never used to delete.

    Extraction cannot know what a later read will want, so a frame the classifier
    calls camera footage still lands on disk — `window` filters at read time and
    `--all` overrides it there.
    """
    from PIL import Image

    scores: dict[str, float] = {}
    for f in frames:
        with Image.open(f.path) as img:
            scores[f.path.name] = round(flatness(img), 4)
    return scores


def separates(scores: dict[str, float], threshold: float = CONTENT_FLATNESS,
              half_width: float = VALLEY_HALF_WIDTH,
              max_occupancy: float = VALLEY_MAX_OCCUPANCY) -> bool:
    """Is there a valley at the threshold, or is this one continuous spread?

    Guards against the classifier's real failure mode — content drawn over
    photographic backgrounds, which lands mid-scale and gets filed as camera
    footage. Hiding a frame that carries payload is the one error this tool
    cannot make, so an unclear distribution means classify nothing.
    """
    if not scores:
        return False
    near = sum(1 for v in scores.values() if abs(v - threshold) <= half_width)
    return near / len(scores) <= max_occupancy


def segments(frames: list[Frame], scores: dict[str, float],
             threshold: float = CONTENT_FLATNESS,
             gap: int = SEGMENT_GAP, minimum: int = SEGMENT_MIN
             ) -> list[tuple[int, int]]:
    """Contiguous spans where a screen was being shared.

    This is the map a reader needs on a long video: a 58-minute podcast carries
    22 minutes of screen across 17 spans, and naming them is the difference
    between reading the payload and reading an hour of faces.
    """
    hits = sorted(int(f.ts) for f in frames
                  if scores.get(f.path.name, 0.0) >= threshold)
    runs: list[list[int]] = []
    for t in hits:
        if runs and t - runs[-1][1] <= gap:
            runs[-1][1] = t
        else:
            runs.append([t, t])
    return [(a, b) for a, b in runs if b - a >= minimum]


def rename_by_timestamp(frames: list[Frame], outdir: Path) -> list[Frame]:
    """Rename survivors to their timestamp and delete the rejects.

    Names are the index: `window` finds a span by sorting these, with no
    manifest to fall out of sync with the directory.
    """
    renamed: list[Frame] = []
    seen: set[str] = set()

    for f in frames:
        stem = hhmmss(f.ts, sep="-")
        # Sub-second sampling can round two frames into the same second; a plain
        # rename would silently overwrite the first one.
        if stem in seen:
            n = 2
            while f"{stem}_{n:02d}" in seen:
                n += 1
            stem = f"{stem}_{n:02d}"
        seen.add(stem)
        dest = outdir / f"{stem}.jpg"
        f.path.rename(dest)
        renamed.append(Frame(f.ts, dest))

    for junk in outdir.glob("s_*.jpg"):
        junk.unlink()

    return renamed


# --------------------------------------------------------------------------
# 4. Bundle assembly
# --------------------------------------------------------------------------
def useful_links(description: str) -> list[str]:
    """URLs from the description, minus the affiliate and social boilerplate."""
    from urllib.parse import urlparse

    def noisy(url: str) -> bool:
        try:
            parsed = urlparse(url)
        except ValueError:
            return True                      # unparseable is not a useful link
        host = (parsed.hostname or "").lower()
        if host.startswith("www."):
            host = host[4:]
        path = (parsed.path or "").lower()
        matches = lambda h: host == h or host.endswith("." + h)   # noqa: E731
        return (any(matches(n) for n in NOISE_HOSTS)
                or any(matches(h) and path.startswith(p)
                       for h, p in NOISE_HOST_PATHS)
                or any(m in url.lower() for m in NOISE_MARKERS))

    seen: list[str] = []
    for url in URL_RE.findall(description or ""):
        url = url.rstrip(".,;:)")
        if url in seen or noisy(url):
            continue
        seen.append(url)
    return seen


def derive_sections(spans: list[tuple[int, int]], cues: list[Cue],
                    lead: int = 15, width: int = 70) -> list[dict]:
    """Navigation sections for a video whose author published no chapters.

    Boundaries are structural — where a screen came up — and labels are simply
    the first words spoken over each. That is a weaker thing than a chapter and
    is labelled as such in BUNDLE.md: it exists so a reader can find a span, not
    so it can be quoted as the author's own outline.
    """
    out: list[dict] = []
    for a, b in spans:
        head = " ".join(c.text for c in cues if a <= c.start < a + lead).strip()
        head = " ".join(head.split())
        if len(head) > width:
            head = head[:width].rsplit(" ", 1)[0] + "…"
        out.append({"start": a, "end": b, "title": head or "(silent)"})
    return out


def build_bundle(meta: dict, cues: list[Cue], frames: list[Frame], out: Path) -> Path:
    """Emit BUNDLE.md as a *navigation map*, not the payload.

    An earlier version inlined every frame as a markdown image. Two problems:
    at 1 fps that file is thousands of images long, and `![](frames/x.jpg)` in a
    file Claude reads is inert text — it renders nowhere and loads nothing. The
    bundle now carries meta, chapters, the full transcript, and an index of what
    frames exist; the frames themselves are read on demand via `window`.
    """
    est = len(frames) * TOKENS_PER_FRAME
    lines = [
        f"# {meta['title']}",
        "",
        f"**Channel:** {meta['channel']}  ",
        f"**Duration:** {hhmmss(meta['duration'])}  ",
        f"**Source:** {meta['url']}  ",
        f"**Frames:** {len(frames)} (~{est // 1000}k tokens if read whole)",
        "",
        "> Navigation map. The frames are the payload and are NOT inlined here —",
        "> reading this file alone is not watching the video.",
        ">",
        "> Read a span with the watchwith skill, which resolves the script:",
        f"> `window {meta['id']} <START> <END>`",
        "",
    ]

    links = useful_links(meta.get("description", ""))
    if links:
        lines += ["## Links from the description", ""]
        lines += [f"- {u}" for u in links[:25]]
        lines += [""]

    if meta.get("description", "").strip():
        lines += ["## Description", "",
                  "> Author-written. Often carries repo URLs, tool versions and",
                  "> prerequisites that appear nowhere on screen.", ""]
        lines += ["```", meta["description"].strip(), "```", ""]

    spans = [tuple(s) for s in meta.get("segments", [])]
    scores = meta.get("flatness", {})
    thr = meta.get("content_threshold", CONTENT_FLATNESS)
    n_content = sum(1 for v in scores.values() if v >= thr)

    if meta["chapters"]:
        lines += ["## Chapters", ""]
        lines += [
            f"- `{hhmmss(c['start'])}` {c['title']}" for c in meta["chapters"]
        ]
        lines += [""]
    elif spans:
        lines += [
            "## Derived sections",
            "",
            "> The author published no chapters. These boundaries are where a",
            "> screen came up; the labels are the first words spoken over each.",
            "> Navigation only — not the author's outline.",
            "",
        ]
        lines += [f"- `{hhmmss(s['start'])}`-`{hhmmss(s['end'])}` {s['title']}"
                  for s in derive_sections(spans, cues)]
        lines += [""]
    if spans:
        covered = sum(b - a for a, b in spans)
        lines += [
            "## Screen-share segments",
            "",
            f"{n_content} of {len(frames)} frames show a screen rather than a "
            f"camera — {covered // 60}m{covered % 60:02d}s across {len(spans)} "
            f"spans. `window` reads these by default; `--all` includes the rest.",
            "",
            "| span | length | ~tokens |",
            "| - | - | - |",
        ]
        for a, b in spans:
            n = sum(1 for f in frames
                    if a <= f.ts <= b and scores.get(f.path.name, 0.0) >= thr)
            lines += [f"| `{hhmmss(a)}`-`{hhmmss(b)}` | {b - a}s | "
                      f"{n * TOKENS_PER_FRAME // 1000}k |"]
        lines += [""]

    lines += [
        "## Frame index",
        "",
        f"`frames/` holds {len(frames)} frames named `HH-MM-SS.jpg`. Coverage:",
        "",
    ]
    # Per-minute density tells you where the video is busy without listing
    # thousands of filenames.
    buckets: dict[int, int] = {}
    for f in frames:
        buckets[int(f.ts // 60)] = buckets.get(int(f.ts // 60), 0) + 1
    if buckets:
        lines += ["| minute | frames |", "| - | - |"]
        lines += [f"| `{m:02d}:00` | {buckets[m]} |" for m in sorted(buckets)]
        lines += [""]

    lines += [
        "## Transcript",
        "",
        "> Interleaved with the frames that were on screen while each line was",
        "> spoken. `grep FRAME` lists every frame worth reading, and a FRAME",
        "> line's path is literal.",
        ">",
        "> Frames are named for the second they came from. Camera frames are on",
        "> disk under the same scheme with no FRAME line. Seconds whose screen",
        "> did not change have no file at all — a missing frame means the screen",
        "> was unchanged, NOT that nothing was on screen. Read the nearest",
        "> earlier frame.",
        "",
    ]
    # Said even when frames follow: "no narration at all" is a fact about the
    # video, and the frame list below is not evidence against it.
    if not cues:
        lines += ["_No subtitle track was available for this video._", ""]
    if cues or frames:
        # Frame before cue at the same second: the screen was up, then it was
        # talked over. A content frame with nothing said over it still gets a
        # line — a silent screen is exactly the payload a transcript omits.
        events: list[tuple[float, int, str]] = [
            (c.start, 1, c.text) for c in cues
        ]
        # Unclassified means every frame is a candidate. Emitting only classified
        # content here would leave a declined video with no frame pointers at
        # all — the scribe gutted for exactly the videos we chose not to judge.
        events += [
            (f.ts, 0, f"FRAME frames/{f.path.name}")
            for f in frames
            if not scores or scores.get(f.path.name, 0.0) >= thr
        ]
        events.sort(key=lambda e: (e[0], e[1]))
        lines += [f"`{hhmmss(ts)}` {payload}" for ts, _, payload in events]
    lines += [""]

    path = out / "BUNDLE.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


# --------------------------------------------------------------------------
# 5. Window — read a span back at a size that fits
# --------------------------------------------------------------------------
def emit_window(bundle: Path, start: float, end: float, force: bool = False,
                every: bool = False) -> None:
    """Print an interleaved slice: what was on screen and what was said.

    Frame paths are printed bare and absolute, one per line, precisely so they
    can be fed straight to Read. Markdown image syntax would look right and load
    nothing.
    """
    meta_path = bundle / "meta.json"
    if not meta_path.is_file():
        sys.exit(f"not a bundle: {meta_path} missing")
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        sys.exit(f"corrupt bundle: {meta_path} is not valid JSON ({e})")

    require_frames(bundle)
    touch_used(bundle)
    frames = frames_in_span(bundle, start, end)

    # Camera frames carry no payload and crowd out the ones that do. They stay on
    # disk — this is a read-time filter, and --all turns it off. A bundle built
    # before classification existed has no scores, and then every frame is shown.
    scores = meta.get("flatness") or {}
    thr = meta.get("content_threshold", CONTENT_FLATNESS)
    dropped = 0
    fellback = False
    if scores and not every:
        keep = [f for f in frames if scores.get(f.path.name, 0.0) >= thr]
        # Never hand back an empty span. A span of pure conversation has no
        # content frames at all, and silently showing nothing would read as "the
        # video has no footage here" rather than "no screen was shared here".
        if keep:
            dropped = len(frames) - len(keep)
            frames = keep
        elif frames:
            fellback = True

    cues = [
        Cue(c["start"], c["text"])
        for c in meta.get("transcript", [])
        if start <= c["start"] <= end
    ]

    # Count the text too. A heavily-deduped long video is few frames and a full
    # transcript, so a frames-only estimate let ~123k tokens of paths and cue
    # lines walk past a cap whose whole job is bounding context.
    frame_tokens = len(frames) * TOKENS_PER_FRAME
    text_chars = (sum(len(str(f.path)) + 20 for f in frames)
                  + sum(len(c.text) + 20 for c in cues))
    text_tokens = text_chars // 4
    est = frame_tokens + text_tokens

    # Refuse rather than warn. Printing the advice and then the payload delivers
    # it to a reader that has already paid for it.
    if est > WINDOW_TOKEN_CAP and not force:
        sys.exit(
            f"~{est // 1000}k tokens of frames for {hhmmss(start)}-{hhmmss(end)} "
            f"({len(frames)} frames). Narrow the span, or pass --force."
        )

    print(f"# {meta.get('title', bundle.name)} — {hhmmss(start)} to {hhmmss(end)}")
    print()
    print(f"{len(frames)} frames (~{frame_tokens // 1000}k tokens) + "
          f"{len(cues)} cues (~{text_tokens // 1000}k tokens)."
          + (f" {dropped} camera frames hidden; --all shows them."
             if dropped else "")
          + (" No screen was shared in this span — showing camera frames."
             if fellback else ""))
    print()
    print("Read every path under FRAME. The narration between them is what was")
    print("being said while that was on screen.")
    print()

    events = [(f.ts, 0, str(f.path)) for f in frames]
    events += [(c.start, 1, c.text) for c in cues]
    events.sort(key=lambda e: (e[0], e[1]))   # frame first: screen state, then talk

    for ts, kind, payload in events:
        if kind == 0:
            print(f"FRAME {hhmmss(ts)}  {payload}")
        else:
            print(f"      {hhmmss(ts)}  {payload}")


# --------------------------------------------------------------------------
# 6. Artifact — a shareable page of one span
# --------------------------------------------------------------------------
def frames_in_span(bundle: Path, start: float, end: float) -> list[Frame]:
    return [f for f in bundle_frames(bundle) if start <= f.ts <= end]


def pick_for_display(frames: list[Frame], distance: int,
                     whole: bool = False) -> list[Frame]:
    """Second, harsher dedupe pass, for the page rather than for reading.

    Hashes HASH_BOX for the same reason `dedupe` does: corner webcams move every
    frame and hold every one of them alive. Whole-frame hashing here kept 2072 of
    2771 frames on a 58-minute podcast and built a 94 MB page against a 16 MB cap.
    """
    import imagehash
    from PIL import Image

    kept: list[Frame] = []
    last = None
    for f in frames:
        with Image.open(f.path) as img:
            h = imagehash.phash(img if whole else hash_box(img),
                                hash_size=PHASH_SIZE)
        if last is None or (h - last) > distance:
            kept.append(f)
            last = h
    return kept


def encode_frame(path: Path, width: int, quality: int) -> str:
    """Re-encode one frame small enough to embed, as a data: URI."""
    import io

    from PIL import Image

    with Image.open(path) as img:
        img = img.convert("RGB")
        if img.width > width:
            h = round(img.height * width / img.width)
            img = img.resize((width, h), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=quality, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def build_artifact(bundle: Path, start: float, end: float, out: Path,
                   template: Path, distance: int) -> Path:
    if not template.is_file():
        sys.exit(f"artifact template not found: {template}")
    meta_path = bundle / "meta.json"
    if not meta_path.is_file():
        sys.exit(f"not a bundle: {meta_path} missing")
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        sys.exit(f"corrupt bundle: {meta_path} is not valid JSON ({e})")

    require_frames(bundle)
    touch_used(bundle)

    # Same read-time filter `window` applies: a page of webcam stills is bytes
    # spent telling the reader nothing. Falls back to every frame when the span
    # holds no screen, so a conversational stretch still renders.
    raw = frames_in_span(bundle, start, end)
    scores = meta.get("flatness") or {}
    if scores:
        thr = meta.get("content_threshold", CONTENT_FLATNESS)
        content = [f for f in raw if scores.get(f.path.name, 0.0) >= thr]
        if content:
            raw = content

    frames = pick_for_display(raw, distance)
    if not frames:
        sys.exit(f"no frames between {hhmmss(start)} and {hhmmss(end)}")

    cues = [c for c in meta.get("transcript", []) if start - 8 <= c["start"] <= end + 8]
    rows = []
    for i, f in enumerate(frames):
        # The first row reaches back to the start of the span, not to its own
        # timestamp. Anchoring it at f.ts dropped every cue spoken before the
        # first surviving frame — on a page whose whole purpose is pairing
        # narration with the screen it was spoken over, and silently.
        lo = start - 8 if i == 0 else f.ts
        nxt = frames[i + 1].ts if i + 1 < len(frames) else end + 8
        said = " ".join(c["text"] for c in cues if lo <= c["start"] < nxt).strip()
        rows.append({"t": f.ts, "label": hhmmss(f.ts),
                     "said": said,
                     "img": encode_frame(f.path, ARTIFACT_WIDTH, ARTIFACT_QUALITY)})

    payload = {
        "title": meta.get("title", bundle.name),
        "channel": meta.get("channel", ""),
        "url": meta.get("url", ""),
        "fps": meta.get("fps", FPS),
        "spanLabel": f"{hhmmss(start)}\u2013{hhmmss(end)}",
        "chapters": [{"t": c["start"], "label": hhmmss(c["start"]), "title": c["title"]}
                     for c in meta.get("chapters", [])
                     if start - 30 <= c["start"] <= end],
        "description": meta.get("description", ""),
        "links": useful_links(meta.get("description", ""))[:25],
        "totalFrames": meta.get("frame_count", len(frames)),
        "cueCount": len(meta.get("transcript", [])),
        "frames": rows,
    }

    # The title is network-derived third-party metadata and lands inside
    # <title> as raw markup. Unescaped, a title of
    # `</title><script>...</script>` breaks out and executes in a page this
    # tool then tells you to publish. Same untrusted source as the video id,
    # which already required safe_dest() for a real path traversal.
    #
    # The payload below needs no such escape: the template assigns every field
    # with textContent, and `</` is neutralized so the JSON cannot close the
    # script element early.
    import html as html_escape

    html = template.read_text(encoding="utf-8")
    html = html.replace("__TITLE__", html_escape.escape(payload["title"], quote=True))
    html = html.replace(
        "var D = window.__SCRIBE__;",
        "var D = " + json.dumps(payload).replace("</", "<\\/") + ";",
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")

    size = out.stat().st_size
    print(f"[done] {out}")
    print(f"       {len(frames)} screens, {size / 1048576:.2f} MB")
    if size > ARTIFACT_SOFT_LIMIT:
        print(f"       ! over {ARTIFACT_SOFT_LIMIT // 1048576} MB — narrow the span "
              f"or raise --display-distance before publishing")
    return out


def cmd_artifact(args: argparse.Namespace) -> None:
    start, end = parse_span(args.start), parse_span(args.end)
    if end <= start:
        sys.exit(f"end ({args.end}) must be after start ({args.start})")
    bundle = resolve_bundle(args.bundle)
    template = args.template or (Path(__file__).resolve().parent.parent
                                 / "assets" / "artifact-template.html")
    out = args.out or Path(f"{bundle.name}-{int(start)}-{int(end)}.html")
    build_artifact(bundle, start, end, out, template, args.display_distance)


# --------------------------------------------------------------------------
# 7. Library — index, search, prune
#
# `prune` removes bundles, and that is the whole of it. A pruned video is gone
# from the library: frames, scribe, meta, directory. It is re-scribed by
# building it again.
#
# There was a --frames-only mode that kept the scribe and evicted the frames,
# on the argument that the scribe is 0.05% of the bytes. It was removed: half a
# bundle on disk meant every consumer had to reason about a bundle whose scribe
# described frames that were not there, and it produced five review findings
# without ever being asked for.
# --------------------------------------------------------------------------
PRUNE_BUDGET = 2 * 1024 ** 3        # library-wide ceiling `prune` defaults to
# Control characters, minus the whitespace `str.split` already handles. \x1b
# falls inside \x0e-\x1f, which is the point: see `clip`.
CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")
SIZE_UNITS = {"": 1, "K": 1024, "M": 1024 ** 2, "G": 1024 ** 3, "T": 1024 ** 4}
USED_MARKER = ".last_used"


@dataclass
class Entry:
    """One bundle in the library, as the maintenance commands see it.

    The size is measured lazily. `index` and `prune` need it; `search` and the
    name resolver do not, and walking every frame of every video to answer
    "which video says oracle" is the slow path nobody asked for. Measuring on
    first access keeps that off the hot path without giving any caller an Entry
    whose byte count is quietly zero.
    """
    path: Path
    meta: dict
    used: float                          # epoch seconds, last read or last built
    _frames: int | None = None
    _bytes: int | None = None

    @property
    def id(self) -> str:
        return str(self.meta.get("id") or self.path.name)

    @property
    def cues(self) -> int:
        """Transcript lines. Zero is a real state, not a corrupt bundle.

        `fetch_subtitles` is deliberately non-fatal — YouTube rate-limits the
        caption endpoint far harder than the media one — so a build can finish
        with every frame and no narration. Nothing downstream said so, and a
        bundle whose whole premise is pairing the two is worth flagging before
        someone reads it and concludes the video was silent.
        """
        return len(self.meta.get("transcript") or [])

    @property
    def frames(self) -> int:
        """Frames currently on disk."""
        if self._frames is None:
            d = self.path / "frames"
            self._frames = sum(1 for _ in d.glob("*.jpg")) if d.is_dir() else 0
        return self._frames

    @property
    def bytes(self) -> int:
        """Everything under the bundle."""
        if self._bytes is None:
            self._bytes = dir_bytes(self.path)
        return self._bytes


def parse_size(text: str) -> int:
    """Accept 2G, 500M, 1.5G, or a plain byte count."""
    m = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*([KMGT]?)B?\s*", text, re.I)
    if not m:
        sys.exit(f"bad size {text!r} — expected 2G, 500M, or a byte count")
    return int(float(m.group(1)) * SIZE_UNITS[m.group(2).upper()])


def human(n: float) -> str:
    for unit in ("B", "K", "M", "G"):
        if n < 1024:
            return f"{n:.0f}{unit}" if unit == "B" else f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}T"


def touch_used(bundle: Path) -> None:
    """Record that this bundle was read. Never fatal — a library on read-only
    media still reads, and `prune` falls back to build time."""
    try:
        (bundle / USED_MARKER).touch()
    except OSError:
        pass


def last_used(bundle: Path) -> float:
    """When this bundle was last read, else when it was built.

    `prune` evicts least-recently-used first, so a bundle nobody has opened is
    judged on its build time rather than counting as fresh forever.
    """
    for candidate in (bundle / USED_MARKER, bundle / "meta.json", bundle):
        try:
            return candidate.stat().st_mtime
        except OSError:
            continue
    return 0.0


def dir_bytes(path: Path) -> int:
    """Bytes on disk under `path`.

    Symlinks are measured as links and never followed: a link pointing out of
    the library would otherwise inflate the number `prune --over` acts on, and
    a link loop would hang the walk.
    """
    total = 0
    for root, _dirs, files in os.walk(path, followlinks=False):
        for name in files:
            try:
                total += os.lstat(os.path.join(root, name)).st_size
            except OSError:
                continue
    return total


def read_meta(bundle: Path) -> dict | None:
    """This bundle's meta, or None when the directory is not one of ours.

    The signature is deliberately narrow, and `prune` is why. `meta.json` is one
    of the most common filenames on a developer's disk; accepting any directory
    that holds one turned `prune --yes` into `rm -rf` for anything a `--root`
    happened to point at — an npm package and a photo folder, both destroyed in
    review. A bundle must therefore also carry the BUNDLE.md that `build_bundle`
    writes on every build, and a meta that names the video.
    """
    try:
        meta = json.loads((bundle / "meta.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(meta, dict) or not meta.get("id"):
        return None
    if not (bundle / "BUNDLE.md").is_file():
        return None
    return meta


def library(root: Path) -> list[Entry]:
    """Every bundle under `root`, most recently read first.

    The root also collects `_staging` from an interrupted build and whatever the
    file manager drops in it — none of that is something to list, and
    emphatically not something to delete. `read_meta` is the gate.
    """
    entries: list[Entry] = []
    try:
        children = sorted(root.iterdir())
    except OSError:
        return []
    for d in children:
        if not d.is_dir():
            continue
        meta = read_meta(d)
        if meta is None:
            continue
        entries.append(Entry(path=d, meta=meta, used=last_used(d)))
    entries.sort(key=lambda e: e.used, reverse=True)
    return entries


def clip(text: str, width: int) -> str:
    """One bounded line, with control characters removed.

    A title is network-derived third-party metadata — the same source that
    required HTML-escaping before it reached the artifact page. Here the surface
    is the terminal, and `prune`'s dry-run plan is the text a person reads
    before authorising a delete: ANSI cursor and erase sequences in a title can
    rewrite rows in it. `str.split` drops \r, \n and \t; it leaves \x1b.
    """
    text = " ".join(CONTROL.sub("", str(text)).split())
    return text if len(text) <= width else text[:width - 1] + "…"


def cmd_index(args: argparse.Namespace) -> None:
    root = args.root if args.root is not None else bundles_root()
    entries = library(root)

    if args.json:
        print(json.dumps([{
            "id": e.id,
            "title": e.meta.get("title"),
            "channel": e.meta.get("channel"),
            "url": e.meta.get("url"),
            "duration": e.meta.get("duration") or 0,
            "frames": e.frames,
            "cues": e.cues,
            "bytes": e.bytes,
            "last_used": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(e.used)),
            "path": str(e.path),
        } for e in entries], indent=2))
        return

    if not entries:
        print(f"no bundles under {root}")
        return

    print(f"{'ID':<12} {'FRAMES':>7} {'CUES':>6} {'SIZE':>8} {'LENGTH':>8}  "
          f"{'LAST READ':<10}  TITLE")
    silent = 0
    for e in entries:
        cues = e.cues
        silent += not cues
        print(f"{clip(e.id, 12):<12} {e.frames:>7} "
              f"{cues if cues else 'none':>6} {human(e.bytes):>8} "
              f"{hhmmss(e.meta.get('duration') or 0):>8}  "
              f"{time.strftime('%Y-%m-%d', time.localtime(e.used)):<10}  "
              f"{clip(e.meta.get('title') or '', 44)}")

    total = sum(e.bytes for e in entries)
    print(f"\n{len(entries)} bundle{'s' if len(entries) != 1 else ''} · "
          f"{human(total)} on disk in {root}")
    if silent:
        print(f"{silent} with no narration — the caption fetch failed at build "
              f"time. Re-run build to get it.")


def cmd_search(args: argparse.Namespace) -> None:
    root = args.root if args.root is not None else bundles_root()
    entries = library(root)
    if not entries:
        sys.exit(f"no bundles under {root}")

    if args.id:
        wanted = {pick_one(needle, entries).id for needle in args.id}
        entries = [e for e in entries if e.id in wanted]

    flags = 0 if args.case else re.IGNORECASE
    source = args.term if args.regex else re.escape(args.term)
    try:
        pattern = re.compile(source, flags)
    except re.error as e:
        sys.exit(f"bad --regex pattern {args.term!r}: {e}")

    limit = args.limit if args.limit > 0 else None

    # Two phases, because counting is cheap and rendering is not. Matching runs
    # over the transcript already in memory; rendering walks the frames
    # directory. Counting everything first means `--limit` can stop the
    # rendering without making the "N more" figure a lie.
    matched = []
    hits = 0
    for e in entries:
        # Both keys, not just one: this loop reads `start` too, and guarding
        # half of what it touches turned a hand-edited meta into a KeyError
        # traceback rather than the "corrupt bundle" exit used everywhere else.
        cues = [c for c in (e.meta.get("transcript") or [])
                if isinstance(c, dict) and "text" in c and "start" in c]
        found = [i for i, c in enumerate(cues) if pattern.search(str(c["text"]))]
        title_hit = bool(pattern.search(str(e.meta.get("title") or "")))
        if found or title_hit:
            matched.append((e, cues, found, title_hit))
            hits += len(found)

    if not matched:
        print(f"no match for {args.term!r} in {len(entries)} "
              f"bundle{'s' if len(entries) != 1 else ''}")
        return

    shown = 0
    for e, cues, found, title_hit in matched:
        # Checked before the header, not inside the row loop: a header printed
        # over an empty body reads as "matched, nothing to show".
        if limit is not None and shown >= limit:
            break
        stamps = bundle_frames(e.path)
        keys = [f.ts for f in stamps]

        print(f"\n{e.id}  {clip(e.meta.get('title') or '', 66)}"
              f"{'  (title)' if title_hit and not found else ''}")
        print(f"  {e.path}")
        # Marked by membership, not by the loop index. Two hits closer together
        # than --context share a window, so the second one is printed as the
        # first one's context — and keying the marker on `j == i` left it
        # unmarked and indistinguishable from a line that never matched.
        marks = set(found)
        last = -1                       # highest cue already printed, so that
        for i in found:                 # adjacent hits do not repeat context
            if limit is not None and shown >= limit:
                break
            lo = max(0, i - args.context, last + 1)
            hi = min(len(cues), i + args.context + 1)
            for j in range(lo, hi):
                cue = cues[j]
                frame = frame_for(stamps, keys, float(cue["start"]))
                # `frames/NAME`, not the bare name: joined onto the bundle
                # path printed above it, that is a path Read can open.
                where = f"frames/{frame.path.name}" if frame else "-"
                mark = ">" if j in marks else " "
                print(f"  {mark} {hhmmss(float(cue['start']))}  {where:<24}  "
                      f"{clip(cue['text'], 96)}")
            last = max(last, hi - 1)
            shown += 1

    print(f"\n{hits} hit{'s' if hits != 1 else ''} in {len(matched)} of "
          f"{len(entries)} bundle{'s' if len(entries) != 1 else ''}")
    if limit is not None and hits > shown:
        print(f"stopped at --limit {limit}; {hits - shown} more "
              f"(--limit 0 for all)")
    print("read a span:  window <id> <start> <end>")


def prune_targets(entries: list[Entry], args: argparse.Namespace) -> list[Entry]:
    """Which bundles are pruned. The selectors do not combine.

    Precedence is fixed, highest first: --id, --older-than, --keep, --over. It
    is NOT argument order — `--keep 2 --id foo` and `--id foo --keep 2` both
    prune foo — so a command never means two things at once.
    """
    return _select(entries, args)


def _select(entries: list[Entry], args: argparse.Namespace) -> list[Entry]:
    if args.id:
        # Deduplicated by id: two needles that name the same video must not
        # produce two rows, nor double-count the bytes they free.
        picked: dict[str, Entry] = {}
        for needle in args.id:
            hit = pick_one(needle, entries)
            picked[hit.id] = hit
        return list(picked.values())

    if args.older_than is not None:
        cutoff = time.time() - args.older_than * 86400
        return [e for e in entries if e.used < cutoff]

    if args.keep is not None:
        return entries[args.keep:]              # entries are most-recent first

    budget = parse_size(args.over) if args.over else PRUNE_BUDGET
    total = sum(e.bytes for e in entries)
    doomed = []
    for e in reversed(entries):                 # least recently read first
        if total <= budget:
            break
        doomed.append(e)
        total -= e.bytes
    return doomed


def drop(entry: Entry, root: Path) -> bool:
    """Delete one bundle, having proved it is one.

    Everything here comes from `library`, which only yields real bundles. This
    is nonetheless the one command in the tool that removes data, so it
    re-derives containment instead of trusting its caller — and reports a
    refusal rather than exiting, so one odd entry cannot abandon a prune
    half-applied and unsummarised.
    """
    bundle = entry.path.resolve()
    if bundle.parent != root.resolve() or read_meta(bundle) is None:
        print(f"   ! skipped {bundle}: not a bundle directly under {root}")
        return False

    shutil.rmtree(bundle, ignore_errors=True)
    return True


def cmd_prune(args: argparse.Namespace) -> None:
    if args.keep is not None and args.keep < 0:
        sys.exit("--keep must be 0 or more")
    if args.older_than is not None and args.older_than <= 0:
        sys.exit("--older-than must be a positive number of days")

    root = args.root if args.root is not None else bundles_root()
    entries = library(root)
    if not entries:
        sys.exit(f"no bundles under {root}")

    targets = prune_targets(entries, args)
    if not targets:
        print(f"nothing to remove — {len(entries)} bundles, "
              f"{human(sum(e.bytes for e in entries))} on disk")
        return

    freed = sum(e.bytes for e in targets)
    for e in targets:
        print(f"remove {clip(e.id, 12):<12} {human(e.bytes):>8}  "
              f"last read {time.strftime('%Y-%m-%d', time.localtime(e.used))}  "
              f"{clip(e.meta.get('title') or '', 44)}")
    print(f"\n{len(targets)} bundle{'s' if len(targets) != 1 else ''}, "
          f"{human(freed)} — scribe, frames, directory")

    if not args.yes:
        print("dry run — nothing removed. Re-run with --yes to remove.")
        return

    done = [e for e in targets if drop(e, root)]
    print(f"removed {len(done)}, freed {human(sum(e.bytes for e in done))}")


# --------------------------------------------------------------------------
def venv_python(venv: Path) -> Path:
    """The interpreter inside a venv, on this platform."""
    if os.name == "nt":
        return venv / "Scripts" / "python.exe"
    return venv / "bin" / "python"


def missing_modules(py: Path, names) -> list[str]:
    """Which of `names` that interpreter cannot import.

    Asked of the venv's python, not this one — the whole point is that the
    caller is usually a bare system python3 that has none of them.
    """
    probe = ("import importlib.util, sys\n"
             "print(' '.join(m for m in sys.argv[1:]\n"
             "               if importlib.util.find_spec(m) is None))")
    try:
        out = subprocess.run([str(py), "-c", probe, *names],
                             capture_output=True, text=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return list(names)
    return out.stdout.split()


def cmd_bootstrap(args: argparse.Namespace) -> None:
    """Create the runtime venv and install what is missing. Idempotent.

    Prints the interpreter path on stdout and nothing else, so a caller can bind
    it directly:  PY=$(python3 watchwith.py bootstrap)

    Progress goes to stderr for that reason. Runs on a bare system python3 — it
    imports only the standard library, because on a fresh plugin install nothing
    else exists yet.
    """
    venv = Path(args.venv).expanduser() if args.venv else DEFAULT_VENV.expanduser()
    py = venv_python(venv)

    if not py.is_file():
        print(f"-> creating venv at {venv}", file=sys.stderr)
        import venv as venv_module
        try:
            venv_module.EnvBuilder(with_pip=True).create(venv)
        except Exception as e:                      # noqa: BLE001
            sys.exit(f"could not create venv at {venv}: {e}")
        if not py.is_file():
            sys.exit(f"venv created at {venv} but {py} is missing")

    wanted = {**REQUIRED_DEPS, **OPTIONAL_DEPS}
    missing = missing_modules(py, list(wanted))
    if missing:
        pkgs = sorted({wanted[m] for m in missing})
        print(f"-> installing {' '.join(pkgs)}", file=sys.stderr)
        # pip's stdout goes to stderr. stdout here carries exactly one thing —
        # the interpreter path the caller binds — and a pip upgrade notice
        # landing in it would silently corrupt that.
        r = subprocess.run([str(py), "-m", "pip", "install", "-q", *pkgs],
                           stdout=sys.stderr)
        if r.returncode != 0:
            sys.exit(f"pip install failed for {' '.join(pkgs)}")

    # Re-check only what the script actually imports. An optional package that
    # will not build on this machine must not fail the bootstrap.
    still = missing_modules(py, list(REQUIRED_DEPS))
    if still:
        sys.exit(f"still missing after install: {' '.join(sorted(still))}")

    absent = missing_modules(py, list(OPTIONAL_DEPS))
    for tool, why in (("ffmpeg", "required — sampling cannot run without it"),
                      ("deno", "optional — yt-dlp drops formats without a JS runtime")):
        if not shutil.which(tool):
            print(f"   ! {tool} not on PATH ({why})", file=sys.stderr)
    if absent:
        print(f"   ! optional, not installed: {' '.join(sorted(absent))}",
              file=sys.stderr)

    print(py)


def cmd_build(args: argparse.Namespace) -> None:
    # Arguments first: the checks are free, deterministic, and independent of the
    # environment, so a typo gets named as a typo rather than being masked by
    # whatever happens to be missing from the machine.
    if not 0 < args.fps < 1000:      # the range form also rejects nan and inf
        sys.exit("--fps must be between 0 and 1000")
    if args.crop and not re.fullmatch(r"\d+:\d+:\d+:\d+", args.crop):
        sys.exit(f"--crop must be W:H:X:Y in pixels, got {args.crop!r}")

    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg not found on PATH")
    # Fail before the download, not after it. yt_dlp imports in fetch() and
    # imagehash/PIL only in dedupe(), so a missing Pillow used to surface as an
    # unhandled ImportError after the full download and the whole sampling pass.
    try:
        import imagehash  # noqa: F401
        import PIL        # noqa: F401
        import yt_dlp     # noqa: F401
    except ImportError as e:
        sys.exit(
            f"missing dependency: {e.name}\n"
            f"  run:  python3 {Path(__file__).name} bootstrap\n"
            f"  then re-run this build with the interpreter it prints"
        )

    out = args.out if args.out is not None else bundles_root()

    # Cleared, not reused. A leftover video.mp4 from a prior --keep-video run
    # makes yt-dlp skip the download, and the bundle silently describes the
    # previous video.
    staging = out / "_staging"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)

    print("-> fetching video + subtitles")
    meta = fetch(args.url, staging)

    dest = safe_dest(out, meta["id"])
    dest.mkdir(parents=True, exist_ok=True)

    found = find_subs(staging)
    if found:
        subs, kind = found
        cues = parse_json3(subs) if kind == "json3" else parse_vtt(subs)
        print(f"   {len(cues)} transcript cues ({kind})")
    else:
        cues = []
        print("   ! no subtitles found")

    video = find_video(staging)

    print(f"-> sampling at {args.fps} fps")
    # Sample into a sibling and swap only on success. Clearing dest/frames up
    # front destroyed the previous bundle's frames whenever this run then failed,
    # leaving BUNDLE.md and meta.json describing frames that no longer existed.
    work = dest / "frames.new"
    try:
        raw = sample_frames(video, work, args.fps, args.crop)
        kept = dedupe(raw, args.phash_distance, whole=args.whole_frame_hash)
        frames = rename_by_timestamp(kept, work)
    except BaseException:
        shutil.rmtree(work, ignore_errors=True)   # no half-built dir survives a failure
        raise
    # Move the old directory aside rather than deleting it first, so there is
    # never an instant where the bundle has no frames directory.
    live, old = dest / "frames", dest / "frames.old"
    shutil.rmtree(old, ignore_errors=True)
    if live.exists():
        live.rename(old)
    work.rename(live)
    shutil.rmtree(old, ignore_errors=True)
    frames = [Frame(f.ts, dest / "frames" / f.path.name) for f in frames]
    print(f"   {len(raw)} sampled -> {len(frames)} kept after dedupe")

    # A run that still retains almost everything has had no dedupe at all —
    # an animated background, or footage whose motion fills HASH_BOX.
    ratio = len(frames) / max(len(raw), 1)
    if ratio > 0.85 and len(raw) > 60:
        print(f"   ! dedupe kept {ratio:.0%} — motion fills the hash region. "
              f"Try a lower --fps.")

    print("-> classifying frames")
    scores = score_frames(frames)
    spans: list[tuple[int, int]] = []
    if separates(scores, args.content_flatness):
        spans = segments(frames, scores, args.content_flatness)
        n_content = sum(1 for v in scores.values() if v >= args.content_flatness)
        print(f"   {n_content} content frames, {len(frames) - n_content} camera "
              f"({len(spans)} screen span{'s' if len(spans) != 1 else ''})")
    else:
        # Recorded but not acted on: the scores stay out of meta so `window`
        # takes its unclassified path and shows every frame.
        scores = {}
        print("   frames do not separate into screen and camera — "
              "keeping all of them")

    # Transcript rides in meta.json so `window` needs no second parse.
    # BUNDLE.md carries its own copy for reading; both come from `cues` in this
    # same run, so they cannot drift.
    meta["transcript"] = [{"start": c.start, "text": c.text} for c in cues]
    meta["fps"] = args.fps
    meta["frame_count"] = len(frames)
    meta["flatness"] = scores
    meta["content_threshold"] = args.content_flatness
    meta["segments"] = [[a, b] for a, b in spans]
    (dest / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    bundle = build_bundle(meta, cues, frames, dest)

    if not args.keep_video:
        shutil.rmtree(staging, ignore_errors=True)

    est = len(frames) * TOKENS_PER_FRAME
    print(f"\n[done] {bundle}")
    print(f"       {len(frames)} frames (~{est // 1000}k tokens whole) in {dest / 'frames'}")
    print(f"       watch a span: window {meta['id']} 00:00 05:00")


def cmd_window(args: argparse.Namespace) -> None:
    start, end = parse_span(args.start), parse_span(args.end)
    if end <= start:
        sys.exit(f"end ({args.end}) must be after start ({args.start})")
    emit_window(resolve_bundle(args.bundle), start, end, args.force, args.every)


def main() -> None:
    ap = argparse.ArgumentParser(description="tutorial video -> spec-ready bundle")
    sub = ap.add_subparsers(dest="cmd", required=True)

    bs = sub.add_parser("bootstrap",
                        help="create the runtime venv and install dependencies")
    bs.add_argument("--venv", default=None,
                    help=f"venv location (default {DEFAULT_VENV})")
    bs.set_defaults(func=cmd_bootstrap)

    b = sub.add_parser("build", help="download a video and build a bundle")
    b.add_argument("url")
    b.add_argument("-o", "--out", default=None, type=Path,
                   help=f"bundle root (default: ${BUNDLES_ENV}, else {DEFAULT_BUNDLES})")
    b.add_argument("--fps", type=float, default=FPS,
                   help=f"frames sampled per second (default {FPS})")
    b.add_argument("--phash-distance", type=int, default=PHASH_DISTANCE,
                   help=f"lower keeps more near-identical frames, 0-{PHASH_SIZE**2} "
                        f"(default {PHASH_DISTANCE})")
    b.add_argument("--crop", default=None,
                   help="ffmpeg crop W:H:X:Y applied before hashing, to exclude "
                        "a webcam overlay or animated background")
    b.add_argument("--keep-video", action="store_true")
    b.add_argument("--whole-frame-hash", action="store_true",
                   help="hash the whole frame instead of its centre — for "
                        "footage whose edges are the content")
    b.add_argument("--content-flatness", type=float, default=CONTENT_FLATNESS,
                   help=f"flatness at or above which a frame counts as a screen "
                        f"rather than camera footage (default {CONTENT_FLATNESS})")
    b.set_defaults(func=cmd_build)

    w = sub.add_parser("window", help="print a span of a bundle for reading")
    w.add_argument("bundle", type=Path,
                   help=f"video id, URL, or words from its title or channel — or a bundle directory")
    w.add_argument("start", help="SS, MM:SS, or HH:MM:SS")
    w.add_argument("end", help="SS, MM:SS, or HH:MM:SS")
    w.add_argument("--all", dest="every", action="store_true",
                   help="include camera frames, not just screen content")
    w.add_argument("--force", action="store_true",
                   help=f"emit even above ~{WINDOW_TOKEN_CAP // 1000}k tokens of frames")
    w.set_defaults(func=cmd_window)

    a = sub.add_parser("artifact", help="build a shareable HTML page for a span")
    a.add_argument("bundle", type=Path,
                   help=f"video id, URL, or words from its title or channel — or a bundle directory")
    a.add_argument("start", help="SS, MM:SS, or HH:MM:SS")
    a.add_argument("end", help="SS, MM:SS, or HH:MM:SS")
    a.add_argument("-o", "--out", type=Path, default=None, help="output .html path")
    a.add_argument("--display-distance", type=int, default=DISPLAY_DISTANCE,
                   help=f"cull harder than the build pass (default {DISPLAY_DISTANCE})")
    a.add_argument("--template", type=Path, default=None)
    a.set_defaults(func=cmd_artifact)

    root_help = (f"library root (default: ${BUNDLES_ENV}, else {DEFAULT_BUNDLES})")

    i = sub.add_parser("index", help="list the scribed videos in the library")
    i.add_argument("--root", type=Path, default=None, help=root_help)
    i.add_argument("--json", action="store_true", help="machine-readable form")
    i.set_defaults(func=cmd_index)

    s_ = sub.add_parser("search", help="find a phrase across every scribe")
    s_.add_argument("term")
    s_.add_argument("--root", type=Path, default=None, help=root_help)
    s_.add_argument("--id", action="append", default=[], metavar="VIDEO",
                    help=f"restrict to this video — video id, URL, or words from its title or channel (repeatable)")
    s_.add_argument("-C", "--context", type=int, default=0, metavar="N",
                    help="also print N cues either side of each hit")
    s_.add_argument("-e", "--regex", action="store_true",
                    help="read the term as a regular expression")
    s_.add_argument("--case", action="store_true", help="match case")
    s_.add_argument("--limit", type=int, default=40,
                    help="stop after this many hits (0 for all, default 40)")
    s_.set_defaults(func=cmd_search)

    pr = sub.add_parser("prune", help="remove a scribed video from the library")
    pr.add_argument("--root", type=Path, default=None, help=root_help)
    pr.add_argument("--id", action="append", default=[], metavar="VIDEO",
                    help=f"prune this video — video id, URL, or words from its title or channel; ambiguity is refused, "
                         f"never guessed (repeatable)")
    pr.add_argument("--older-than", type=float, default=None, metavar="DAYS",
                    help="prune bundles unread for this many days")
    pr.add_argument("--keep", type=int, default=None, metavar="N",
                    help="keep the N most recently read, prune the rest")
    pr.add_argument("--over", default=None, metavar="SIZE",
                    help=f"prune least-recently-read first until the library "
                         f"fits (default {human(PRUNE_BUDGET)})")
    pr.add_argument("--yes", action="store_true",
                    help="actually delete; without it this is a dry run")
    pr.set_defaults(func=cmd_prune)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
