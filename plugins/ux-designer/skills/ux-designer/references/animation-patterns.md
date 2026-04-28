# Animation Patterns

Copy-pasteable animation patterns for design generation. Load this reference when the user wants animations, transitions, or interactive effects. Every pattern includes a `prefers-reduced-motion` fallback.

## Accessibility First

Wrap all animations with this global reduced-motion query. Place it at the end of your stylesheet so it overrides everything:

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

---

## 1. Entrance Animations (CSS-only)

### Fade In

```css
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.fade-in {
  animation: fadeIn 0.6s ease forwards;
  opacity: 0;
}
```

### Slide Up

```css
@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.slide-up {
  animation: slideUp 0.6s ease forwards;
  opacity: 0;
}
```

### Scale In

```css
@keyframes scaleIn {
  from {
    opacity: 0;
    transform: scale(0.95);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

.scale-in {
  animation: scaleIn 0.5s ease forwards;
  opacity: 0;
}
```

### Blur In

```css
@keyframes blurIn {
  from {
    opacity: 0;
    filter: blur(10px);
  }
  to {
    opacity: 1;
    filter: blur(0);
  }
}

.blur-in {
  animation: blurIn 0.7s ease forwards;
  opacity: 0;
}
```

### Slide In From Side

```css
@keyframes slideInLeft {
  from {
    opacity: 0;
    transform: translateX(-30px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

@keyframes slideInRight {
  from {
    opacity: 0;
    transform: translateX(30px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.slide-in-left {
  animation: slideInLeft 0.6s ease forwards;
  opacity: 0;
}

.slide-in-right {
  animation: slideInRight 0.6s ease forwards;
  opacity: 0;
}
```

### Staggering Entrance Animations

Apply incremental delays to child elements for a cascading entrance:

```css
.stagger > :nth-child(1) { animation-delay: 0ms; }
.stagger > :nth-child(2) { animation-delay: 100ms; }
.stagger > :nth-child(3) { animation-delay: 200ms; }
.stagger > :nth-child(4) { animation-delay: 300ms; }
.stagger > :nth-child(5) { animation-delay: 400ms; }
.stagger > :nth-child(6) { animation-delay: 500ms; }
```

Or generate dynamically with a CSS custom property:

```css
.stagger > * {
  animation-delay: calc(var(--i, 0) * 100ms);
}
```

```html
<div class="stagger">
  <div class="slide-up" style="--i: 0">First</div>
  <div class="slide-up" style="--i: 1">Second</div>
  <div class="slide-up" style="--i: 2">Third</div>
</div>
```

---

## 2. Scroll-Triggered Animations

### CSS-only (modern browsers)

Uses `animation-timeline` for scroll-linked animations. Supported in Chrome/Edge 115+.

```css
.scroll-fade-in {
  animation: fadeIn linear both;
  animation-timeline: view();
  animation-range: entry 0% entry 100%;
}

.scroll-slide-up {
  animation: slideUp linear both;
  animation-timeline: view();
  animation-range: entry 0% entry 100%;
}

/* Browser support: Chrome 115+, Edge 115+. Firefox/Safari fall back to no animation
   (the @keyframes ending state holds), which is acceptable. For full coverage, use
   the Intersection Observer approach below. */
```

### JavaScript (Intersection Observer)

Reusable observer that adds a `.visible` class when elements scroll into view:

```javascript
function createScrollObserver(options = {}) {
  const {
    threshold = 0.1,    // 0.1 = trigger early, 0.5 = trigger at center
    rootMargin = '0px',
    once = true,        // unobserve after first trigger
    selector = '[data-animate]',
  } = options;

  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        if (once) observer.unobserve(entry.target);
      } else if (!once) {
        entry.target.classList.remove('visible');
      }
    });
  }, { threshold, rootMargin });

  document.querySelectorAll(selector).forEach((el) => observer.observe(el));

  // Return both the observer and a cleanup fn so SPA components can teardown cleanly
  return {
    observer,
    destroy: () => observer.disconnect(),
  };
}

// Initialize
const scroll = createScrollObserver({ threshold: 0.1 });

// On SPA route change / component unmount:
// scroll.destroy();
```

