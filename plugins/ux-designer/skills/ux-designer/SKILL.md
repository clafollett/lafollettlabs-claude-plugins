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
```

If an existing design system or Storybook is detected:
- Load `references/design-system-template.md` and extract existing tokens
- Note detected framework and component library
- Inform the user: "I detected [framework/library/Storybook]. I'll work within your existing design system."

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

### Step 1: Generate Design Brief

Compile all discovery answers into a design brief. Load `assets/design-brief-template.md` for the template structure.

Persist the brief as `.design/brief.md` in the project root. This file survives session boundaries and serves as the contract for sub-agents during parallel exploration.

### Step 2: Plan Milestones

Present milestones before generating anything:

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
    browser_take_screenshot()          # for pixel evaluation
    OR browser_snapshot()              # accessibility tree, token-cheap

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

### When to Trigger

- User says "try a few different approaches" or "explore variations"
- User is undecided between two visual directions
- User explicitly asks for A/B variations
- The design brief identifies multiple viable styles the user cannot choose between

### Step 1: Ask for Variation Count

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

### Step 2: Define Variation Directives

For each variation, define a specific visual direction. Example for 3 variations:

- **Variation A**: "Dark mode with neon accents, immersive animations"
- **Variation B**: "Light and airy, minimal with lots of whitespace"
- **Variation C**: "Bold and colorful, playful with rounded shapes"

Present the directives to the user for approval before spawning agents.

### Step 3: Dispatch Sub-Agents in Isolated Worktrees

Spawn one sub-agent per variation using the **Agent tool with `isolation: "worktree"`**. The harness creates each worktree automatically, runs the agent inside it, and returns the resulting branch name and path on completion. Do **not** create worktrees manually beforehand — `isolation: "worktree"` already handles that and would conflict with manual creation.

Send all sub-agent calls in a **single message with multiple Agent tool uses** so they run in parallel.

Prompt template for each sub-agent:

```markdown
You are a UX designer creating variation {LETTER} of a design. You are running in an isolated git worktree — work here, commit here, and the parent agent will merge your branch.

## Design Brief
{paste the full contents of .design/brief.md}

## Your Variation Direction
{variation-specific directive — e.g., "Dark mode with neon accents and immersive scroll animations"}

## Instructions
1. Follow the milestones from the brief in order
2. Use the framework specified in the brief
3. Commit after each milestone with message: "design(variation-{letter}): {milestone description}"
4. If Storybook is part of the brief, generate stories for each component you build
5. **Work autonomously — you cannot interact with the user.** AskUserQuestion is not available to sub-agents. If you hit a genuinely blocking ambiguity, stop and report it back instead of guessing or improvising. Otherwise, follow the brief and your variation direction; minor judgment calls are yours to make.
6. When all milestones are complete, report:
   - Branch name (current branch)
   - 2-3 sentence summary of your approach
   - What makes this variation distinct
   - Path to any final screenshots if Playwright is available
```

### Step 4: Convergence

```
on all sub-agents complete:
  results = harness returns {worktree_path, branch_name} per agent

  if playwright_available:
    for each variation:
      navigate variation's dev server (or git checkout branch)
      browser_take_screenshot()
    present side-by-side comparison
  else:
    present text summary per variation (directive + approach)

  winner = ask user via AskUserQuestion ("Which variation should we ship?")

  git checkout main
  git merge design/variation-{winner}
  git branch -D design/variation-{losers...}

  # Worktrees auto-clean on agent completion if no changes were made.
  git worktree list                      # verify
  git worktree remove {path}             # explicit cleanup if any remain

  continue iterating on merged result
```

**Note:** For explicit worktree-path control (e.g., multiple dev servers running simultaneously for live comparison), create worktrees manually with `git worktree add` and dispatch sub-agents WITHOUT `isolation: "worktree"`. You then own cleanup.

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
- **Design brief is the contract.** Always persist it to `.design/brief.md`. Sub-agents during parallel exploration must follow it. Update it when the user changes direction.
- **Commit after every milestone.** This gives the user rollback points and makes parallel exploration possible.
- **Playwright is optional.** The skill must work without it. When unavailable, guide the user to check their browser and provide text feedback.
- **Storybook is optional.** Only initialize or use it when the project already has it or the user explicitly requests it. Don't add Storybook to a simple landing page unless asked.
- **Self-correction has a cap.** Maximum 2 self-correction passes per milestone when using Playwright screenshots. This prevents infinite loops where the model keeps finding minor issues.
- **Respect existing patterns.** If the project has an established component structure, naming convention, or design system, follow it rather than imposing new patterns.
