# Watchwith

Automates the watching and the scribing: Claude watches a video and writes down
what was actually on screen, so you can build anything from it.

## Why this exists

YouTube transcripts already exist, and they're the wrong artifact. In a
screencast the payload lives in the pixels — terminal commands, file trees, IDE
state, config panels, hand-drawn architecture. The narration around them is
filler: "and then we just wire this up here."

So stage 1 samples the video densely and keeps every visually-distinct frame,
named by timestamp. Stage 2 reads a span of them back. Claude reads images
natively, so a span of aligned frames plus the narration over them approximates
having watched that stretch of the video.

What you do with that is open. A spec is the shipped example, with a template
and a quality bar; a review of the video, a summary, a walkthrough, or the list
of commands actually run all come off the same bundle. Every one of them cites
`Watch:` spans, so any claim is re-openable.

A review is the case where this matters most. An author says "and we just wire
this up here" while the screen shows three undocumented flags — a review built
on the transcript reviews the claim, a review built on the frames reviews what
they did.

## Design decisions

**Sample at a fixed rate, don't detect scenes.** The first version used
ffmpeg's `select='gt(scene,N)'` and recovered timestamps by parsing `pts_time`
out of stderr, then zipping that list against the written files. That pairing
was load-bearing and fragile: an ffmpeg version difference or one stray warning
line silently shifted every timestamp in the bundle, and the output still looked
plausible. `fps=N` makes frame N's timestamp arithmetic — `(N-1)/fps` — so there
is nothing left to misalign. It also emits a frame at `t=0`, which scene
detection never does, and it is content-blind in a way scene detection only
pretended not to be.

**1 fps by default.** Matches the granularity transcripts are already cut at,
and is dense enough to catch a command between being typed and scrolling away.

**1408px wide, not 1280 and not 1920.** Claude downscales anything over ~1.15
megapixels, so 1408×792 (1.12 MP, ~1487 tokens) is the widest frame whose pixels
survive the trip. 1568 and 1920 cost more bytes and arrive identical.

**Source resolution is load-bearing; source bitrate is not.** Because frames are
scaled to 1408, a 1920-wide source is downscaled — a low-pass filter that
discards exactly the high-frequency detail bitrate buys — while a 1280-wide
source is *upscaled*, inventing pixels that were never there. Measured on a
1080p screen-share containing a diagram with near-sub-pixel labels: av01 at
587 MB and YouTube's premium vp9 at over 1 GB are character-for-character
identical after the pipeline, and 720p loses the filename and the test output
entirely. So `format_sort` takes the resolution first and then the smallest
encode of it; `bestvideo` alone was picking the premium stream and paying ~40%
more for nothing.

**JPEG, not PNG.** Measured on h264-sourced frames of dense terminal text:
SSIM 0.995, PSNR 42.7 dB against lossless, and both crops read identically.
Token cost is set by pixel dimensions, not file size, so PNG's 2.8× disk buys
nothing but a faithful copy of h264's artifacts — YouTube already discarded the
real detail before we got it.

**`phash(hash_size=16)`, not the library default.** This one silently ate half
the video. `imagehash.phash()` defaults to a 32×32 grayscale DCT, which
annihilates small text — two frames showing entirely different terminal commands
hash nearly identically. Measured across six distinct scenes: at `hash_size=8`
the distinct-scene distances were 0, 0, 4, 6, 14 while identical frames scored
0, so **no threshold separates them** and the old default of 6 discarded three
of five real transitions. At `hash_size=16` the same input scores 26 minimum
between distinct scenes and 0 within identical ones.

**Build greedily, budget at read time.** An earlier version culled to 60 frames
during extraction to protect a context budget. That threw pixels away
permanently to solve a problem at the wrong layer — extraction cannot know what
you will want to look at. Now `build` keeps everything distinct and `window`
enforces the budget, because it is the only stage that knows the question.

