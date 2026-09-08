# session-analyzer

Find, read, and measure your Claude Code sessions. They are JSONL files on disk;
this turns them into transcripts and statistics.

```
/plugin install session-analyzer
```

Python 3.10+, zero dependencies.

## Skills

| Skill | |
| - | - |
| `/session-analyzer:session-analyzer` | find sessions, extract transcripts, report statistics |

## Usage

Ask in your own words — the skill maps intent onto the right command:

```text
You: analyze my last session
You: find the session where we discussed the CREW prototype
You: extract yesterday's conversation with tool calls
You: what did we talk about Monday?
You: how many tokens did that session burn?
```

Underneath there are four commands: `list` (find sessions, filtered by project,
date, or size), `search` (case-insensitive content match across sessions),
`extract` (readable markdown transcript), and `analyze` (duration, tokens, cache
hit rate, tool breakdown, files modified).

## Tips

**`extract` writes a file and prints the path — let it.** Pulling a full
transcript into the conversation burns the context you are trying to study. Use
`--head` / `--tail` only for a quick peek.

**Search first when you do not know which session.** `list` by date works when
you remember *when*; `search` works when you only remember *what*. Sessions are
per-project, so run it from the repo you were working in.

**Cache hit rate is the number worth watching.** `cache_read / (input +
cache_read)` — a low rate on a long session usually means something was
invalidating the prefix, and that is a cost problem you can act on.

**`--tools` and `--timestamps` change what a transcript is for.** Without them
you get the conversation; with them you get an audit trail of what actually ran
and when. Add `--thinking` when you are debugging a decision rather than reading
a discussion.

**Sub-agent conversations are excluded by default.** Pass `--sidechains` when
the interesting work happened inside a dispatched agent — otherwise a session
that delegated heavily will look emptier than it was.

**Rename your sessions.** A custom session title flows into the extracted
filename; without one you get a UUID fragment, which is not something you will
recognize in three weeks.

**It streams.** Arbitrarily large session files are fine — nothing is loaded
whole.
