# init-project

Bootstraps the `/code-reviewer` skill into any project. Scans the repo,
detects languages/frameworks/test commands, and generates configuration
automatically.

## What It Does

1. **Detects stacks** — Go, Vue, React, CDK, Terraform, Rust, Python, Java, C#, Docker, CI/CD
2. **Maps directories** — which paths belong to which stack and PE type
3. **Finds test commands** — reads `package.json` scripts, `Makefile` targets, or uses stack defaults
4. **Generates PE references** — one per detected stack with activation patterns, test commands, and three-pass review protocol
5. **Writes `.code-reviewer.yml`** — project-level config with Stack Map and settings
6. **Suggests `CLAUDE.md` additions** — Stack Map table for the project instructions

## Usage

```text
You: /init-project
Claude: [Scans repo, generates config, creates PE references]
```

## Output

- `.code-reviewer.yml` — project config with Stack Map
- `references/pe-*.md` — PE reference files for each detected stack
- Summary of what was detected and generated

## Supported Stacks

Go, Vue/Nuxt, React, Svelte, Angular, Astro, Next.js, AWS CDK, CDKTF,
Terraform, Rust, Python, Java, C#/.NET, Docker, GitHub Actions, GitLab CI.

Unsupported stacks fall back to generic three-pass review without
stack-specific test commands.

---

*Part of [code-reviewer plugin](../../README.md)*