**`BUNDLE.md` is a map, not the payload.** It carries chapters, per-minute frame
density, and the full transcript. It does not inline frames: at 1 fps that file
would be thousands of images long, and `![](frames/x.jpg)` in a file Claude
reads is inert text that renders nowhere and loads nothing. `window` prints bare
absolute paths precisely so they can be fed straight to Read.

**Keep the description verbatim.** It routinely carries what neither the frames
nor the narration do: repo URLs, tool versions, prerequisites, the author's own
outline. An earlier version truncated it at 2000 characters, which severed real
descriptions mid-link — and truncating at all is compression at the wrong layer,
since nothing else in stage 1 summarizes either. `BUNDLE.md` also lists the URLs
it contains, minus affiliate and social boilerplate.

**Emit is not automated.** The idea lives in the user's head; the video only
informs it. The bundle exists so Claude can argue about the idea concretely
instead of nodding along.

**Ask YouTube for json3, not vtt.** The famous rolling duplication — each cue
restating the previous one's tail — is an artefact of **VTT**, which is built for
on-screen display where lines scroll. YouTube serves the same captions as json3,
already de-duplicated. Measured across five videos, json3 matches a
VTT-plus-merge pipeline at 97.9-100%, and every single difference is a residual
duplicate the merge left behind: 34 deletions, 0 insertions, 0 replacements.
json3 drops nothing.

That deleted an entire subsystem — rolling-track detection, a word-overlap merge,
a minimum-overlap threshold, and a minimum-cue floor, all of which existed only
to undo VTT's display formatting. It also removed the one failure this plugin
could not make safe: the merge deleted real speech on tracks that did not roll
("run the test" / "run the test again" became "run the test", "again"), and no
heuristic separating the two cases was ever going to be perfect. `parse_vtt` and
its merge remain as a fallback for a source that does not serve json3.

Nothing here transcribes. The text is whichever caption track YouTube already
has, preferring an author-uploaded one and falling back to the auto-generated.

## Rejected approaches

**YouTube OAuth as a content route.** `captions.list` returns caption track IDs
for any video, but `captions.download` returns 403 unless the OAuth token belongs
to the account that *owns* the video. Not a scope problem, not a quota problem —
by design.

**A Gemini extraction pass.** Shipped briefly as `--gemini`, cut before release.
It returned `extraction.md`: Gemini's reading of the video, already compressed.
That is derived evidence, and it fails for the same reason a transcript does —
a spec citing it cites a claim, where a spec citing a frame cites a source. It
also carried the plugin's only API key, its only second vendor, and a code path
that had never executed. `docs/plans/watchwith-gemini-ingestion.md` holds the
full analysis and the follow-up worth building: let Gemini pick *which
timestamps matter*, then cut frames there with ffmpeg and read the pixels
ourselves. Selection is the part it is genuinely better at.

**Transcribing the audio.** The first draft was framed around the spoken track.
Wrong layer — the narration is the filler and the screen is the payload. The
name kept the "scribe" half deliberately: this does scribe, it just scribes the
pixels.

## Dependencies

The first plugin here that requires installing its own dependencies rather than
borrowing a project's existing toolchain:

- `ffmpeg` on PATH
- `yt-dlp`, `imagehash`, `pillow`
- `curl_cffi` and `deno` — strongly recommended, see below

Only the video stream is downloaded. Nothing decodes audio — frames come from
`-vf` and the narration comes from the subtitle track — so pulling `+bestaudio`
was fetching roughly a quarter of the bytes to discard them (measured 33.2 MiB
vs 25.6 MiB on a 7-minute tutorial).

`build` preflights all four and names the missing one before downloading
anything — they import lazily deep in the pipeline, so without that check a
missing Pillow surfaced only after the full download and the entire sampling
pass.

```bash
brew install ffmpeg deno     # or the platform's package manager
python3 -m venv ~/.watchwith/venv
~/.watchwith/venv/bin/pip install -q yt-dlp imagehash pillow curl_cffi
```

`curl_cffi` and `deno` are not imported by this script, and `build` does not
preflight them — yt-dlp uses them when they are present and warns when they are
not:

