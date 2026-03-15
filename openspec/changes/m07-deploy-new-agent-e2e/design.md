## Context

The kernel currently routes generic forms by stage graph and distributes required stage skill packages, but routed forms do not explicitly include a machine-managed field that tells the recipient which skill to execute. Operators and agents infer this from workflow definitions, which is error-prone in long multi-stage flows.

`deploy_new_agent` is the first target workflow for M07 validation. It already encodes a multi-step approval and deployment path and includes a deployment stage owned by `deploy-new-claw-agent`. The product decision for this milestone is to preserve manual deployment execution at stage level (skill-driven), not to introduce automatic provisioning side effects at transition time.

## Goals / Non-Goals

**Goals**
- Make next-stage skill guidance explicit in routed payloads via `stage_skill`.
- Keep routing deterministic and overwrite stale client-provided guidance metadata.
- Standardize workspace form stage-skill naming to hyphen style.
- Provide repeatable deterministic and host-live validation for `deploy_new_agent` cycle.

**Non-Goals**
- Automatic kernel provisioning when approval decision is made.
- `UPDATE_TEMPLATE` workflow implementation.
- New authN/authZ model for who may execute deploy-stage scripts.

## Decisions

### 1) `stage_skill` is kernel-authored routed metadata
- **Decision:** IPC router writes `stage_skill` into routed frontmatter on every successful transition.
- **Rationale:** recipients can read one field to identify current stage skill without deriving from workflow JSON.
- **Rule:** `stage_skill` always reflects next-stage `required_skill`; incoming frontmatter value is ignored/overwritten.

### 2) Terminal stage emits explicit empty guidance
- **Decision:** when next stage is terminal/no-holder (`target: null|none`), router writes `stage_skill: ""`.
- **Rationale:** preserve stable key presence while making no-op stage intent explicit.

### 3) Deployment remains stage-skill executed
- **Decision:** no kernel auto-provision execution is added to transition engine in M07.
- **Rationale:** user requirement is explicit manual execution in `AGENT_DEPLOYMENT` then `deploy_and_archive`.

### 4) Workspace form skills use hyphen naming convention
- **Decision:** migrate `workspace/forms/*/skills/<name>` and matching `required_skill` values to hyphen style.
- **Rationale:** enforce one naming convention for workspace-packaged form skills while keeping snake_case form type keys unchanged.

### 5) Live smoke is operator-driven, not daemon-owned
- **Decision:** add script/runbook that orchestrates:
  - macOS-originated form seed,
  - IPC scan ticks,
  - per-holder `nullclaw agent -m "read HEARTBEAT.md ..."` runs.
- **Rationale:** validates actual host workspace/runtime behavior without adding runtime daemon coupling into kernel code.

## Data / Interface Changes

### Routed frontmatter contract
Existing output keys remain, plus:
- `stage_skill`: kernel-set string.

Behavior:
- Non-terminal next stage with required skill: `stage_skill: <required_skill>`.
- Terminal no-holder next stage: `stage_skill: ""`.

## Risks / Trade-offs

- [Risk] Hyphen migration may break tests/examples that still reference underscore names.
  - Mitigation: update all workspace form workflows and affected tests/docs in one change.
- [Risk] Live smoke depends on local model/auth runtime setup.
  - Mitigation: explicit preflight in script and deploy skill SOP with deterministic checks.
- [Risk] Exposing config template copied from director may include environment-specific values.
  - Mitigation: store as stage-skill template with clear operator note that it is seed-only and should be simplified per environment.

## Verification Plan

- Automated:
  - `uv run pytest -q`
  - assert `stage_skill` routed metadata semantics and full `deploy_new_agent` stage cycle in IPC integration tests.
- OpenSpec:
  - `openspec validate --type change m07-deploy-new-agent-e2e --strict`
- Live host smoke:
  - run new forms smoke script in dry-run/apply modes as documented.
