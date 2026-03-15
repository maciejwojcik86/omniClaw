# Nanobot Internalization Into OmniClaw Monorepo — OpenSpec Planning Draft

Status: planning draft for next session
Suggested next change id: `m10b-nanobot-monorepo-internalization`

## Why this change is needed

Current live usage accounting depends on customized Nanobot runtime code in an external checkout (`/home/macos/nanobot/nanobot/agent/loop.py`) that directly imports `omniclaw.*` modules.

That creates four problems:
- OmniClaw runtime correctness depends on a separately maintained Nanobot checkout.
- A stock published Nanobot package is not sufficient for OmniClaw live usage logging.
- The current coupling is backward: Nanobot imports OmniClaw internals instead of calling a stable integration contract owned by OmniClaw.
- Future runtime features will be harder to evolve safely if the effective product boundary spans two repos/install locations.

The user direction is to avoid maintaining a long-lived fork and instead move the customized Nanobot runtime under OmniClaw control inside the monorepo, while still allowing CLI-style Nanobot execution semantics for agent runs.

## Product decision to capture

Adopt an OmniClaw-owned monorepo runtime strategy:
- OmniClaw vendors/incorporates the runtime code it depends on.
- Automatic LLM usage logging remains a runtime responsibility.
- Runtime/business tools used by agents remain decoupled from repo structure and rely only on kernel endpoints or packaged scripts.
- Internal runtime integration points may be product-internal, but must be deliberately owned, packaged, and documented within OmniClaw rather than relying on an external mutable checkout.

## Goals

1. Remove production dependence on `/home/macos/nanobot` as an external source checkout for OmniClaw runtime correctness.
2. Keep `nanobot agent` / gateway style execution ergonomics available through an OmniClaw-controlled runtime package or wrapper.
3. Preserve automatic runtime-level usage/cost/session logging.
4. Replace direct `import omniclaw.*` from external Nanobot code with a cleaner owned integration boundary.
5. Make startup, deployment, tests, and operator runbooks deterministic from the monorepo alone.
6. Keep agent-facing workflows fully endpoint/script based.

## Non-goals

- Do not redesign the entire Nanobot product.
- Do not require upstream Nanobot to adopt OmniClaw-specific logic in this change.
- Do not change agent business workflow contracts beyond any runtime command-path updates needed for internalization.
- Do not introduce a hidden dependency on repo inspection for agent workflows.

## Architectural options considered

### Option A — Keep external Nanobot checkout and patch it
Pros:
- Lowest immediate implementation effort.

Cons:
- Still an external mutable dependency.
- Hard to reproduce and package.
- Encourages drift and hidden local-environment coupling.

Decision: reject.

### Option B — Upstream generic hooks to Nanobot and consume released package only
Pros:
- Cleanest long-term relationship with upstream if accepted.

Cons:
- Depends on upstream roadmap and release timing.
- Does not solve immediate need for OmniClaw-owned runtime evolution.

Decision: desirable future path, but insufficient as the immediate solution.

### Option C — Vendor/internalize Nanobot runtime into OmniClaw monorepo
Pros:
- Full control over runtime evolution.
- Deterministic packaging and tests from one repo.
- Easier to add OmniClaw-specific runtime features safely.

Cons:
- Requires clear repo structure and ownership policy.
- Requires a deliberate sync/update strategy if upstream Nanobot changes are later desired.

Decision: preferred.

## Recommended target architecture

### 1) Monorepo-owned runtime package
Create an OmniClaw-owned runtime area for the integrated Nanobot code, with a clear repository map update. Two acceptable structural patterns:

Pattern 1:
- `vendor/nanobot/` for imported upstream-derived runtime code
- `src/omniclaw/runtime_integration/` for OmniClaw-specific adapters

Pattern 2:
- `src/omniclaw_nanobot/` for the integrated runtime package
- `src/omniclaw/runtime_integration/` for accounting/session adapters

Preferred bias:
- Keep upstream-derived code visually separated from OmniClaw adapters so future updates are easier.

### 2) Explicit runtime integration boundary
Replace the current direct external import pattern with a monorepo-owned adapter contract, for example:
- `src/omniclaw/runtime_integration/usage_recorder.py`
- `src/omniclaw/runtime_integration/session_bridge.py`

The integrated runtime should call a narrow interface like:
- `record_llm_call(node_id, session_key, response_metadata, started_at, finished_at)`

