# Code Review: watchwith-rename-and-janitor

**Verdict:** 🚫 BLOCKED — round 2; see the latest round below

| | |
| - | - |
| **Branch** | `main` (commit range `bb221b1..HEAD`) |
| **Reviewer** | @Cali LaFollett |
| **Review Round** | 1 |
| **Reviewed SHA** | `3573d376e1dd0d62a5f07d4c6bd5e0a4d76554a3` |
| **Title** | screenscribe → watchwith rename, plugin-janitor, plugin READMEs |
| **Files Changed** | 30 |
| **Lines Changed** | +1768 / -525 |
| **Date** | 2026-09-08 |

---

## Summary

Fourteen commits that had never been reviewed: the `--frames-only` removal, six
SKILL.md revisions, an entirely new `plugin-janitor` plugin, the rename of
`screenscribe` to `watchwith`, and seven plugin READMEs.

`pe-governance` reviewed the two SKILL.md files. Python and the manifests have
no matching PE, so the primary ran the generic three-pass on those directly.
READMEs were excluded from `pe-governance` by dispatch — their audience is a
human reading GitHub, and applying audience-is-the-model token discipline to
them would be a false-positive class.

One HIGH was found **independently by both reviewers**, by execution rather than
reading: the primary arrived from hostile registry shapes, `pe-governance` from
a SKILL.md safety claim that the code does not honour. Same defect, same line.

The rename itself is clean. Both `require_frames` call sites were updated after
its signature changed, surviving `--frames-only` references are historical
comments, `prune --help` reflects `$WATCHWITH_BUNDLES`, `bootstrap` exits 0, and
239 + 31 tests pass on both the venv and system python3.

---

## Findings Overview

| Severity | In Scope | Out of Scope |
| -------- | -------- | ------------ |
| 🔴 CRITICAL | 0 | 0 |
| 🟠 HIGH | 1 | 0 |
| 🟡 MEDIUM | 6 | 0 |
| 🟢 LOW | 4 | 0 |
| ℹ️ INFO | 1 | 0 |

---

## In Scope Findings

### 🟠 HIGH-001 — A registry that parses but names no installs deletes the entire cache

**Expert:** Primary + PE-Governance (independently reproduced) ·
**Location:** `plugins/plugin-janitor/skills/plugin-janitor/scripts/janitor.py:93-120`,
claim at `plugins/plugin-janitor/skills/plugin-janitor/SKILL.md:43-45`

`installed()` aborts on `OSError`, `ValueError`, and non-dict. It does not abort
when the file parses into a dict whose *shape* it does not understand:

```python
for key, entries in (data.get("plugins") or {}).items():   # null -> {}
    for entry in entries or []:                            # dict/str -> skipped
        if not isinstance(entry, dict):
            continue
```

`live` comes back empty, every version is therefore stale, `emptied()` sweeps
every directory above them, and `--yes` removes the lot.

**Reproduced** against the real schema
(`{"version":…, "plugins": {key: [{scope, installPath, …}]}}`):

| Registry | Result |
| - | - |
| `plugins: null` | 3 versions → 0, **exit 0** |
| entries became an object | 3 versions → 0, **exit 0** |
| entry is a bare string | 3 versions → 0, **exit 0** |
| `{"plugins": {}}` | 3 versions → 0, **exit 0** |

The realistic trigger is Claude Code changing the registry schema — the file
carries a top-level `version` field, so it is expected to. This codebase has
been bitten by exactly this class once already: the v0.7.x `prune` HIGH, where
accepting any directory containing `meta.json` turned `prune --yes` into
`rm -rf`.

Two aggravating factors. SKILL.md states the rationale the code does not
implement — *"without it every version looks unreachable"* — so the governance
file describes a narrower blast radius than the tool has. And the final
self-check is vacuous precisely when the bug fires: `live` is empty, so `gone`
is empty, so it prints `verified: 0/0 installs intact` and exits 0.

**Recommendation:** validate the shape, then refuse the ambiguous case. Both
halves were prototyped and verified — all four scenarios abort with the cache
intact, and all 31 existing tests still pass unchanged.

```python
plugins = data.get("plugins")
if not isinstance(plugins, dict):
    sys.exit(f"{root / REGISTRY} has no 'plugins' object — refusing to guess")
for key, entries in plugins.items():
    if not isinstance(entries, list):
        sys.exit(f"{root / REGISTRY}: {key!r} is not a list of installs — refusing to guess")
    for entry in entries:
        if not isinstance(entry, dict):
            sys.exit(f"{root / REGISTRY}: {key!r} holds a non-object entry — refusing to guess")
```

and in `main_with`, after `every = versions(cache)`:

```python
if every and not live:
    sys.exit(f"{root / REGISTRY} lists no installs, but {cache} holds {len(every)} versions.\n"
             f"  every one looks unreachable, which is what a registry this tool cannot read\n"
             f"  also looks like — refusing to delete the whole cache on that basis")
```

A user who genuinely uninstalled everything and still wants the sweep needs an
escape hatch. `pe-governance`'s position, which the primary adopts: give it its
own flag, never a widening of `--yes`, gated so `--json` and the dry run still
report. Then widen the SKILL.md sentence to "missing, unparseable, or empty",
and add a test asserting `{"plugins": {}}` aborts with the cache intact.

---

### 🟡 MEDIUM-001 — `_holds_only` is vacuously true, and contradicts two SKILL.md claims

**Expert:** Primary + PE-Governance (merged — one root cause, two manifestations) ·
**Location:** `janitor.py:177-186`, claims at `SKILL.md:47-49` and `SKILL.md:53-59`

`_holds_only` is `all(kid in doomed for kid in path.iterdir())`, which is
vacuously `True` for a directory that is already empty. Two consequences, both
reproduced:

1. SKILL.md says *"A `<plugin>` or `<marketplace>` directory **left empty by
   that sweep** goes too"*. Directories that no sweep emptied go too. The
   `emptied()` docstring says so, `test_an_already_empty_directory_is_swept`
   asserts it, and 5a092e1's commit message says it — the only place it did not
   land is the governance file that commit was amending.
2. A registered-but-missing plugin's empty directory is deleted while the same
   run prints *"registered but missing … janitor does not touch these"*.
   Reproduced: a dangling `ghost@mk` entry, and `mk/ghost` removed in the run
   that reported it as untouched.

Nothing recoverable is lost — the directories are empty. The defect is a delete
tool whose output contradicts itself inside one run.

**Recommendation:** amend the sentence to *"a directory that the sweep empties —
or that was already empty — goes too"*, and either exclude the directories of
dangling installs from the sweep or narrow the "does not touch these" claim to
the registry entry it actually means.

---

### 🟡 MEDIUM-002 — `index --json` is documented as emitting two fields that do not exist

**Expert:** PE-Governance (confirmed by primary execution) ·
**Location:** `plugins/watchwith/skills/watchwith/SKILL.md:334`

Documented as `# adds url, pruned, reclaimable, path`. **Measured** on the live
library, `index --json` emits exactly:

```
bytes, channel, cues, duration, frames, id, last_used, path, title, url
```

`pruned` and `reclaimable` do not exist anywhere in `cmd_index`. `reclaimable`
*is* a real key in `janitor.py`'s `--json`, which is the likely source of the
carry-across; `pruned` is a survivor of the `--frames-only` era removed in
0.7.0. The real delta is also under-stated — `channel`, `duration`, `bytes` and
`last_used` go unmentioned.

Same class as 0.3.0's MEDIUM-004, and the expensive kind: a model piping
`index --json` for a `reclaimable` figure gets `None`, with no signal that the
SKILL was wrong rather than the library empty.

**Recommendation:** `# adds channel, url, duration, bytes, last_used, path`.

---

### 🟡 MEDIUM-003 — Stage 4 branch 2 swallows the page question, reintroducing the defect 395dee9 fixed

**Expert:** PE-Governance (confirmed by primary against git history) ·
**Location:** `plugins/watchwith/skills/watchwith/SKILL.md:233-249`

`395dee9` diagnosed shape and page as independent decisions and replaced the
conflating branch with two accumulators, plus the sentence that justified them:
*"Two independent decisions … Naming one does not answer the other."*

`bad0352` deleted both accumulators **and** that sentence, collapsing to a
single predicate:

```
elif they answered AFTER the scribe existed:  honour it, ask nothing
```

A post-scribe *"now write me notes"* answers the shape, says nothing about a
page, matches branch 2, and the page question never fires — verbatim the
failure `395dee9` exists to prevent, and a regression against a capability the
user asked for by name.

Exhaustiveness and reachability are both fine: the block terminates in `else`
and all three branches are reachable. The defect is branch 2 over-capturing,
which neither property surfaces.

**Recommendation:**

```
if the user asked a question, not for an artifact:  answer inline, ask nothing
open = []
if shape not answered AFTER the scribe existed:  open += "what this becomes"
if page not answered AFTER the scribe existed:   open += "a page as well"
if a page is wanted and no span was named:       open += "which span"
if open:  AskUserQuestion — one call, those rows only, before writing anything
```

---

### 🟡 MEDIUM-004 — "the scribe" has two referents, and the wrong one inverts stage 4's gate

