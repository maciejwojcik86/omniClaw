## Context

The repository is currently minimal and does not provide a service framework for upcoming kernel features. M01 establishes runtime conventions for app initialization, configuration, logging, and health checking.

## Goals / Non-Goals

**Goals:**
- Add a maintainable Python package structure for kernel code.
- Implement a FastAPI app factory with a stable health endpoint.
- Provide environment-backed configuration loading.
- Add baseline test coverage for app boot and health route behavior.

**Non-Goals:**
- Database models and migrations.
- Daemon processes and IPC routing logic.
- Linux provisioning and runtime orchestration.

## Decisions

- Use `src/` layout to separate package code from root-level scripts.
- Keep configuration simple with environment variables and typed dataclass parsing.
- Emit JSON-formatted logs to standard output for easy ingestion by systemd/journald and local tooling.
- Keep endpoint surface minimal (`/healthz`) until schema and domain APIs are introduced.

## Risks / Trade-offs

- [Risk] Early design might constrain future API structure. -> Mitigation: app factory and router registration keep expansion flexible.
- [Risk] Logging shape may evolve once observability is introduced. -> Mitigation: isolate formatter logic in a dedicated module.
