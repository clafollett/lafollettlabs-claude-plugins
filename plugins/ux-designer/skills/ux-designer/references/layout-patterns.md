# Layout Patterns

Structural HTML/Tailwind skeletons for layout generation. Copy, adapt, and fill in content. Every snippet uses semantic HTML5 and modern Tailwind (v4 compatible) with responsive classes.

---

## Hero Patterns

### 1. Full-Bleed Image

```html
<section class="relative min-h-[80vh] flex items-center justify-center">
  <img src="{image}" alt="" class="absolute inset-0 w-full h-full object-cover" />
  <div class="absolute inset-0 bg-black/50"></div>
  <div class="relative z-10 text-center max-w-2xl px-4">
    <h1 class="text-4xl md:text-6xl font-bold text-white">{Headline}</h1>
    <p class="mt-4 text-lg text-white/80">{Subheading}</p>
    <a href="#" class="mt-8 inline-block px-8 py-3 bg-white text-black rounded-lg">{CTA Text}</a>
  </div>
</section>
```

**When to use:** Product launches, brand landing pages, event announcements -- any page that needs immediate visual impact.

**Responsive:** Image height scales via `min-h-[80vh]`. Text sizes step down via `text-4xl md:text-6xl`. CTA stays centered at all widths.

---

### 2. Split Layout

```html
<section class="grid grid-cols-1 md:grid-cols-2 min-h-[80vh]">
  <div class="flex flex-col justify-center px-8 md:px-16 py-12">
    <h1 class="text-4xl md:text-5xl font-bold">{Headline}</h1>
    <p class="mt-4 text-lg text-gray-600">{Description}</p>
    <a href="#" class="mt-8 inline-block w-fit px-8 py-3 bg-black text-white rounded-lg">{CTA Text}</a>
  </div>
  <div class="relative min-h-[50vh] md:min-h-0">
    <img src="{image}" alt="" class="absolute inset-0 w-full h-full object-cover" />
  </div>
</section>
```

**When to use:** Product feature highlights, about sections, app showcases where text and visual carry equal weight. Reverse column order with `md:order-first` on the image div.

**Responsive:** Columns stack vertically on mobile. Image becomes a contained block above or below text. Each half goes full-width.

---

### 3. Centered Text with Gradient

```html
<section class="min-h-[80vh] flex items-center justify-center bg-gradient-to-br from-indigo-600 to-purple-700">
  <div class="text-center max-w-2xl px-4">
    <h1 class="text-4xl md:text-6xl font-bold text-white">{Headline}</h1>
    <p class="mt-4 text-lg text-white/80 max-w-xl mx-auto">{Description}</p>
    <a href="#" class="mt-8 inline-block px-8 py-3 bg-white text-black rounded-lg">{CTA Text}</a>
  </div>
</section>
```

**When to use:** SaaS landing pages, waitlists, minimal-brand pages where imagery is unavailable or unnecessary.

**Responsive:** Nearly identical on all breakpoints. Padding and font sizes scale. The simplest hero to make responsive.

---

### 4. Video Background

```html
<section class="relative min-h-[80vh] flex items-center justify-center overflow-hidden">
  <video autoplay muted loop playsinline poster="{poster}" class="absolute inset-0 w-full h-full object-cover">
    <source src="{video}" type="video/mp4" />
  </video>
  <div class="absolute inset-0 bg-black/60"></div>
  <div class="relative z-10 text-center max-w-2xl px-4">
    <h1 class="text-4xl md:text-6xl font-bold text-white">{Headline}</h1>
    <p class="mt-4 text-lg text-white/80">{Subheading}</p>
    <a href="#" class="mt-8 inline-block px-8 py-3 bg-white text-black rounded-lg">{CTA Text}</a>
  </div>
</section>
```

**When to use:** Brand storytelling, luxury/lifestyle products, agencies -- anywhere cinematic impact matters and page weight is acceptable.

**Responsive:** Video replaced with poster image on mobile via JS or `<picture>`. Overlay and text remain centered. Height reduces. Consider `prefers-reduced-motion` to pause autoplay.

---

### 5. Product Screenshot

```html
<section class="relative overflow-hidden bg-gradient-to-b from-gray-50 to-white">
  <div class="max-w-4xl mx-auto px-4 pt-20 pb-32 text-center">
    <h1 class="text-4xl md:text-6xl font-bold">{Headline}</h1>
    <p class="mt-4 text-lg text-gray-600">{Subheading}</p>
    <a href="#" class="mt-8 inline-block px-8 py-3 bg-black text-white rounded-lg">{CTA Text}</a>
    <div class="mt-16 mx-auto max-w-3xl rounded-xl shadow-2xl overflow-hidden">
      <img src="{screenshot}" alt="{Product Name}" class="w-full" />
    </div>
  </div>
</section>
```

**When to use:** SaaS products, app launches, tools -- whenever showing the actual product builds credibility.

