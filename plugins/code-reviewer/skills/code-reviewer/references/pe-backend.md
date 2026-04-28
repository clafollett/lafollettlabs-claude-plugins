---
name: PE-Backend
activates_on: ["*.go", "go.mod", "go.sum", "*.sql"]
---

# PE-Backend — Review Reference

## Test Commands

```bash
cd <worktree> && go vet ./...
cd <worktree> && go test ./... -count=1 -race
cd <worktree> && staticcheck ./... 2>/dev/null || true
```

Test failures are CRITICAL findings. `go vet` warnings are HIGH findings.

## Three-Pass Review

### Pass 1: Architecture

- SOLID principles in Go (single responsibility per package, interface segregation)
- Package boundaries — no circular imports, clean dependency direction
- DAL layer isolation — handlers never import `pgx` directly
- Event-driven patterns — CloudEvents schema, EventBridge integration
- Migration safety — SQL syntax valid against existing schema, arg counts match function signatures
- Destructive vs non-destructive migrations declared
- No hardcoded ARNs, account IDs, or region strings

### Pass 2: Quality (includes test execution)

- Run test suite — failures are CRITICAL
- `go vet` clean — warnings are HIGH
- Error handling — `errors.Is`/`errors.As` not string matching, `fmt.Errorf("%w")` not `%v`
- Structured logging — `slog` JSON handler, correlation IDs, appropriate levels
- No PII/secrets in logs
- Audit trail — writes via `write_audit()` SECURITY DEFINER
- TDD discipline — tests exist for new code paths
- Self-report honesty — engineer's claimed test results match actual
- Greenfield discipline — no deprecated paths, no legacy compat pre-first-customer
- pgx v5 native — not database/sql adapter
- Issue linkage — `Closes #NNN` present

### Pass 3: Security (top 1% strict)

- No hardcoded secrets — Secrets Manager or env vars only
- RLS exercised in tests — no bypass paths (master user without WithTenantTx)
- Race conditions — missing FOR UPDATE on read-then-write patterns
- Input validation at system boundaries — all external input sanitized
- SQL injection — parameterized queries only, no string concatenation
- Auth checks — every handler verifies JWT claims, tenant isolation enforced
- Dependency audit — no known CVEs in go.sum
- OWASP Top 10 applied to every endpoint
- Assume an attacker is reading this diff

## What This PE Catches That Others Miss

- Function signature mismatches between SQL and Go (arg count, types)
- RLS bypass paths (master user without WithTenantTx)
- Race conditions (missing FOR UPDATE on read-then-write)
- Audit trail gaps (writes without write_audit)
- Test isolation failures (tests that pass alone but share state)

## Domain Expertise

Go (primary), PostgreSQL (RLS, SECURITY DEFINER, migrations), pgx v5,
testcontainers-go, AWS Lambda, CDK/CDKTF, CloudEvents, EventBridge.
