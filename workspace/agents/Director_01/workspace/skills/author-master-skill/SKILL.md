---
name: author-master-skill
description: Draft, revise, and activate loose company master skills through the OmniClaw skills API.
version: "1.0.0"
author: omniclaw-kernel
---

# Author Master Skill

## Scope

Use this skill when you need to create a new loose company master skill or update an existing one under the kernel-controlled master skill catalog.

## Required Inputs

- running kernel API reachable at `${OMNICLAW_KERNEL_URL:-http://127.0.0.1:8000}`
- local draft skill folder containing `SKILL.md`
- target master skill name
- optional version and description overrides

## Execution Steps

1. Prepare a local draft folder with:
   - `SKILL.md`
   - optional `skill.json`
   - optional `templates/`, `scripts/`, `docs/`, or `assets/`
2. Draft the loose master skill into the company catalog:
   - `bash /home/macos/omniClaw/scripts/skills/draft_master_skill.sh --apply --skill-name <skill_name> --source-path <draft_dir>`
3. Review the catalog entry:
   - `bash /home/macos/omniClaw/scripts/skills/list_master_skills.sh --apply`
4. Update the same skill after edits:
   - `bash /home/macos/omniClaw/scripts/skills/update_master_skill.sh --apply --skill-name <skill_name> --source-path <draft_dir>`
5. Activate the skill once approved:
   - `bash /home/macos/omniClaw/scripts/skills/set_master_skill_status.sh --apply --skill-name <skill_name> --lifecycle-status ACTIVE`

## Verification

- Confirm the skill appears in `list_master_skills`.
- Confirm the catalog row points at `workspace/master_skills/<skill_name>/`.
- Confirm the skill reaches `ACTIVE` only after review/approval.

## Fallback

- If draft creation fails, verify the source folder contains `SKILL.md`.
- If the kernel rejects activation, inspect the current lifecycle state with `list_master_skills`.
- If you need to revise a live skill, use `update_master_skill` and then re-run activation only if policy requires it.