Combine with entrance animation classes by toggling on `.visible`:

```css
[data-animate] {
  opacity: 0;
  transform: translateY(20px);
  transition: opacity 0.6s ease, transform 0.6s ease;
}

[data-animate].visible {
  opacity: 1;
  transform: translateY(0);
}

/* Per-element delay via data attribute */
[data-animate][data-delay="100"] { transition-delay: 100ms; }
[data-animate][data-delay="200"] { transition-delay: 200ms; }
[data-animate][data-delay="300"] { transition-delay: 300ms; }
```

```html
<div data-animate>Fades in on scroll</div>
<div data-animate data-delay="200">Fades in 200ms later</div>
```

---

## 3. Hover Effects

### Scale

```css
.hover-scale {
  transition: transform 300ms ease;
}

.hover-scale:hover {
  transform: scale(1.03);
}
```

### Lift + Shadow

```css
.hover-lift {
  transition: transform 300ms ease, box-shadow 300ms ease;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.hover-lift:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 24px rgba(0, 0, 0, 0.12);
}
```

### Glow

```css
.hover-glow {
  transition: box-shadow 400ms ease;
}

.hover-glow:hover {
  box-shadow: 0 0 20px rgba(59, 130, 246, 0.4),
              0 0 40px rgba(59, 130, 246, 0.15);
}
```

Customize the glow color by changing the rgba values, or use a CSS custom property:

```css
.hover-glow {
  --glow-color: 59, 130, 246; /* blue-500 */
  transition: box-shadow 400ms ease;
}

.hover-glow:hover {
  box-shadow: 0 0 20px rgba(var(--glow-color), 0.4),
              0 0 40px rgba(var(--glow-color), 0.15);
}
```

### Color Shift

```css
.hover-color-shift {
  background-color: var(--bg-default, #f3f4f6);
  transition: background-color 300ms ease, color 300ms ease;
}

.hover-color-shift:hover {
  background-color: var(--bg-hover, #3b82f6);
  color: var(--text-hover, #ffffff);
}
```

### Underline Expand

```css
.hover-underline {
  position: relative;
  display: inline-block;
}

.hover-underline::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 50%;
  width: 0;
  height: 2px;
  background-color: currentColor;
  transition: width 300ms ease, left 300ms ease;
}

.hover-underline:hover::after {
  width: 100%;
  left: 0;
}
```

### Image Zoom

```css
.hover-zoom {
  overflow: hidden;
  border-radius: inherit;
}

.hover-zoom img {
  transition: transform 400ms ease;
  display: block;
  width: 100%;
}

.hover-zoom:hover img {
  transform: scale(1.1);
}
```

---

## 4. Smooth Scrolling

### CSS-only

```css
html {
  scroll-behavior: smooth;
}

@media (prefers-reduced-motion: reduce) {
  html {
    scroll-behavior: auto;
  }
}
```

### Lenis Integration (premium smooth scroll)

Install:

```bash
npm install lenis
```

Setup with proper cleanup:

```javascript
import Lenis from 'lenis';
import 'lenis/dist/lenis.css';

let lenis;
let rafId;

export function initLenis() {
  // Respect motion preferences
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return null;

  lenis = new Lenis({
    duration: 1.2,
    easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)), // easeOutExpo
    orientation: 'vertical',
    smoothWheel: true,
  });

  function raf(time) {
    lenis.raf(time);
    rafId = requestAnimationFrame(raf);
  }
  rafId = requestAnimationFrame(raf);

  return lenis;
}

export function destroyLenis() {
  if (rafId) cancelAnimationFrame(rafId);
  if (lenis) lenis.destroy();
  rafId = null;
  lenis = null;
}
```

