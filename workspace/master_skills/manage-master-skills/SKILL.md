---
name: manage-master-skills
description: Inspect the master skill catalog, review active loose skills, and change loose skill lifecycle state.
version: "1.0.0"
author: omniclaw-kernel
---

# Manage Master Skills

## Scope

Use this skill when you need visibility into the company master skill catalog or need to activate, deactivate, or update a loose company skill.

## Required Inputs

- running kernel API reachable at `${OMNICLAW_KERNEL_URL:-http://127.0.0.1:8000}`
- optional local draft folder when updating a skill
- loose skill name when changing lifecycle or contents

## Execution Steps

1. List every cataloged master skill:
   - `bash /home/macos/omniClaw/scripts/skills/list_master_skills.sh --apply`
2. List only active loose skills that are eligible for manual assignment:
   - `bash /home/macos/omniClaw/scripts/skills/list_active_master_skills.sh --apply`
3. Update an existing loose skill package:
   - `bash /home/macos/omniClaw/scripts/skills/update_master_skill.sh --apply --skill-name <skill_name> --source-path <draft_dir>`
4. Change loose skill lifecycle:
   - approve/activate:
     - `bash /home/macos/omniClaw/scripts/skills/set_master_skill_status.sh --apply --skill-name <skill_name> --lifecycle-status ACTIVE`
   - send back to draft:
     - `bash /home/macos/omniClaw/scripts/skills/set_master_skill_status.sh --apply --skill-name <skill_name> --lifecycle-status DRAFT`
   - discontinue:
     - `bash /home/macos/omniClaw/scripts/skills/set_master_skill_status.sh --apply --skill-name <skill_name> --lifecycle-status DEACTIVATED`

## Verification

- Confirm catalog output shows `form_type_key: null` for loose skills you manage here.
- Confirm `list_active_master_skills` only returns `ACTIVE` loose skills.
- Confirm deactivated skills stop appearing in the active-only list.

## Fallback

- If a skill is form-linked (`form_type_key` is not null), do not change it here; update the owning workflow package instead.
- If update fails, verify the source directory still contains `SKILL.md`.
- If lifecycle change is rejected, confirm the skill name is correct and the catalog entry exists.
