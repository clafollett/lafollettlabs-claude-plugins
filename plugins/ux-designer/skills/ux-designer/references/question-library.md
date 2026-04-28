# Question Library

Rich, opinionated discovery questions. Each question has the full set of considered options as a knowledge base.

When invoking `AskUserQuestion`, the tool accepts only 2-4 options per question. Pick the top 4 most relevant options for the current user's brief — drop the rest. Users can still type any dropped option via the auto-added "Other" choice. When falling back to plain markdown (AskUserQuestion unavailable), display the full option set.

Select questions based on gap analysis. For each dimension the user's prompt does not adequately cover, pick 1-2 questions from the relevant category. Group up to 4 related questions into a single AskUserQuestion call. If the user's prompt already addresses a dimension thoroughly, skip the entire category. The goal is to fill gaps, not interrogate.

Maximum 2 rounds of questions. Fill remaining gaps with sensible defaults in the design brief and let the user redirect during iteration.

---

## 1. Purpose & Audience

### Q1.1: Primary Goal

**Skip if:** user stated what the site/app is supposed to accomplish
**Header:** Goal

> What is the single most important thing this project should do?

**Options:**
- **Convert visitors** — Turn traffic into signups, leads, or trial activations
- **Inform & educate** — Content-first experience, teach or explain something
- **Showcase work** — Portfolio, product gallery, or brand presence
- **Drive engagement** — Get users interacting and returning
- **Sell directly** — Drive purchases of products or services

### Q1.2: Target Audience

**Skip if:** user described who the product is for
**Header:** Audience

> Who is the primary audience for this?

**Options:**
- **Developers** — Technical users, engineers, API consumers
- **Decision-makers** — Executives, founders, buyers evaluating solutions
- **General consumers** — Broad public audience, non-technical users
- **Students / learners** — Education-focused, course or tutorial audiences
- **Enterprise teams** — Internal users at organizations, B2B operators

### Q1.3: Industry Context

**Skip if:** user mentioned the industry, niche, or domain
**Header:** Industry

> What space does this live in?

**Options:**
- **SaaS / dev tools** — Software products, developer infrastructure, APIs
- **E-commerce / retail** — Physical or digital goods, storefronts
- **Healthcare / wellness** — Medical, mental health, fitness, wellbeing
- **Fintech** — Financial services, payments, banking, investing
- **Education / edtech** — Schools, courses, learning platforms
- **Agency / creative** — Studios, freelancers, creative service providers

### Q1.4: Inspiration References

**Skip if:** user provided reference sites, screenshots, or named specific designs they like
**Header:** References

> Do you have any reference sites or designs you admire?

**Options:**
- **Yes, specific URLs** — I'll share links or screenshots of designs I like
- **Vague vibe only** — I'll describe the feel, no specific references
- **No references** — Surprise me based on the brief

### Q1.5: Success Metric

**Skip if:** user defined what "working" looks like or mentioned KPIs
**Header:** Success

> How will you know this project is working?

**Options:**
- **Signups / leads** — Form submissions, account creations, demo requests
- **Engagement** — Time on page, content consumed, depth of interaction
- **Purchases** — Revenue, transactions, conversion to paid
- **Retention** — Repeat visits, returning users, long-term stickiness
- **Downloads / installs** — App installs, binary downloads, package adoption

---

## 2. Visual Direction

### Q2.1: Overall Visual Style

**Skip if:** user described the visual style or provided a reference design
**Header:** Visual Style

> What visual direction feels right for this project?

**Options:**
- **Clean & minimal** — Lots of whitespace, subtle colors, understated elegance
- **Bold & expressive** — Strong colors, large typography, dynamic layout
- **Warm & approachable** — Rounded shapes, soft gradients, friendly feel
- **Dark & immersive** — Dark backgrounds, glowing accents, cinematic atmosphere
- **Corporate & trustworthy** — Structured, professional, conservative palette
- **Playful & creative** — Quirky shapes, bright palette, personality-driven

### Q2.2: Color Temperature

**Skip if:** user specified colors, a palette, or a clear mood that implies color direction
**Header:** Color Temp

> What color family should dominate?

**Options:**
- **Cool blues / grays** — Calm, professional, tech-forward
- **Warm oranges / reds** — Energetic, urgent, human
- **Neutral earth tones** — Grounded, organic, timeless
- **Monochrome** — Black, white, and shades of gray
- **Vibrant multi-color** — Bold, diverse, attention-grabbing

### Q2.3: Typography Feel

**Skip if:** user specified fonts or described a typographic direction
**Header:** Typography

> What should the typography communicate?

**Options:**
- **Modern sans-serif** — Inter, Geist, DM Sans territory
- **Classic serif** — Editorial, authoritative, literary
- **Technical mono** — Code-native, developer-oriented
- **Rounded & friendly** — Nunito, Quicksand, approachable vibe
- **Mixed pairing** — Serif headlines with sans body, or vice versa

### Q2.4: Imagery Style

**Skip if:** user described what kind of visuals they want or provided assets
**Header:** Imagery

> What type of imagery fits the project?

