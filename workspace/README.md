# OmniClaw Workspace Root

`workspace/` stores company-level soft configuration and workspace artifacts.

## Top-level folders
- `workspace/<node_workspace>/`: individual HUMAN/AGENT workspaces (`inbox`, `outbox`, `skills`, etc.)
- `workspace/forms/`: approved form workflow packages
  - `workspace/forms/<form_type>/workflow.json`
  - `workspace/forms/<form_type>/skills/<required_skill>/SKILL.md`
- `workspace/master_skills/`: organization master skills used to bootstrap and govern behavior
- `workspace/form_archive/`: routed-form backup ledger copies

## Form package convention
Each form package has:
- graph definition (`workspace/forms/<form_type>/workflow.json`)
- per-stage skills in `workspace/forms/<form_type>/skills/`
- optional templates/docs/scripts colocated with each stage skill