For SPAs (React/Vue/Svelte), call `destroyLenis()` on unmount or route change. Skipping cleanup leaks the RAF loop and continues running after navigation.

Scroll to element programmatically:

```javascript
lenis.scrollTo('#target-section', {
  offset: -80,       // account for fixed header
  duration: 1.5,
  easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
});
```

---

## 5. Parallax

### CSS-only Parallax

Uses `perspective` and `translateZ` to create depth layers without JavaScript:

```css
.parallax-container {
  height: 100vh;
  overflow-x: hidden;
  overflow-y: auto;
  perspective: 1px;
}

.parallax-layer {
  position: absolute;
  inset: 0;
}

.parallax-layer--back {
  transform: translateZ(-2px) scale(3);
  z-index: -1;
}

.parallax-layer--base {
  transform: translateZ(0);
  z-index: 1;
}

.parallax-layer--front {
  transform: translateZ(0.5px) scale(0.5);
  z-index: 2;
}
```

```html
<div class="parallax-container">
  <div class="parallax-layer parallax-layer--back">
    <img src="background.jpg" alt="" />
  </div>
  <div class="parallax-layer parallax-layer--base">
    <section>Main content here</section>
  </div>
</div>
```

### JS-based Parallax

Simple scroll-based `translateY` at different rates per layer:

```javascript
function initParallax() {
  // Respect motion preferences — bail entirely for reduced-motion users
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    return () => {}; // no-op cleanup
  }

  const layers = document.querySelectorAll('[data-parallax]');

  function updateParallax() {
    const scrollY = window.scrollY;
    layers.forEach((layer) => {
      const speed = parseFloat(layer.dataset.parallax) || 0.5;
      const offset = scrollY * speed;
      layer.style.transform = `translateY(${offset}px)`;
    });
  }

  let ticking = false;
  function onScroll() {
    if (!ticking) {
      requestAnimationFrame(() => {
        updateParallax();
        ticking = false;
      });
      ticking = true;
    }
  }

  window.addEventListener('scroll', onScroll, { passive: true });
  updateParallax(); // initial paint

  // Return cleanup fn for SPA component unmount
  return () => window.removeEventListener('scroll', onScroll);
}

const cleanup = initParallax();
// On unmount: cleanup();
```

```html
<!-- speed < 1 = slower than scroll, > 1 = faster -->
<div data-parallax="0.3">Slow background</div>
<div data-parallax="0.6">Medium layer</div>
<div data-parallax="1.0">Moves with scroll</div>
```

---

## 6. Page/Section Transitions

### Fade Between Sections

```css
.section-transition {
  opacity: 0;
  transition: opacity 0.5s ease;
}

.section-transition.active {
  opacity: 1;
}
```

```javascript
function showSection(sectionId) {
  document.querySelectorAll('.section-transition').forEach((s) => {
    s.classList.remove('active');
  });

  const target = document.getElementById(sectionId);
  if (target) {
    requestAnimationFrame(() => {
      target.classList.add('active');
    });
  }
}
```

### Slide Transitions

```css
.slide-container {
  display: grid;
  grid-template-areas: "main";
  overflow: hidden;
}

.slide-panel {
  grid-area: main;
  transform: translateX(100%);
  opacity: 0;
  transition: transform 0.5s ease, opacity 0.5s ease;
}

.slide-panel.active {
  transform: translateX(0);
  opacity: 1;
}

.slide-panel.exit-left {
  transform: translateX(-100%);
  opacity: 0;
}
```

### View Transitions API (Chrome 111+)

```css
::view-transition-old(root) {
  animation: fadeOut 0.3s ease forwards;
}

::view-transition-new(root) {
  animation: fadeIn 0.3s ease forwards;
}

@keyframes fadeOut {
  from { opacity: 1; }
  to { opacity: 0; }
}
```