**Responsive:** Screenshot scales down proportionally. Text stacks above. On very small screens, screenshot may be hidden or replaced with a simplified graphic.

---

### 6. Animated / Illustrated

```html
<section class="grid grid-cols-1 md:grid-cols-2 gap-8 items-center min-h-[80vh] px-8 md:px-16">
  <div class="py-12">
    <h1 class="text-4xl md:text-5xl font-bold">{Headline}</h1>
    <p class="mt-4 text-lg text-gray-600">{Description}</p>
    <a href="#" class="mt-8 inline-block px-8 py-3 bg-black text-white rounded-lg">{CTA Text}</a>
  </div>
  <div class="flex items-center justify-center">
    <!-- Replace with <lottie-player>, SVG animation, or illustration -->
    <div class="w-full max-w-md aspect-square">{Illustration / Animation}</div>
  </div>
</section>
```

**When to use:** Startups, creative agencies, developer tools -- brands that want personality without relying on photography.

**Responsive:** Stacks vertically. Illustration scales down or a simpler version is swapped in. Animation may be replaced with a static frame on low-power devices via `prefers-reduced-motion`.

---

## Section Patterns

### 1. Feature Grid (2x3 or 3x3)

```html
<section class="py-20 px-4">
  <div class="max-w-6xl mx-auto text-center">
    <h2 class="text-3xl md:text-4xl font-bold">{Section Headline}</h2>
    <p class="mt-4 text-lg text-gray-600 max-w-2xl mx-auto">{Section Description}</p>
    <div class="mt-16 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-8">
      <!-- Repeat card 3-9 times -->
      <article class="p-6 rounded-lg border">
        <div class="w-12 h-12">{Icon}</div>
        <h3 class="mt-4 text-xl font-semibold">{Feature Title}</h3>
        <p class="mt-2 text-gray-600">{Feature Description}</p>
      </article>
    </div>
  </div>
</section>
```

**When to use:** Feature overviews, benefits sections, service listings -- any time you need to present 3-9 parallel items.

**Responsive:** 3 columns collapse to 2 on tablet (`sm:grid-cols-2`), then 1 on mobile. Cards stack vertically. Consistent card height per row on desktop.

---

### 2. Alternating Rows

```html
<section class="py-20 px-4">
  <div class="max-w-6xl mx-auto space-y-24">
    <!-- Row 1: image left, text right -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-12 items-center">
      <img src="{image-1}" alt="" class="rounded-lg" />
      <div>
        <h3 class="text-2xl font-bold">{Feature Title}</h3>
        <p class="mt-4 text-gray-600">{Feature Description}</p>
      </div>
    </div>
    <!-- Row 2: text left, image right -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-12 items-center">
      <div class="md:order-first">
        <h3 class="text-2xl font-bold">{Feature Title}</h3>
        <p class="mt-4 text-gray-600">{Feature Description}</p>
      </div>
      <img src="{image-2}" alt="" class="rounded-lg" />
    </div>
  </div>
</section>
```

**When to use:** Feature deep-dives, how-it-works sections, storytelling flows where each point deserves its own visual.

**Responsive:** All rows stack to image-on-top, text-below on mobile. Alternation disappears but each feature remains a clear unit.

---

### 3. Card Carousel

```html
<section class="py-20">
  <div class="max-w-6xl mx-auto px-4">
    <h2 class="text-3xl font-bold">{Section Headline}</h2>
    <div class="mt-12 flex gap-6 overflow-x-auto snap-x snap-mandatory pb-4 -mx-4 px-4">
      <!-- Repeat card N times -->
      <article class="snap-start shrink-0 w-72 rounded-lg border overflow-hidden">
        <img src="{image}" alt="" class="w-full h-48 object-cover" />
        <div class="p-4">
          <h3 class="font-semibold">{Card Title}</h3>
          <p class="mt-2 text-sm text-gray-600">{Card Description}</p>
        </div>
      </article>
    </div>
    <!-- Optional: dot indicators or arrow buttons via JS -->
  </div>
</section>
```

**When to use:** Portfolios, product listings, blog post previews, testimonial collections -- content sets too large for a static grid.

**Responsive:** Shows fewer cards per view. CSS `snap-x` provides native scroll-snap on touch devices. Consider full-width single-card on mobile.

---

### 4. Pricing Table