| Missing | yt-dlp says | Cost |
| - | - | - |
| `curl_cffi` | "no impersonate target is available" | requests do not match a browser's TLS fingerprint, so YouTube is likelier to rate-limit them |
| `deno` | "extraction without a JS runtime has been deprecated" | some formats are not offered, which can defeat the 1080p selection above |

Neither is required, and neither authenticates anything. Cookies
(`--cookies-from-browser`) would make requests look like a signed-in human, but
they attach the download to a real Google account and YouTube suspends accounts
for automated use — the impersonation route carries no such risk, so try it
first.

The venv lives under `$HOME`, deliberately not in `~/.claude/plugins/cache/`:
that directory holds versions side by side and gets a fresh one on every plugin
update, so anything installed there is orphaned immediately. The skill runs
`watchwith.py bootstrap`, which creates the venv when it is missing, installs
anything absent, and prints the interpreter path the skill then binds.

For developing this repo, a throwaway `.venv` at the repo root is enough — it is
gitignored, and the test suite is stdlib-only apart from `imagehash`/`pillow`:

```bash
python3 -m venv .venv && .venv/bin/pip install -q imagehash pillow
.venv/bin/python -m unittest discover -s plugins/watchwith/skills/watchwith/tests
```

## The shareable page

`artifact <video_id> <start> <end>` emits a self-contained HTML page for a span:
the frames, each paired with what was said over them, plus chapters, the
author's description and its links.

Frames embed as `data:` URIs because the artifact runtime serves no asset store,
so the page budget is the constraint rather than disk. Two things follow. Frames
are re-encoded to 900px, which is ample for reading a terminal on screen and a
fraction of the bytes. And a second, harsher perceptual-hash pass runs for
display only: on a tutorial with a moving webcam, a 170-second span kept 108
frames for reading and 33 for the page — the other 75 were near-identical jitter
that would have cost 3 MB without telling the reader anything.

The page ships two controls that are not decoration. Every screen collapses
individually, and one toggle hides them all — leaving exactly what the transcript
alone would have given you. On the span above, of eleven concrete things visible
on screen (`git rebase -i HEAD~4`, `--continue`, `--abort`, the commit SHAs),
**none** appear in the narration. The toggle makes that checkable in one click
rather than asserted in a README.

Frames with nothing said over them are labelled rather than quietly captioned,
so the page never implies narration that does not exist.

## Where bundles live

`-o <path>`, else `$WATCHWITH_BUNDLES`, else `~/.watchwith/bundles`.

The default is under `$HOME` rather than the working directory on purpose. A
bundle runs 100-240 MB, so a cwd-relative default drops that into whatever repo
you happen to be standing in and obliges every one of them to carry its own
gitignore entry. One library also means a video informing three projects is
downloaded once instead of three times.

`window` takes a bare video id against that root, so a `Watch:` line resolves
from any working directory:

```bash
watchwith.py window 3sHNpzgNCYY 12:04 14:30
```

Pass `-o ./bundles` when you want the bundle to live with the project.

A direct path that is already a bundle always wins over the library, so an
explicit `-o` bundle is never shadowed.

## Constraints

`yt-dlp` sits in a ToS gray area. Fine for personal learning; do not vendor this
into a shipped product without a licensed transcript or video source.

Disk scales with how much the frame actually changes, so it varies a lot by
production style. Two measured points: a 7.4-minute tutorial with a live webcam
behind a translucent terminal kept 312 of 444 frames (70%) and ran 30 MB; a
58-minute interview with two face cams kept 3165 of 3517 (90%) and ran 245 MB.
Talking heads are the worst case — every frame differs perceptually while
carrying no payload.

Peak transient disk is higher than the bundle, and higher than first documented.
The 58-minute video downloaded over 1 GB before sampling, because `bestvideo`
selected YouTube's premium stream. With the format sort below it is 587 MB, and
peak is that plus the pre-dedupe frames.

## Without a video

The spec template and quality bar stand on their own. Skip stages 1–2 to author
a spec from a plain idea.
