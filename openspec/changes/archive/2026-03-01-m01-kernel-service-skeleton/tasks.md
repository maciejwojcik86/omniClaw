## 1. Service Skeleton

- [x] 1.1 Create `src/omniclaw` package with app factory and router wiring.
- [x] 1.2 Implement `GET /healthz` response contract.

## 2. Runtime Foundations

- [x] 2.1 Add typed configuration loader for service settings.
- [x] 2.2 Add structured logging bootstrap used by entrypoint/app startup.

## 3. Verification

- [x] 3.1 Add tests for app boot and `/healthz` behavior.
- [x] 3.2 Run test suite and `openspec validate --type change m01-kernel-service-skeleton --strict`.