```html
<section class="py-20 px-4">
  <div class="max-w-5xl mx-auto text-center">
    <h2 class="text-3xl md:text-4xl font-bold">{Choose Your Plan}</h2>
    <div class="mt-16 grid grid-cols-1 md:grid-cols-3 gap-8 items-start">
      <!-- Standard tier -->
      <article class="rounded-lg border p-8">
        <h3 class="text-lg font-semibold">{Basic}</h3>
        <p class="mt-4 text-4xl font-bold">{$9}<span class="text-base font-normal text-gray-500">/mo</span></p>
        <ul class="mt-8 space-y-3 text-left text-sm">
          <li>{Feature A}</li>
          <li>{Feature B}</li>
        </ul>
        <a href="#" class="mt-8 block w-full py-3 text-center rounded-lg border">{Select Plan}</a>
      </article>
      <!-- Highlighted tier -->
      <article class="rounded-lg border-2 border-black p-8 relative">
        <span class="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 bg-black text-white text-xs rounded-full">{Popular}</span>
        <h3 class="text-lg font-semibold">{Pro}</h3>
        <p class="mt-4 text-4xl font-bold">{$29}<span class="text-base font-normal text-gray-500">/mo</span></p>
        <ul class="mt-8 space-y-3 text-left text-sm">
          <li>{Feature A}</li>
          <li>{Feature B}</li>
          <li>{Feature C}</li>
        </ul>
        <a href="#" class="mt-8 block w-full py-3 text-center rounded-lg bg-black text-white">{Select Plan}</a>
      </article>
      <!-- Premium tier -->
      <article class="rounded-lg border p-8">
        <h3 class="text-lg font-semibold">{Enterprise}</h3>
        <p class="mt-4 text-4xl font-bold">{$99}<span class="text-base font-normal text-gray-500">/mo</span></p>
        <ul class="mt-8 space-y-3 text-left text-sm">
          <li>{Feature A}</li>
          <li>{Feature B}</li>
          <li>{Feature C}</li>
          <li>{Feature D}</li>
        </ul>
        <a href="#" class="mt-8 block w-full py-3 text-center rounded-lg border">{Select Plan}</a>
      </article>
    </div>
  </div>
</section>
```

**When to use:** SaaS pricing, subscription plans, service tiers -- any comparative purchase decision.

**Responsive:** Columns stack vertically on mobile. Highlighted tier stays visually prominent via `border-2`. Feature comparison may collapse into an accordion on small screens.

---

### 5. Testimonial Slider

```html
<section class="py-20 px-4">
  <div class="max-w-3xl mx-auto text-center">
    <!-- Single testimonial visible at a time; cycle via JS -->
    <blockquote class="text-2xl md:text-3xl font-medium leading-relaxed">
      "{Quote text goes here. It can span multiple lines comfortably.}"
    </blockquote>
    <div class="mt-8 flex flex-col items-center gap-2">
      <img src="{avatar}" alt="" class="w-12 h-12 rounded-full object-cover" />
      <cite class="not-italic font-semibold">{Name}</cite>
      <span class="text-sm text-gray-500">{Title, Company}</span>
    </div>
    <!-- Navigation -->
    <div class="mt-8 flex items-center justify-center gap-2">
      <button aria-label="Previous">&larr;</button>
      <span class="flex gap-1.5">
        <span class="w-2 h-2 rounded-full bg-black"></span>
        <span class="w-2 h-2 rounded-full bg-gray-300"></span>
        <span class="w-2 h-2 rounded-full bg-gray-300"></span>
      </span>
      <button aria-label="Next">&rarr;</button>
    </div>
  </div>
</section>
```

**When to use:** Social proof sections, case study previews, review highlights.

**Responsive:** Layout stays centered and works well at all sizes. Quote font scales via `text-2xl md:text-3xl`. Navigation dots and arrows remain accessible.

---

### 6. Stats Bar

```html
<section class="py-16 px-4 bg-gray-50">
  <div class="max-w-5xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
    <div>
      <p class="text-4xl md:text-5xl font-bold">{10K+}</p>
      <p class="mt-2 text-sm text-gray-500">{Customers}</p>
    </div>
    <div>
      <p class="text-4xl md:text-5xl font-bold">{99.9%}</p>
      <p class="mt-2 text-sm text-gray-500">{Uptime}</p>
    </div>
    <div>
      <p class="text-4xl md:text-5xl font-bold">{50M+}</p>
      <p class="mt-2 text-sm text-gray-500">{Requests}</p>
    </div>
    <div>
      <p class="text-4xl md:text-5xl font-bold">{24/7}</p>
      <p class="mt-2 text-sm text-gray-500">{Support}</p>
    </div>
  </div>
</section>
```

**When to use:** Trust-building sections, company milestones, platform metrics.

**Responsive:** Wraps to 2x2 grid on mobile via `grid-cols-2 md:grid-cols-4`. Numbers remain large and prominent at every breakpoint.

---

### 7. CTA Banner

```html
<section class="py-20 px-4 bg-black text-white">
  <div class="max-w-3xl mx-auto text-center">
    <h2 class="text-3xl md:text-4xl font-bold">{Ready to get started?}</h2>
    <p class="mt-4 text-lg text-white/70">{Short supporting sentence.}</p>
    <a href="#" class="mt-8 inline-block px-8 py-3 bg-white text-black rounded-lg">{CTA Text}</a>
  </div>
</section>
```

**When to use:** Between content sections as a conversion nudge, before footer as a closing CTA, after a feature or pricing section.

