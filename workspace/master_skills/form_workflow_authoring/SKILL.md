# Skill: form_workflow_authoring

## Purpose
Design, version, publish, and maintain graph-based OmniClaw form workflows so agents and humans can run company processes through deterministic form routing.

This skill is the canonical SOP for turning a business process into:
1. `workflow.json` (graph definition)
2. stage skill packages (`SKILL.md` + templates/scripts/docs)
3. active kernel form type definition in DB

## Primary References
- `docs/form/SOP Designing Graph Forms.md`
- `docs/form/prompt.md`

## System Model
- OmniClaw routes **forms**, not chats.
- A form is a markdown document with YAML frontmatter.
- Only one holder (agent or human) owns a form at a time, unless terminal stage has no holder.
- Kernel reads `form_type`, `stage`, `transition` and uses active `workflow_graph` to resolve next stage/holder.
- Form state is tracked in DB (`forms_ledger`, `form_transition_events`) and backups are copied to `workspace/form_archive/`.
- Workflow registry endpoint: `POST /v1/forms/actions` with `action: upsert_form_type|validate_form_type|activate_form_type`.

`message` is just one form type, not a special subsystem.

## Canonical Storage Layout
For each form type `<form_type>`:
- `workspace/forms/<form_type>/workflow.json`
- `workspace/forms/<form_type>/skills/<required_skill>/SKILL.md`
- `workspace/forms/<form_type>/skills/<required_skill>/templates/*` (optional)
- `workspace/forms/<form_type>/skills/<required_skill>/scripts/*` (optional)
- `workspace/forms/<form_type>/skills/<required_skill>/docs/*` (optional)

## Markdown Form Runtime Contract
A routed form file should include YAML frontmatter like:

```yaml
---
form_type: message
stage: DRAFT
transition: send
target: Director_01
form_id: message-2026-03-04-001
---
```

### Required runtime fields
- `form_type`: approved type key (snake_case)
- `stage`: current stage key from workflow
- `transition`: explicit decision from current stage transitions (mandatory; no implicit fallback)

### Common optional fields
- `target`: required when next stage target is dynamic (`{{any}}` / `{{var}}`)
- `form_id`: present after first successful transition
- domain-specific fields (`subject`, `requested_role`, etc.)

### Header minimization policy
- Keep frontmatter small and stage-oriented.
- Do not depend on `initiator_node_id`, `target_node_id`, or `in_reply_to` as runtime routing fields.
- Kernel validates `transition` against current-stage transitions in active `workflow.json`.

## Workflow JSON Schema (Stage Graph)
`workflow.json` is the source of truth for routing.

```json
{
  "form_type": "example_form",
  "version": "1.0.0",
  "description": "What this process does.",
  "start_stage": "DRAFT",
  "end_stage": "ARCHIVED",
  "stages": {
    "DRAFT": {
      "target": "{{initiator}}",
      "required_skill": "draft-example-form",
      "transitions": {
        "submit": "REVIEW"
      }
    },
    "REVIEW": {
      "target": "Reviewer_Node",
      "required_skill": "review-example-form",
      "transitions": {
        "approve": "ARCHIVED",
        "return": "DRAFT"
      }
    },
    "ARCHIVED": {
      "target": null,
      "is_terminal": true
    }
  }
}
```

## Target Semantics
Per stage, `target` controls next holder resolution:
- Specific node name: `"Department_Head_HR"`
- Specific node id (UUID): `"<uuid>"`
- `"{{initiator}}"`: back to form initiator
- `"{{any}}"`: runtime chooses from frontmatter `target`
- `"{{var}}"`: runtime chooses from frontmatter `<var>`
- `null` / `"none"`: no holder (terminal/automation close)

## required_skill Semantics
- `required_skill` is required for:
  - all non-terminal stages
  - terminal stages that still target a holder (agent/human)
- `required_skill` is optional for terminal stages that close with `target: null` / `none`.
- When `required_skill` is present, kernel validation requires master copy at:
  - `workspace/forms/<form_type>/skills/<required_skill>/SKILL.md`
