## Why

OmniClaw needs a real kernel service entrypoint to support subsequent milestones (database, daemons, provisioning, and APIs). The repository currently lacks a production-oriented app skeleton and health endpoint.

## What Changes

- Add a Python package layout under `src/omniclaw`.
- Implement a FastAPI app factory with a `/healthz` endpoint.
- Add configuration loading and structured logging setup for service startup.
- Add baseline tests to prove local service boot and health behavior.

## Capabilities

### New Capabilities
- `kernel-service-skeleton`: Provides the baseline FastAPI kernel runtime, config bootstrap, logging, and health checks.

### Modified Capabilities
- None.

## Impact

- Affected code: `main.py`, new `src/omniclaw/*`, and test files.
- Affected project metadata: `pyproject.toml` dependencies.
- Enables M02 schema work by providing a stable app/runtime base.