**Responsive:** Stays full-width. Text and button center. Padding adjusts. One of the simplest patterns to keep responsive.

---

### 8. FAQ Accordion

```html
<section class="py-20 px-4">
  <div class="max-w-3xl mx-auto">
    <h2 class="text-3xl md:text-4xl font-bold text-center">{Frequently Asked Questions}</h2>
    <div class="mt-12 divide-y">
      <!-- Repeat for each FAQ item -->
      <details class="group py-4">
        <summary class="flex items-center justify-between cursor-pointer font-medium">
          {Question goes here?}
          <span class="ml-4 transition-transform group-open:rotate-45">+</span>
        </summary>
        <p class="mt-3 text-gray-600">{Answer text is revealed below the question when the user clicks to expand it.}</p>
      </details>
    </div>
  </div>
</section>
```

**When to use:** Support pages, product pages, pricing pages -- anywhere users have predictable questions.

**Responsive:** Naturally works at all widths. Full-width single column. `<details>` provides native expand/collapse without JS. Touch targets are inherently large.

---

### 9. Logo Bar

```html
<section class="py-12 px-4">
  <div class="max-w-5xl mx-auto text-center">
    <p class="text-sm font-medium text-gray-500">{Trusted by leading companies}</p>
    <div class="mt-8 flex flex-wrap items-center justify-center gap-x-12 gap-y-6 opacity-60">
      <img src="{logo-1}" alt="{Company}" class="h-8" />
      <img src="{logo-2}" alt="{Company}" class="h-8" />
      <img src="{logo-3}" alt="{Company}" class="h-8" />
      <img src="{logo-4}" alt="{Company}" class="h-8" />
      <img src="{logo-5}" alt="{Company}" class="h-8" />
    </div>
  </div>
</section>
```

**When to use:** Social proof, partnerships, integrations, press mentions.

**Responsive:** `flex-wrap` handles overflow naturally. Logos wrap to multiple rows on narrow screens. `opacity-60` keeps logos muted so they don't compete with primary content.

---

### 10. Timeline

Horizontal variant:

```html
<section class="py-20 px-4">
  <div class="max-w-4xl mx-auto text-center">
    <h2 class="text-3xl font-bold">{How It Works}</h2>
    <div class="mt-16 hidden md:grid grid-cols-3 gap-8 relative">
      <!-- Connecting line -->
      <div class="absolute top-5 left-[16%] right-[16%] h-0.5 bg-gray-200"></div>
      <!-- Step -->
      <div class="relative">
        <div class="w-10 h-10 mx-auto rounded-full bg-black text-white flex items-center justify-center text-sm font-bold">1</div>
        <h3 class="mt-4 font-semibold">{Step One}</h3>
        <p class="mt-2 text-sm text-gray-600">{Description}</p>
      </div>
      <div class="relative">
        <div class="w-10 h-10 mx-auto rounded-full bg-black text-white flex items-center justify-center text-sm font-bold">2</div>
        <h3 class="mt-4 font-semibold">{Step Two}</h3>
        <p class="mt-2 text-sm text-gray-600">{Description}</p>
      </div>
      <div class="relative">
        <div class="w-10 h-10 mx-auto rounded-full bg-black text-white flex items-center justify-center text-sm font-bold">3</div>
        <h3 class="mt-4 font-semibold">{Step Three}</h3>
        <p class="mt-2 text-sm text-gray-600">{Description}</p>
      </div>
    </div>
  </div>
</section>
```

Vertical variant (also the mobile fallback):

```html
<div class="md:hidden mt-12 space-y-8 relative pl-8 border-l-2 border-gray-200">
  <div class="relative">
    <div class="absolute -left-[calc(1rem+1px)] top-0 w-6 h-6 rounded-full bg-black text-white flex items-center justify-center text-xs">1</div>
    <h3 class="font-semibold">{Step One}</h3>
    <p class="mt-1 text-sm text-gray-600">{Description}</p>
  </div>
  <div class="relative">
    <div class="absolute -left-[calc(1rem+1px)] top-0 w-6 h-6 rounded-full bg-black text-white flex items-center justify-center text-xs">2</div>
    <h3 class="font-semibold">{Step Two}</h3>
    <p class="mt-1 text-sm text-gray-600">{Description}</p>
  </div>
  <div class="relative">
    <div class="absolute -left-[calc(1rem+1px)] top-0 w-6 h-6 rounded-full bg-black text-white flex items-center justify-center text-xs">3</div>
    <h3 class="font-semibold">{Step Three}</h3>
    <p class="mt-1 text-sm text-gray-600">{Description}</p>
  </div>
</div>
```

**When to use:** Onboarding flows, process explanations, company history, product roadmaps.

**Responsive:** Horizontal layout uses `hidden md:grid` so it only shows on desktop. Vertical variant uses `md:hidden` as the mobile fallback. Vertical timelines work natively at all widths.

