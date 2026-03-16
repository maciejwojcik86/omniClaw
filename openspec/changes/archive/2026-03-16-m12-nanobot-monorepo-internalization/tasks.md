## 1. Change And Packaging Setup

- [x] 1.1 Archive `m11b-configurable-company-workspaces` and make `m12-nanobot-monorepo-internalization` the active change in trackers.
- [x] 1.2 Vendor the current Nanobot repo into `third_party/nanobot/` and repoint OmniClaw packaging metadata to the monorepo path.
- [x] 1.3 Add the `omniclaw` package entrypoint and a bootstrap installer script for the shared monorepo environment.

## 2. Runtime Integration Boundary

- [x] 2.1 Replace hardcoded external checkout and `PYTHONPATH` coupling with a settings-backed runtime binary plus explicit OmniClaw integration env.
- [x] 2.2 Move native usage persistence behind an optional runtime integration hook that Nanobot loads only for OmniClaw-managed runs.
- [x] 2.3 Add final provider request payload logging to agent runtime prompt-log artifacts for OmniClaw-managed inference calls.

## 3. Runtime Tooling, Docs, And Skills

- [x] 3.1 Update canonical runtime/provisioning scripts and package-source helpers to use the vendored Nanobot source and `omniclaw` CLI contract.
- [x] 3.2 Update tracker docs, operator/developer docs, and repository map for the vendored Nanobot layout and packaged runtime flow.
- [x] 3.3 Capture the monorepo install/runtime/prompt-log workflow as a mirrored developer/copilot skill.

## 4. Validation

- [x] 4.1 Add or update automated tests for runtime env handoff, optional integration usage persistence, and provider prompt artifact logging.
- [x] 4.2 Run targeted pytest coverage for runtime actions, runtime integration, and prompt logging.
- [x] 4.3 Run full pytest and strict OpenSpec validation for `m12-nanobot-monorepo-internalization`.
