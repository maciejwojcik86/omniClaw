---
name: deploy-new-nanobot-standalone
description: Standalone loose master skill to deploy a repo-local Nanobot agent without the full deploy_new_agent approval workflow.
license: MIT
compatibility: Linux/macOS host, Python 3.11+, Nanobot CLI available or packaged from local fork
metadata:
  author: omniclaw
  version: "1.0.0"
---

Use this skill when you want to provision and bootstrap a Nanobot agent under `workspace/agents/<agent_name>/` without running the routed `deploy_new_agent` approval process.

## Installation

See [SETUP.md](./SETUP.md) for Nanobot install and packaging options.

## Scope

This loose company skill mirrors the workflow-owned `deploy-new-nanobot` stage skill, but it is packaged for direct/manual assignment under M11.

This skill covers the canonical Nanobot deploy path:
- Scaffold the repo-local agent workspace at `workspace/agents/<agent_name>/workspace/`.
- Write or update the sibling Nanobot runtime config at `workspace/agents/<agent_name>/config.json` using the canonical template at `/home/macos/omniClaw/workspace/nanobot_workspace_templates/config.json`.
- Write workspace-root `AGENTS.md` instructions and preserve the Nanobot-native context files using the canonical files under `/home/macos/omniClaw/workspace/nanobot_workspace_templates/`.
- Register or update the AGENT node through the kernel `provision_agent` action.
- Keep line-management semantics intact: every AGENT still has one manager node.
- Optionally package the vendored monorepo `third_party/nanobot/` fork into a reusable source archive for another machine.
- Provide explicit `nanobot gateway -w -c` and `nanobot agent -w -c` smoke commands.

Use this standalone copy when:
- a high-level manager or operator needs direct deployment capability
- the full approval workflow is intentionally being skipped
- you still want the exact approved helper scripts and templates used by the workflow-owned deploy skill

Do not confuse it with the form-linked `deploy-new-nanobot` package under `workspace/forms/deploy_new_agent/skills/`; that version remains owned by the workflow and is not manually assignable.

## Layout Contract

Each deployed agent uses this layout:

```text
workspace/agents/<agent_name>/
├── config.json
└── workspace/
    ├── AGENTS.md
    ├── HEARTBEAT.md
    ├── SOUL.md
    ├── TOOLS.md
    ├── USER.md
    ├── inbox/
    ├── outbox/
    ├── memory/
    ├── sessions/
    └── skills/
```

Notes:
- `workspace_root` in the DB remains the nested `workspace/` directory.
- Skills are copied into `workspace/.../skills/` as markdown/script folders; no `skill.json` metadata is required inside Nanobot workspaces.
- `config.json` stays next to the workspace, not inside it.

## AGENTS.md Writing Guidance

Use [AGENTS_AUTHORING.md](./AGENTS_AUTHORING.md) to write clear, durable Nanobot-facing instructions.

## Scripts (bundled in this skill)

Primary entrypoint:
- `skills/deploy-new-nanobot-standalone/scripts/deploy_new_nanobot.sh`: unified local deploy flow for the Nanobot layout.

Core helper wrappers:
- `skills/deploy-new-nanobot-standalone/scripts/package_nanobot_source.sh`
- `skills/deploy-new-nanobot-standalone/scripts/create_workspace_tree.py`
- `skills/deploy-new-nanobot-standalone/scripts/init_nanobot_config.py`
- `skills/deploy-new-nanobot-standalone/scripts/write_agent_instructions.py`

Endpoint + audit wrappers:
- `skills/deploy-new-nanobot-standalone/scripts/trigger_kernel_action.sh`
- `skills/deploy-new-nanobot-standalone/scripts/list_agents_permissions.py`

Compatibility wrappers:
- `skills/deploy-new-nanobot-standalone/scripts/deploy_new_nanobot_agent.sh`
- `skills/deploy-new-nanobot-standalone/scripts/provision_agent_workflow.sh`

## Quick Workflow

1. Optional: package the local Nanobot fork so another machine can install the same runtime:
   - `skills/deploy-new-nanobot-standalone/scripts/package_nanobot_source.sh --apply --source-dir /home/macos/omniClaw/third_party/nanobot --output-dir /home/macos/.omniClaw/workspace/runtime_packages`
2. Dry-run deployment:
   - `skills/deploy-new-nanobot-standalone/scripts/deploy_new_nanobot.sh --username agent_hr_head_01 --node-name HR_Head_01 --manager-name Director_01 --role-name "Head of Human Resources" --agents-source-file /tmp/hr-head-01-AGENTS.md --seed-config skills/deploy-new-nanobot-standalone/templates/nanobot_seed_config.json`
3. Apply deployment:
   - `skills/deploy-new-nanobot-standalone/scripts/deploy_new_nanobot.sh --apply --username agent_hr_head_01 --node-name HR_Head_01 --manager-name Director_01 --role-name "Head of Human Resources" --agents-source-file /tmp/hr-head-01-AGENTS.md --seed-config skills/deploy-new-nanobot-standalone/templates/nanobot_seed_config.json`
