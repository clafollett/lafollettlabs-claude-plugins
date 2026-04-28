---
name: ux-designer
description: UX design harness — structured discovery, prototype generation, visual iteration via Playwright, Storybook support, parallel variations via worktrees.
---

# UX Designer

Design harness for Claude Code. Phases: Discovery → Brief & Milestones → Build & Converge.

The skill (parent agent) is a **collector + variation manager**. It runs discovery, writes the master brief and per-variation briefs, dispatches `design-engineer` sub-agents to build in isolated worktrees, then converges screenshots and merges the chosen variation.

**The parent does NOT build code.** Every variation — including `variation_count == 1` — is dispatched to a `design-engineer` sub-agent. Build mechanics live in `agents/design-engineer.md`.

## When to Use

- User asks to design a UI, landing page, dashboard, app screen, or visual interface
- User asks to prototype, wireframe, or mock up something
- User says "make this look good" or asks for design help on existing UI
- User provides a Figma reference, screenshot, or design system to replicate
- User wants to explore multiple visual variations
- User asks to build/update Storybook stories
- User wants animations, scroll effects, or immersive interactions
- User mentions "Claude Design" or wants that workflow

## Core Philosophy

1. **Code is the deliverable** — every artifact is shippable HTML/React/Vue/Svelte/Astro.
2. **Discovery before generation** — fill gaps before building. Never guess direction.
3. **Visual verification** — iterate on reality (screenshots), not assumptions.
4. **Parallel exploration** — worktrees + sub-agents try multiple directions simultaneously.

## AskUserQuestion

Every multiple-choice prompt uses the `AskUserQuestion` tool. Plain markdown is the fallback.

**Load before first use** (deferred tool):

```
ToolSearch({ query: "select:AskUserQuestion", max_results: 1 })
```

**Constraints:**
- 1-4 questions per call; 2-4 options per question
- Do NOT add an "Other" option — the tool adds it automatically
- Each option: `label` (1-5 words) + `description`
- Append `(Recommended)` to label for top-pick when one direction is best
- `multiSelect: true` only for genuinely non-exclusive prompts

**Fallback:** if `ToolSearch` doesn't return `AskUserQuestion`, use markdown blockquote prompts and tell the user once: *"AskUserQuestion isn't available — I'll use text prompts instead."*

---

## Canonical Paths

`.design/` is a sibling of the project's `package.json`. For monorepos with the design target in a subdir (e.g., `web/`), `.design/` lives in that subdir, not the repo root.

```
.design/
├── brief.md                              # Master design brief — shared baseline.
│                                         #   Written in Phase 2. ONE master per run.
│                                         #   Variations reference it; never copy from it.
├── briefs/                               # Per-variation briefs (main repo only)
│   └── brief-variation-{slug}.md         #   one file per variation, named by slug
│                                         #   ALWAYS written, even when variation_count == 1
├── shipped-direction.md                  # Post-merge — master brief + winning slug (optional)
└── screenshots/
    └── variation-{slug}/
        └── {page}-{viewport}.png         # e.g., variation-dark-neon/home-desktop.png
```

**Conventions:**
- `{viewport}` is `desktop` (1440×900) or `mobile` (375×812)
- `{slug}` is kebab-case from the variation directive (`dark-neon`, `trust-clarity`)
- `{page}` is route minus the slash (`home` for `/`, `about`, etc.)
- All lowercase, dash-separated