Trigger a view transition in JavaScript:

```javascript
function navigateTo(url) {
  if (!document.startViewTransition) {
    window.location.href = url;
    return;
  }

  document.startViewTransition(() => {
    window.location.href = url;
  });
}
```

Named view transitions for shared element animations:

```css
.card-image {
  view-transition-name: hero-image;
}

::view-transition-old(hero-image) {
  animation: scaleDown 0.3s ease forwards;
}

::view-transition-new(hero-image) {
  animation: scaleUp 0.3s ease forwards;
}

@keyframes scaleDown {
  from { transform: scale(1); }
  to { transform: scale(0.8); opacity: 0; }
}

@keyframes scaleUp {
  from { transform: scale(0.8); opacity: 0; }
  to { transform: scale(1); opacity: 1; }
}
```

---

## 7. Micro-interactions

### Button Press

```css
.btn-press {
  transition: transform 150ms ease;
}

.btn-press:active {
  transform: scale(0.97);
}
```

### Toggle Switch

```css
.toggle {
  position: relative;
  width: 48px;
  height: 26px;
  background: #d1d5db;
  border-radius: 13px;
  border: none;
  cursor: pointer;
  transition: background-color 300ms ease;
  padding: 0;
}

.toggle::after {
  content: '';
  position: absolute;
  top: 3px;
  left: 3px;
  width: 20px;
  height: 20px;
  background: #ffffff;
  border-radius: 50%;
  transition: transform 300ms ease;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.15);
}

.toggle[aria-checked="true"] {
  background: #3b82f6;
}

.toggle[aria-checked="true"]::after {
  transform: translateX(22px);
}
```

```html
<button class="toggle" role="switch" aria-checked="false"
        onclick="this.setAttribute('aria-checked', this.getAttribute('aria-checked') === 'true' ? 'false' : 'true')">
  <span class="sr-only">Toggle setting</span>
</button>
```

### Loading Spinner

```css
@keyframes spin {
  to { transform: rotate(360deg); }
}

.spinner {
  width: 24px;
  height: 24px;
  border: 3px solid #e5e7eb;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
```

### Success Checkmark

```css
@keyframes drawCheck {
  to { stroke-dashoffset: 0; }
}

@keyframes scaleCheck {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.1); }
}

.checkmark-circle {
  stroke: #22c55e;
  fill: none;
  stroke-width: 2;
  stroke-dasharray: 166;
  stroke-dashoffset: 166;
  animation: drawCheck 0.6s ease forwards;
}

.checkmark-check {
  stroke: #22c55e;
  fill: none;
  stroke-width: 3;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-dasharray: 48;
  stroke-dashoffset: 48;
  animation: drawCheck 0.3s 0.4s ease forwards;
}

.checkmark-svg {
  animation: scaleCheck 0.4s 0.6s ease both;
}
```

```html
<svg class="checkmark-svg" width="52" height="52" viewBox="0 0 52 52">
  <circle class="checkmark-circle" cx="26" cy="26" r="25" />
  <path class="checkmark-check" d="M14.1 27.2l7.1 7.2 16.7-16.8" />
</svg>
```

### Skeleton Loading

```css
@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}

.skeleton {
  background: linear-gradient(
    90deg,
    #e5e7eb 25%,
    #f3f4f6 50%,
    #e5e7eb 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.5s ease-in-out infinite;
  border-radius: 4px;
}

.skeleton-text {
  height: 1em;
  margin-bottom: 0.5em;
}

.skeleton-text:last-child {
  width: 60%;
}

.skeleton-avatar {
  width: 48px;
  height: 48px;
  border-radius: 50%;
}

.skeleton-image {
  width: 100%;
  height: 200px;
}
```

### Number Counter

