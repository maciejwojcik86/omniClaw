## Context

OmniClaw already treats Nanobot as the canonical agent runtime, but the live customization seam still sits in an external checkout where Nanobot imports `omniclaw.*` directly. At the same time, local startup still leans on `main.py` and ad hoc path assumptions instead of a package install contract. M12 closes both gaps by moving the customized runtime into the monorepo and defining one install/runtime boundary for `omniclaw` plus `nanobot`.

## Goals / Non-Goals

**Goals:**
- Vendor the current Nanobot fork into the OmniClaw repo without turning it into an OmniClaw subpackage.
- Make `omniclaw` installable as a CLI package while keeping `nanobot` separately installable from the same environment.
- Replace hardcoded `/home/macos/nanobot` and `PYTHONPATH` coupling with an explicit runtime integration contract.
- Persist final provider request payload artifacts for OmniClaw-managed Nanobot calls.

**Non-Goals:**
- Multi-repo upstream sync automation for Nanobot.
- Prompt payload indexing or retention policy in SQLite.
- Publishing wheels to PyPI or making OmniClaw runnable without a source checkout.

## Decisions

### Vendor Nanobot under `third_party/nanobot`
- Decision: copy the current runtime repo into `third_party/nanobot/` and keep `nanobot-ai` as its own package.
- Rationale: this preserves clear ownership boundaries and keeps upstream-derived runtime code visually separate from OmniClaw adapters.
- Rejected alternative: fold Nanobot into `src/omniclaw/` or a new `src/omniclaw_nanobot/`, which would blur package ownership and make future upstream diffs harder to reason about.

### Use one shared environment with two packages
- Decision: install `omniclaw` and `nanobot-ai` into the same project environment via `uv sync`, with a bootstrap script to make that the canonical setup path.
- Rationale: the optional runtime hook can import OmniClaw when Nanobot is launched by the kernel, while `nanobot-ai` still remains a distinct distribution and CLI.
- Rejected alternative: install `omniclaw` and `nanobot` as isolated `uv tool` environments, which would break the direct optional import hook between the launched Nanobot process and OmniClaw.

### Add an optional runtime integration hook
- Decision: Nanobot loads an integration factory only when OmniClaw sets explicit environment variables, and otherwise runs standalone with no OmniClaw dependency.
- Rationale: this removes direct `omniclaw.*` imports from Nanobot core code while preserving current automatic usage logging when the kernel owns the runtime.
- Rejected alternative: keep direct imports in Nanobot loop code, which would preserve the same coupling problem under a new path.

### Log final provider request bodies to files only
- Decision: providers write JSON prompt artifacts under `drafts/runtime/prompt_logs/` for OmniClaw-managed runs, with no DB prompt-body storage in this change.
- Rationale: prompt bodies can be large and sensitive; filesystem artifacts fit the existing runtime-output model and are enough for operator verification.
- Rejected alternative: store prompt payloads in SQLite, which would bloat canonical state and complicate retention/security handling.

## Risks / Trade-offs

- [Vendored fork drift] → Document the repo location and treat future upstream updates as explicit manual sync work.
- [Repo-root assumptions remain in some bootstrap paths] → Keep editable/source-based install as the supported deployment model for this milestone.
- [Prompt artifacts may expose sensitive business text] → Persist only request bodies, exclude auth headers/credentials, and keep storage under agent-local runtime output roots.
- [Runtime subprocesses depend on PATH correctness] → Add `runtime_command_bin`, package entrypoints, and canonical scripts that launch through the synced project environment.

## Migration Plan

1. Archive M11b after syncing its spec deltas into main specs.
2. Vendor `/home/macos/nanobot` into `third_party/nanobot/` and switch root dependency metadata.
3. Add the `omniclaw` package entrypoint and bootstrap installer script.
4. Introduce runtime integration env/hook loading and provider prompt logging.
5. Update runtime helper scripts, docs, skills, and validations.

Rollback:
- Repoint `tool.uv.sources.nanobot-ai` back to the external checkout and revert the runtime integration env changes.
- Prompt logging changes are file-only and can be disabled by removing the OmniClaw runtime env.

## Open Questions

- None for this implementation slice; the monorepo location, installer mode, and prompt-log storage mode are locked for M12.