**Options:**
- **Photography** — Real photos, lifestyle shots, product imagery
- **3D renders** — Dimensional, modern, product-centric
- **Illustrations** — Hand-drawn or vector, storytelling-friendly
- **Abstract / geometric** — Patterns, gradients, shapes, no figurative imagery
- **Icons only** — No large imagery, icon-driven communication
- **None** — Pure typography and layout, no decorative imagery

### Q2.5: Density & Spacing

**Skip if:** user described layout density or referenced a spacious/dense design
**Header:** Density

> How much breathing room should the design have?

**Options:**
- **Editorial** — Luxurious whitespace, one idea per viewport
- **Spacious** — Generous spacing, deliberate pacing
- **Balanced** — Comfortable spacing, multiple elements visible without crowding
- **Information-dense** — Pack it in, maximize above-the-fold content

### Q2.6: Color Mode

**Skip if:** user specified light mode, dark mode, or both
**Header:** Color Mode

> What about light vs. dark mode?

**Options:**
- **Light only** — Single light theme, no dark mode
- **Dark only** — Single dark theme, no light mode
- **Both with toggle** — User-controlled switch between modes
- **System preference** — Auto-follow OS-level light/dark setting

---

## 3. Layout & Structure

### Q3.1: Page Type

**Skip if:** user described the page structure or app architecture
**Header:** Page Type

> What kind of page structure are we building?

**Options:**
- **Single-page scroll** — One long page with anchored sections
- **Multi-page site** — Separate pages with shared navigation
- **SPA with routing** — Single-page app with client-side route changes
- **Wizard / onboarding** — Step-by-step progression through a flow
- **Dashboard** — Data-heavy interface, panels and widgets

### Q3.2: Hero Section Style

**Skip if:** user described the hero/header area or provided a reference that makes it obvious
**Header:** Hero Style

> What should the hero section look like?

**Options:**
- **Full-bleed image** — Edge-to-edge photography or artwork
- **Video background** — Looping ambient video behind text
- **Split layout** — Text on one side, image or graphic on the other
- **Centered text + gradient** — Headline-forward over abstract background
- **Animated / illustrated** — Motion graphics or custom illustration
- **Product screenshot** — Show the actual product front and center

### Q3.3: Section Count

**Skip if:** user outlined specific sections or content blocks
**Header:** Sections

> How many sections should the page have (roughly)?

**Options:**
- **3-4 focused** — Tight, high-impact, no filler
- **5-7 standard** — Covers the bases without overloading
- **8+ comprehensive** — Full story, lots of content blocks
- **Let content decide** — Tell me what you need, you figure out structure

### Q3.4: Navigation Style

**Skip if:** user described navigation behavior or provided a reference that shows nav treatment
**Header:** Navigation

> How should navigation work?

**Options:**
- **Fixed top bar** — Always visible, scrolls with the page
- **Transparent overlay** — Visible on hero, solidifies on scroll
- **Sidebar nav** — Persistent left or right panel
- **Hamburger only** — Hidden by default, expands on click
- **Tabbed nav** — Horizontal tabs for section switching
- **None** — No visible nav, scroll-only experience

### Q3.5: Footer Complexity

**Skip if:** user described footer requirements
**Header:** Footer

> What should the footer include?

**Options:**
- **Minimal centered** — Copyright and a few links, nothing more
- **Multi-column links** — Organized sitemap-style link groups
- **CTA banner + links** — Final call-to-action above the link columns
- **Newsletter + links** — Email capture integrated into the footer

---

## 4. Content

### Q4.1: Headline Tone

**Skip if:** user provided copy, described their brand voice, or showed examples of their writing style
**Header:** Tone

> What tone should headlines and copy strike?

**Options:**
- **Professional authority** — "Enterprise-grade solutions for modern teams"
- **Conversational & friendly** — "Build something your users will actually love"
- **Bold & direct** — "Stop guessing. Ship faster. Sleep better."
- **Technical & precise** — "Sub-50ms latency. Zero-config deployment. Full type safety."

### Q4.2: Call-to-Action Style

**Skip if:** user described CTA behavior or placement
**Header:** CTA

> How should calls-to-action be handled?

**Options:**
- **Single prominent CTA** — One clear action, repeated at key moments
- **Multiple CTAs per section** — Different actions for different segments
- **Subtle inline links** — Woven into content naturally, no big buttons
- **Floating / sticky CTA** — Always visible as the user scrolls

### Q4.3: Social Proof

**Skip if:** user mentioned testimonials, logos, reviews, or case studies
**Header:** Social Proof

> What kind of social proof should we include?

**Options:**
- **Customer testimonials** — Quotes with names and photos
- **Logo bar** — "Trusted by" row of recognizable company logos
- **Case studies** — Detailed success stories with outcomes
- **Metrics & stats** — "10K+ users," "$1M+ saved" style proof points
- **Reviews / ratings** — Star ratings, review excerpts, third-party scores
- **None needed** — Skip social proof entirely

### Q4.4: Media Assets

**Skip if:** user described their asset situation or provided files
**Header:** Media