```javascript
function animateCounter(element, target, duration = 2000) {
  const start = parseInt(element.textContent, 10) || 0;
  const range = target - start;
  const startTime = performance.now();

  function update(currentTime) {
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1);

    // easeOutQuart for a satisfying deceleration
    const eased = 1 - Math.pow(1 - progress, 4);
    const current = Math.round(start + range * eased);

    element.textContent = current.toLocaleString();

    if (progress < 1) {
      requestAnimationFrame(update);
    }
  }

  requestAnimationFrame(update);
}

// Usage
const el = document.querySelector('.counter');
animateCounter(el, 12500, 2000);
```

```html
<span class="counter" data-target="12500">0</span>
```

---

## 8. Advanced Patterns

### Stagger Children

Automatically stagger animation delay for each child element:

```css
.stagger-children > * {
  opacity: 0;
  transform: translateY(15px);
  transition: opacity 0.4s ease, transform 0.4s ease;
}

.stagger-children.visible > * {
  opacity: 1;
  transform: translateY(0);
}
```

```javascript
function applyStagger(container, delayPerChild = 100) {
  // Idempotent — reset any prior delays before applying so re-runs don't compound
  Array.from(container.children).forEach((child, i) => {
    child.style.transitionDelay = `${i * delayPerChild}ms`;
  });
}

function clearStagger(container) {
  Array.from(container.children).forEach((child) => {
    child.style.transitionDelay = '';
  });
}

// Usage with Intersection Observer (one-shot)
const staggerContainers = document.querySelectorAll('.stagger-children');
const observer = new IntersectionObserver((entries) => {
  entries.forEach((entry) => {
    if (entry.isIntersecting) {
      applyStagger(entry.target, 100);
      requestAnimationFrame(() => entry.target.classList.add('visible'));
      observer.unobserve(entry.target);
    }
  });
}, { threshold: 0.1 });

staggerContainers.forEach((el) => observer.observe(el));
```

### Text Reveal

Character-by-character reveal using CSS and minimal JS:

```css
.text-reveal .char {
  display: inline-block;
  opacity: 0;
  transform: translateY(20px);
  transition: opacity 0.3s ease, transform 0.3s ease;
}

.text-reveal.visible .char {
  opacity: 1;
  transform: translateY(0);
}
```

```javascript
function splitTextIntoChars(element) {
  const text = element.textContent;
  element.textContent = '';
  element.setAttribute('aria-label', text);

  text.split('').forEach((char, i) => {
    const span = document.createElement('span');
    span.classList.add('char');
    span.style.transitionDelay = `${i * 30}ms`;
    span.textContent = char === ' ' ? ' ' : char;
    span.setAttribute('aria-hidden', 'true');
    element.appendChild(span);
  });
}

// Word-by-word variant
function splitTextIntoWords(element) {
  const text = element.textContent;
  element.textContent = '';
  element.setAttribute('aria-label', text);

  text.split(' ').forEach((word, i) => {
    const span = document.createElement('span');
    span.classList.add('char'); // reuses same animation class
    span.style.transitionDelay = `${i * 80}ms`;
    span.textContent = word;
    span.setAttribute('aria-hidden', 'true');
    element.appendChild(span);

    // Add space between words
    if (i < text.split(' ').length - 1) {
      element.appendChild(document.createTextNode(' '));
    }
  });
}

// Initialize
document.querySelectorAll('.text-reveal').forEach(splitTextIntoChars);
```

### Magnetic Cursor

Element subtly follows the cursor when hovering within a radius:

```css
.magnetic {
  transition: transform 0.3s ease;
}
```

```javascript
function initMagnetic(selector, strength = 0.3) {
  document.querySelectorAll(selector).forEach((el) => {
    el.addEventListener('mousemove', (e) => {
      const rect = el.getBoundingClientRect();
      const centerX = rect.left + rect.width / 2;
      const centerY = rect.top + rect.height / 2;

      const deltaX = (e.clientX - centerX) * strength;
      const deltaY = (e.clientY - centerY) * strength;

      el.style.transform = `translate(${deltaX}px, ${deltaY}px)`;
    });

    el.addEventListener('mouseleave', () => {
      el.style.transform = 'translate(0, 0)';
    });
  });
}

initMagnetic('.magnetic', 0.3);
```

