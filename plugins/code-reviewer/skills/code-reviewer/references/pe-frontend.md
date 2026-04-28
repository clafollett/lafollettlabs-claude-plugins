---
name: PE-Frontend
activates_on: ["*.vue", "*.tsx", "*.jsx", "*.stories.ts", "tailwind.config.*", "nuxt.config.*", "vite.config.*"]
---

# PE-Frontend — Review Reference

## Test Commands

```bash
cd <worktree>/crew && npm ci && npm run typecheck && npm run generate && npm test
```

If Storybook components changed:
```bash
cd <worktree>/crew && npm run build-storybook
```

Test failures are CRITICAL findings. TypeScript errors are HIGH findings.

## Three-Pass Review

### Pass 1: Architecture

- Component composition — single responsibility, proper prop drilling vs composables
- Reactive state management — no stale refs, proper use of `ref` vs `reactive`
- `computed` vs `watch` — computed for derived state, watch for side effects only
- Route middleware — auth checks in middleware, not in page components
- Layout usage — correct layout applied, no layout logic in pages
- Code splitting — lazy-loaded routes, dynamic imports for heavy components
- Design token adherence — uses semantic tokens (`--cb-primary`, `--cb-border`), not raw hex
- No legacy aliases (`--cb-teal-deep` etc.) in new code

### Pass 2: Quality (includes test execution)

- Run test suite — failures are CRITICAL
- TypeScript strict — `tsc --noEmit` clean, no `any` casts hiding bugs
- Warm palette — no cold blues, clinical whites, or neon (Board directive)
- Component keys — list rendering uses stable keys, not array index
- Cleanup on unmount — intervals, subscriptions, event listeners cleared in `onBeforeUnmount`
- Error boundaries — network failures, auth expiry, empty states all handled
- Mobile responsive — tested at 375px viewport minimum
- Loading states — skeletons or spinners, not blank screens
- TDD discipline — tests exist, test suite passes
- Scaffold labels — mock data clearly marked `// SCAFFOLD`
- Issue linkage — `Closes #NNN` present

### Pass 3: Security (top 1% strict)

- No XSS vectors — no `v-html` with user data, no `innerHTML`, no `eval`
- No secrets in client code — tokens via HttpOnly cookies only
- Auth flow completeness — all Cognito steps handled (MFA, verify, password reset)
- Token storage — secure, not raw localStorage
- CSRF protection — proper origin/referer checks
- Content Security Policy compatible — no inline scripts/styles that bypass CSP
- Dependency audit — no known CVEs in package-lock.json
- OWASP Top 10 applied to every user-facing surface
- Assume an attacker is reading this diff

### Accessibility (WCAG 2.1 AA — first-order, not follow-up)

- Keyboard navigation — all interactive elements reachable via Tab
- ARIA labels — proper `aria-label`, `aria-describedby`, `role` attributes
- Color contrast — AA minimum (4.5:1 normal text, 3:1 large text)
- Screen reader semantics — headings hierarchy, landmark regions, live regions
- Focus management — visible focus rings (`focus-visible`), logical tab order
- Form labels — every input has an associated `<label>`
- Error announcements — `role="alert"` on error messages

## What This PE Catches That Others Miss

- Hydration mismatches (`Math.random()` in setup, Date.now() in templates)
- Memory leaks (intervals, subscriptions not cleaned on unmount)
- Accessibility gaps (missing ARIA, role misuse, keyboard traps)
- Reactivity bugs (static model-value, stale closures in watchers)
- Auth flow gaps (unhandled Cognito steps, token refresh failures)
- Bundle bloat (unnecessary dependencies, missing code splitting)
- Warm palette violations (the plumber's wife shouldn't feel like she's in a hospital)

## Domain Expertise

Vue 3 (Composition API, `<script setup>`), Nuxt 3 (SPA + SSR, Nitro, middleware),
TypeScript (strict mode), Tailwind CSS, Storybook, Vitest, Playwright,
Cloudflare Pages, AWS Amplify Auth, Pinia, TanStack Query.
