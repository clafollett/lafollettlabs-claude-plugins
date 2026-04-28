---
name: ux-designer
description: UX design harness — structured discovery, prototype generation, visual iteration via Playwright, Storybook support, parallel variations via worktrees.
---

# UX Designer

A design harness for Claude Code that replicates and improves upon Claude Design's workflow. Structured discovery → milestone planning → design generation → visual iteration → parallel exploration. Everything it produces is shippable code, not throwaway prototypes.

## When to Use This Skill

- User asks to design a UI, landing page, dashboard, app screen, or any visual interface
- User asks to prototype, wireframe, or mock up something
- User says "make this look good" or asks for design help on existing UI
- User provides a Figma reference, screenshot, or design system to replicate
- User wants to explore multiple visual variations of a design
- User asks to build or update Storybook stories for components
- User wants animations, scroll effects, or immersive UI interactions
- User mentions "Claude Design" or wants that type of workflow

## Core Philosophy

1. **Code is the deliverable** — every design artifact is shippable HTML/React/Vue/Svelte/Astro. No throwaway prototypes.
2. **Discovery before generation** — always ask clarifying questions to fill gaps. Never guess at design direction.
3. **Visual verification** — see what you built (via Playwright or Storybook). Iterate on reality, not assumptions.
4. **Parallel exploration** — use worktrees and sub-agents to try multiple directions simultaneously. Converge on the best.
5. **Component-first when appropriate** — for projects with component architecture, design at the component level via Storybook, then compose into pages.

## Asking Questions — Use AskUserQuestion

Every multiple-choice prompt in this skill (reference intake, discovery questions, framework selection, variation count) **should use the `AskUserQuestion` tool** for proper selection UI. Plain markdown blockquotes force users to type answers and degrade UX.

### Loading the tool

`AskUserQuestion` is a **deferred tool** in Claude Code — its schema is not loaded by default, so calling it directly will error. Before the first prompt in a session, load it explicitly:

```
ToolSearch({ query: "select:AskUserQuestion", max_results: 1 })
```

After ToolSearch returns the schema, `AskUserQuestion` is callable for the rest of the turn.

### Constraints

- **1-4 questions per call** — group related discovery questions together to minimize round trips
- **2-4 options per question** — every question in `references/question-library.md` is already pre-formatted to fit
- **Do NOT add an "Other / something different" option** — the tool adds "Other" automatically
- Each option needs a short `label` (1-5 words) and a `description` explaining the choice
- Include `(Recommended)` at the end of the label for your top-pick option when one direction is clearly best
- Set `multiSelect: true` only for genuinely non-exclusive questions (e.g., "which features do you want?")

### Example invocation (Phase 1 questioning, grouped round)

```
AskUserQuestion({
  questions: [
    {
      question: "What visual direction feels right?",
      header: "Visual Style",
      multiSelect: false,
      options: [
        { label: "Clean & minimal", description: "Lots of whitespace, subtle colors, understated" },
        { label: "Bold & expressive", description: "Strong colors, large typography, dynamic" },
        { label: "Dark & immersive", description: "Dark backgrounds, glowing accents, cinematic" },
        { label: "Warm & approachable", description: "Rounded shapes, soft gradients, friendly" }
      ]
    },
    {
      question: "What is the primary goal of this project?",
      header: "Goal",
      multiSelect: false,
      options: [
        { label: "Convert visitors", description: "Sign-ups, leads, purchases" },
        { label: "Showcase work", description: "Portfolio, product, brand" },
        { label: "Inform & educate", description: "Documentation, content-first" },
        { label: "Drive engagement", description: "Community, repeat visits" }
      ]
    }
  ]
})
```

### Fallback

If `ToolSearch` does not return `AskUserQuestion` (e.g., the tool is unavailable in this environment), fall back to plain markdown multi-choice prompts using the format shown later in this skill. Note this once to the user: "AskUserQuestion isn't available — I'll use text prompts instead."

---

## Canonical Paths