That boundary may still be an internal Python call if the runtime now ships inside the same monorepo/package boundary. The key fix is:
- no dependency on an external checkout
- no ad hoc `PYTHONPATH` wiring to import repo internals from outside the product package
- no hidden runtime correctness requirement on a separately maintained Nanobot install

### 3) CLI compatibility layer
Provide an OmniClaw-controlled command path that preserves current invocation ergonomics. Examples:
- `omniclaw-nanobot agent ...`
- `python -m omniclaw_nanobot ...`
- wrapper script under `scripts/runtime/` that dispatches to the integrated runtime package

RuntimeService should invoke the OmniClaw-controlled command path, not assume a globally installed unrelated Nanobot binary is the authoritative runtime.

### 4) Packaging and installation contract
Update packaging so a fresh OmniClaw environment can install everything needed from the monorepo alone.

Expected outcomes:
- `uv sync` (or equivalent) installs the integrated runtime package.
- tests and runtime commands resolve against monorepo-owned code.
- operator docs no longer require a separate `/home/macos/nanobot` checkout for correctness-critical paths.

### 5) Upstream sync policy
Document how upstream Nanobot changes are handled in the future:
- either periodic manual vendor sync with changelog notes
- or permanent product divergence under OmniClaw ownership

This is a planning/ownership requirement, even if the first implementation is simple.

## Required OpenSpec change contents

For the next session, create a new change:
- Change ID: `m10b-nanobot-monorepo-internalization`

Artifacts to author:
- `openspec/changes/m10b-nanobot-monorepo-internalization/proposal.md`
- `openspec/changes/m10b-nanobot-monorepo-internalization/design.md`
- `openspec/changes/m10b-nanobot-monorepo-internalization/tasks.md`
- specs delta(s) under `openspec/changes/m10b-nanobot-monorepo-internalization/specs/`

Recommended spec deltas:
1. `specs/agent-runtime-bootstrap/spec.md`
   - runtime command ownership
   - packaging/install expectations
   - integrated runtime logging contract
2. `specs/usage-and-session-tracking/spec.md` or equivalent canonical usage spec
   - runtime auto-recording responsibility
   - integration boundary expectations
3. If needed, add a new spec such as `specs/runtime-packaging-boundary/spec.md`
   - monorepo ownership of runtime dependencies
   - no external mutable checkout requirement for production correctness

## Draft proposal content

### Title
Internalize the customized Nanobot runtime into the OmniClaw monorepo and replace external-checkout coupling.

### Problem
Live usage logging currently depends on customized code inside an external Nanobot checkout that directly imports OmniClaw modules. This makes the system non-self-contained, brittle to environment drift, and difficult to package.

### Proposal
Move the customized Nanobot runtime under OmniClaw monorepo ownership, provide an OmniClaw-controlled runtime command path, and refactor automatic LLM usage logging behind a deliberate internal integration boundary.

### Impact
- More deterministic runtime packaging
- Clearer ownership of runtime modifications
- Easier future feature work on the runtime
- Reduced risk from external checkout drift

## Draft design content

### Design principles
- One repo should contain the code required for correctness-critical runtime behavior.
- Agent workflow surfaces remain endpoint/script based.
- Runtime accounting remains automatic.
- The integrated runtime should depend on narrow adapters, not broad cross-package imports sprinkled through runtime code.

### Proposed implementation slices

#### Slice 1 — Repository and packaging structure
- Introduce the monorepo-owned integrated runtime location.
- Add packaging metadata so the integrated runtime is importable/executable in the OmniClaw env.
- Update repo map in `AGENTS.md`.

#### Slice 2 — Runtime integration adapter
- Extract the usage-recording logic currently embedded in Nanobot loop code into a dedicated OmniClaw adapter module.
- Keep API response shape stable.
- Ensure Decimal-safe cost handling remains intact.

#### Slice 3 — Runtime command migration
- Update `src/omniclaw/runtime/service.py` so runtime invocations target the integrated runtime command path.
- Update wrapper scripts and smoke paths accordingly.

#### Slice 4 — Verification and docs
- Add tests proving the integrated runtime logs usage without external checkout dependency.
- Update operator docs, setup docs, and verification skill(s).
- Capture the workflow as a developer skill and mirror it into both skill trees.

