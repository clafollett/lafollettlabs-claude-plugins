# Design System Template

Use this reference when an existing design system is detected in the project or when building a new one. Extract tokens from existing code, or define new ones based on the design brief.

## Extraction Instructions

### From Tailwind Config
```bash
# Check for tailwind config
cat tailwind.config.* 2>/dev/null
# Look for theme extensions
grep -A 50 "theme:" tailwind.config.* 2>/dev/null
```
Map `theme.extend.colors`, `theme.extend.fontFamily`, `theme.extend.spacing` to tokens below.

### From CSS Custom Properties
```bash
# Find CSS variable definitions (search src/, app/, and styles/)
grep -rE "^\s*--[a-z]" src app styles --include="*.css" 2>/dev/null | head -30
```
Map CSS variables to the token categories.

### From Existing Components
```bash
# Find component files for pattern extraction (parens are required for -o to work as expected)
find src app -type f \( -name "*.tsx" -o -name "*.jsx" -o -name "*.vue" -o -name "*.svelte" \) 2>/dev/null | head -20
# Look for common styling patterns
grep -rn "className\|class=" src app --include="*.tsx" --include="*.jsx" 2>/dev/null | head -20
```

### From Figma
If the user provides a Figma URL or screenshot:
- Extract color palette from fills and strokes
- Extract typography from text styles
- Extract spacing from auto-layout gaps and padding
- Extract border radius from corner radius values
- Extract shadow values from effect styles

## Token Definitions

### Colors

```
Primary:      {hex} — brand color, buttons, links, active states
Secondary:    {hex} — secondary actions, tags, badges
Accent:       {hex} — highlights, decorative elements, notifications
Neutral:
  50:         {hex} — lightest background
  100:        {hex} — subtle background, hover states
  200:        {hex} — borders, dividers
  300:        {hex} — disabled text, placeholders
  400:        {hex} — secondary text
  500:        {hex} — body text
  600:        {hex} — headings
  700:        {hex} — emphasis text
  800:        {hex} — high contrast text
  900:        {hex} — darkest text
  950:        {hex} — dark mode backgrounds
Semantic:
  Success:    {hex} — confirmations, positive states
  Warning:    {hex} — caution states, pending
  Error:      {hex} — errors, destructive actions
  Info:       {hex} — informational, neutral alerts
Background:   {hex} — page background
Surface:      {hex} — card/panel backgrounds
```

### Typography

All sizes assume a 16px root (`html { font-size: 16px }`), the browser default. Tailwind uses the same base.

```
Font Families:
  Heading:    {family} (e.g., Inter, Cal Sans, Geist)
  Body:       {family} (e.g., Inter, system-ui)
  Mono:       {family} (e.g., JetBrains Mono, Fira Code)

Scale:
  xs:         0.75rem / 12px  — captions, labels
  sm:         0.875rem / 14px — secondary text, metadata
  base:       1rem / 16px     — body text
  lg:         1.125rem / 18px — lead paragraphs
  xl:         1.25rem / 20px  — section subheadings
  2xl:        1.5rem / 24px   — card titles
  3xl:        1.875rem / 30px — section headings
  4xl:        2.25rem / 36px  — page headings
  5xl:        3rem / 48px     — hero subheading
  6xl:        3.75rem / 60px  — hero heading
  7xl:        4.5rem / 72px   — display, oversized hero

Weights:
  Light:      300
  Normal:     400
  Medium:     500
  Semibold:   600
  Bold:       700
  Extrabold:  800

Line Heights:
  Tight:      1.1   — headings, display text
  Snug:       1.25  — subheadings
  Normal:     1.5   — body text
  Relaxed:    1.625 — long-form reading
  Loose:      2     — spaced-out text

Letter Spacing:
  Tight:      -0.025em — headings
  Normal:     0        — body text
  Wide:       0.025em  — uppercase labels, overlines
  Wider:      0.05em   — all-caps headings
```

### Spacing

```
Base unit: 4px (0.25rem)

0:    0
0.5:  2px / 0.125rem
1:    4px / 0.25rem
1.5:  6px / 0.375rem
2:    8px / 0.5rem
2.5:  10px / 0.625rem
3:    12px / 0.75rem
4:    16px / 1rem
5:    20px / 1.25rem
6:    24px / 1.5rem
8:    32px / 2rem
10:   40px / 2.5rem
12:   48px / 3rem
16:   64px / 4rem
20:   80px / 5rem
24:   96px / 6rem
32:   128px / 8rem

Section Padding:   16-24 (64-96px vertical)
Card Padding:      4-6 (16-24px)
Button Padding:    2-3 vertical, 4-6 horizontal
Input Padding:     2-3 vertical, 3-4 horizontal
Gap (grid/flex):   4-8 (16-32px)
```

### Border Radius

Matches Tailwind v4 defaults exactly so token names map 1:1 with utility classes.

