# ux-designer

A design harness that produces shippable code, not pictures. Structured
discovery, then parallel visual directions built in isolated worktrees and
compared side by side.

```
/plugin install ux-designer
```

Optional but recommended: the Playwright MCP server, for screenshot-based
self-critique.

## Skills

| Skill | |
| - | - |
| `/ux-designer:ux-designer` | the full workflow — Discovery → Brief & Milestones → Build & Converge |

Ships a `design-engineer` sub-agent that does the building. The parent skill
never writes the code itself; it collects direction, writes briefs, dispatches,
and converges.

## Usage

```text
You: /ux-designer:ux-designer
You: design a pricing page for this app
You: make this dashboard look less like a bootstrap template
You: here's a Figma screenshot — build this
You: give me three directions for the landing page
```

Discovery asks before it builds — audience, tone, visual direction, framework —
and asks up front how many directions you want (one, or two to four in
parallel). Each variation is built by its own sub-agent in its own git worktree,
so they cannot collide, and every milestone is committed.

Briefs persist at `.design/brief.md` (the shared baseline) and
`.design/briefs/variation-a.md` (what makes each one different).

## Tips

**Answer discovery honestly, including "I don't know".** The questions exist to
stop it guessing a direction and building three milestones in the wrong one. "I
don't know, show me options" is a real answer and produces variations.

**Ask for parallel variations when the direction is genuinely open.** One
direction is right when you know what you want and need it built. Two to four is
right when the argument is about *what it should feel like* — comparing built
pages settles that faster than describing them.

**Bring a reference if you have one.** A screenshot, a Figma frame, a URL, an
existing design system. Discovery will extract far more from an artifact than
from adjectives.

**Install Playwright if you want it to critique itself.** Without it the skill
builds from assumption; with it, it screenshots what it built and iterates
against the render. That difference shows up most in spacing, contrast, and
responsive behavior.

**It works with an existing Storybook, not just a new one.** Component-level
design against your real components beats a standalone page that has to be
back-ported.

**`.design/` sits next to the `package.json` it belongs to.** In a monorepo with
the target in `web/`, that means `web/.design/`, not the repo root. Worth
knowing before you go looking for the brief.

**Milestones are commits.** The iteration history is in git, so backing out one
step is a revert rather than a redesign.