> Where are the images and media coming from?

**Options:**
- **User-provided** — My own images, photos, and media
- **Stock photography** — Use stock with my approval on selections
- **AI-generated** — Generate imagery as needed
- **Icons / illustrations only** — No photos, vector-only assets
- **Text-only** — No media assets needed

---

## 5. Interactions

### Q5.1: Animation Level

**Skip if:** user described animation preferences or referenced a site with a specific animation style
**Header:** Animation

> How much animation should the design have?

**Options:**
- **None** — Fully static, no motion
- **Subtle entrances** — Elements fade or slide in on scroll
- **Moderate scroll effects** — Sections animate as they enter the viewport
- **Immersive transitions** — Heavy motion, cinematic full-page feel

### Q5.2: Scroll Behavior

**Skip if:** user described scroll behavior or provided a reference that demonstrates it
**Header:** Scroll

> How should scrolling feel?

**Options:**
- **Standard scroll** — Native browser scroll, predictable, fast
- **Smooth scroll** — Eased anchor scrolling, gentle momentum
- **Parallax layers** — Background and foreground move at different speeds
- **Scroll-snapping** — Each section locks into view as you scroll

### Q5.3: Hover Effects

**Skip if:** user described interaction details or micro-interactions
**Header:** Hover

> What should happen on hover?

**Options:**
- **Nothing** — No hover effects at all
- **Subtle** — Slight opacity or scale changes
- **Prominent** — Color shifts, shadow reveals, clear state changes
- **Animated reveals** — Content or details expand on hover

### Q5.4: Special Effects

**Skip if:** user requested or ruled out specific effects
**Header:** Effects

> Any special visual effects?

**Options:**
- **None** — Keep it clean and performance-focused
- **Video background** — Ambient looping video behind content
- **Particle / grain** — Texture overlays, floating particles
- **3D elements** — WebGL, three.js, or CSS 3D transforms
- **Cursor effects** — Custom cursor, trail effects, magnetic buttons

---

## 6. Technical

### Q6.1: Framework Preference

**Skip if:** user specified a framework or tech stack
**Header:** Framework

> What framework should this be built with?

**Options:**
- **Vue + Vite** — Bare Vue SPA with Vite. Wire up routing and state yourself. Maximum control, minimal magic
- **Nuxt** — Vue meta-framework with file-based routing. Supports SSR, SSG, SPA, and hybrid rendering modes
- **Vanilla HTML + Tailwind** — Static HTML with Tailwind CDN, no build step
- **Astro** — Content-focused, ships minimal JS by default, islands architecture, plays nicely with Vue components
- **Next.js** — React meta-framework with file-based routing. Supports SSR, SSG, SPA, RSC, and hybrid rendering
- **React + Vite** — React SPA with fast Vite tooling, no SSR
- **Svelte / SvelteKit** — Compiler-based, minimal runtime, optional meta-framework
- **Solid + Vite** — Fine-grained reactivity, JSX, fast Vite tooling

### Q6.2: Responsive Priority

**Skip if:** user stated a responsive strategy or device priority
**Header:** Responsive

> Which devices matter most?

**Options:**
- **Mobile-first** — Design for phones, scale up to desktop
- **Desktop-first** — Design for large screens, adapt down
- **Equal priority** — Both mobile and desktop get first-class treatment

### Q6.3: Accessibility Target

**Skip if:** user mentioned accessibility requirements or compliance level
**Header:** A11y

> What level of accessibility should we target?

**Options:**
- **Basic** — Semantic HTML, alt text, reasonable contrast
- **WCAG AA** — Proper contrast, full keyboard nav, screen reader support
- **WCAG AAA** — Maximum compliance, exceeds standard requirements

---

## 7. Design System

### Q7.1: Existing Brand Assets

**Skip if:** user mentioned having a brand guide, design system, or provided brand assets
**Header:** Brand

> Do you have existing brand assets to work with?

**Options:**
- **Yes, full brand** — Logos, brand colors, and fonts all defined
- **Partial** — Some elements (logo or colors) but not everything
- **Starting fresh** — No brand yet, build it all from scratch

### Q7.2: Component Library

**Skip if:** user specified a component library or UI kit
**Header:** Components

> Any preference for a component library?

**Options:**
- **None — custom** — Build custom components, full control
- **ShadCN / Radix** — Headless, composable, Tailwind-native
- **Aceternity UI** — Animated, modern, scroll-driven components
- **HeroUI** — Clean, accessible, pre-styled components
- **Headless UI** — Unstyled, accessible primitives
- **Material UI** — Google's design system, opinionated
- **DaisyUI** — Tailwind plugin with themed components

### Q7.3: Icon Style

**Skip if:** user specified an icon set or provided custom icons
**Header:** Icons

> What icon set should we use?

**Options:**
- **Lucide** — Clean, consistent, widely supported
- **Heroicons** — Tailwind team's set, two stroke styles
- **Phosphor** — Flexible weights, large library
- **Font Awesome** — Classic, massive selection
- **Custom SVGs** — Bespoke icons designed for the project
- **Emoji** — Native emoji as icons
