# watchwith

Watch a video *with* Claude. It cannot see or hear, so this hands it a facsimile
dense enough to learn from: a frame per second, each one married to the words
spoken over it.

```
/plugin install watchwith
```

Requires `ffmpeg` on PATH. Python dependencies install themselves on first run.

## Skills

| Skill | |
| - | - |
| `/watchwith:watchwith` | the whole pipeline — build, watch, scribe, emit |

You rarely need to type it. Paste a YouTube URL and ask for what you want; the
skill's description covers "watch this", "what did they actually run", "write me
a spec from this talk", and re-opening a `Watch:` span cited in an old document.

## Usage

```text
You: /watchwith:watchwith https://www.youtube.com/watch?v=VIDEO_ID
You: watch this and tell me what commands he actually ran — <url>
You: /watchwith:watchwith                      # no video — author a spec from an idea
You: re-watch the span cited in docs/specs/004-rebase.md
```

The skill takes a full URL or a bare video id. Copy the URL from the address
bar; converting it to an id is work you do not need to do.

After it scribes, it **stops and asks** what to do with the result — a spec, a
review, notes, a walkthrough, a shareable page, or an inline answer. It asks
even when you said up front, because what you asked for before anyone had seen
the frames was a guess.

### The library

Every video you scribe stays in `~/.watchwith/bundles` and is addressable later.

```text
You: what videos have I scribed?              → index
You: search my videos for "subagent"          → search across every transcript
You: which of these can I delete?             → prune, dry run first
```

Name a video by id, URL, or any words from its title or channel. Ambiguity is
listed for you to pick from, never guessed.

## Tips

**Let it pick the span.** A whole video is rarely the question. The bundle
carries a screen-share segment table, and asking about a topic beats asking for
the whole thing — 10 minutes at 1 fps is roughly 150k tokens.

**Frames beat narration, and the gap is the point.** Where the author says "and
we just wire this up here" over three undocumented flags, the frames have the
flags. Ask what was *shown*, not what was said.

**Raise `--fps` for dense terminal work**, lower it for talking heads. Default
is 1.0. Raise `--phash-distance` when near-identical frames survive; lower it
when distinct screens get dropped.

**Notes are written for a future session, not for you.** If you have already
watched the video, the output will read as more literal than a summary you would
write yourself — mechanism, syntax, exact commands. That is deliberate: the
audience is a session with no memory of it.

**Every claim carries a `Watch:` span.** A disputed requirement is settled by
re-opening the source, not by trusting prose. Keep the bundle and the citation
stays live.

**A shareable page needs a span, and 12 MB is the ceiling.** Frames embed as
`data:` URIs. Narrow the span if a page refuses to publish.

**Disk is production-dependent.** A 7-minute tutorial ran 30 MB; a 58-minute
two-camera interview ran 245 MB. Talking heads are the worst case — every frame
differs while carrying no payload.

**`yt-dlp` sits in a ToS gray area.** Fine for personal learning. Do not vendor
this into a shipped product without a licensed video or transcript source.

## Deeper

[Design decisions, dependencies, measurements, and rejected
approaches](./skills/watchwith/README.md) — why 1408px, why `hash_size=16`, why
json3 instead of VTT, and what a Gemini pass would and would not buy.