---

## Navigation Patterns

### 1. Fixed Top Bar

```html
<header class="fixed top-0 inset-x-0 z-50 bg-white/80 backdrop-blur border-b">
  <nav class="max-w-6xl mx-auto flex items-center justify-between px-4 h-16">
    <a href="/" class="font-bold text-lg">{Logo}</a>
    <div class="hidden md:flex items-center gap-8">
      <a href="#" class="text-sm">{Home}</a>
      <a href="#" class="text-sm">{Features}</a>
      <a href="#" class="text-sm">{Pricing}</a>
    </div>
    <a href="#" class="hidden md:inline-block px-4 py-2 bg-black text-white text-sm rounded-lg">{Sign Up}</a>
    <!-- Mobile hamburger trigger -->
    <button class="md:hidden" aria-label="Menu">{Icon}</button>
  </nav>
</header>
<!-- Spacer for fixed header -->
<div class="h-16"></div>
```

**When to use:** Most marketing sites, SaaS products, any site with 3-7 top-level pages.

**Responsive:** Links collapse into hamburger on mobile via `hidden md:flex`. Logo and CTA remain visible. `backdrop-blur` gives a modern frosted-glass effect.

---

### 2. Transparent Overlay

```html
<header class="fixed top-0 inset-x-0 z-50 transition-colors" data-scroll="transparent">
  <!-- JS toggles: bg-transparent → bg-white/80 backdrop-blur border-b on scroll -->
  <nav class="max-w-6xl mx-auto flex items-center justify-between px-4 h-16">
    <a href="/" class="font-bold text-lg text-white">{Logo}</a>
    <div class="hidden md:flex items-center gap-8">
      <a href="#" class="text-sm text-white/80 hover:text-white">{Home}</a>
      <a href="#" class="text-sm text-white/80 hover:text-white">{About}</a>
      <a href="#" class="text-sm text-white/80 hover:text-white">{Contact}</a>
    </div>
    <a href="#" class="hidden md:inline-block px-4 py-2 border border-white text-white text-sm rounded-lg">{CTA}</a>
  </nav>
</header>
```

**When to use:** Full-bleed hero pages, photography or portfolio sites, any design where the hero should feel immersive.

**Responsive:** Same as fixed top bar on mobile. Transparency effect may be dropped for readability on small screens. JS swaps `text-white` to `text-black` when background turns opaque.

---

### 3. Sidebar

```html
<div class="flex min-h-screen">
  <aside class="hidden md:flex md:w-64 flex-col border-r bg-gray-50">
    <div class="p-6 font-bold text-lg">{Logo}</div>
    <nav class="flex-1 px-4 space-y-1">
      <a href="#" class="block px-3 py-2 rounded-lg bg-gray-200 font-medium">{Active Link}</a>
      <a href="#" class="block px-3 py-2 rounded-lg hover:bg-gray-100">{Link 2}</a>
      <a href="#" class="block px-3 py-2 rounded-lg hover:bg-gray-100">{Link 3}</a>
      <a href="#" class="block px-3 py-2 rounded-lg hover:bg-gray-100">{Link 4}</a>
    </nav>
    <div class="p-4 border-t space-y-1">
      <a href="#" class="block px-3 py-2 rounded-lg hover:bg-gray-100 text-sm">{Settings}</a>
      <a href="#" class="block px-3 py-2 rounded-lg hover:bg-gray-100 text-sm">{Logout}</a>
    </div>
  </aside>
  <main class="flex-1 p-8">{Main Content}</main>
</div>
```

**When to use:** Dashboards, admin panels, documentation sites, tools with many navigation items that do not fit in a top bar.

**Responsive:** Sidebar is `hidden md:flex` -- collapses to a hamburger-triggered slide-out panel on mobile. Main content expands to full width. Some designs use a narrow icon-only sidebar (`md:w-16`) on tablet.

---

### 4. Hamburger Mobile

```html
<!-- Mobile nav shell — toggled via JS -->
<header class="md:hidden fixed top-0 inset-x-0 z-50 bg-white border-b">
  <div class="flex items-center justify-between px-4 h-14">
    <a href="/" class="font-bold">{Logo}</a>
    <button aria-label="Toggle menu" aria-expanded="false">{Hamburger Icon}</button>
  </div>
  <!-- Expanded panel (hidden by default, toggled via JS) -->
  <nav class="hidden border-t px-4 py-6 space-y-4 bg-white">
    <a href="#" class="block text-lg">{Home}</a>
    <a href="#" class="block text-lg">{Features}</a>
    <a href="#" class="block text-lg">{Pricing}</a>
    <a href="#" class="block text-lg">{About}</a>
    <a href="#" class="block w-full py-3 text-center bg-black text-white rounded-lg">{Sign Up}</a>
  </nav>
</header>
```

**When to use:** Mobile-first designs, sites with many nav items, any responsive site as the small-screen fallback.