- During routing, kernel distributes next-stage skill package to participant workspaces.
- For `{{any}}` target stages, distribute to all active agents plus resolved holder.

## Terminal Node Options
You can end workflows in two valid ways:

1. Terminal archive-only close (no agent handoff):
  - `is_terminal: true`
  - `target: null` (or `none`)
  - no transitions
  - `required_skill` optional (usually omitted)
  - IPC routes file to sender archive + `workspace/form_archive`, with no inbox delivery.

2. Terminal action close (final agent/human does closure work):
  - `is_terminal: true`
  - `target: <agent name/id>` (or dynamic variable)
  - no transitions
  - `required_skill` required
  - Final holder executes closure SOP (KPI summary, cost report, archival script, etc.).

## Workflow Design Method (Mandatory)

### 1) Model process first
Define:
- Trigger event
- Actors
- Decision points
- Return loops
- Terminal outcomes

### 2) Define stages
For each stage, answer:
- Who should own this stage?
- What decision keys are allowed?
- What evidence must be written in form body?
- Which skill teaches that behavior?

### 3) Define transitions
- Keep decision keys explicit and short (`submit`, `approve`, `reject`, `return_to_hr`)
- Use loops intentionally (rework cycles)
- Ensure `end_stage` is reachable

### 4) Define stage skill packages
Each stage skill must include:
- Scope/purpose
- Inputs needed
- Exact frontmatter decision rules
- Tool/scripts to run (if any)
- Validation checklist
- Fallback path

### 5) Validate operational safety
Before activation verify:
- no unreachable stages
- no ambiguous decisions from same stage
- required skill folders exist
- dynamic target requirements documented in skill

## End-to-End Authoring SOP

### A) Create package skeleton
```bash
mkdir -p workspace/forms/<form_type>
mkdir -p workspace/forms/<form_type>/skills/<skill_name>/templates
```

### B) Author workflow graph
- Start from template:
  - `workspace/master_skills/form_workflow_authoring/templates/workflow_template.json`
- Save as:
  - `workspace/forms/<form_type>/workflow.json`

### C) Author stage skills
For every `required_skill` in workflow:
- create `workspace/forms/<form_type>/skills/<required_skill>/SKILL.md`
- add templates/scripts/docs as needed

### D) Publish to kernel DB
Canonical endpoint payload shape:
```json
{
  "action": "upsert_form_type",
  "type_key": "<form_type>",
  "version": "<semver>",
  "workflow_graph": { "...": "..." },
  "stage_metadata": {}
}
```

Dry-run payload generation:
```bash
scripts/forms/upsert_workflow_from_workspace.sh --form-type <form_type>
```

Apply + validate + activate:
```bash
scripts/forms/upsert_workflow_from_workspace.sh --apply --activate --form-type <form_type>
```

Sync all workspace forms into DB and prune stale DB definitions:
```bash
uv run scripts/forms/sync_form_types_from_workspace.py
```

Activation-time checks and actions:
- Validate graph structure and transitions.
- Validate static target nodes exist (by name or UUID).
- Validate required master skills exist under `workspace/forms/<form_type>/skills/...`.
- Distribute required stage skills to participant agent workspaces when missing.

### E) Manual lifecycle actions
Validate specific version:
```bash
scripts/forms/trigger_forms_action.sh --apply \
  --action validate_form_type --type-key <form_type> --version <version>
```

Activate specific version:
```bash
scripts/forms/trigger_forms_action.sh --apply \
  --action activate_form_type --type-key <form_type> --version <version>
```

Deprecate:
```bash
scripts/forms/trigger_forms_action.sh --apply \
  --action deprecate_form_type --type-key <form_type> --version <version>
```

Delete:
```bash
scripts/forms/trigger_forms_action.sh --apply \
  --action delete_form_type --type-key <form_type> --version <version>
```

## Example 1: Message Form (Simple)

