## Why

OmniClaw still depends on an external `/home/macos/nanobot` checkout for correctness-critical runtime behavior, while the kernel itself is not yet packaged as a CLI install. That makes deployments brittle, hides local runtime customizations outside the monorepo, and blocks a clean install path for both `omniclaw` and `nanobot`.

## What Changes

- Internalize the current customized Nanobot repo into `third_party/nanobot/` as a monorepo-owned fork while preserving `nanobot-ai` as a separate Python package and CLI.
- Make OmniClaw installable as a package with an `omniclaw` CLI entrypoint and add a bootstrap installer script that installs both packages from the monorepo.
- Remove runtime dependence on hardcoded external checkout paths and pass OmniClaw-managed runtime integration context to Nanobot through explicit environment variables.
- Add prompt-payload artifact logging for OmniClaw-managed Nanobot inference calls, capturing the final provider request body under each agent runtime output root.
- **BREAKING**: the authoritative local Nanobot source for OmniClaw development moves from `/home/macos/nanobot` to `third_party/nanobot/` inside this repo.

## Capabilities

### New Capabilities
- `runtime-packaging-boundary`: monorepo-owned packaging and installation contract for the OmniClaw kernel and the vendored Nanobot runtime.

### Modified Capabilities
- `agent-runtime-bootstrap`: runtime launch must use the installed `nanobot` command, explicit integration env, and prompt-log artifact roots.
- `usage-logging`: provider-native usage logging must flow through the optional runtime hook without external checkout coupling, and OmniClaw-managed calls must persist final prompt payload artifacts.

## Impact

- Affected code: `pyproject.toml`, `src/omniclaw/runtime/service.py`, new `src/omniclaw/runtime_integration/`, vendored Nanobot provider/agent loop code, install scripts, runtime helper scripts, and package docs.
- Affected dependencies: root local-path dependency changes from `../nanobot` to `third_party/nanobot`; OmniClaw gains a package entrypoint.
- Affected runtime behavior: child runtime processes receive explicit OmniClaw integration env and write prompt artifacts under agent runtime outputs.