**Responsive:** This IS the responsive fallback. On larger screens, replace with a top bar or sidebar. The `md:hidden` wrapper ensures it only renders on mobile.

---

### 5. Mega Menu

```html
<header class="relative z-50 border-b bg-white">
  <nav class="max-w-6xl mx-auto flex items-center justify-between px-4 h-16">
    <a href="/" class="font-bold text-lg">{Logo}</a>
    <div class="hidden lg:flex items-center gap-8">
      <!-- Trigger -->
      <div class="relative group">
        <button class="text-sm flex items-center gap-1">{Products} <span>&darr;</span></button>
        <!-- Mega panel -->
        <div class="hidden group-hover:block absolute top-full left-1/2 -translate-x-1/2 w-[800px] p-8 bg-white border rounded-lg shadow-lg">
          <div class="grid grid-cols-3 gap-8">
            <div>
              <h4 class="text-xs font-semibold uppercase text-gray-400">{Category A}</h4>
              <ul class="mt-3 space-y-2 text-sm">
                <li><a href="#">{Link 1}</a></li>
                <li><a href="#">{Link 2}</a></li>
                <li><a href="#">{Link 3}</a></li>
              </ul>
            </div>
            <div>
              <h4 class="text-xs font-semibold uppercase text-gray-400">{Category B}</h4>
              <ul class="mt-3 space-y-2 text-sm">
                <li><a href="#">{Link 1}</a></li>
                <li><a href="#">{Link 2}</a></li>
              </ul>
            </div>
            <div>
              <h4 class="text-xs font-semibold uppercase text-gray-400">{Category C}</h4>
              <ul class="mt-3 space-y-2 text-sm">
                <li><a href="#">{Link 1}</a></li>
                <li><a href="#">{Link 2}</a></li>
              </ul>
            </div>
          </div>
          <!-- Optional featured card -->
          <div class="mt-6 pt-6 border-t flex gap-4 items-center">
            <div class="w-16 h-16 rounded-lg bg-gray-100"></div>
            <div>
              <p class="font-medium text-sm">{Featured Item}</p>
              <p class="text-xs text-gray-500">{Description}</p>
            </div>
          </div>
        </div>
      </div>
      <a href="#" class="text-sm">{Solutions}</a>
      <a href="#" class="text-sm">{Pricing}</a>
    </div>
    <a href="#" class="hidden lg:inline-block px-4 py-2 bg-black text-white text-sm rounded-lg">{CTA}</a>
  </nav>
</header>
```

**When to use:** Enterprise sites, e-commerce, platforms with many product lines or feature categories.

**Responsive:** Collapses into nested accordion menus within the hamburger slide-out on mobile. Categories become expandable `<details>` sections. Uses `hidden lg:flex` since mega menus need more horizontal space than standard navs.

---

## Footer Patterns

### 1. Multi-Column

```html
<footer class="bg-gray-900 text-white pt-16 pb-8 px-4">
  <div class="max-w-6xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-8">
    <div>
      <p class="font-bold text-lg">{Logo}</p>
      <p class="mt-2 text-sm text-gray-400">{Tagline text}</p>
    </div>
    <div>
      <h4 class="font-semibold text-sm">{Product}</h4>
      <ul class="mt-3 space-y-2 text-sm text-gray-400">
        <li><a href="#">{Features}</a></li>
        <li><a href="#">{Pricing}</a></li>
        <li><a href="#">{Changelog}</a></li>
        <li><a href="#">{API}</a></li>
      </ul>
    </div>
    <div>
      <h4 class="font-semibold text-sm">{Company}</h4>
      <ul class="mt-3 space-y-2 text-sm text-gray-400">
        <li><a href="#">{About}</a></li>
        <li><a href="#">{Careers}</a></li>
        <li><a href="#">{Blog}</a></li>
        <li><a href="#">{Press}</a></li>
      </ul>
    </div>
    <div>
      <h4 class="font-semibold text-sm">{Support}</h4>
      <ul class="mt-3 space-y-2 text-sm text-gray-400">
        <li><a href="#">{Help}</a></li>
        <li><a href="#">{Docs}</a></li>
        <li><a href="#">{Contact}</a></li>
        <li><a href="#">{Status}</a></li>
      </ul>
    </div>
  </div>
  <div class="max-w-6xl mx-auto mt-12 pt-8 border-t border-gray-800 flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-gray-400">
    <p>&copy; {Year} {Company}. All rights reserved.</p>
    <div class="flex gap-6">
      <a href="#">{Privacy}</a>
      <a href="#">{Terms}</a>
    </div>
  </div>
</footer>
```

**When to use:** Most marketing sites, SaaS products, any site with enough pages to warrant organized link groups.

**Responsive:** `grid-cols-2 md:grid-cols-4` -- columns pair up on mobile. Link groups may become accordions. Bottom bar wraps via `flex-col sm:flex-row`.

---