```
none:   0
xs:     0.125rem / 2px   — subtle rounding (Tailwind: rounded-xs)
sm:     0.25rem / 4px    — small buttons, badges (rounded-sm)
md:     0.375rem / 6px   — buttons, inputs (rounded-md)
lg:     0.5rem / 8px     — cards (rounded-lg)
xl:     0.75rem / 12px   — modals, larger cards (rounded-xl)
2xl:    1rem / 16px      — hero sections, large panels (rounded-2xl)
3xl:    1.5rem / 24px    — large surface treatments (rounded-3xl)
full:   9999px           — circles, pill buttons (rounded-full)
```

### Shadows

```
sm:     0 1px 2px 0 rgb(0 0 0 / 0.05)
md:     0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)
lg:     0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)
xl:     0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)
2xl:    0 25px 50px -12px rgb(0 0 0 / 0.25)
inner:  inset 0 2px 4px 0 rgb(0 0 0 / 0.05)
glow:   0 0 24px rgb(var(--color-primary-rgb) / 0.35)   — dark mode accent effect; replace with concrete RGB if not using CSS vars
```

**Dark Mode Adjustments**

Shadows on dark backgrounds rarely show — replace with subtle borders or glows:

```
dark-border:  0 0 0 1px rgb(255 255 255 / 0.08)
dark-elevation: 0 0 0 1px rgb(255 255 255 / 0.06), 0 8px 24px rgb(0 0 0 / 0.4)
```

### Breakpoints

```
sm:     640px   — large phones, landscape
md:     768px   — tablets
lg:     1024px  — small laptops
xl:     1280px  — desktops
2xl:    1536px  — large desktops

Container max-widths:
  sm:   640px
  md:   768px
  lg:   1024px
  xl:   1280px
  2xl:  1400px  — content max-width (readable line length)
```

### Component Patterns

```
Button Variants:
  Primary:    bg-primary, text-white, hover:bg-primary/90
  Secondary:  bg-secondary, text-secondary-foreground, hover:bg-secondary/80
  Outline:    border-2 border-primary, text-primary, hover:bg-primary hover:text-white
  Ghost:      bg-transparent, text-foreground, hover:bg-neutral-100
  Destructive: bg-error, text-white, hover:bg-error/90

Button Sizes:
  sm:         h-8, px-3, text-sm
  md:         h-10, px-4, text-base
  lg:         h-12, px-6, text-lg

Card Pattern:
  bg-surface, rounded-lg, shadow-md, p-6
  With hover: hover:shadow-lg, transition-shadow

Input Pattern:
  Base:     border border-neutral-200, rounded-md, px-3, py-2, bg-white
  Focus:    focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary
  Error:    border-error focus:ring-error/50
  Success:  border-success focus:ring-success/50
  Disabled: opacity-50 cursor-not-allowed bg-neutral-50
  Dark:     dark:bg-neutral-900 dark:border-neutral-800 dark:text-white

Badge Pattern:
  inline-flex, px-2.5, py-0.5, text-xs, font-medium, rounded-full
```

### Dark Mode Token Strategy

Two recommended approaches — pick one per project, never mix.

**Approach 1: CSS variables with class toggle (recommended for ShadCN-style projects)**
```css
:root {
  --color-bg: 255 255 255;
  --color-text: 15 23 42;
}
.dark {
  --color-bg: 9 9 11;
  --color-text: 250 250 250;
}
```
Toggle by adding/removing `.dark` on `<html>`. Tokens reference `rgb(var(--color-bg))` in Tailwind config.

**Approach 2: Tailwind `dark:` variant (simpler, no JS state needed)**
```html
<div class="bg-white dark:bg-neutral-950 text-neutral-900 dark:text-neutral-50">
```
Activates via `prefers-color-scheme`. No theme toggle without extra JS.

## Quick-Start Design Systems

### Minimal Neutral
Primary: #0F172A (slate-900), Accent: #3B82F6 (blue-500), BG: #FFFFFF
Fonts: Inter, system-ui | Radius: md | Shadows: sm-md

### Bold Dark
Primary: #8B5CF6 (violet-500), Accent: #06B6D4 (cyan-500), BG: #0A0A12 (near-black with cool tint)
Fonts: Cal Sans (headings), Inter (body) | Radius: lg | Shadows: glow + dark-border

### Warm Approachable
Primary: #F97316 (orange-500), Accent: #A855F7 (purple-500), BG: #FFFBF5
Fonts: DM Sans, system-ui | Radius: xl-2xl | Shadows: md-lg

### Corporate Trust
Primary: #1E40AF (blue-800), Accent: #475569 (slate-600), BG: #F8FAFC
Fonts: Source Sans Pro, Georgia | Radius: sm-md | Shadows: sm

Keep all values production-ready and consistent with Tailwind CSS defaults where possible.
