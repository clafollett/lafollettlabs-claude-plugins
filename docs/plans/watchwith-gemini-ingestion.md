# Plan: Gemini video ingestion for `watchwith`

**Status:** DECIDED 2026-09-07 — option B. `--gemini` cut before release.
**Affects:** `plugins/watchwith/skills/watchwith/scripts/watchwith.py`
**Written:** 2026-09-07

> ## Decision
>
> **B now, D next.** `--gemini` was deleted rather than ported.
>
> Two things changed the calculus after this was written:
>
> 1. **Windowed reads.** `window <bundle> <start> <end>` reads a span back on
>    demand, so dense primary evidence became cheap to hold. The token table
>    below prices frames as "expensive to hold" — that was a 200k-context
>    assumption. At 1M, a 10-minute span at 1 fps is ~150k tokens.
> 2. **The frame budget stopped being a build-time decision.** `build` now keeps
>    every distinct frame; only `window` spends context. The "60 frames/hour vs
>    Gemini's 3600" comparison below was measuring a cap that no longer exists.
>
> What survives unchanged is the primary/derived argument in "The actual
> argument for keeping both" — and it argues *against* shipping `extraction.md`,
> not for it. A spec citing Gemini's reading cites a claim.
>
> **Option D remains the real design** and is the follow-up: let Gemini pick
> which timestamps matter for a given intent, cut frames there with ffmpeg, and
> read the pixels ourselves. Selection is what it is genuinely better at;
> extraction is what we should not delegate.
>
> ### Verified against Google's live docs, 2026-09-07
>
> | This doc claimed | Actually |
> | - | - |
> | `generate_content` "probably broken" | Interactions API went GA June 2026 and is recommended; `generate_content` is **legacy but fully supported** |
> | text goes *after* the video part | The YouTube example puts **text first** |
> | `interactions.create`, `processing: "agentic"`, `media_resolution`, static `fps` / `start_offset` | Confirmed, all real |
> | public-only, 8h/day free tier, 10 videos/request on 2.5+ | Confirmed |
>
> So the flag was stale, not broken — but it had still never executed, which is
> the standard this doc itself sets.

---

## TL;DR for the reviewer

Three things, in order of urgency:

1. **The shipped `--gemini` implementation targets a legacy API surface and is
   probably broken.** It has never run. See "Known defect" below.
2. **Gemini's agentic video mode may obsolete stage 1's core heuristic.** Our
   scene-detection frame culling is a hand-rolled approximation of something
   Gemini now does natively, better, with the prompt in hand.
3. **Keeping both is still defensible** — but for an epistemic reason, not a
   coverage reason, and that reason should be written down before someone
   "simplifies" the pipeline.

---

## Background

`watchwith.py` builds a bundle: scene-change keyframes interleaved with
timestamped narration, so Claude sees the on-screen content a transcript omits.
`--gemini` was added as an optional second pass — Gemini ingests the YouTube URL
natively and returns a verbatim extraction of on-screen code and commands, saved
to `extraction.md` next to the bundle.

The original reasoning was "belt and suspenders": two readers catch more than
one. That reasoning was made without checking what Gemini's video pipeline
actually does now. It does considerably more than assumed.

## Known defect

`gemini_pass()` calls:

```python
client.models.generate_content(
    model="gemini-flash-latest",
    contents=[{"text": PROMPT}, {"file_data": {"file_uri": url}}],
)
```

Current documented shape is the Interactions API:

```python
client.interactions.create(
    model="gemini-3.8-flash",
    input=[
        {"type": "video", "uri": "https://www.youtube.com/watch?v=..."},
        {"type": "text", "text": PROMPT},
    ],
)
```

Google publishes both a "Migrate to Interactions API" guide and an "Interactions
breaking changes (May 2026)" page, so `generate_content` is the older surface.
Whether it still resolves YouTube URIs via `file_data` is untested.

Also note: the technical-details section says that when combining text with a
single video, the text prompt goes **after** the video part in `input` — while
the YouTube example on the same page puts text first. Worth testing rather than
trusting either.

**Action regardless of the strategic decision below:** port to `interactions.create`,
or delete the flag. Shipping a code path that has never executed against an API
shape we didn't verify is worse than not shipping it.

## What Gemini actually offers now

- **Static mode (default):** frames sampled at **1 FPS**, audio at 1 Kbps,
  timestamps every second. Docs note it may miss detail in rapid motion or quick
  scene changes.
- **Agentic mode:** the model dynamically navigates the timeline, selectively
  loading transcript, frames, and audio on demand based on the prompt. Claimed
  up to **88% fewer tokens** and **~7% higher quality** on long-form content.
  Supported on Gemini 3.8 / 3.7 / 3.6 Flash and 3.5 Flash Lite.
- **`media_resolution`:** caps tokens per frame. Higher improves reading fine
  text — directly relevant, since legible terminal text is the whole reason
  stage 1 caps at 1080p.
- **Custom `fps` and clipping intervals** in static mode: sample one chapter
  densely instead of the whole video uniformly.
- **Limits:** public videos only (not private or unlisted); free tier caps at
  8 hours of YouTube per day; 10 videos per request on 2.5+.
- **Timeouts:** long or complex requests should use streaming or background
  execution — synchronous calls can surface spurious 401s or timeouts.

### The uncomfortable comparison

Stage 1 currently gives Claude roughly **60 frames per hour** of video. Gemini
static mode sees **3,600 frames per hour**, plus the audio track, at native
temporal resolution. Agentic mode sees whatever it decides it needs, guided by
the prompt.

Our scene-detection-plus-phash-plus-downsample pipeline is a heuristic guess at
which moments matter, made with no knowledge of the question being asked.
Agentic mode makes that same selection *with the prompt in hand*. That is
strictly more informed.

