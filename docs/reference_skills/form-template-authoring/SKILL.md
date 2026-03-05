---
name: form-template-authoring
description: SOP for authoring reusable Markdown/YAML templates per form stage, colocated with stage skills.
license: MIT
compatibility: OmniClaw M06 form registry and stage metadata
metadata:
  author: omniclaw
  version: "0.1"
---

Use this skill when creating or updating stage templates that are referenced from skill docs (`SKILL.md`) rather than stored in form-type metadata.

## Scope

This skill covers:
- skill-local template path conventions
- required frontmatter and stage-specific fields
- review criteria for clear handoff between holders
- alignment between template paths and stage skills

## Required Inputs

- Form type key (`feature_pipeline_form`, `message`, etc.)
- Stage/status name (`DRAFT`, `PLANNED`, `IMPLEMENTED_TESTED`, ...)
- Required structured fields for that stage
- Target skill path (for example `.codex/skills/read-and-acknowledge-messages/`)

## Execution Steps

1. Create template file under:
   - `.codex/skills/<skill-name>/templates/<form_type_key>/<stage>.md`
2. Include frontmatter with at least:
   - `type` (MESSAGE/message or stage-specific value)
   - `form_type_key`
   - `status`
   - holder/target fields needed for next decision (unless stage is terminal with `next_holder: none`)
3. Add stage sections for:
   - objective
   - required evidence/artifacts
   - decision options (`approve`, `request_changes`, etc. where applicable)
4. Update the corresponding `SKILL.md` to reference the template path and usage instructions.
5. Validate and activate form definition after skill updates.

## Verification Commands

- Check templates:
  - `find .codex/skills -path '*/templates/*' -type f | sort`
- Validate form type definition:
  - `./scripts/forms/trigger_forms_action.sh --apply --body-file <validate.json>`
- Run forms tests:
  - `uv run pytest -q tests/test_forms_actions.py`

## Fallback Path

If a template causes repeated decision errors:
1. Compare template fields against `next_holder` resolution needs.
2. Add missing context fields explicitly in frontmatter/body.
3. Re-run validation and test decision with a sample form instance.