4. Manual runtime smoke:
   - `nanobot gateway -w /home/macos/omniClaw/workspace/agents/HR_Head_01/workspace -c /home/macos/omniClaw/workspace/agents/HR_Head_01/config.json -p 18792`
   - `nanobot agent -w /home/macos/omniClaw/workspace/agents/HR_Head_01/workspace -c /home/macos/omniClaw/workspace/agents/HR_Head_01/config.json -m "hello"`
5. Audit canonical node state:
   - `python3 skills/deploy-new-nanobot-standalone/scripts/list_agents_permissions.py --database /home/macos/omniClaw/workspace/omniclaw.db`

## M11 Assignment Notes

- New agents receive company-configured default loose skills during provisioning.
- Current default set:
  - `form_workflow_authoring`
- This standalone deploy skill is not a default skill; assign it intentionally to managers or operators who should bypass the full approval workflow.
- Review active loose skills available for post-deploy assignment:
  - `bash /home/macos/omniClaw/scripts/skills/list_active_master_skills.sh --apply`
- Inspect the deployed agent's current effective skill set:
  - `bash /home/macos/omniClaw/scripts/skills/list_agent_skill_assignments.sh --apply --target-node-name <agent_name>`
- Assign this standalone deploy capability explicitly:
  - `bash /home/macos/omniClaw/scripts/skills/assign_agent_skills.sh --apply --target-node-name <agent_name> --skill-names "deploy-new-nanobot-standalone"`
- Add multiple loose skills after deployment in one request:
  - `bash /home/macos/omniClaw/scripts/skills/assign_agent_skills.sh --apply --target-node-name <agent_name> --skill-names "skill_a,skill_b"`
- Remove multiple manually assigned loose skills:
  - `bash /home/macos/omniClaw/scripts/skills/remove_agent_skills.sh --apply --target-node-name <agent_name> --skill-names "skill_a,skill_b"`
- The form-linked `deploy-new-nanobot` remains workflow-owned and cannot be manually assigned.

## Standalone Usage Notes

- Use this skill for direct deployment tasks, manager-issued deployment requests, or live M11 skill-assignment validation.
- Use the form-linked `deploy-new-nanobot` when the deploy action must happen as the `AGENT_DEPLOYMENT` stage of the `deploy_new_agent` workflow.
- If the target host needs your local Nanobot fork, archive it first and install from that archive on the destination host.
- Before first use, verify the helper scripts work from the deployed skill path in the agent workspace:
  - `skills/deploy-new-nanobot-standalone/scripts/deploy_new_nanobot.sh`
  - `skills/deploy-new-nanobot-standalone/scripts/init_nanobot_config.py`
  - `skills/deploy-new-nanobot-standalone/scripts/list_agents_permissions.py`

## Line Management Contract

- Every AGENT must be linked to exactly one manager.
- Manager can be HUMAN or AGENT.
- HUMAN nodes do not require a manager above them.
- Use `manager_node_id` or `manager_node_name` when calling `provision_agent`.
- Use `set_line_manager` only for pre-existing AGENT rows that need manager linkage after the fact.

## Verification

- `ls -la /home/macos/omniClaw/workspace/agents/<agent_name>/config.json`
- `find /home/macos/omniClaw/workspace/agents/<agent_name>/workspace -maxdepth 2 -type d | sort`
- `ls -la /home/macos/omniClaw/workspace/agents/<agent_name>/workspace/AGENTS.md`
- `ls -la /home/macos/omniClaw/workspace/agents/<agent_name>/workspace/HEARTBEAT.md`
- `nanobot gateway -w /home/macos/omniClaw/workspace/agents/<agent_name>/workspace -c /home/macos/omniClaw/workspace/agents/<agent_name>/config.json -p 18790`
- `nanobot agent -w /home/macos/omniClaw/workspace/agents/<agent_name>/workspace -c /home/macos/omniClaw/workspace/agents/<agent_name>/config.json -m "hello"`
- `python3 skills/deploy-new-nanobot-standalone/scripts/list_agents_permissions.py --database /home/macos/omniClaw/workspace/omniclaw.db`

## Troubleshooting SOP

If deployment or first runtime smoke fails, use [TROUBLESHOOTING.md](./TROUBLESHOOTING.md).

## Execution Reporting

- If deployment is blocked or fails, record the failure details, next-step owner, and smoke output in the calling task or operator log.
- If deployment succeeds, record the final workspace path, config path, packaged runtime artifact path, and smoke command results.
- If this standalone skill is invoked from another workflow later, let that outer workflow own archival and decision handling.

## Related Docs

- [WORKFLOW.md](./WORKFLOW.md)
- [SETUP.md](./SETUP.md)
- [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)
- [AGENTS_AUTHORING.md](./AGENTS_AUTHORING.md)
