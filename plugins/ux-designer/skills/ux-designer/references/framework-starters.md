# Framework Starters

Use this reference to initialize a project with the user's chosen framework. Each starter includes shell commands, essential file structure, base CSS, and the dev server command.

---

## 1. Vanilla HTML + Tailwind CDN

The zero-setup option. A single `index.html` file with Tailwind loaded via CDN — no build tools, no dependencies.

### File structure

```
project/
  index.html
  assets/          # optional — images, fonts, etc.
```

### `index.html`

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Project Name</title>

  <!-- Google Fonts — Inter -->
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@100..900&display=swap" rel="stylesheet" />

  <!-- Tailwind CDN -->
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {
      theme: {
        extend: {
          fontFamily: {
            sans: ['Inter', 'system-ui', 'sans-serif'],
          },
          colors: {
            primary: {
              50:  '#f0f9ff',
              100: '#e0f2fe',
              200: '#bae6fd',
              300: '#7dd3fc',
              400: '#38bdf8',
              500: '#0ea5e9',
              600: '#0284c7',
              700: '#0369a1',
              800: '#075985',
              900: '#0c4a6e',
              950: '#082f49',
            },
          },
        },
      },
    }
  </script>

  <link rel="icon" href="/favicon.svg" type="image/svg+xml" />
</head>
<body class="font-sans antialiased text-gray-900 bg-white">

  <!-- Content goes here -->

</body>
</html>
```

### Dev server

```bash
python3 -m http.server 3000
# or
npx serve .
```

---

## 2. React + Vite + Tailwind

### Setup

```bash
npm create vite@latest {project-name} -- --template react
cd {project-name}
npm install
npm install -D tailwindcss @tailwindcss/vite
```

### Essential files

#### `vite.config.js`

```js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
})
```

#### `src/index.css`

```css
@import "tailwindcss";
```

#### `src/App.jsx`

```jsx
function App() {
  return (
    <div className="min-h-screen bg-white font-sans antialiased text-gray-900">
      {/* Content goes here */}
    </div>
  )
}

export default App
```

#### Inter font

Add to `index.html` `<head>`:

```html
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@100..900&display=swap" rel="stylesheet" />
```

Add to `src/index.css`:

```css
@import "tailwindcss";

@theme {
  --font-sans: 'Inter', system-ui, sans-serif;
}
```

### Dev server

```bash
npm run dev
# default port 5173
```

---

## 3. Next.js + Tailwind

### Setup

```bash
npx create-next-app@latest {project-name} --tailwind --app --src-dir --no-import-alias
cd {project-name}
```

### Essential files

#### `src/app/layout.tsx`

```tsx
import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Project Name',
  description: '',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={`${inter.className} antialiased`}>
        {children}
      </body>
    </html>
  )
}
```

#### `src/app/page.tsx`

```tsx
export default function Home() {
  return (
    <main className="min-h-screen bg-white text-gray-900">
      {/* Content goes here */}
    </main>
  )
}
```

#### `src/app/globals.css`

```css
@import "tailwindcss";
```

### Dev server

```bash
npm run dev
# default port 3000
```

---

## 4. Vue + Vite + Tailwind

### Setup

```bash
npm create vue@latest {project-name}
cd {project-name}
npm install
npm install -D tailwindcss @tailwindcss/vite
```

### Essential files

#### `vite.config.js`

```js
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [
    vue(),
    tailwindcss(),
  ],
})
```

#### `src/assets/main.css`

```css
@import "tailwindcss";

@theme {
  --font-sans: 'Inter', system-ui, sans-serif;
}
```

#### `src/App.vue`

```vue
<template>
  <div class="min-h-screen bg-white font-sans antialiased text-gray-900">
    <!-- Content goes here -->
  </div>
</template>

<script setup>
</script>
```

#### Inter font

Add to `index.html` `<head>`:

```html
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@100..900&display=swap" rel="stylesheet" />
```

### Dev server

```bash
npm run dev
# default port 5173
```

---

## 5. Nuxt + Tailwind

### Setup

```bash
npx nuxi@latest init {project-name}
cd {project-name}
npm install
npm install -D @nuxtjs/tailwindcss
```

### Essential files

#### `nuxt.config.ts`

```ts
export default defineNuxtConfig({
  modules: ['@nuxtjs/tailwindcss'],
  devtools: { enabled: true },
})
```

#### `assets/css/main.css`

```css
@import "tailwindcss";