```json
{
  "form_type": "message",
  "version": "2.1.0",
  "description": "Generic internal message form routed by workflow stages.",
  "start_stage": "DRAFT",
  "end_stage": "ARCHIVED",
  "dispatch_decision": "send",
  "acknowledge_decision": "acknowledge_read",
  "stages": {
    "DRAFT": {
      "target": "{{initiator}}",
      "required_skill": "draft-internal-message",
      "transitions": {
        "send": "WAITING_TO_BE_READ"
      }
    },
    "WAITING_TO_BE_READ": {
      "target": "{{any}}",
      "required_skill": "read-and-acknowledge-internal-message",
      "transitions": {
        "acknowledge_read": "ARCHIVED"
      }
    },
    "ARCHIVED": {
      "target": null,
      "is_terminal": true
    }
  }
}
```

Design notes:
- Sender drafts and chooses target.
- Receiver acknowledges and archives to close the flow.
- No separate message subsystem needed.

## Example 2: Deploy New Agent (Complex)

```json
{
  "form_type": "deploy_new_agent",
  "version": "1.0.0",
  "description": "Cross-department workflow for deploying a new Nanobot agent.",
  "start_stage": "BUSINESS_CASE",
  "end_stage": "ARCHIVED",
  "stages": {
    "BUSINESS_CASE": {
      "target": "{{initiator}}",
      "required_skill": "draft-agent-business-case",
      "transitions": {
        "submit_to_hr": "HR_REVIEW"
      }
    },
    "HR_REVIEW": {
      "target": "Department_Head_HR",
      "required_skill": "review-agent-role-and-template",
      "transitions": {
        "approve_to_finance": "FINANCE_REVIEW",
        "return_to_initiator": "BUSINESS_CASE"
      }
    },
    "FINANCE_REVIEW": {
      "target": "Department_Head_Finance",
      "required_skill": "allocate-agent-budget",
      "transitions": {
        "approve_to_director": "DIRECTOR_APPROVAL",
        "return_to_hr": "HR_REVIEW"
      }
    },
    "DIRECTOR_APPROVAL": {
      "target": "Agent_000_Director",
      "required_skill": "final-agent-signoff",
      "transitions": {
        "execute_deployment": "AGENT_DEPLOYMENT",
        "return_to_finance": "FINANCE_REVIEW",
        "reject": "ARCHIVED"
      }
    },
    "AGENT_DEPLOYMENT": {
      "target": "HR_Agent_Spawner",
      "required_skill": "deploy-new-nanobot",
      "transitions": {
        "deploy_and_archive": "ARCHIVED"
      }
    },
    "ARCHIVED": {
      "target": "HR_Archiver",
      "required_skill": "archive-agent-deployment-form",
      "is_terminal": true
    }
  }
}
```

Design notes:
- Multi-department approvals with return loops.
- Director can reject directly to terminal archive.
- Final stages can execute real tooling and archive summary.

## Runtime Behavior You Must Teach Agents
When writing stage skills, always include:
- Which `transition` values are legal in this stage
- Whether `target` must be filled manually
- What evidence/sections must be appended before submission
- Which script/endpoint to call for stage completion actions
- What to do if IPC returns `undelivered`

## Quality Gate Checklist (Before Activation)
- [ ] `form_type` is snake_case
- [ ] `start_stage` and `end_stage` defined
- [ ] every non-terminal stage has transitions
- [ ] every `required_skill` has `SKILL.md` in workspace package
- [ ] dynamic target requirements documented in stage skills
- [ ] workflow published, validated, and activated

## Troubleshooting

### Missing skill error on activate
Cause:
- `required_skill` declared but folder missing.
Fix:
- create `workspace/forms/<form_type>/skills/<required_skill>/SKILL.md` and republish.

### Undelivered: missing target for `{{any}}`
Cause:
- form file missing frontmatter `target`.
Fix:
- set `target` to node name/id, keep file in `outbox/pending`, rerun scan.

### Transition rejected
Cause:
- invalid decision for current stage, stale `stage`, or wrong holder.
Fix:
- check DB snapshot, correct frontmatter, retry.

## Change Management Rule
Any change to workflow logic must bump `version`, republish, validate, activate, and leave old versions for historical replay until deprecation policy allows cleanup.