### 2. Minimal Centered

```html
<footer class="py-8 px-4 text-center text-sm text-gray-500">
  <div class="flex items-center justify-center gap-4 flex-wrap">
    <span>&copy; {Year} {Company}</span>
    <a href="#">{Privacy}</a>
    <a href="#">{Terms}</a>
  </div>
</footer>
```

**When to use:** Single-page sites, apps, landing pages, MVPs -- anywhere a full footer is unnecessary.

**Responsive:** Naturally responsive. Links wrap via `flex-wrap` on very narrow screens.

---

### 3. CTA Footer

```html
<div>
  <!-- CTA section -->
  <section class="py-20 px-4 bg-black text-white text-center">
    <h2 class="text-3xl md:text-4xl font-bold">{Ready to start building?}</h2>
    <a href="#" class="mt-8 inline-block px-8 py-3 bg-white text-black rounded-lg">{Get Started}</a>
  </section>
  <!-- Standard footer below -->
  <footer class="bg-gray-900 text-white pt-12 pb-8 px-4">
    <div class="max-w-6xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-8">
      <div><p class="font-bold">{Logo}</p></div>
      <div>
        <h4 class="font-semibold text-sm">{Product}</h4>
        <ul class="mt-3 space-y-2 text-sm text-gray-400">
          <li><a href="#">{Features}</a></li>
          <li><a href="#">{Pricing}</a></li>
        </ul>
      </div>
      <div>
        <h4 class="font-semibold text-sm">{Company}</h4>
        <ul class="mt-3 space-y-2 text-sm text-gray-400">
          <li><a href="#">{About}</a></li>
          <li><a href="#">{Blog}</a></li>
        </ul>
      </div>
      <div>
        <h4 class="font-semibold text-sm">{Support}</h4>
        <ul class="mt-3 space-y-2 text-sm text-gray-400">
          <li><a href="#">{Help}</a></li>
          <li><a href="#">{Docs}</a></li>
        </ul>
      </div>
    </div>
    <div class="max-w-6xl mx-auto mt-12 pt-8 border-t border-gray-800 text-sm text-gray-400 text-center">
      <p>&copy; {Year} {Company} &middot; <a href="#">{Privacy}</a> &middot; <a href="#">{Terms}</a></p>
    </div>
  </footer>
</div>
```

**When to use:** Conversion-focused pages where one last CTA before the footer can capture stragglers.

**Responsive:** CTA section stacks naturally. Link columns collapse as in the multi-column pattern.

---

### 4. Newsletter Signup

```html
<footer class="bg-gray-900 text-white pt-16 pb-8 px-4">
  <div class="max-w-xl mx-auto text-center">
    <h3 class="text-xl font-bold">{Stay in the loop}</h3>
    <form class="mt-6 flex flex-col sm:flex-row gap-3">
      <input type="email" placeholder="you@email.com" class="flex-1 px-4 py-3 rounded-lg bg-gray-800 border border-gray-700 text-white" />
      <button type="submit" class="px-6 py-3 bg-white text-black rounded-lg font-medium">{Subscribe}</button>
    </form>
    <div class="mt-8 flex items-center justify-center gap-4">
      <!-- Social icons -->
      <a href="#" aria-label="Twitter">{tw}</a>
      <a href="#" aria-label="LinkedIn">{li}</a>
      <a href="#" aria-label="GitHub">{gh}</a>
      <a href="#" aria-label="Instagram">{ig}</a>
    </div>
  </div>
  <div class="max-w-6xl mx-auto mt-12 pt-8 border-t border-gray-800 text-sm text-gray-400 text-center">
    <p>&copy; {Year} {Company} &middot; <a href="#">{Privacy}</a> &middot; <a href="#">{Terms}</a></p>
  </div>
</footer>
```

**When to use:** Content businesses, newsletters, communities, any product that benefits from an email list.

**Responsive:** Input and button stack vertically on mobile via `flex-col sm:flex-row`. Social icons remain in a single row. Legal links wrap as needed.

---

## Page Archetypes

Compositions of the patterns defined above. Use these as assembly guides -- each comment references a pattern you can copy from the corresponding section.

### 1. Landing Page

```html
<!-- Landing Page -->
<div class="min-h-screen flex flex-col">
  <!-- Nav: Fixed Top Bar -->
  <!-- Hero: Full-Bleed Image or Split Layout -->
  <!-- Social Proof: Logo Bar -->
  <!-- Features: Feature Grid -->
  <!-- Deep Dive: Alternating Rows -->
  <!-- Testimonials: Testimonial Slider -->
  <!-- Pricing: Pricing Table -->
  <!-- CTA: CTA Banner -->
  <!-- FAQ: FAQ Accordion -->
  <!-- Footer: Multi-Column -->
</div>
```

**Key considerations:** Each section should have one clear purpose. Alternate light/dark backgrounds for visual rhythm. Keep CTAs consistent in style throughout.