All design artifacts live under `.design/` (sibling of the project's `package.json` — for a monorepo with the design target in a subdir, this is `<subdir>/.design/`, not the monorepo root):

```
.design/
├── brief.md                              # Phase 2 — master design brief
├── briefs/                               # Phase 5 — per-variation briefs (main repo only)
│   ├── variation-a.md                    #   master brief + variation-A directive + runtime config
│   ├── variation-b.md
│   └── variation-c.md
├── shipped-direction.md                  # Post-merge — captures brief + winning directive (optional)
└── screenshots/
    ├── {milestone}-{viewport}.png        # Phase 4 single-agent iteration
    │   # examples: m1-hero-desktop.png, m1-hero-mobile.png, m4-pricing-desktop.png
    └── variation-{letter}/               # Phase 5 parallel exploration (one subdir per variation)
        └── {page}-{viewport}.png
        #   examples: variation-a/home-desktop.png, variation-b/contact-mobile.png
```

**Filename conventions:**
- `{viewport}` is `desktop` (1440×900) or `mobile` (375×812) — extend if you add tablet captures
- `{milestone}` is the milestone shorthand (e.g., `m1-hero`, `m4-pricing`)
- `{page}` is the route minus the slash (`home` for `/`, `about`, `how-it-works`, etc.)
- Always lowercase, dash-separated. No spaces, no caps.

**Why one canonical location:**
- Parent agent reading screenshots during Phase 5 convergence does NOT need to discover where each sub-agent put its files
- Sub-agents do NOT have to invent a path — drop them at the documented location
- `git diff`, code review, and `find` all work predictably
- `.design/` aligns with `brief.md`'s home — design artifacts cluster

**Per-variation briefs live in the MAIN REPO, not worktrees.** Phase 5 writes `.design/briefs/variation-{letter}.md` in the main repo before dispatching sub-agents. The harness creates each worktree from the current branch HEAD and does NOT include uncommitted files — so sub-agents must read their brief via the **absolute filesystem path** to the main repo (e.g., `/Users/foo/myproject/.design/briefs/variation-a.md`), not via a relative path inside their worktree. The dispatch prompt passes this absolute path explicitly.

Sub-agents in Phase 5 write **screenshots** to their own worktree's `<worktree>/.design/screenshots/variation-{letter}/`. The parent reads from each worktree's `.design/screenshots/` path during convergence.

---

## Phase 1 — Discovery

### Step 1: Reference Material Intake

Before asking design questions, ask the user if they have reference material. **Use AskUserQuestion** with `multiSelect: true` since they may have multiple types of references:

```
AskUserQuestion({
  questions: [{
    question: "Do you have any reference material to share before we start?",
    header: "References",
    multiSelect: true,
    options: [
      { label: "Epics or stories", description: "Requirements docs, GitHub Issues, PRDs" },
      { label: "Wireframes or screenshots", description: "Mockups or reference site captures" },
      { label: "Figma or design system", description: "Existing design files or token documentation" },
      { label: "Brand assets", description: "Logos, colors, fonts, guidelines" }
    ]
  }]
})
```

**On response:**

```
if response.Other mentions Storybook:
  storybook_signal = true

if response includes epics/stories:
  extract `what` + `why` → drives layout, content hierarchy, feature sections
  design must reflect what engineering is building

if user provided Storybook URL OR `.storybook/` exists:
  generation_strategy = "component_first"   # see Phase 3 Step 2
```

### Step 2: Project Detection

Scan the current project for existing patterns:

```bash
# Framework configs
ls package.json tsconfig.json tailwind.config.* next.config.* nuxt.config.* vite.config.* astro.config.* svelte.config.* 2>/dev/null

# Component libraries and design tooling
grep -l "shadcn\|@radix\|@heroui\|aceternity\|framer-motion\|storybook" package.json 2>/dev/null

# Storybook setup
find . -maxdepth 2 -name ".storybook" -type d 2>/dev/null
find . \( -name "*.stories.tsx" -o -name "*.stories.jsx" -o -name "*.stories.ts" -o -name "*.stories.js" -o -name "*.stories.svelte" -o -name "*.stories.vue" \) -not -path "./node_modules/*" 2>/dev/null | head -5

# Design tokens — check both src/ and app/ (Next.js App Router) and root
find src app . -maxdepth 3 \( -name "globals.css" -o -name "theme.css" -o -name "tokens.css" -o -name "*.module.css" \) -not -path "*/node_modules/*" 2>/dev/null | head -10

# Feature flags / env-gated UI states — pages that render differently based on env vars
grep -rE "import\.meta\.env\.PUBLIC_|process\.env\.NEXT_PUBLIC_|process\.env\.VITE_" src app 2>/dev/null | grep -iE "enabled|disabled|flag|gate" | head -10
grep -rE "(PUBLIC_|VITE_|NEXT_PUBLIC_)[A-Z_]+_(ENABLED|DISABLED|FLAG)" package.json 2>/dev/null | head -5
```

```
if existing_design_system OR storybook detected:
  load references/design-system-template.md
  extract tokens
  inform user: "I detected [framework/library/Storybook]. I'll work within your existing design system."

if env-gated UI states detected:
  list flags found (e.g., PUBLIC_CONTACT_ENABLED, VITE_FEATURE_X)
  ask user which dev-time defaults to use OR document them in the brief
  pass env vars to sub-agents in Phase 5 prompts so dev preview renders correctly
```

### Step 3: Gap Analysis

Analyze the user's prompt for completeness across these dimensions:

| Dimension | What to Assess |
|-----------|---------------|
| Purpose & Audience | Who is this for? What is the primary goal? |
| Visual Direction | Color palette, mood, style |
| Layout & Structure | Page type, hero style, section order |
| Content | Headlines, copy tone, imagery, CTAs |
| Interactions | Animations, scroll effects, hover states |
| Technical Stack | Framework, component libraries, responsive |
| Design System | Existing brand, typography, component patterns |

```
if dimensions_covered_in_prompt >= 5:
  skip questioning → proceed to Phase 2
else:
  load references/question-library.md
  select 1-2 questions per uncovered dimension
```

### Step 4: Questioning Flow

Pick questions from `references/question-library.md` based on dimensions the gap analysis flagged. Group up to 4 questions per `AskUserQuestion` call.

**Round loop:**

```
N = 1
while true:
  ask round N  (≤4 questions via AskUserQuestion)
  re-run gap analysis
  if no consequential gaps remain: break
  if N < 2: N += 1; continue          # rounds 1-2 are default, no permission needed
  ask user via AskUserQuestion:
    "Continue with N more questions on [dimensions], or use sensible defaults?"
  if user picks defaults: break
  N += 1
proceed to Phase 2
```

Goal: fill gaps, not interrogate. Stop the moment the user prefers defaults.

**Use AskUserQuestion** — every question in the library is already AskUserQuestion-ready: 2-4 distinct options each, with `Header` and `Skip if` metadata. Map them directly to AskUserQuestion fields:
- The `Header:` line → `header` field (max 12 chars)
- The blockquote question → `question` field
- The bolded option labels → `options[].label`
- The em-dash descriptions → `options[].description`

Fallback format (only if AskUserQuestion is unavailable):

```
Before I start designing, a few questions to nail the direction:

**1. Visual Style**
   a) Clean & minimal — lots of whitespace, subtle colors
   b) Bold & expressive — strong colors, large typography
   c) Warm & approachable — rounded shapes, soft gradients
   d) Dark & immersive — dark backgrounds, glowing accents
   e) Or tell me something different

**2. Primary Goal**
   a) Convert visitors to sign up / purchase
   b) Showcase a portfolio or product
   c) Provide information / documentation
   d) Build community engagement
   e) Or tell me something different

**3. Animation Level**
   a) None — fully static
   b) Subtle entrance animations on scroll
   c) Moderate scroll-triggered effects
   d) Immersive, cinematic motion
   e) Or tell me something different
```

When the round loop exits, fill any remaining gaps with sensible defaults in the design brief. The user can always redirect during iteration.

---

## Phase 2 — Design Brief & Milestones

### Step 1: Choose Design Approach

**Always ask this proactively** — single-direction vs parallel variations is a top-level branch in the flow, not a hidden option that waits for the user to use specific keywords.

Use `AskUserQuestion`:

```
AskUserQuestion({
  questions: [{
    question: "Should I build one focused design, or explore multiple variations in parallel?",
    header: "Approach",
    multiSelect: false,
    options: [
      { label: "Single direction (Recommended)", description: "One cohesive design — fastest path, deepest iteration" },
      { label: "2 variations", description: "A/B comparison — focused, easy to decide" },
      { label: "3 variations", description: "Broader exploration — more options to choose from" },
      { label: "4 variations", description: "Maximum breadth — takes longer, uses more context" }
    ]
  }]
})
```

Map the selected label to an integer `variation_count` — persist the integer, not the label string. The branch at the end of Phase 2 (and all downstream logic) compares against the integer:

| Selected label | `variation_count` |
| --- | --- |
| `Single direction (Recommended)` | `1` |
| `2 variations` | `2` |
| `3 variations` | `3` |
| `4 variations` | `4` |

If the user picks `Other` and types a number, parse it as an integer in the range 1-4 (clamp anything outside that range to the nearest valid value, or re-ask).

### Step 2: Generate Design Brief

Compile all discovery answers into a design brief. Load `assets/design-brief-template.md` for the template structure.

Persist the brief as `.design/brief.md` in the project root. This file survives session boundaries and serves as the master contract for sub-agents during parallel exploration.

### Step 3: Plan Milestones

Present milestones before generating anything. When `variation_count > 1`, frame the milestones as "(per variation)" — each sub-agent will execute them independently in its own worktree.

```
## Design Milestones

1. **Project Setup** — initialize framework, install dependencies
2. **Design System** — define or extract color tokens, typography, spacing
3. **Layout & Structure** — page skeleton, section ordering, responsive grid
4. **Hero Section** — primary visual impact area with CTA
5. **Content Sections** — features, testimonials, pricing, etc.
6. **Navigation & Footer** — header nav, footer links, mobile menu
7. **Visual Polish** — colors, typography, spacing, imagery refinement
8. **Interactions & Animation** — scroll effects, hover states, transitions
9. **Responsive Verification** — test at mobile, tablet, desktop breakpoints
10. **Storybook Stories** — component documentation and visual catalog (if applicable)
```

Ask: "Does this plan look right, or should I adjust anything before I start building?"

### Step 4: Branch on variation count

```
if variation_count == 1:
  → proceed to Phase 3 (single-build flow)
else:
  → skip Phase 3 single-build, jump to Phase 5 Step 2 (Define Variation Directives)
  # variation_count is already known, so Phase 5 Step 1 is skipped
```

---

## Phase 3 — Design Generation

### Step 1: Framework Selection

```
if framework detected in project:
  inform user: "I see [framework]. I'll build with that unless you want something different."
else:
  ask via AskUserQuestion (Q6.1 in question-library.md)
  default top 4: Vue + Vite, Nuxt, Vanilla HTML + Tailwind, Astro
  adjust top 4 based on brief (content-heavy → lead Astro; dashboard → SPA option)
  "Other" picks: Next.js, React + Vite, Svelte/SvelteKit, Solid

load references/framework-starters.md
```

Example invocation:

```
AskUserQuestion({
  questions: [{
    question: "Which framework should I build this with?",
    header: "Framework",
    multiSelect: false,
    options: [
      { label: "Vue + Vite (Recommended)", description: "Composition API, fast Vite tooling, lightweight SPA" },
      { label: "Nuxt", description: "Vue meta-framework with SSR, routing, file-based pages" },
      { label: "Vanilla HTML + Tailwind", description: "Static HTML with Tailwind CDN, no build step" },
      { label: "Astro", description: "Content-focused, ships minimal JS, plays nicely with Vue" }
    ]
  }]
})
```

### Step 2: Storybook Strategy

```
if existing_storybook detected (.storybook/ OR *.stories.* found):
  storybook_active = true
  generation_strategy = "component_first"
  read .storybook/ config
  read 1-2 existing stories (match CSF3 vs CSF2, naming, args style)
  generate new stories matching detected conventions
  every new component → co-located .stories.* file

elif user_requested_storybook:
  run: npx storybook@latest init
  storybook_active = true
  generation_strategy = "component_first"
  create design-system story (color tokens, typography, spacing)
  every new component → .stories.{tsx|js|svelte|vue}

else:
  storybook_active = false
  generation_strategy = "page_first"
  build pages directly
  if user later requests storybook → add incrementally
```

**Component-first workflow** (when `generation_strategy == "component_first"`):

```
for each component (button, card, hero, nav, ...):
  design component
  create story with variants (primary, secondary, sizes)
  visually verify in storybook
compose verified components → full pages
```

Produces higher-quality, more reusable output than page-first design.

### Step 3: Generation Strategy

Build iteratively through milestones:

1. Generate the full page skeleton first (all sections as semantic placeholders)
2. Fill each section with real content, one milestone at a time
3. If Storybook is active, create stories alongside each new component
4. After each milestone, commit with a descriptive message
5. After completing the full initial design, take a visual checkpoint (Phase 4)

Load references on demand:
- `references/layout-patterns.md` — for spatial reasoning about section structure
- `references/animation-patterns.md` — when the user wants interactions
- `references/design-system-template.md` — when extracting or building a design system

### Step 4: Component Library Integration

If the project uses ShadCN, Aceternity, HeroUI, Radix, or similar:
- Use existing component primitives rather than building from scratch
- If an MCP server is available for the component library, use it to discover and install components
- Load `references/design-system-template.md` for integration patterns

### Step 5: Git Discipline

Commit after each milestone:

```bash
git add -A && git commit -m "design: {milestone description}"
```

Branch naming convention for design work: `design/{description}` (e.g., `design/landing-page-v1`, `design/dashboard-redesign`).

---

## Phase 4 — Visual Iteration

A "visual checkpoint" means: render the current state in a browser (via Playwright or manually), evaluate it against the design brief, and either self-correct or present to the user for feedback.

### Step 1: Detect Visual Tools

```
playwright_available = any tool name starts with "mcp__playwright__browser_"
storybook_available = (package.json has "storybook" script) AND (.storybook/ exists)

if playwright_available AND storybook_available: visual_mode = "playwright + storybook"
elif playwright_available: visual_mode = "playwright"
elif storybook_available: visual_mode = "storybook"
else: visual_mode = "manual"
```

Mode behaviors:
- **playwright** — screenshot-based iteration with self-critique
- **storybook** — component-level iteration (manual user check)
- **playwright + storybook** — Storybook for components, Playwright for full pages
- **manual** — user opens browser, provides text feedback

### Step 2: Visual Iteration with Playwright MCP

`@playwright/mcp` exposes browser tools as `mcp__playwright__browser_*`. Screenshots use the **current viewport** — call `browser_resize` first to capture mobile vs desktop.

```
ensure dev server running (start in background if not: `npm run dev &`)

for viewport in [(1440, 900) "desktop", (375, 812) "mobile"]:
  browser_resize(viewport)
  browser_navigate(dev_server_url)
  optionally browser_wait_for(content_ready)

  capture:
    browser_take_screenshot(path: ".design/screenshots/{milestone}-{viewport}.png")
    OR browser_snapshot()              # accessibility tree, token-cheap (no file)

  evaluate against design brief:
    - layout alignment, spacing
    - color harmony, contrast
    - typography hierarchy
    - visual balance, whitespace
    - mobile responsiveness (on mobile pass)

  self_correct (max 2 passes per milestone):
    list 1-3 specific issues
    apply fixes
    re-screenshot to verify

present to user: "Here's desktop and mobile. Any feedback?"
```

### Step 3: Visual Iteration with Storybook

If Storybook is configured in the project:

1. Start Storybook in the background if not already running:
   ```bash
   npm run storybook &
   ```
   Default port is typically 6006 — verify in the project's `package.json` or Storybook config.

2. For each new or modified component, direct the user to the Storybook URL:
   "Check the [ComponentName] story at http://localhost:6006/?path=/story/{component-name}--{variant}"

3. If Playwright MCP is also available, capture Storybook stories for self-critique:
   - `mcp__playwright__browser_navigate` to the story URL
   - `mcp__playwright__browser_take_screenshot` to capture
   - Evaluate component-level details (states, variants, edge cases)

4. Iterate on individual component stories before composing into full pages.

### Step 4: Manual Fallback

If neither Playwright nor Storybook is available:

1. After each milestone, tell the user:
   "I've completed [milestone]. Open your browser to see the result and let me know what you'd like to change."

2. Suggest setup for richer iteration:
   "For visual iteration, I recommend setting up the Playwright MCP: `claude mcp add playwright npx @playwright/mcp@latest`"

3. Accept feedback as text descriptions, pasted screenshots, or direct file edits.

### Step 5: User Feedback Loop

After presenting the design:
- User provides feedback ("make the hero taller", "the colors feel too cold")
- Apply changes, re-screenshot or direct user to browser
- Commit after each iteration round
- Continue until the user is satisfied

---

## Phase 5 — Parallel Design Exploration

### Letter Casing Convention

Variations are identified by a single letter (`a`, `b`, `c`, `d`). **One canonical form, two presentations:**

- **Lowercase** (`a|b|c|d`) is the canonical identifier. Use it for **everything machine-readable**: filesystem paths (`.design/briefs/variation-a.md`, `.design/screenshots/variation-a/`), git branch names (`design/variation-a`), agent names (`design-variation-a`), commit-message scopes (`design(variation-a):`), and any value passed into a sub-agent prompt as `{letter}`.
- **Uppercase** (`A|B|C|D`) is for **user-facing display only**: when telling the user "Variation A: Dark mode with neon accents…" or showing a comparison table. Convert from lowercase at presentation time (`letter.upper()`) — do NOT store uppercase as the source of truth.

When iterating in pseudocode below, the loop variable is always lowercase. Display strings are derived, not stored.

### When to Trigger

- **Default path when the user picked 2-4 variations during Phase 2 Step 1.** Phase 5 runs because it was chosen up front; jump straight to Step 2 (variation count is already known, Step 1 is skipped).
- Mid-flight pivot — user initially picked "Single direction" but later says "try a few different approaches", asks for A/B variations, or is undecided between two visual directions. Use Step 1 below to capture the count, then continue.
- The design brief identifies multiple viable styles the user cannot choose between.

### Step 1: Ask for Variation Count (fallback only)

Skip this step if the user already answered Phase 2 Step 1 with a variation count > 1 — the count is already known. Use this **only** for mid-flight pivots where the user originally chose "Single direction" but now wants to explore variations.

**Use AskUserQuestion**:

```
AskUserQuestion({
  questions: [{
    question: "How many variations should I explore in parallel?",
    header: "Variations",
    multiSelect: false,
    options: [
      { label: "2 (Recommended)", description: "Focused A/B comparison — fast, easy to decide" },
      { label: "3", description: "Broader exploration — more options" },
      { label: "4", description: "Maximum breadth — takes longer, uses more context" }
    ]
  }]
})
```

### Step 2: Define Variation Directives & Write Per-Variation Briefs

**2a. Define directives.** For each variation, define a specific visual direction. The canonical key is lowercase (`a`, `b`, `c`, `d`); display labels uppercase the letter for the user. Example for 3 variations:

| Key (canonical) | Display label | Directive |
| --- | --- | --- |
| `a` | Variation A | "Dark mode with neon accents, immersive animations" |
| `b` | Variation B | "Light and airy, minimal with lots of whitespace" |
| `c` | Variation C | "Bold and colorful, playful with rounded shapes" |

Present the directives to the user for approval using the display labels. Persist and dispatch using the lowercase keys.

**2b. Write per-variation brief files in the MAIN REPO** at `.design/briefs/variation-{letter}.md`. These files are the contract each sub-agent reads (via absolute path — see Step 3). They live in the main repo, NOT in the worktrees, because the harness creates worktrees from the current branch HEAD and uncommitted files don't appear there.

Each brief file follows this structure:

```markdown
# Variation {LETTER}

## Master Brief

{verbatim copy of .design/brief.md — keep self-contained so the sub-agent never needs to follow include paths}

## Variation Direction

{the directive for this variation, e.g., "Dark mode with neon accents and immersive scroll animations"}

## Runtime Config

- **Dev server port:** {A=4321, B=4322, C=4323, D=4324}
- **Feature flags / env vars:** {list any PUBLIC_*/VITE_*/NEXT_PUBLIC_* env vars discovered in Phase 1 Step 2 that gate UI states — sub-agent must set them when running `npm run dev` so dev-time UI renders correctly}
- **Project subdirectory:** {if monorepo, the subdir within the worktree where the project lives, e.g., `web/`}

## Differentiator

{1-2 sentence statement of what makes this variation distinct from siblings — used by the parent during convergence to compare}
```

After writing the brief files, present the file paths to the user briefly so they can preview/edit before dispatch.

### Step 3: Dispatch Sub-Agents in Isolated Worktrees

**Setup — prefer Agent Teams when available:**

```
if env CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS == "1":
  TeamCreate(team_name: "design-exploration", description: "Parallel design variations")
  use_teams = true
else:
  warn user: "Agent Teams not enabled — using ad-hoc Agent + name + SendMessage (best-effort coordination). For reliable mid-flight updates, set CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1."
  use_teams = false
```

**Resolve the absolute brief path before dispatch.** The sub-agent's worktree is a fresh checkout that does NOT contain uncommitted files. Pass the brief's absolute path in the main repo so the sub-agent can read it from outside its worktree.

`.design/` is a sibling of the project's `package.json` (per Canonical Paths). For a single-project repo that's the git toplevel; for a monorepo where the design target lives in a subdir (e.g., `web/`), `.design/` lives in that subdir. Derive `project_root_abs` by locating the `.design/brief.md` file Phase 2 already wrote — no need to guess subdir layout:

```bash
git_toplevel = `git rev-parse --show-toplevel`             # e.g., /Users/foo/myproject

# Find where Phase 2 wrote brief.md. Bounded depth, skip node_modules + worktrees.
brief_master = `find "$git_toplevel" -maxdepth 4 -path "*/.design/brief.md" \
                  -not -path "*/node_modules/*" -not -path "*/.git/*" 2>/dev/null | head -1`

if [ -z "$brief_master" ]; then
  abort("Phase 2 brief.md not found — Phase 2 Step 2 must run before Phase 5 dispatch")
fi

project_root_abs = `dirname $(dirname "$brief_master")`    # strips /.design/brief.md
project_subdir   = "${project_root_abs#$git_toplevel/}"    # bash strips git_toplevel/ prefix; portable (no GNU realpath needed)
[ "$project_subdir" = "$project_root_abs" ] && project_subdir="."
                                                           # "." for single-project (no prefix stripped), "web" for monorepo subdir
brief_abs_path   = "{project_root_abs}/.design/briefs/variation-{letter}.md"

# Sanity-check before dispatch — fail loudly if the per-variation brief is missing:
test -f "{brief_abs_path}" || abort("variation brief missing at {brief_abs_path} — Phase 5 Step 2b didn't write it")
```

Pass `project_subdir` to the sub-agent too (omit when `.`), so its dev-server commands and screenshot paths target the same location.

**Spawn — single message, multiple Agent calls (parallel execution):**

```
for letter in ["a", "b", "c", "d"][:variation_count]:    # lowercase canonical key
  Agent(
    subagent_type: "ux-designer:design-engineer",
    name: "design-variation-{letter}",                   # e.g., "design-variation-a"
    team_name: "design-exploration",                     # ONLY if use_teams
    isolation: "worktree",                               # harness creates the worktree, returns branch + path
    run_in_background: true,
    prompt: <short dispatch prompt — see below>
  )
```

Do **NOT** create worktrees manually — `isolation: "worktree"` already handles that.

**Mid-flight updates:**

```
SendMessage(to: "design-variation-{letter}", message: "<update>")
# delivered at the teammate's next tool round
# Agent Teams: reliable; ad-hoc named Agents: best-effort
```

**Browser tools are SHARED, not per-agent:** Playwright MCP exposes ONE browser instance per session. Sub-agents trying to use it concurrently will serialize or collide. **Sub-agents must NOT call Playwright tools in this skill.** Visual verification (M8) happens in Step 4 (Convergence), driven by the parent agent serially per variation. The `design-engineer` agent's system prompt enforces this.

**Short dispatch prompt** (the agent's system prompt at `plugins/ux-designer/agents/design-engineer.md` carries the contract — commit format, screenshot paths, no-Playwright-MCP rule, autonomous-work rules, reporting format. The dispatch only needs to provide inputs):

```
You are design-engineer. Your inputs:
- Brief: {absolute path to main repo}/.design/briefs/variation-{letter}.md
- Worktree: <your CWD — set by isolation: "worktree">
- Project subdirectory: {if monorepo, e.g., "web/"; otherwise omit}
- Variation letter: {a|b|c|d}

Read your brief and execute. Report back per your standard reporting format.
```

### Step 4: Convergence

Parent agent drives this serially — Playwright MCP has ONE browser instance, so screenshots happen one variation at a time.

```
on all sub-agents complete:
  results = {worktree_path, branch_name, summary} per variation

  # Visual capture — SERIAL because browser is shared
  # Prefer reading screenshots sub-agents already wrote to .design/screenshots/variation-{letter}/
  # Only re-capture if a sub-agent reported "skipped M8" or screenshots are missing.
  if playwright_available AND screenshots_missing:
    for each variation in order:
      cd <worktree>/<project_subdir>
      npm install (if node_modules missing)
      npm run dev -- --port <unique_port> &  # background, with feature-flag env vars
      wait for server ready
      browser_resize(1440x900); browser_navigate(http://localhost:<port>)
      browser_take_screenshot(path: ".design/screenshots/variation-{letter}/{page}-desktop.png")
      browser_resize(375x812); browser_take_screenshot(path: ".design/screenshots/variation-{letter}/{page}-mobile.png")
    present side-by-side: read images from each worktree's .design/screenshots/variation-{letter}/

  else:
    present text summary per variation (directive + approach)

  # Decision (or trial-mode pause)
  if trial_mode (user wants external review, no commitment yet):
    keep all worktrees + dev servers running
    hand off URLs + screenshots to user
    skip merge / cleanup
  else:
    winner = ask user via AskUserQuestion ("Which variation should we ship?")
    git checkout main
    git merge design/variation-{winner}
    git branch -D design/variation-{losers...}

    # Worktrees auto-clean on agent completion if no changes were made.
    git worktree list                      # verify
    git worktree remove {path}             # explicit cleanup if any remain

    if use_teams:
      for each teammate: SendMessage(to: name, message: {type: "shutdown_request"})
      wait for shutdowns
      TeamDelete()

    continue iterating on merged result
```

**Note:** For explicit worktree-path control (e.g., long-running comparison branches), create worktrees manually with `git worktree add` and dispatch sub-agents WITHOUT `isolation: "worktree"`. You then own cleanup.

---

## References (load on demand)

| Reference | When to Load |
|-----------|-------------|
| `references/question-library.md` | Phase 1 — selecting discovery questions for gap analysis |
| `references/layout-patterns.md` | Phase 2/3 — planning and building layout structure |
| `references/design-system-template.md` | Phase 3 — existing design system detected or building new one |
| `references/animation-patterns.md` | Phase 3 — user wants animations, transitions, or interactions |
| `references/framework-starters.md` | Phase 3 — initializing a project with the chosen framework |

## Important

- **Use AskUserQuestion for every prompt.** Load it once via ToolSearch at the start of the session, then use it for reference intake, discovery questions, framework selection, and variation count. Markdown blockquote prompts are the fallback only.
- **Never skip discovery.** Even a brief questioning round produces dramatically better designs than jumping straight to code. The only exception is when the user's prompt is already comprehensive (5+ dimensions covered).
- **Design brief is the contract.** Always persist the master brief to `.design/brief.md`. For parallel exploration, write per-variation briefs to `.design/briefs/variation-{letter}.md` (Phase 5 Step 2) and pass each sub-agent the absolute path to its brief — worktrees don't include uncommitted files. Update briefs when the user changes direction.
- **Commit after every milestone.** This gives the user rollback points and makes parallel exploration possible.
- **Playwright is optional.** The skill must work without it. When unavailable, guide the user to check their browser and provide text feedback.
- **Storybook is optional.** Only initialize or use it when the project already has it or the user explicitly requests it. Don't add Storybook to a simple landing page unless asked.
- **Self-correction has a cap.** Maximum 2 self-correction passes per milestone when using Playwright screenshots. This prevents infinite loops where the model keeps finding minor issues.
- **Respect existing patterns.** If the project has an established component structure, naming convention, or design system, follow it rather than imposing new patterns.
