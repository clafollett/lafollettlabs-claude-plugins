# Code Review: screenscribe-library

**Verdict:** 🚫 BLOCKED

| | |
| - | - |
| **Branch** | `main` (commit range `01b5ad4..a444a63`) |
| **Reviewer** | @Cali LaFollett |
| **Review Round** | 1 |
| **Reviewed SHA** | `a444a633ee663aabfbf8481975b5efe436d769f3` |
| **Title** | Library layer — index, search, prune, and fuzzy video naming |
| **Files Changed** | 7 |
| **Lines Changed** | +1099 / -28 |
| **Date** | 2026-09-07 |

---

## Summary

Three commits added a library layer to screenscribe: `index`, `search`, `prune`
(f10e104), the inversion of `prune`'s default from frame-eviction to
bundle-removal (9112d64), and a widened video-name resolver (a444a63).

One HIGH: `prune --yes` recursively deletes directories that were never
screenscribe bundles. Reproduced by execution — two unrelated directories
destroyed, source file included.

Seven MEDIUM, ten LOW. Two of the MEDIUMs are the same defect seen from opposite sides: after a
`--frames-only` prune, the bundle's own `BUNDLE.md` still instructs a reader to
"read the nearest earlier frame" when every frame is gone, and SKILL.md carries
the identical stale rule on the grep path it leads with.

`pe-governance` reviewed SKILL.md. Python has no matching PE, so the primary
agent ran the generic three-pass on `screenscribe.py` and the test suite
directly. Every finding below marked *reproduced* was executed before it was
written down; none was inferred from reading alone.

**Test suite is green (220 tests, both interpreters).** That is the point: none
of these findings is caught today.

---

## 🔴 HIGH

### HIGH-001 — `prune --yes` deletes directories that were never bundles

**Location:** `scripts/screenscribe.py` — `library()` L1363, `drop()` L1557
**In scope:** yes (both functions are new in this diff)

`library()` accepts any directory holding a JSON *object* named `meta.json` as a
bundle. `drop()` then `shutil.rmtree`s it. `meta.json` is one of the most common
filenames in a developer's tree.

Reproduced against a throwaway directory containing an npm-shaped package and a
photo folder:

```
$ prune --root <dir> --keep 0 --yes
remove my-photos         19B  last read 2026-09-07
remove some-node-p…      50B  last read 2026-09-07
removed 2, freed 69B
```

Both directories were removed, including `some-node-package/index.js`. The only
signal on screen is an empty TITLE column.

Reachable through `--root` or `$SCREENSCRIBE_BUNDLES` — and supporting a library
outside the default root is exactly what those exist for. The dry run shows the
plan first, but the plan renders foreign directories as plausible bundle rows.

**Why the tests missed it:** `test_only_directories_with_meta_are_bundles`
rejects `.DS_Store`, `_staging` and `notes.txt` — every one of them for *lacking*
a `meta.json`. The predicate was never exercised against a directory that has
one.

**Fix:** require a screenscribe signature — `BUNDLE.md` present *and* `meta`
carrying an `id`. Verified all four bundles in the author's real library satisfy
both, and `build_bundle` writes `BUNDLE.md` on every build, so nothing legitimate
is excluded.

---

## 🟡 MEDIUM

### MEDIUM-001 — `search --limit` prints bundle headers with no rows under them

**Location:** `scripts/screenscribe.py` — `cmd_search` L1442 · **In scope:** yes

The header and bundle path print before the per-hit loop, which then breaks
immediately once `shown >= limit`. Reproduced with three matching bundles and
`--limit 2`: two bundles rendered a header and path with zero hit lines, reading
as "matched, but nothing to show."

**Fix:** print the header lazily, on the first row actually emitted for that
bundle; stop scanning once the limit is reached.

### MEDIUM-002 — the lazy-frame-walk optimisation does not exist

**Location:** `scripts/screenscribe.py` — `cmd_search` L1519 comment · **In scope:** yes

The comment claims *"The frames directory is only walked for a bundle that
actually matched — a library scan that stats every frame of every video to print
nothing is the slow path nobody asked for."* `library()` already called
`dir_bytes()` on every bundle and its `frames/` before `cmd_search` ran a single
comparison. Instrumented `os.walk`: 6 walks for 3 bundles, before any matching.

