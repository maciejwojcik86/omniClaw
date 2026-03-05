---
name: form-type-authoring
description: Operator SOP for creating, validating, activating, and deprecating custom snake_case form types with node-centric graph workflows in OmniClaw M06.
license: MIT
compatibility: OmniClaw kernel with `/v1/forms/actions`
metadata:
  author: omniclaw
  version: "0.1"
---

Use this skill when defining a new reusable form type (for example `feature_pipeline_form`) and loading it into canonical DB state.

`message` is treated the same as other form types: activate the desired version in `form_types`, and runtime will use that active definition without code-side graph overwrite.

## Scope

This skill covers:
- snake_case form type keys (`^[a-z][a-z0-9_]*$`)
- node-centric graph structure (`start_node`, `end_node`, `nodes`, `edges`)
- node requirements (`status`, `stage_skill_ref`, `holder`)
- edge requirements (`from`, `to`, `decision`)
- form type lifecycle actions (`DRAFT`, `VALIDATED`, `ACTIVE`, `DEPRECATED`)
- endpoint/script-driven registry updates

## Required Inputs

- Form type key in snake_case (for example `feature_pipeline_form`)
- Semantic version (for example `1.0.0`)
- `workflow_graph` JSON:
  - `start_node` and required `end_node`
  - `nodes{}` where each node declares:
    - `status`
    - `stage_skill_ref`
    - `holder` (`strategy`: `static_node`, `static_node_name`, `field_ref`, `previous_holder`, `previous_actor`, `none`)
  - `edges[]` with `from`, `to`, and required `decision`
- Keep `stage_metadata` as `{}` for node-centric definitions (legacy field retained for compatibility only)

## Execution Steps

1. Draft payload JSON for `upsert_form_type`.
2. Submit draft definition:
   - `./scripts/forms/trigger_forms_action.sh --apply --body-file <payload.json>`
3. Validate definition:
   - action `validate_form_type` with `type_key` and `version`
4. Activate definition after zero validation errors:
   - action `activate_form_type`
5. Confirm active record:
   - action `list_form_types` filtered by `type_key`
6. If replacing old active version, activate new version and keep old one as `VALIDATED` or `DEPRECATED`.

## Verification Commands

- Dry-run request build:
  - `./scripts/forms/trigger_forms_action.sh --action list_form_types --type-key feature_pipeline_form`
- Validate + activate (apply mode):
  - `./scripts/forms/trigger_forms_action.sh --apply --action validate_form_type --type-key feature_pipeline_form --version 1.0.0`
  - `./scripts/forms/trigger_forms_action.sh --apply --action activate_form_type --type-key feature_pipeline_form --version 1.0.0`
- Run focused tests:
  - `uv run pytest -q tests/test_forms_actions.py`

## Fallback Path

If activation fails:
1. Inspect returned validation errors.
2. Fix graph ambiguity (duplicate `(from, decision)` edges), missing `end_node`, invalid node `holder` strategy/value, or missing node `stage_skill_ref`.
3. Re-run `upsert_form_type` in `DRAFT` state.
4. Re-run `validate_form_type` before trying activation again.
