# Resume Context

Load a previously saved context handoff and orient this session around it.

## Steps

1. **Read** `.context/context-handoff.json` from the project root.
   - If the file does not exist, check for any `.context/context-handoff.*.json` files and list them. Tell the user no active handoff was found and show available history.

2. **Parse** the JSON and verify it has the expected schema (version, task, state, etc.).

3. **Diff against prior handoff** — find the most recent `.context/context-handoff.<timestamp>.json` archive file (sort by filename timestamp, pick the latest). If one exists:
   - Parse it and extract its `state.completed` array.
   - Compare the current handoff's `next_steps` against the prior `completed` items. Use substring/keyword matching — items won't be verbatim identical but will reference the same PR numbers, issue numbers, or key phrases.
   - Flag any `next_steps` that appear already completed in the prior session — these are **stale** and should be called out in the briefing as "already done (prior session)".
   - Also check current `blocked` items against prior `completed` — a blocker that was resolved in the prior session should be flagged as "potentially unblocked".
   - If no archived handoff exists, skip this step silently.

4. **Orient the session** — print a concise briefing for the user:
   - What we were working on (task goal + why)
   - Current state (what's done, what's in progress, what's blocked)
   - Key decisions made and constraints discovered
   - Immediate next steps (with any stale items from step 3 clearly marked)
   - Current branch and any uncommitted changes (check live git status, don't just trust the file)

5. **Archive the handoff** — rename the file to `.context/context-handoff.<YYYYMMDD>T<HHMMSS>.json` using the current UTC timestamp. This prevents stale context from being loaded in a future session.

6. **Verify against reality** — the handoff was written in a prior session and may be stale:
   - Confirm the branch still exists and is checked out
   - Spot-check that key files mentioned in `files_modified` exist
   - If anything doesn't match, flag it to the user before proceeding

## Important

- This is the FIRST thing running in a fresh session. Be explicit — no references to "what we discussed" since there is no prior conversation.
- Treat the handoff as a briefing document, not gospel. Verify before acting.
- After orienting, ask the user what they'd like to tackle from the next steps (don't auto-start work).