---

### 2. Dashboard

```html
<!-- Dashboard -->
<div class="flex min-h-screen">
  <!-- Nav: Sidebar -->
  <main class="flex-1">
    <!-- Top Bar: search + avatar + notifications -->
    <!-- Stats: Stats Bar (as card grid) -->
    <!-- Content: charts, tables, activity feeds -->
  </main>
</div>
```

**Key considerations:** Sidebar collapses on mobile. Stat cards reflow to fewer columns. Tables become scrollable or switch to card view. Prioritize information density without overwhelming.

---

### 3. Documentation

```html
<!-- Documentation -->
<div class="min-h-screen flex flex-col">
  <!-- Nav: Fixed Top Bar (with search + version selector) -->
  <div class="flex flex-1">
    <!-- Left: Sidebar (collapsible section nav) -->
    <main class="flex-1 max-w-3xl mx-auto px-8 py-12">
      <!-- Content: prose with headings, code blocks, callouts -->
    </main>
    <!-- Right: on-page ToC sidebar (hidden on mobile) -->
  </div>
</div>
```

**Key considerations:** Left sidebar is primary nav (collapsible sections). Right sidebar is on-page ToC (hidden on mobile). Content column max-width 60-80 characters for readability. Code blocks need horizontal scrolling.

---

### 4. Portfolio

```html
<!-- Portfolio -->
<div class="min-h-screen flex flex-col">
  <!-- Nav: Fixed Top Bar (minimal, name-based) -->
  <!-- Hero: Centered Text or Split Layout (name + title + statement) -->
  <!-- Work: Feature Grid (2-col project thumbnails with hover) -->
  <!-- About: Split Layout (photo + bio + skills) -->
  <!-- Contact: CTA Banner or contact form -->
  <!-- Footer: Minimal Centered -->
</div>
```

**Key considerations:** Project grid can use masonry for varied image sizes. Hover states should preview project details. Image quality is critical. Keep the about section personal and concise.

---

### 5. E-commerce Product

```html
<!-- E-commerce Product -->
<div class="min-h-screen flex flex-col">
  <!-- Nav: Fixed Top Bar (with search + cart + account) -->
  <!-- Breadcrumbs -->
  <!-- Product: Split Layout (image gallery left, details right) -->
  <!-- Tabs: Description | Specs | Reviews -->
  <!-- Related: Card Carousel -->
  <!-- Footer: Multi-Column -->
</div>
```

**Key considerations:** Image gallery is the primary selling tool -- support zoom and multiple angles. Add-to-cart must be visible without scrolling on desktop. Reviews build trust. Related products increase average order value.

---

### 6. Blog / Article

```html
<!-- Blog / Article -->
<div class="min-h-screen flex flex-col">
  <!-- Nav: Fixed Top Bar -->
  <!-- Hero: Full-Bleed Image (article hero) -->
  <!-- Meta: title + author + date + read time -->
  <div class="flex">
    <!-- Content: prose column (max-w-prose) -->
    <!-- Sidebar: author bio, related posts, newsletter (hidden on mobile) -->
  </div>
  <!-- Footer: Newsletter Signup or Multi-Column -->
</div>
```

**Key considerations:** Content column max-width 680-720px for readability. Sidebar hidden on mobile. Clear typography hierarchy H1-H4. Include share buttons and estimated read time.

---

### 7. Pricing Page

```html
<!-- Pricing Page -->
<div class="min-h-screen flex flex-col">
  <!-- Nav: Fixed Top Bar -->
  <!-- Hero: Centered Text (headline + monthly/annual toggle) -->
  <!-- Pricing: Pricing Table (3-4 tiers) -->
  <!-- Comparison: Feature Grid (detailed checkmark matrix) -->
  <!-- FAQ: FAQ Accordion (pricing objections) -->
  <!-- Social Proof: Testimonial Slider -->
  <!-- CTA: CTA Banner -->
  <!-- Footer: Multi-Column -->
</div>
```

**Key considerations:** Monthly/annual toggle is expected. Highlight the recommended tier. Feature comparison should use checkmarks, not paragraph text. FAQ should address pricing objections. Enterprise tier with "Contact Us" handles edge cases.

---

### 8. Onboarding Wizard

```html
<!-- Onboarding Wizard -->
<div class="min-h-screen flex flex-col">
  <!-- Minimal header: Logo + Skip link -->
  <!-- Progress: Timeline (horizontal, step-based) -->
  <main class="flex-1 flex items-center justify-center px-4">
    <div class="w-full max-w-md">
      <!-- Step title + instructions -->
      <!-- Form fields for current step -->
      <!-- Navigation: Back + Continue buttons -->
    </div>
  </main>
</div>
```

**Key considerations:** Progress bar must reflect actual completion, not just step count. Each step should have a single clear objective. Back button must preserve entered data. Final step shows a summary before confirmation. Keep to 3-5 steps maximum.
