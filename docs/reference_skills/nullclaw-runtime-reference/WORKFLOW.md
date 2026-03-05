# Workflow: Nullclaw Runtime Investigation

## Inputs

- Objective (operate / configure / extend)
- Current `~/.nullclaw/config.json`
- Runtime mode (`agent`, `gateway`, `service`)

## Steps

1. Baseline runtime health
- `nullclaw --version`
- `nullclaw status`
- `nullclaw doctor`

2. Validate config contract
- verify config path and workspace path
- compare current config with upstream structure

3. Validate channel/provider stack
- `nullclaw channel status`
- inspect configured providers + default model

4. For extension work
- identify subsystem (`providers`, `channels`, `tools`, `memory`, `security`)
- follow source-linked playbook in `references/EXTENDING_NULLCLAW.md`

5. Final check
- run small smoke command in same environment as deployment
- avoid broadening permissions unless explicitly required

6. Failure branch
- if smoke command fails (for example `AllProvidersFailed`), follow [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)