`search` never uses the byte counts. The comment describes an optimisation that
was never implemented, and will mislead the next maintainer into believing the
hot path is already handled.

**Fix:** make the size computation opt-in (`library(root, sizes=False)`), used by
`index` and `prune` but not `search` or `resolve_bundle`; correct the comment.

### MEDIUM-003 — network-derived titles reach the terminal unsanitised

**Location:** `scripts/screenscribe.py` — `clip()` L1399, consumed by `cmd_index` / `cmd_prune`
**In scope:** yes

`clip()` normalises whitespace via `str.split()`, which drops `\r` and `\n` but
**not** `\x1b`. Reproduced: ESC survives into the output. A title is
network-derived third-party metadata — the same source that required `safe_dest()`
after a real path traversal, and that produced HIGH-001 of the v0.3.0 review.

The surface here is `prune`'s dry-run plan: the text a user reads to decide
whether to type `--yes`. ANSI erase/cursor sequences can rewrite or hide rows in
that plan.

**Fix:** strip C0/C1 control characters in `clip()`.

### MEDIUM-004 — a pruned bundle's scribe still asserts frames exist

**Location:** `scripts/screenscribe.py` — `build_bundle` preamble L1043-1055, `drop()` L1557
**In scope:** yes · **Credit:** raised by `pe-governance` as a cross-file note, verified here

Every `BUNDLE.md` carries, unconditionally:

> Seconds whose screen did not change have no file at all — a missing frame means
> the screen was unchanged, NOT that nothing was on screen. Read the nearest
> earlier frame.

`drop(frames_only=True)` removes `frames/` and rewrites `meta.json` only.
`BUNDLE.md` is written at exactly one place — inside `build_bundle` — so nothing
short of a full rebuild corrects it.

Reproduced on a copy of bundle `XV2PAHWnJN0`: after `prune --frames-only --yes`,
`BUNDLE.md` is byte-identical to the unpruned original and its first pointer,
`frames/00-00-06.jpg`, does not resolve. A reader following the file's own
instruction reaches for the nearest earlier frame, which is also gone.

