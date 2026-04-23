# Handoff Context

Save the current session's working state to a structured JSON file so it survives a `/clear` and can be resumed later via `/resume-context`.

## Steps

1. **Ensure `.context/` exists** at the project root. Create it if missing.

2. **Check `.gitignore`** — if `.context/` is not already ignored, append it with a comment:
   ```
   # Context handoff files (session state, not committed)
   .context/
   ```

3. **Archive any existing handoff** — if `.context/context-handoff.json` exists, rename it to `.context/context-handoff.<YYYYMMDD>T<HHMMSS>.json` using the current UTC timestamp before writing the new one.

4. **Self-dedupe against current session** — before building the handoff JSON, review the `completed` items you're about to write. Any item that appears in both `completed` and `next_steps` should be removed from `next_steps`. This prevents the next session from picking up work that was already finished in this session.

   Also check if any `blocked` items were resolved during this session (i.e., they appear in `completed` or are no longer blocked based on conversation context). Remove resolved blockers from the `blocked` array.

5. **Diff against prior handoff** — if an archived handoff exists (`.context/context-handoff.<timestamp>.json`), read the most recent one and check for items in your new `next_steps` that already appear in the prior handoff's `completed`. Remove them — they're stale leftovers from a previous session that were never cleaned up.

6. **Analyze the full conversation** and build a JSON object with this schema:

```json
{
  "version": "1.0",
  "created_at": "<ISO-8601 UTC>",
  "project_root": "<absolute path>",
  "branch": "<current git branch>",
  "task": {
    "goal": "<what we were trying to accomplish>",
    "why": "<motivation / context behind the task>"
  },
  "state": {
    "completed": ["<items finished>"],
    "in_progress": ["<items started but not done>"],
    "blocked": ["<items blocked, with reasons>"]
  },
  "decisions": [
    {
      "decision": "<what was decided>",
      "rationale": "<why>",
      "alternatives_rejected": ["<options considered but not chosen>"]
    }
  ],
  "constraints": ["<discovered constraints, edge cases, gotchas>"],
  "issues": ["<bugs, warnings, problems encountered>"],
  "files_modified": ["<files changed in this session>"],
  "next_steps": ["<ordered list of what to do next>"],
  "notes": "<any other important context that doesn't fit above>"
}
```

7. **Write** the JSON to `.context/context-handoff.json` (pretty-printed, 2-space indent).

8. **Confirm** to the user: show what was saved (summary, not the full JSON), and remind them of the next steps:
   ```
   /clear
   /resume-context
   ```

## Important

- Be thorough. The next session starts with zero memory of this conversation.
- Capture the WHY behind decisions, not just what was decided.
- Include specific file paths, branch names, and PR numbers — vague references won't survive the clear.
- If git has uncommitted changes, note that in `state.in_progress`.
- Omit empty arrays/fields — keep the JSON clean.