@theme {
  --font-sans: 'Inter', system-ui, sans-serif;
}
```

#### `app.vue`

```vue
<template>
  <div>
    <NuxtPage />
  </div>
</template>
```

#### `pages/index.vue`

```vue
<template>
  <main class="min-h-screen bg-white font-sans antialiased text-gray-900">
    <!-- Content goes here -->
  </main>
</template>

<script setup>
</script>
```

### Dev server

```bash
npm run dev
# default port 3000
```

---

## 6. Svelte / SvelteKit + Tailwind

### Setup

```bash
npx sv create {project-name}
cd {project-name}
npm install
npx sv add tailwindcss
```

### Essential files

#### `src/app.css`

```css
@import "tailwindcss";

@theme {
  --font-sans: 'Inter', system-ui, sans-serif;
}
```

#### `src/routes/+layout.svelte`

```svelte
<script>
  import '../app.css'
</script>

<slot />
```

#### `src/routes/+page.svelte`

```svelte
<main class="min-h-screen bg-white font-sans antialiased text-gray-900">
  <!-- Content goes here -->
</main>
```

### Dev server

```bash
npm run dev
# default port 5173
```

---

## 7. Astro + Tailwind

### Setup

```bash
npm create astro@latest {project-name}
cd {project-name}
npx astro add tailwind
```

### Essential files

#### `astro.config.mjs`

```js
import { defineConfig } from 'astro/config'
import tailwindcss from '@astrojs/tailwind'

export default defineConfig({
  integrations: [tailwindcss()],
})
```

#### `src/layouts/Layout.astro`

```astro
---
interface Props {
  title: string;
}

const { title } = Astro.props;
---

<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{title}</title>

  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@100..900&display=swap" rel="stylesheet" />

  <link rel="icon" href="/favicon.svg" type="image/svg+xml" />
</head>
<body class="font-sans antialiased text-gray-900 bg-white">
  <slot />
</body>
</html>
```

#### `src/pages/index.astro`

```astro
---
import Layout from '../layouts/Layout.astro';
---

<Layout title="Project Name">
  <main class="min-h-screen">
    <!-- Content goes here -->
  </main>
</Layout>
```

### Dev server

```bash
npm run dev
# default port 4321
```

---

## 8. Solid + Vite + Tailwind

### Setup

```bash
npx degit solidjs/templates/js {project-name}
cd {project-name}
npm install
npm install -D tailwindcss @tailwindcss/vite
```

### Essential files

#### `vite.config.js`

```js
import { defineConfig } from 'vite'
import solidPlugin from 'vite-plugin-solid'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [
    solidPlugin(),
    tailwindcss(),
  ],
})
```

#### `src/index.css`

```css
@import "tailwindcss";

@theme {
  --font-sans: 'Inter', system-ui, sans-serif;
}
```

#### `src/App.jsx`

```jsx
function App() {
  return (
    <div class="min-h-screen bg-white font-sans antialiased text-gray-900">
      {/* Content goes here */}
    </div>
  )
}

export default App
```

### Dev server

```bash
npm run dev
# default port 3000
```

---

## Common Setup Notes

### Google Fonts (Inter)

Add to the `<head>` of your HTML entry point:

```html
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@100..900&display=swap" rel="stylesheet" />
```

Configure Tailwind to use it (Tailwind v4 CSS-first config):

```css
@theme {
  --font-sans: 'Inter', system-ui, sans-serif;
}
```

Or in a `tailwind.config.js` (v3-style, used by some integrations):

```js
module.exports = {
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
}
```

### Base Reset / Globals

Tailwind's Preflight already applies `box-sizing: border-box` and resets margins. Add these extras for polish:

```css
html {
  scroll-behavior: smooth;
}

body {
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
```

Or use Tailwind utility classes on `<body>`:

```html
<body class="antialiased scroll-smooth">
```

### Favicon

Add a favicon to every project. SVG favicons are recommended for scalability:

```html
<link rel="icon" href="/favicon.svg" type="image/svg+xml" />
```

Place the favicon file in the `public/` directory (for Vite, Next.js, Astro, Nuxt, SvelteKit) or the project root (for vanilla HTML).
