---
name: manage-agent-skills
description: List, assign, and remove approved loose master skills for target agents or subordinate agents.
version: "1.0.0"
author: omniclaw-kernel
---

# Manage Agent Skills

## Scope

Use this skill when you need to inspect an agent's approved skill set or apply batch loose-skill assignment changes to any target agent you are allowed to manage.

## Required Inputs

- running kernel API reachable at `${OMNICLAW_KERNEL_URL:-http://127.0.0.1:8000}`
- target agent node name or ID
- one or more active loose skill names when assigning or removing
- optional actor node name or ID when you are operating as a manager over subordinates

## Execution Steps

1. Review a target agent's current effective assignments:
   - operator mode:
     - `bash /home/macos/omniClaw/scripts/skills/list_agent_skill_assignments.sh --apply --target-node-name <agent_name>`
   - manager-scoped mode:
     - `bash /home/macos/omniClaw/scripts/skills/list_agent_skill_assignments.sh --apply --actor-node-name <manager_name> --target-node-name <agent_name>`
2. Review active loose skills available for assignment:
   - `bash /home/macos/omniClaw/scripts/skills/list_active_master_skills.sh --apply`
3. Assign multiple loose skills in one request:
   - operator mode:
     - `bash /home/macos/omniClaw/scripts/skills/assign_agent_skills.sh --apply --target-node-name <agent_name> --skill-names "skill_a,skill_b"`
   - manager-scoped mode:
     - `bash /home/macos/omniClaw/scripts/skills/assign_agent_skills.sh --apply --actor-node-name <manager_name> --target-node-name <agent_name> --skill-names "skill_a,skill_b"`
4. Remove multiple manually assigned loose skills in one request:
   - `bash /home/macos/omniClaw/scripts/skills/remove_agent_skills.sh --apply --target-node-name <agent_name> --skill-names "skill_a,skill_b"`
5. If needed, force an explicit workspace reconciliation:
   - `bash /home/macos/omniClaw/scripts/skills/sync_agent_skills.sh --apply --target-node-name <agent_name>`

## Verification

- Confirm `list_agent_skill_assignments` shows the expected `assignment_sources`.
- Confirm assignment and removal responses include a successful sync summary.
- Confirm the target agent workspace `skills/` directory contains only the approved assigned skills after sync.

## Fallback

- If assignment is rejected, verify the skill names are present in `list_active_master_skills`.
- If manager-scoped assignment is rejected, confirm the target agent is inside your allowed management chain.
- If the sync step fails, rerun `sync_agent_skills` for the target and inspect the returned missing-source error.
