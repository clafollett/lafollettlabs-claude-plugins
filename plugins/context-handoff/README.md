# context-handoff

Carry a session's working state across a `/clear`. Writes what you were doing,
why, and what is left to `.context/context-handoff.json`, then rebuilds the
briefing on the other side.

```
/plugin install context-handoff
```

## Commands

| Command | |
| - | - |
| `/context-handoff:handoff-context` | serialize the session before clearing |
| `/context-handoff:resume-context` | load it, orient, verify against live git |

## Usage

The whole flow is three lines:

```text
You: /context-handoff:handoff-context
You: /clear
You: /context-handoff:resume-context
```

The handoff captures the task goal and its motivation, what is completed /
in-progress / blocked, decisions with their rationale and the alternatives
rejected, discovered constraints, modified files, and ordered next steps.

`.context/` is created and added to `.gitignore` automatically — session state
is not committed.

## Tips

**Hand off before you are forced to.** The handoff is written by a session that
still remembers; one written at the very end of a full context window is
compressed by the same pressure it exists to escape.

**The *why* is the part that does not survive otherwise.** "Chose polling over
webhooks" is worth little; "chose polling because the vendor's webhook retries
are not idempotent and we saw duplicates" is the whole decision. The schema has
a slot for rationale and rejected alternatives — let it be used.

**Stale next-steps get flagged, not silently followed.** Resume diffs the new
`next_steps` against the prior archive's `completed` and marks anything already
done. A blocker resolved last session shows as "potentially unblocked" rather
than blocking you again.

**Resume verifies before it trusts.** The branch is checked out, files are
spot-checked, live `git status` beats the file. Treat the briefing as a
briefing, not gospel — it was written by a session that has since ended.

**Handoffs archive, they do not accumulate.** Resuming renames the file to
`.context/context-handoff.<timestamp>.json`, so a stale handoff cannot be loaded
twice. The archives are what the dedupe reads.

**Name specifics.** File paths, branch names, PR numbers. "The auth thing" does
not survive a clear.
