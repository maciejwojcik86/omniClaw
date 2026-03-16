## 1. Change Setup

- [x] 1.1 Update trackers/docs to make `m12b-global-company-registry` the active change after archiving M12.
- [x] 1.2 Author the OpenSpec proposal, design, and spec deltas for the global company registry model.

## 2. Global Config And Runtime Resolution

- [x] 2.1 Add a global config/registry loader for `~/.omniClaw/config.json` and extend `Settings` to carry resolved company identity and settings.
- [x] 2.2 Update the `omniclaw` CLI to resolve a company by slug/display name and boot from the global registry.
- [x] 2.3 Fail fast when the selected company workspace path from global config does not exist.

## 3. Service And Script Migration

- [x] 3.1 Refactor budgets, instructions, and skills services to read company settings from the resolved global config rather than from workspace-local company config files.
- [x] 3.2 Update workspace bootstrap/migration tooling to write company settings into the global config and stop treating workspace-local company config as canonical.
- [x] 3.3 Update canonical runtime/provisioning/helper scripts to use `--company` / global config resolution instead of workspace-config startup.

## 4. Validation, Skills, And Local Migration

- [x] 4.1 Update automated tests for the new global config contract and keep legacy compatibility paths covered where needed.
- [x] 4.2 Migrate the current local OmniClaw company into `~/.omniClaw/config.json` and validate live startup against the company reference.
- [x] 4.3 Update mirrored developer/copilot skills and implementation docs for the global company registry workflow.