This produces precisely the false inference `require_frames`' docstring says it
exists to prevent. The author had already reasoned about this failure class for
the build path (`cmd_build`: *"leaving BUNDLE.md and meta.json describing frames
that no longer existed"*); the prune path is the one that got missed.

**Fix:** have `drop(frames_only=True)` rewrite the `BUNDLE.md` preamble to state
that the frames were pruned and name the rebuild URL.

### MEDIUM-005 — SKILL.md's grep path has no pruned-bundle recovery

**Location:** `SKILL.md` L143-158 · **Expert:** PE-Governance · **In scope:** yes

Stage 2 states the missing-frame rule unconditionally, and the Stage 2 table
makes `grep "$BUNDLE"` the *primary* read path. The new pruned-bundle guidance
was wired only into `window`. A model that greps a pruned bundle gets dead FRAME
paths and is then told the screen was unchanged. There is no exit.

**Fix:** gate the rule — if `frames/` is gone, the bundle was pruned; rebuild
from `meta.json`'s url.

### MEDIUM-006 — the Library table hands out `--yes` against its own guardrail

**Location:** `SKILL.md` L304-310 vs L331-336 · **Expert:** PE-Governance · **In scope:** yes

Three of five rows in the lookup table are copy-paste destructive commands
carrying `--yes`, while the guardrail twenty lines below says to run `prune`,
show the plan, and stop. The table is the faster-matching form, so a model routing
on "one video gone" executes an unconfirmed delete before parsing the guardrail.
This is the only irreversible operation in the tool.

**Fix:** strip `--yes` from the table rows, leaving the guardrail as the only
place it appears.

### MEDIUM-007 — `--root` is undocumented, so `-o` bundles are unreachable

**Location:** `SKILL.md` L269-336 · **Expert:** PE-Governance · **In scope:** yes

Stage 1 sanctions `-o ./bundles` for project-local bundles. `index`, `search` and
`prune` take `--root`, which appears **zero** times in SKILL.md (verified by
grep), and otherwise fall back to `bundles_root()`. Reproduced: a bundle placed
outside the default root is invisible to `index`, and no documented flag recovers
it.

**Fix:** document `--root` in the Library block.

---

## 🟢 LOW

| ID | Finding | Location |
| - | - | - |
| LOW-001 | `drop()` calls `sys.exit` mid-loop; a containment failure on bundle 3 of 5 leaves a partially applied prune with no summary | `screenscribe.py` `drop()` |
| LOW-002 | `search -C N` reprints overlapping cues for adjacent hits | `screenscribe.py` `cmd_search` |
| LOW-003 | `search` guards `"text" in c` then reads `c["start"]` — a cue missing `start` raises a bare `KeyError` instead of the "corrupt bundle" exit used elsewhere (reproduced) | `screenscribe.py` `cmd_search` |
| LOW-004 | Test gaps: `--limit` has no test, and the bundle predicate is never tested against a foreign `meta.json` (the gap behind HIGH-001) | `tests/test_screenscribe.py` |
| LOW-005 | "The first one given wins" is false — `_select` uses fixed precedence (`id` > `older-than` > `keep` > `over`) regardless of argument order. Wrong in **both** SKILL.md L316 and the `prune_targets` docstring (verified) | `SKILL.md`, `screenscribe.py` |
| LOW-006 | "`-` there means the frames were pruned" over-claims: `frame_for` returns `None` whenever no frame is on disk, and `cmd_search` never reads `meta["pruned"]` | `SKILL.md` L314 |
| LOW-007 | "any words from the title" implies token matching; `matches()` is a contiguous substring test | `SKILL.md` L287 |
| LOW-008 | The "do NOT work from the prose summary" guardrail lost its original branch — the new `elif` was inserted above it at the same indent, narrowing its scope from the missing-bundle case to the pruned case | `SKILL.md` L346-352 |
| LOW-009 | Token weight: ~10 of the section's 72 lines are design justification (the `~0.05%` rationale), and routing is triplicated across the bash block, the "Want \| Do" table and the selector table. SKILL.md is paid on every invocation, and the repo's own rule is to cut any line whose removal does not change what the model does | `SKILL.md` L271-272, 300-310 |
| LOW-010 | "or by asking the user which one" sits above pseudocode saying "do NOT ask them for an id" — close enough to read as contradictory | `SKILL.md` L291-298 |

---

## ℹ️ INFO

| ID | Observation |
| - | - |
| INFO-001 | `resolve_bundle` on a non-existent path now falls through to fuzzy matching, so a stale `-o ./bundles/<id>` path silently resolves to the central library's copy of the same id. Probably desirable; noted because it changes a previously hard error into a silent redirect. |
| INFO-002 | "scribe" is used as a noun for `BUNDLE.md` throughout but never defined as one. |
| INFO-003 | `search --limit` (default 40) is undocumented, so `search` truncates silently. Compounds MEDIUM-001. |
| INFO-004 | `index --json` is undocumented; it carries `url`, `pruned` and `path`, which the human table omits. |
| INFO-005 | The `index` bash comment omits the LENGTH column. |

---

## Action Items

**Must fix (blocks):**

1. HIGH-001 — tighten the bundle signature before `prune` can delete
2. MEDIUM-001 through MEDIUM-007

**Should fix:** LOW-001 through LOW-010.

---

## Notes on Method

Every Python finding was reproduced by execution before being written down —
HIGH-001 by destroying two real directories in a sandbox, MEDIUM-002 by
instrumenting `os.walk`, MEDIUM-004 by pruning a copy of a real bundle and
diffing its `BUNDLE.md` against the original.

MEDIUM-004 is the finding the primary agent missed and `pe-governance` caught
across a file boundary it was not asked to review. Its more serious half — the
frozen false claim in every pruned bundle on disk — lives in the Python, outside
that agent's scope.

The recurring theme is that the v0.3.0 review established two invariants — *the
title is untrusted* and *the scribe must not misrepresent the video* — and this
diff added new consumers of both without carrying either forward.

---

Generated with Claude Code