## Token economics

Rough, for a 60-minute tutorial:

| Path | Cost to produce | Cost to consume (Claude context) |
|---|---|---|
| Bundle frames | ~free after download | ~60–90k (60 images) + ~10k transcript |
| Gemini static, low res | ~350k tokens into Gemini | ~5–10k (markdown out) |
| Gemini static, high res | ~1M tokens into Gemini | ~5–10k |
| Gemini agentic | up to 88% less than static | ~5–10k |

Frames are cheap to produce and expensive to hold. Gemini extraction is
expensive to produce and cheap to hold. They are not competing for the same
budget, which is part of why "just pick one" is harder than it looks.

## The actual argument for keeping both

Not coverage. **Provenance.**

- **Frames are primary evidence.** Claude looks at the pixels. If a spec
  question comes up that nobody anticipated — "wait, what was the exact flag on
  that command?" — the frame is still there to re-read.
- **`extraction.md` is derived evidence.** It is one model's reading, already
  compressed. Claude cannot interrogate what Gemini chose not to mention without
  re-running the call. A second model's errors enter the record looking exactly
  like observations.

That distinction matters for a tool whose output feeds `/goal`. A spec citing
`extraction.md` is citing a claim; a spec citing a frame is citing a source.

**If we keep both, `BUNDLE.md` must label `extraction.md` as derived**, and
`spec-quality.md` should say that provenance timestamps referencing Gemini
output are weaker evidence than timestamps referencing a frame. Currently
neither does. That is a gap in what shipped.

## Options

**A. Port `--gemini` to the Interactions API, keep it optional.**
Smallest change. Preserves the primary/derived split. Still carries a preview
dependency, an API key, a second vendor, and nondeterminism.

**B. Drop `--gemini` entirely.**
Kills the extra dependency, the key handling, the preview risk, and the
provenance ambiguity in one move. Plugin stays single-vendor. Loses the second
reader on transient on-screen content that 1-frame-per-minute sampling misses.

**C. Invert: Gemini agentic becomes stage 1, frames become the fallback.**
Follows the capability honestly. Gemini navigates the video, and we keep a small
set of frames purely as citable evidence for whatever it flags. Biggest rewrite;
makes a preview API load-bearing for the plugin's main path.

**D. Keep frames, replace the Gemini *extraction* with Gemini *targeting*.**
Ask Gemini which timestamps matter for a given intent, then extract frames at
exactly those points with ffmpeg. Gemini picks the moments; Claude reads the
pixels. Primary evidence preserved, selection made by something that can
actually read the content.

## Recommendation

**A now, D as the real design.**

Port the call, ship it optional and clearly labeled derived — that clears the
"never executed" defect without betting the plugin on a preview API. Then
prototype D, because it resolves the tension rather than splitting the
difference: the weakest part of stage 1 is that scene-change detection is
content-blind, and D fixes exactly that while keeping frames as primary
evidence.

C is tempting and probably where this ends up in a year. Not while the YouTube
URL path is preview, free-tier-capped, and public-video-only.

## What would settle this

Run one real 60-minute coding tutorial through every path and compare against a
hand-built ground truth of what's actually on screen:

1. Bundle only (60 frames)
2. Bundle at `--max-frames 150`
3. Gemini static, high `media_resolution`
4. Gemini agentic
5. Option D: Gemini-selected timestamps → ffmpeg frames

Score on: commands captured verbatim, file paths captured, config values
captured, architecture correctly described, and **hallucination rate** — things
asserted that are not on screen. That last column is the one that decides
whether derived evidence is trustworthy enough to cite in a spec.

## Open questions

1. Does `--gemini` justify being the plugin's only external-API dependency, or
   does it belong in a separate plugin so `watchwith` stays self-contained?
2. Where does `GEMINI_API_KEY` come from, and what does the skill do when it's
   absent — silent skip (current behavior) or hard fail? Silent skip means a
   bundle can be quietly missing a section the spec assumed was there.
3. Does the ToS position change if the Gemini path replaces `yt-dlp`? Passing a
   URL to Google's API is a different act from downloading the stream. Worth a
   real answer, since it affects whether any of this can go near Corebizy.
4. If we go with D, does `watchwith.py` still need `yt-dlp` at all, or can
   frame extraction run against a stream URL without a full download?


---

## Inherited open questions

Carried over from the skill's `PLAN.md`, which was deleted — it was an internal
status file shipping inside a distributed plugin.

Closed:

- **What does `/goal` expect as input?** `/goal` does not exist in this
  marketplace or in the authoring environment. The claim was removed from both
  READMEs rather than designed against.
- **Dependency precedent.** Accepted. `ffmpeg` + `yt-dlp`/`imagehash`/`pillow`,
  documented in the plugin README. Cutting `--gemini` keeps it to one vendor and
  no API keys.
- **Never run end-to-end.** Stage 1 now has a test suite covering the VTT
  parser, frame sampling, dedupe, timestamp naming, and windowed read-back
  against a generated video. A real YouTube run is still outstanding.

Still open:

1. **`docs/specs/` vs `issue-manager`'s `docs/epics/`.** Both turn intent into
   structured work items. A spec that becomes an Epic plus Stories is a
   plausible chain. Decide whether watchwith emits into issue-manager's flow or
   stays parallel. The `Watch:` provenance directive is designed to survive that
   hand-off either way — an Epic or Story can carry it unchanged.
2. **Does stage 1 belong in this plugin at all?** The spec template and quality
   bar are useful with no video anywhere in sight. If the ingest pipeline grows,
   splitting it keeps the spec half dependency-free.
