# SPEC-<NNN>: <Title>

**Status:** draft | approved | building | done
**Source:** <video URL, or "original">
**Watch:** <bundle path + span, or omit if no video>

---

## Intent

One paragraph. Why this exists and what problem it removes. Written so an agent
choosing between two valid implementations picks the right one.

Not "build a caching layer." Rather: "cold starts dominate our p99 and the data
changes hourly at most, so we trade freshness for latency."

## Outcomes

Observably different states when this lands. Two to four bullets. Each describes
a state, not a task.

- <someone> can <do thing> without <previous friction>
- <metric> moves from <x> to <y>

## Requirements

- **R1 (MUST)** ...
- **R2 (MUST)** ...
- **R3 (SHOULD)** ...

<!-- One per line. A requirement containing "and" is two requirements. -->

## Non-goals

- Not doing <adjacent thing>
- Not handling <case> — deferred until <trigger>

<!-- Mandatory section. Empty means unfinished, not minimal. -->

## Constraints

- Language / runtime:
- No dependencies beyond:
- Budget:

## Acceptance criteria

- [ ] **AC1** — `<command>` exits 0 / produces `<artifact>`
- [ ] **AC2** — Given `<input>`, output contains `<observable>`
- [ ] **AC3** — <edge case>: `<test name>` passes
- [ ] **AC4** — No regression: existing suite green

<!-- Every criterion verifiable by running or observing something.
     `cmd exits 0` beats "the output looks right." -->

## Open questions

- [ ] <question> — blocking R<n>?

<!-- An agent hitting one of these stops and asks. -->

## Inferred (confirm or strike)

- <item Claude added that the user never stated>

<!-- Empty is ideal. -->

## Provenance

- Video: <url>
- Bundle: `<video_id>` (under the screenscribe bundle root)
- Deviations from source: <what differs, and why>

Each key moment cites a span, not a memory. An agent picking this up re-opens it:

Re-open a span with the screenscribe skill — it resolves the script:
`window <video_id> 12:04-14:30`

| Watch | What was on screen | Feeds |
| - | - | - |
| `12:04-14:30` | <what the frames show> | R1, AC2 |
| `31:10-33:45` | <what the frames show> | R4 |

<!-- A row whose bundle no longer exists is an unverifiable claim. Say so rather
     than implementing from the summary. -->