**Expert:** PE-Governance · **Location:** `SKILL.md:161, 230, 235, 336`

At `:230` and `:235` "the scribe" means the stage-3 notes. At `:161` and `:336`
"every scribe" means the bundles in the library. Stage 4's gate is
*"an instruction given before the scribe existed was a guess"* — read with the
Library's meaning, the scribe exists the moment `build` finishes, so **every**
post-build instruction counts as an answer and the gate collapses to
always-honour.

This is 0.3.0's LOW-005 returning with a behavioural consequence attached. The
rename was supposed to free the word: with the plugin no longer called
`screenscribe`, "scribe" is available to mean exactly one thing.

**Recommendation:** keep "the scribe" for the stage-3 notes only; the library
holds *bundles*.

---

### 🟡 MEDIUM-005 — The spec quality gate and the universal `Watch:` rule are stranded inside the page subsection

**Expert:** PE-Governance (confirmed by primary) ·
**Location:** `SKILL.md:308-326`, under `### A page to look at`

The `acceptance_criteria` / `non_goals` gate and *"Every claim traced to the
video carries a `Watch:` line"* sit under a subsection about shareable HTML
pages. Neither is about pages: the first governs **specs**, the second governs
**every artifact**. A model that skips the subsection because no page was
wanted skips the spec quality bar and the citation rule with it.

**Recommendation:** lift both out of `### A page to look at` to stage 4 top
level, above the artifact table.

---

### 🟡 MEDIUM-006 — janitor's documented invocation fails; the repo has two answers to script resolution and ships the fragile one

**Expert:** PE-Governance, **re-aimed by primary after measurement** ·
**Location:** `plugins/plugin-janitor/skills/plugin-janitor/SKILL.md:19`

`pe-governance` raised this as watchwith reimplementing `$CLAUDE_PLUGIN_ROOT`
in ~35 lines of Python. **Measurement inverts it.** `$CLAUDE_PLUGIN_ROOT` is
unset in the Bash calls a skill's commands actually execute through:

```
janitor  JAN="$CLAUDE_PLUGIN_ROOT/skills/..."  ->  '/skills/plugin-janitor/scripts/janitor.py'
                                                   No such file or directory
watchwith  39-line resolver                    ->  /Users/…/watchwith/1.0.1/skills/watchwith/scripts/watchwith.py
```

janitor was run successfully three times during this session only because the
operator resolved the absolute path by hand instead of following SKILL.md. The
documented invocation has never been exercised. `code-reviewer`'s own SKILL.md
already records the constraint: the variable is reliably available to the skill
orchestrator, and *not* below it.

The inconsistency is real, but the correct resolution is the reverse of the one
proposed: janitor should adopt watchwith's `installed_plugins.json` resolver,
not watchwith drop it.

**Recommendation:** replace janitor's one-liner with the proven resolver, or at
minimum add the `find ~/.claude/skills` fallback and a guard that fails loudly
when the path does not resolve.

---

## LOW / INFO (awareness only — do not block)

| ID | Expert | Finding |
| - | - | - |
| LOW-001 | Primary | A refused version removal leaves the printed plan over-promising: the empty directories it listed never go, reconciled only by an adjacent `! skipped` line |
| LOW-002 | PE-Gov | `SKILL.md:242` "the rows further down" now passes over the Span table before reaching the Artifact/Shape table it means |
| LOW-003 | PE-Gov | `SKILL.md:161,163` bare `search` / `window` in the stage 2 table, missing the `"$PY" "$SC"` prefix every other invocation carries |
| LOW-004 | PE-Gov | janitor `SKILL.md:18-32` documents `--yes` and `--json` twice; only `--root` is unique to the table |
| INFO-001 | Primary | A stale `$SCREENSCRIBE_BUNDLES` export is now silently ignored, so a shell that still exports it builds into `~/.watchwith/bundles` without comment. Deliberate per the no-fallback decision, and correct for a single operator who has already migrated |

---

## Action Items

**Must Fix (blocks merge)**

1. HIGH-001 — validate the registry shape and refuse the zero-installs case, with a test

**Should Fix**

2. MEDIUM-003 — restore the two accumulators; this defeats a requested capability
3. MEDIUM-006 — janitor's documented command does not run
4. MEDIUM-002 — correct the `index --json` field list
5. MEDIUM-005 — lift the spec gate and `Watch:` rule out of the page subsection
6. MEDIUM-001 — make the two SKILL.md claims match the sweep
7. MEDIUM-004 — one referent for "the scribe"

---

## Notes on Method

The HIGH was found twice, independently, by two reviewers approaching from
opposite directions — one from hostile registry shapes, one from a governance
claim that the code failed to honour. Neither found it by reading.

