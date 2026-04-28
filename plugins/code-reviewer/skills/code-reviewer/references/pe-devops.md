---
name: PE-DevOps
activates_on: ["cdk.json", "*.tf", "*.tfvars", "Dockerfile*", "docker-compose*", ".github/workflows/*.yml"]
---

# PE-DevOps — Review Reference

## Test Commands

```bash
# CDK
cd <worktree>/cdk && npm test
cd <worktree>/cdk && npx cdk synth --all

# CDKTF (if changed)
cd <worktree>/cloudflare && npm test
cd <worktree>/cloudflare && npx cdktf synth

# Workflow syntax (if changed)
actionlint <worktree>/.github/workflows/*.yml 2>/dev/null || true
```

Test failures are CRITICAL findings. Synth failures are CRITICAL findings.

## Three-Pass Review

### Pass 1: Architecture

- Infrastructure as code — no ClickOps, CDK/CDKTF assertions are tests
- Stack boundaries — single responsibility per stack, clean cross-stack references
- No stub stacks — empty constructors with TODO comments must not be deployed
- Verify synth output has real resources — near-empty template is a red flag
- Cross-stack dependencies — SSM parameter handoff, not direct exports (ADR banned)
- Cost implications — every new service has projected monthly cost
- Tagging — `Project`, `Stage`, `Stack`, `Owner` on every resource
- No hardcoded ARNs, account IDs, or region strings — use `Arn.format` / construct getters
- Deploy ordering — destructive changes need careful sequencing

### Pass 2: Quality (includes test execution)

- Run CDK tests — failures are CRITICAL
- Run CDK synth — failures are CRITICAL
- CDK assertion tests exist for new constructs (TDD — tests first)
- IAM: `iam.PolicyStatement` + `grant*` methods — never raw JSON policies
- ARNs: `Arn.format` / construct `.arn` getters — never string concatenation
- Retries: AWS SDK built-in retry config — no custom retry loops
- Workflow files — proper `on:` triggers, correct `runs-on`, secrets via `${{ secrets.* }}`
- Concurrency groups — prevent duplicate deploys
- Runbook-or-no-alarm — an alarm without a documented response is paging noise
- Verify the metric exists in AWS namespace before alarming on it
- Issue linkage — `Closes #NNN` present

### Pass 3: Security (top 1% strict)

- IAM least-privilege — no wildcard Resource/Action in production
- Separate execution roles per Lambda — no shared roles
- No `*` in IAM resource ARNs — scope to specific resources
- Secrets via Secrets Manager — 30-day automated rotation
- Encryption at rest — AWS-managed KMS
- Encryption in transit — TLS everywhere, `rds.force_ssl=1`
- Network isolation — private subnets for stateful resources
- VPC endpoints — Gateway for S3, Interface for Secrets Manager
- No public DB endpoints
- Workflow secrets — never echo'd, never logged, no `${{ github.token }}` in curl
- Supply chain — pinned action versions (`@v4` not `@main`), no untrusted marketplace actions
- OWASP Top 10 applied to every infrastructure boundary
- Assume an attacker is reading this diff

## What This PE Catches That Others Miss

- Wildcard IAM policies that look scoped but aren't
- Missing alarms on critical-path resources
- CloudFormation export dependencies that prevent stack updates
- Deploy ordering issues (deleting before creating replacement)
- Cost anomalies (provisioned capacity where on-demand suffices)
- Workflow race conditions (concurrent deploys to same environment)
- DNS propagation gaps (CNAME changes before cert validation)

## Domain Expertise

AWS CDK (TypeScript), Cloudflare (DNS/CDN/WAF/Workers/CDKTF), GitHub Actions,
Docker, CloudWatch/OpenTelemetry, SSL/TLS (ACM), Route 53, IAM, EventBridge,
Lambda, Aurora PostgreSQL, S3, API Gateway HTTP API.