```html
<button class="magnetic">Hover me</button>
```

### Gradient Animation

Slowly shifting background gradient:

```css
@keyframes gradientShift {
  0% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}

.animated-gradient {
  background: linear-gradient(
    -45deg,
    #ee7752,
    #e73c7e,
    #23a6d5,
    #23d5ab
  );
  background-size: 400% 400%;
  animation: gradientShift 15s ease infinite;
}
```

### Marquee / Ticker

Infinite horizontal scroll of logos or text, CSS-only:

```css
.marquee {
  overflow: hidden;
  position: relative;
  width: 100%;
}

.marquee-track {
  display: flex;
  width: max-content;
  animation: marqueeScroll 30s linear infinite;
}

.marquee-track:hover {
  animation-play-state: paused;
}

@keyframes marqueeScroll {
  from { transform: translateX(0); }
  to { transform: translateX(-50%); }
}

.marquee-item {
  flex-shrink: 0;
  padding: 0 2rem;
}
```

```html
<div class="marquee" aria-label="Partner logos">
  <div class="marquee-track">
    <!-- Duplicate the full set of items so the loop is seamless -->
    <div class="marquee-item"><img src="logo1.svg" alt="Partner 1" /></div>
    <div class="marquee-item"><img src="logo2.svg" alt="Partner 2" /></div>
    <div class="marquee-item"><img src="logo3.svg" alt="Partner 3" /></div>
    <div class="marquee-item"><img src="logo4.svg" alt="Partner 4" /></div>
    <!-- Duplicate set for seamless loop -->
    <div class="marquee-item"><img src="logo1.svg" alt="" aria-hidden="true" /></div>
    <div class="marquee-item"><img src="logo2.svg" alt="" aria-hidden="true" /></div>
    <div class="marquee-item"><img src="logo3.svg" alt="" aria-hidden="true" /></div>
    <div class="marquee-item"><img src="logo4.svg" alt="" aria-hidden="true" /></div>
  </div>
</div>
```

Reverse direction variant:

```css
.marquee-track--reverse {
  animation-direction: reverse;
}
```

---

## Framework-Specific Notes

### React

Use **CSS classes** for simple entrance/hover/micro-interaction animations. Reach for **framer-motion** when you need:
- Layout animations (animating between DOM positions)
- Gesture-driven animations (drag, pan, pinch)
- Exit animations (`AnimatePresence`)
- Orchestrated sequences across components

```bash
npm install framer-motion
```

```jsx
import { motion, AnimatePresence } from 'framer-motion';

<AnimatePresence>
  {isVisible && (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.3 }}
    />
  )}
</AnimatePresence>
```

### Vue

Use built-in `<Transition>` and `<TransitionGroup>` components. They pair naturally with the CSS classes defined in this file.

```vue
<Transition name="fade">
  <div v-if="show">Content</div>
</Transition>
```

```css
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.3s ease;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
}
```

### Svelte

Use built-in `transition:` directives for zero-dependency animations:

```svelte
<script>
  import { fade, fly, slide, scale } from 'svelte/transition';
</script>

{#if visible}
  <div transition:fly={{ y: 20, duration: 300 }}>
    Flies in from below
  </div>
{/if}
```

### Astro

Use `<ViewTransitions />` for automatic page transition animations across MPA routes:

```astro
---
import { ViewTransitions } from 'astro:transitions';
---
<html>
  <head>
    <ViewTransitions />
  </head>
  <body>
    <main transition:animate="slide">
      <slot />
    </main>
  </body>
</html>
```

Supported transition presets: `fade`, `slide`, `none`. Custom transitions use the same `::view-transition` CSS API shown in Section 6.