Phase 5 changed one finding materially. MEDIUM-006 arrived asserting that
watchwith's hand-rolled resolver was redundant; measuring `$CLAUDE_PLUGIN_ROOT`
showed it unset, which inverted the finding onto janitor. A relayed finding
would have shipped the wrong recommendation and broken the working resolver.

The remediation for HIGH-001 was prototyped and executed before being written
down: four wipe scenarios abort with the cache intact, 31 existing tests
unchanged and passing.

---

## Review Round 2

**Verdict:** 🚫 BLOCKED

| | |
| - | - |
| **Reviewed SHA** | `19df02d` |
| **Round** | 2 |
| **Date** | 2026-09-08 |

Round 2 existed to confirm round 1's fixes. It found that one of them was
incomplete and that two of them introduced new defects — which is the argument
for round 2 existing.

### Discharge of round 1

| Finding | Status |
| - | - |
| HIGH-001 | **PARTIAL** — see R2-HIGH-001 |
| MEDIUM-001, 002, 004, 005, 006 | DISCHARGED |
| MEDIUM-003 | PARTIAL — see R2-MEDIUM-001 / 002 |
| LOW-002, LOW-003 | DISCHARGED |
| LOW-004 | PARTIAL — `--yes` still documented twice |

MEDIUM-006 was re-measured rather than assumed: with `CLAUDE_PLUGIN_ROOT` unset,
the rewritten `## Run it` block was executed verbatim and resolved.

### 🟠 R2-HIGH-001 — The round-1 guard tested the wrong invariant

**Expert:** Primary + PE-Governance (independently, again) ·
**Location:** `janitor.py:342` @ `19df02d`

Round 1 refused when the registry named **no** installs. A registry naming
sixteen, whose paths all point at a home directory that has since been renamed,
parses fine, passes the new shape validation, and is equally useless as a
reachability oracle.

**Reproduced.** Three versions on disk, a registry whose `installPath`s all
point at an old location: `versions 3 -> 0`, **exit 0**,
`verified: 0/3 installs intact`. The same hole swallowed a relative
`installPath` and an unexpanded `~`.

This is a moved cache, a restored backup, a renamed account, or a changed path
scheme — not a hypothetical. The tool printed "registered but missing" for every
plugin it had, which is a screaming red flag, and then deleted the cache anyway.

**Fixed:** the test is now whether *any* install resolves to a directory that
exists — `reachable = live - {resolved for dangling}`. Verified across eight
path forms including trailing slash, `..` segments, tilde, relative, and a live
entry beside a dangling one (which must **not** refuse).

### 🟡 R2-MEDIUM-001 — Restoring stage 4's accumulators broke the guard above them

`if the user asked a question: answer inline, ask nothing` became a bare `if`
with the accumulator following unconditionally, so a question-asker accumulated
both rows and `AskUserQuestion` fired one line beneath the words "ask nothing".
Fixed with an `else`.

### 🟡 R2-MEDIUM-002 — Consolidating the span question made it unreachable

Whether a page is wanted is unknown while the page question is still open, so
`if a page is wanted: open += "which span"` never fires on the path that needs
it: user says nothing, answers both rows, picks a published Artifact, and is
never asked for a span. The round-1 text asked it in a follow-up call, which
folding everything into one call destroyed. Restored as a second call.

### 🟡 R2-MEDIUM-003 — The registry table said "abort" for two different behaviours

**Measured:** rows 1-3 abort on every path (`exit 1` for dry run, `--json` and
`--yes`); row 4 aborts only on `--yes` and still prints the report. Row 4 now
says so.

### LOW / INFO

| ID | Finding |
| - | - |
| R2-LOW-001 | A benign schema addition aborted with a bare "refusing to guess", reading as a registry bug rather than a tool a version behind the format |
| R2-LOW-002 | "the notes" collided with the `summary / notes` artifact and `docs/notes/` in the same stage; the gate now names stage 3 |
| R2-LOW-003 | Two justification paragraphs whose removal changed no behaviour, one duplicating a comment in `janitor.py` |
| R2-LOW-004 | janitor's resolver lacked watchwith's `find ~/.claude/skills` fallback |
| R2-INFO-001 | `--allow-empty-registry` renamed `--allow-unreachable-registry`; the condition stopped being emptiness, and the flag had reached no one at 0.1.4 |

### Notes on Method

The HIGH was found twice again, independently, on a fix that had already
shipped. Both reviewers had read the round-1 remediation and called it
plausible; both found the hole only by running it.

39 -> 41 janitor tests.

Generated with Claude Code