### Key design decisions to lock
- Whether the integrated runtime remains under a `vendor/` namespace or becomes an OmniClaw-native package name.
- Whether the runtime/OmniClaw boundary is an internal Python adapter only, or also offers an internal HTTP reporting mode for future decoupling.
- What command name becomes canonical for runtime invocation inside OmniClaw.

## Draft tasks.md checklist

## 1. Planning And Change Setup
- [ ] 1.1 Create OpenSpec change `m10b-nanobot-monorepo-internalization` with proposal, design, spec deltas, and tasks.
- [ ] 1.2 Update `docs/current-task.md`, `docs/plan.md`, and `docs/implement.md` so M10b becomes the active change after M10a archive/split decision.
- [ ] 1.3 Decide and document the repository ownership model for integrated Nanobot code (`vendor/` vs dedicated package namespace).

## 2. Monorepo Runtime Internalization
- [ ] 2.1 Add the integrated Nanobot runtime code to the OmniClaw monorepo in the chosen location.
- [ ] 2.2 Update Python packaging/project config so the integrated runtime is installed/resolved from the monorepo environment.
- [ ] 2.3 Update `AGENTS.md` repository map and any bootstrap/setup docs to reflect the new structure.

## 3. Integration Boundary Refactor
- [ ] 3.1 Extract automatic LLM usage logging into a narrow OmniClaw-owned integration module.
- [ ] 3.2 Replace scattered direct `omniclaw.*` imports from runtime loop code with the new boundary.
- [ ] 3.3 Preserve session key, node mapping, token accounting, provider/model capture, and Decimal-safe cost persistence.

## 4. Runtime Command Path Migration
- [ ] 4.1 Update `src/omniclaw/runtime/service.py` to invoke the integrated runtime command path.
- [ ] 4.2 Update canonical wrapper scripts and smoke helpers to use the new command path where needed.
- [ ] 4.3 Prove runtime invocation no longer requires the external `/home/macos/nanobot` checkout for correctness-critical usage logging.

## 5. Verification Coverage
- [ ] 5.1 Add/adjust automated tests for integrated runtime invocation and auto-logging behavior.
- [ ] 5.2 Run targeted runtime/usage/budget tests.
- [ ] 5.3 Run `uv run pytest -q`.
- [ ] 5.4 Run `openspec validate --type change m10b-nanobot-monorepo-internalization --strict`.

## 6. Documentation And Skill Capture
- [ ] 6.1 Update `docs/documentation.md` with the new runtime ownership and setup contract.
- [ ] 6.2 Update the relevant developer/copilot skills in `.codex/skills/` and mirror them into `skills/`.
- [ ] 6.3 Document the upstream sync/ownership policy for future Nanobot changes.

## Acceptance criteria
- OmniClaw runtime correctness no longer depends on a separately maintained external Nanobot checkout.
- Automatic LLM usage logging still occurs for real runtime invocations.
- Canonical runtime invocation and usage/budget verification still pass.
- Setup and operator instructions are reproducible from the monorepo alone.
- Repository map and developer skills are updated in the same change.

## Risks and mitigations

### Risk: vendored runtime drifts from upstream
Mitigation:
- keep vendor boundary explicit
- document sync policy and local modifications
- minimize invasive changes in upstream-derived code

### Risk: command-path migration breaks existing scripts
Mitigation:
- preserve wrapper script interfaces
- change underlying command resolution, not operator-facing script contract unless necessary

### Risk: hidden dependence on external config/home paths remains
Mitigation:
- add verification that runtime usage logging works without `/home/macos/nanobot` on `PYTHONPATH`
- document all remaining runtime dependencies explicitly

## Suggested next-session execution order

1. Decide whether to archive M10a first or keep M10b as the immediate follow-up while M10a remains noted as the precursor hardening gate.
2. Create `m10b-nanobot-monorepo-internalization` OpenSpec change.
3. Choose repo structure for integrated runtime code.
4. Implement packaging + runtime adapter extraction.
5. Migrate runtime service command path.
6. Re-run canonical live verification.
7. Update docs/skills and validate strictly.

## Notes for next session

Known current state to reference:
- external customized runtime file: `/home/macos/nanobot/nanobot/agent/loop.py`
- current direct imports inside runtime loop: `omniclaw.config`, `omniclaw.db.session`, `omniclaw.db.repository`
- OmniClaw runtime caller: `src/omniclaw/runtime/service.py`
- user preference: do not maintain a forked external Nanobot repo as the product dependency; prefer monorepo ownership and future extensibility under OmniClaw control.
