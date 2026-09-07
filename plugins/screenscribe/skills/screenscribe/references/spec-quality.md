# Spec quality bar

Apply before declaring a spec done.

## Acceptance criteria must be checkable

| Not a criterion | A criterion |
| - | - |
| Handles errors gracefully | Given a malformed VTT, exits 1 with a message naming the bad line |
| Fast enough | 90-min video processes in under 4 min on an M-series laptop |
| Good frame selection | 60-min screencast yields 40–60 frames, no two within 4s |
| Works correctly | `pytest tests/test_parse.py` passes |
| Clean code | `ruff check .` exits 0 |

Test: could someone absent from the conversation determine pass/fail without
asking? If not, rewrite.

## Section rules

| Section | Rule |
| - | - |
| Non-goals | Empty means unfinished. Write the fence. |
| Requirements | One per line. A requirement containing "and" is two requirements. |
| Intent | State the tradeoff, not just the goal, so the agent picks the branch you would at a fork the spec did not anticipate. |
| Inferred | Every requirement Claude added that the user did not state goes here. |

## Provenance for video-sourced specs

Every video-sourced requirement cites a **span**, not a timestamp — a span is
re-openable, a timestamp is a bookmark nobody can act on:

```
Watch: <video_id> 12:04-14:30
```

Record deviations from the source, or a future session "fixes" the divergence.

Cite what you saw, not what was said over it. Narration is the author
describing their intent; the frames are what they actually did. Where the two
disagree, the frames win and the disagreement is worth a line in the spec.

## Final check

Name the single riskiest assumption — most likely wrong, most expensive to
discover late.