**Two-file contract.** The master brief is the shared baseline. Each variation brief carries **Overrides** (replace master sections by name) and **Extensions** (additive details master doesn't cover). The sub-agent reads BOTH and applies override semantics.

**Both briefs live in the MAIN REPO, not worktrees.** Worktrees are fresh checkouts without uncommitted files — sub-agents must read briefs via absolute paths (e.g., `/Users/foo/myproject/.design/brief.md`).

**Git is the archive.** Each variation lives on `design/variation-{slug}` with full milestone commit history. List prior runs: `git branch --list 'design/variation-*'`.

---

## Phase 1 — Discovery

### Step 1: Reference Material Intake

```
AskUserQuestion({
  questions: [{
    question: "Do you have any reference material to share before we start?",
    header: "References",
    multiSelect: true,
    options: [
      { label: "Epics or stories",         description: "Requirements docs, GitHub Issues, PRDs" },
      { label: "Wireframes or screenshots", description: "Mockups or reference site captures" },
      { label: "Figma or design system",    description: "Existing design files or token docs" },
      { label: "Brand assets",              description: "Logos, colors, fonts, guidelines" }
    ]
  }]
})
```

```
if response includes epics/stories:
  extract `what` + `why` → drives layout, content hierarchy, feature sections

if response.Other mentions Storybook OR `.storybook/` exists:
  storybook_signal = true   # passed to engineer in brief
```

### Step 2: Project Detection

```bash
# Framework configs
ls package.json tsconfig.json tailwind.config.* next.config.* nuxt.config.* vite.config.* astro.config.* svelte.config.* 2>/dev/null

# Component libraries + design tooling
grep -l "shadcn\|@radix\|@heroui\|aceternity\|framer-motion\|storybook" package.json 2>/dev/null

# Storybook
find . -maxdepth 2 -name ".storybook" -type d 2>/dev/null
find . \( -name "*.stories.tsx" -o -name "*.stories.jsx" -o -name "*.stories.ts" -o -name "*.stories.js" -o -name "*.stories.svelte" -o -name "*.stories.vue" \) -not -path "./node_modules/*" 2>/dev/null | head -5

# Design tokens
find src app . -maxdepth 3 \( -name "globals.css" -o -name "theme.css" -o -name "tokens.css" -o -name "*.module.css" \) -not -path "*/node_modules/*" 2>/dev/null | head -10

# Env-gated UI states
grep -rE "import\.meta\.env\.PUBLIC_|process\.env\.NEXT_PUBLIC_|process\.env\.VITE_" src app 2>/dev/null | grep -iE "enabled|disabled|flag|gate" | head -10
grep -rE "(PUBLIC_|VITE_|NEXT_PUBLIC_)[A-Z_]+_(ENABLED|DISABLED|FLAG)" package.json 2>/dev/null | head -5
```

```
if existing_design_system OR storybook detected:
  load references/design-system-template.md
  extract tokens → record in master brief

if env-gated UI states detected:
  list flags found
  ask user for dev-time defaults OR document in brief
  pass env vars to sub-agents in variation brief Runtime Config
```

### Step 3: Gap Analysis + Questioning

Dimensions: Purpose & Audience, Visual Direction, Layout & Structure, Content, Interactions, Technical Stack, Design System.

```
if dimensions_covered_in_prompt >= 5:
  skip questioning → Phase 2

else:
  load references/question-library.md
  N = 1
  while gaps remain:
    select up to 4 questions covering the most uncovered dimensions
    AskUserQuestion(those questions)
    re-run gap analysis
    if N >= 2:
      ask user: "Continue with N more questions on [dims], or use sensible defaults?"
      if user picks defaults: break
    N += 1
  fill remaining gaps with defaults
```

Question library entries map directly to AskUserQuestion fields: `Header:` → `header`, blockquote → `question`, bolded options → `label`, em-dash text → `description`.

---

## Phase 2 — Brief & Milestones

### Step 1: Choose Design Approach

```
AskUserQuestion({
  questions: [{
    question: "Should I build one focused design, or explore multiple variations in parallel?",
    header: "Approach",
    multiSelect: false,
    options: [
      { label: "Single direction (Recommended)", description: "One cohesive design — fastest path, deepest iteration" },
      { label: "2 variations", description: "A/B comparison — focused, easy to decide" },
      { label: "3 variations", description: "Broader exploration — more options" },
      { label: "4 variations", description: "Maximum breadth — takes longer, more context" }
    ]
  }]
})
```

Map label → integer; persist the integer:

```
"Single direction (Recommended)" → variation_count = 1
"2 variations" → 2
"3 variations" → 3
"4 variations" → 4
"Other" + numeric input → clamp to [1, 4]
```

### Step 2: Framework Selection

```
if framework detected in project:
  inform user: "I see [framework]. I'll build with that unless you want different."
else:
  AskUserQuestion(Q6.1 from question-library.md)
  default top 4: Vue + Vite, Nuxt, Vanilla HTML + Tailwind, Astro
  adjust top 4 based on brief (content-heavy → lead Astro; dashboard → SPA-first)
  "Other" picks: Next.js, React + Vite, Svelte/SvelteKit, Solid

framework → recorded in master brief Technical Stack
```

### Step 3: Generate Master Brief

Compile discovery answers into `.design/brief.md` using `assets/design-brief-template.md`. Master brief is the shared baseline — variation briefs reference it, never copy.

Required sections: Overview (project, goal, audience), Visual Direction (baseline), Layout, Content Direction, Interactions (baseline), Technical Stack (framework, component libraries, storybook flag, env vars, project subdir for monorepos), Source Material, Constraints.

Commit: `git add .design/brief.md && git commit -m "design: master brief"`.

### Step 4: Plan Milestones

Present milestones before building. When `variation_count > 1`, frame as "(per variation)" — each sub-agent runs them independently in its worktree.

```
1. Project Setup — initialize framework, install dependencies
2. Design System — color tokens, typography, spacing
3. Layout & Structure — page skeleton, section ordering, responsive grid
4. Hero Section — primary visual + CTA
5. Content Sections — features, testimonials, pricing, etc.
6. Navigation & Footer
7. Visual Polish — colors, typography, spacing refinement
8. Interactions & Animation — scroll, hover, transitions
9. Responsive Verification — mobile/tablet/desktop breakpoints
10. Storybook Stories — component catalog (if storybook_active)
```

Ask user to confirm or adjust before continuing.

---

## Phase 3 — Build & Converge

### Step 1: Visual Tools Detection

```
playwright_mcp_available = any registered tool name matches "mcp__plugin_playwright_playwright__browser_*"
                           OR "mcp__playwright__browser_*"
storybook_available      = (package.json has "storybook" script) AND (.storybook/ exists)
```

`playwright_mcp_available` is for the **parent's** convergence capture. Sub-agents do NOT use Playwright MCP — they use raw Node `@playwright/test` (single shared MCP browser collides under parallel access). Engineer's contract enforces this.

### Step 2: Slug Convention

Each variation has a **slug** — kebab-case semantic ID derived from its directive. Slug is canonical; letter ordinal (A, B, C, D) is display-only.

```
canonical: slug   (e.g., "dark-neon")
            → filesystem: .design/briefs/brief-variation-dark-neon.md
                          .design/screenshots/variation-dark-neon/
            → branch:     design/variation-dark-neon
            → agent name: design-variation-dark-neon
            → commits:    design(variation-dark-neon): {milestone}

display: letter ordinal (A|B|C|D)
            → derived by enumeration position (first slug = A, …)
            → NEVER stored as source of truth
```

**Slug derivation rules:**
- Lowercase, kebab-case (`dark-neon`, not `DarkNeon`)
- 1-3 words, max ~24 chars
- Alphanumeric + hyphens only
- Unique within run (collision → append `-2`, `-3`)

**Examples:**
- `"Dark mode with neon accents, immersive animations"` → `dark-neon`
- `"Light and airy, minimal whitespace"` → `light-minimal`
- `"Trust-and-clarity, restrained corporate"` → `trust-clarity`

### Step 3: Define Variation Directives + Write Briefs

**3a. Define directives + slugs.** For each variation (1 to N), define a direction (visual, tonal, or any axis the variation pivots on) and propose a slug from its core noun phrase. Show the table to the user:

| Slug (canonical) | Letter (display) | Directive |
| --- | --- | --- |
| `dark-neon` | A | "Dark mode with neon accents, immersive animations, edgy/futuristic tone" |
| `light-minimal` | B | "Light and airy, minimal with lots of whitespace, calm/professional tone" |
| `playful-bold` | C | "Bold and colorful, playful with rounded shapes, irreverent indie tone" |

Let the user rename slugs. For `variation_count == 1`, still pick one slug.

**3b. Write per-variation briefs** at `{project_root_abs}/.design/briefs/brief-variation-{slug}.md`. ALWAYS written, even when `variation_count == 1` — uniform contract.

The variation brief does NOT duplicate master content. Sub-agent reads both files and applies override semantics (Overrides replace; Extensions add).

When writing each variation brief, **load relevant references and embed concrete patterns into Extensions**:

```
load references/layout-patterns.md   if variation has unusual layout philosophy
load references/animation-patterns.md if variation has interactions/scroll/hover
load references/design-system-template.md if variation has bespoke tokens

→ embed concrete code snippets (e.g., specific color palette, animation CSS, layout
  HTML) directly into the variation brief Extensions sections. Engineer does NOT
  load references; everything it needs is in the two briefs.
```

**Variation brief schema:**

```markdown
# Variation: {Display Name}
<!-- slug: {slug} -->
<!-- letter: {A|B|C|D} -->

## Variation Direction
{Multi-paragraph rich description — mood, tone, content angle, layout philosophy.
The HEART of this variation.}

## Overrides
Sections here REPLACE the same-named section in master. Omit a section to inherit.

### Audience           {or omit}
### Tone & Voice       {or omit}
### Visual Direction   {typically present}
### Layout Philosophy  {or omit}
### Content Direction  {or omit}
### Interactions       {or omit}

## Extensions
Additive details master doesn't cover. Treated as on top of master.

### Color Palette Specifics    {hex values, gradient stops}
### Typography Pairing         {specific font choices}
### Animation Treatment        {specific scroll/hover behaviors, with CSS snippets}
### Component Treatments       {button shape/elevation/states}
### Layout Snippets            {specific HTML/Tailwind patterns from layout-patterns.md}

## Differentiator
{1-2 sentence what-makes-this-distinct — used by parent at convergence}

## Runtime Config
- Dev server port: {assigned by enumeration: 4321, 4322, 4323, 4324}
- Feature flags / env vars: {PUBLIC_*/VITE_*/NEXT_PUBLIC_* discovered in Phase 1 Step 2}
- Project subdirectory: {if monorepo, e.g., "web/"; else omit}
```

Show the user the brief paths so they can preview/edit before dispatch.

### Step 4: Resolve Paths + Dispatch

```
if env CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS == "1":
  TeamCreate(team_name: "design-exploration", description: "Parallel design variations")
  use_teams = true
else:
  warn: "Agent Teams not enabled — using ad-hoc Agent + name + SendMessage."
  use_teams = false
```

**Resolve absolute brief paths.** Worktrees don't include uncommitted files — sub-agents read briefs via absolute paths in the main repo.

```bash
git_toplevel = `git rev-parse --show-toplevel`

# Find brief.md (Phase 2 Step 3 wrote it). Bounded depth, skip node_modules/worktrees.
brief_master_path = `find "$git_toplevel" -maxdepth 4 -path "*/.design/brief.md" \
                       -not -path "*/node_modules/*" -not -path "*/.git/*" 2>/dev/null | head -1`

if [ -z "$brief_master_path" ]; then
  abort("brief.md not found — Phase 2 Step 3 must run before dispatch")
fi

project_root_abs = `dirname $(dirname "$brief_master_path")`        # strips /.design/brief.md
project_subdir   = "${project_root_abs#$git_toplevel/}"             # bash strips prefix; portable
[ "$project_subdir" = "$project_root_abs" ] && project_subdir="."   # "." for single-project, "web" for monorepo

for slug in variation_slugs:
  brief_variation_abs = "{project_root_abs}/.design/briefs/brief-variation-{slug}.md"
  test -f "{brief_variation_abs}" || abort("missing variation brief at {brief_variation_abs}")
test -f "{brief_master_path}" || abort("missing master brief at {brief_master_path}")
```

**Spawn — single message, multiple Agent calls (parallel):**

```
for slug in variation_slugs:
  Agent(
    subagent_type: "ux-designer:design-engineer",
    name: "design-variation-{slug}",
    team_name: "design-exploration",          # ONLY if use_teams
    isolation: "worktree",                    # harness creates worktree, returns branch + path
    run_in_background: true,
    prompt: <dispatch prompt below>
  )
```

Do NOT create worktrees manually — `isolation: "worktree"` handles that.

**Dispatch prompt** (the agent's system prompt at `agents/design-engineer.md` carries the full contract):

```
You are design-engineer. Your inputs:
- Master brief:    {brief_master_path}
- Variation brief: {brief_variation_abs}
- Worktree:        <your CWD — set by isolation: "worktree">
- Project subdir:  {project_subdir if not "." else omit}
- Slug:            {slug}

Read both briefs. Apply variation Overrides on top of master inheritance; treat
Extensions as additive. Execute milestones. Report back per your standard format.
```

**Mid-flight updates** (Agent Teams is reliable; ad-hoc is best-effort):

```
SendMessage(to: "design-variation-{slug}", message: "<update>")
```

### Step 5: Convergence

Parent drives serially — Playwright MCP has ONE browser, so screenshots happen one variation at a time.

```
on all sub-agents complete:
  results = {worktree_path, branch_name, summary, screenshots} per slug

  # Visual capture — sub-agents typically already wrote screenshots via raw Node.
  # Only re-capture if they reported "skipped visual check" or screenshots are missing.
  if playwright_mcp_available AND screenshots_missing:
    for each slug in order:
      cd <worktree>/<project_subdir>
      npm install (if node_modules missing)
      npm run dev -- --port <unique_port> &       # background, with feature-flag env vars
      wait for server ready
      browser_resize(1440x900); browser_navigate(http://localhost:<port>)
      browser_take_screenshot(path: ".design/screenshots/variation-{slug}/{page}-desktop.png")
      browser_resize(375x812); browser_take_screenshot(path: ".design/screenshots/variation-{slug}/{page}-mobile.png")

  present side-by-side: read images from each worktree's .design/screenshots/variation-{slug}/

  if variation_count == 1:
    git checkout main
    git merge design/variation-{slug}
    # done — continue iterating on merged result

  elif trial_mode (user wants external review, no commitment yet):
    keep all worktrees + dev servers running
    hand off URLs + screenshots
    skip merge / cleanup

  else:
    winner_slug = AskUserQuestion("Which variation should we ship?")
                  # options use display labels (e.g., "A: Dark Neon"); persist the slug
    git checkout main
    git merge design/variation-{winner_slug}
    # losers: keep branches as archive (default) OR git branch -D design/variation-{loser}

    git worktree list                                   # verify
    git worktree remove {path}                          # cleanup any remaining

    if use_teams:
      for each teammate: SendMessage(to: name, message: {type: "shutdown_request"})
      TeamDelete()
```

For explicit worktree-path control (e.g., long-running comparison branches), create worktrees manually with `git worktree add` and dispatch sub-agents WITHOUT `isolation: "worktree"`. You then own cleanup.

---

## References (load on demand — parent only)

The parent loads references when **writing variation briefs** (Phase 3 Step 3b) — relevant snippets get embedded into variation brief Extensions. The engineer does NOT load references; everything it needs is in the two briefs.

| Reference | When to Load |
|-----------|--------------|
| `references/question-library.md`        | Phase 1 Step 3 — picking discovery questions |
| `references/layout-patterns.md`         | Phase 3 Step 3b — variation has unusual layout |
| `references/animation-patterns.md`      | Phase 3 Step 3b — variation has interactions |
| `references/design-system-template.md`  | Phase 1 Step 2 / Phase 3 Step 3b — extracting or building tokens |
| `references/framework-starters.md`      | Phase 2 Step 2 — initializing a fresh project |
