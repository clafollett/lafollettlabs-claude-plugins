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

---

## Phase 1 — Discovery

### Step 1: Reference Material Intake

Before asking design questions, ask the user if they have reference material:

> Do you have any of the following to share before we start?
>
> a) Epics, stories, or requirements docs (from GitHub Issues or a PRD)
> b) Wireframes, mockups, or screenshots of reference/competitor sites
> c) Figma files or design system documentation
> d) Brand guidelines, logos, or existing visual assets
> e) Existing Storybook setup or component library
> f) None of the above — let's start from scratch

If the user provides epics or stories, extract the **what** and **why** to inform layout structure, content hierarchy, and feature sections. The design should reflect what engineering is building.

If the user provides a Storybook URL or has an existing `.storybook/` directory, note it — this changes the generation strategy to component-first (see Phase 3).

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

**If the prompt covers 5+ dimensions**: skip questioning and proceed to Phase 2.

**Otherwise**: load `references/question-library.md` and select 1-2 questions per uncovered dimension.

### Step 4: Questioning Flow

Present questions as multiple-choice groups. Maximum 2 rounds total, 3-5 questions per round. Pick questions from `references/question-library.md` based on which dimensions the gap analysis flagged. Group related questions into one round when possible.

Format:

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

After the user answers, proceed to Phase 2. Do not chase a third round of questions — fill remaining gaps with sensible defaults from the design brief and let the user redirect during iteration.

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

Always ask the user which framework to use. Present the options:

> Which framework should I use?
>
> a) Vanilla HTML + Tailwind CDN — zero setup, instant preview
> b) React + Vite + Tailwind
> c) Next.js + Tailwind
> d) Vue + Vite + Tailwind
> e) Nuxt + Tailwind
> f) Svelte/SvelteKit + Tailwind
> g) Astro + Tailwind
> h) Solid + Vite + Tailwind
> i) Other — tell me what you want

If a framework is already detected in the project, note it: "I see you're using [framework]. I'll build with that unless you want something different."

Load `references/framework-starters.md` for initialization commands and boilerplate.

### Step 2: Storybook Strategy

Determine the Storybook approach based on project context:

**Existing Storybook detected** (`.storybook/` directory or `*.stories.*` files found):
- Read the existing Storybook config to understand the setup
- Read 1-2 existing stories to match the pattern (CSF3 vs CSF2, naming, args style)
- Generate new stories that match the existing conventions
- New components get stories alongside them

**User requests Storybook but none exists**:
- Initialize Storybook for the detected framework:
  ```bash
  npx storybook@latest init
  ```
- Create a design system story that documents color tokens, typography, and spacing
- Each new component gets a `.stories.tsx` (or `.stories.js`, `.stories.svelte`, etc.) file

**No Storybook requested or needed**:
- Skip Storybook entirely. Build pages directly.
- If the user later asks for Storybook, add it incrementally.

**Component-first workflow** (when Storybook is active):
1. Design individual components first — button, card, hero, nav, etc.
2. Create a Storybook story for each component with variants (primary, secondary, sizes)
3. Visually verify each component in Storybook before composing pages
4. Compose components into full pages
5. This produces higher-quality, more reusable output than page-first design

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

Check which visual feedback tools are available before the first checkpoint:

1. **Playwright MCP**: Check if any `mcp__playwright__browser_*` tools are in your available toolset
2. **Storybook**: Check `package.json` for a `storybook` script and an existing `.storybook/` directory
3. **Neither**: Fall back to manual browser workflow

Set the visual mode for the rest of the session:
- `playwright` — full screenshot-based iteration with self-critique
- `storybook` — component-level iteration via Storybook (manual user check)
- `playwright + storybook` — both available, use Storybook for component stories and Playwright for full pages
- `manual` — user opens browser, provides text feedback

### Step 2: Visual Iteration with Playwright MCP

The official `@playwright/mcp` package exposes browser tools as `mcp__playwright__browser_*`. Note that **screenshots use the current viewport size** — to capture mobile vs desktop, call `browser_resize` first.

If Playwright MCP is available:

1. Ensure the dev server is running (start it in the background if not):
   ```bash
   npm run dev &
   # Wait briefly for the server to be ready before navigating
   ```

2. Navigate to the page (and resize for desktop):
   - `mcp__playwright__browser_resize` with `width: 1440, height: 900`
   - `mcp__playwright__browser_navigate` with the dev server URL
   - Optionally `mcp__playwright__browser_wait_for` for content readiness

3. Capture the page:
   - `mcp__playwright__browser_take_screenshot` to save a desktop screenshot
   - Or use `mcp__playwright__browser_snapshot` to get the accessibility tree (more token-efficient if you don't need pixels)

4. Evaluate against the design brief:
   - Layout alignment and spacing
   - Color harmony and contrast
   - Typography hierarchy
   - Visual balance and whitespace
   - Mobile responsiveness (after the mobile resize below)

5. Self-correct (maximum 2 passes per milestone):
   - List 1-3 specific issues found
   - Apply fixes
   - Re-screenshot to verify

6. Capture mobile viewport:
   - `mcp__playwright__browser_resize` with `width: 375, height: 812`
   - `mcp__playwright__browser_take_screenshot` for the mobile screenshot

7. Present to user: "Here's what I built — desktop and mobile views. Any feedback?"

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

> How many variations should I explore?
>
> a) 2 — focused A/B comparison
> b) 3 — broader exploration
> c) 4 — maximum breadth (takes longer)
> d) Other number

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
5. When all milestones are complete, report:
   - Branch name (current branch)
   - 2-3 sentence summary of your approach
   - What makes this variation distinct
   - Path to any final screenshots if Playwright is available
```

### Step 4: Convergence

After all sub-agents complete, the harness returns each worktree's path and branch name in the agent results.

1. If Playwright is available, navigate each variation's dev server (or check out each branch in turn) to capture screenshots for side-by-side comparison
2. Present a summary of each variation with its directive and approach
3. Ask the user to pick a winner
4. Merge the chosen branch into main:
   ```bash
   git checkout main
   git merge design/variation-{letter}
   ```
5. Delete the unused branches (worktrees were already cleaned up by the harness when sub-agents finished, unless the agents made changes — in which case `git worktree list` will show them):
   ```bash
   git branch -D design/variation-{loser-1} design/variation-{loser-2}
   # If any worktrees remain, remove them explicitly:
   git worktree list
   git worktree remove {path}
   ```
6. Continue iterating on the merged result

**Note:** If you need explicit control over worktree paths (e.g., to host multiple dev servers simultaneously for live comparison), create them manually with `git worktree add` and dispatch sub-agents **without** `isolation: "worktree"` — but then you must also clean up worktrees yourself. The default isolated approach is simpler.

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

- **Never skip discovery.** Even a brief questioning round produces dramatically better designs than jumping straight to code. The only exception is when the user's prompt is already comprehensive (5+ dimensions covered).
- **Design brief is the contract.** Always persist it to `.design/brief.md`. Sub-agents during parallel exploration must follow it. Update it when the user changes direction.
- **Commit after every milestone.** This gives the user rollback points and makes parallel exploration possible.
- **Playwright is optional.** The skill must work without it. When unavailable, guide the user to check their browser and provide text feedback.
- **Storybook is optional.** Only initialize or use it when the project already has it or the user explicitly requests it. Don't add Storybook to a simple landing page unless asked.
- **Self-correction has a cap.** Maximum 2 self-correction passes per milestone when using Playwright screenshots. This prevents infinite loops where the model keeps finding minor issues.
- **Respect existing patterns.** If the project has an established component structure, naming convention, or design system, follow it rather than imposing new patterns.
