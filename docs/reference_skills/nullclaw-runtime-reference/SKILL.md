---
name: nullclaw-runtime-reference
description: >
  Reference skill for Nullclaw runtime behavior, config.json structure, CLI/gateway operation,
  and extension patterns (providers/channels/tools/skills). Use when integrating OmniClaw with
  Nullclaw, editing ~/.nullclaw/config.json, debugging runtime behavior, or planning feature
  expansion against upstream docs and source files.
---

Use this skill when you need accurate, source-linked guidance for how Nullclaw works, how it is configured, and how to extend it safely.

## Installation

See [SETUP.md](./SETUP.md) for first-time setup and optional local snapshot refresh.

## What This Skill Covers

- Runtime model: `agent`, `gateway`, channels, tools, memory, security layers.
- Config model: `~/.nullclaw/config.json` keys and high-impact defaults.
- Operational commands: onboarding, status, service, channel, cron.
- Extension paths: providers/channels/tools/skills and where to edit upstream.
- Curated links to official docs pages, security subpages, and upstream source files.

## Procedure

1. Confirm runtime baseline:
- Run `nullclaw --version`
- Run `nullclaw status`
- Run `nullclaw doctor`

2. Confirm config + workspace contract:
- Config path: `~/.nullclaw/config.json`
- Workspace path: `~/.nullclaw/workspace`
- Compare your config with `config.example.json` from upstream.

3. Map goal to docs quickly:
- Runtime/architecture: [references/RUNTIME_MODEL.md](./references/RUNTIME_MODEL.md)
- Config: [references/CONFIGURATION_GUIDE.md](./references/CONFIGURATION_GUIDE.md)
- Extensibility: [references/EXTENDING_NULLCLAW.md](./references/EXTENDING_NULLCLAW.md)
- Full links index: [references/REFERENCE_MAP.md](./references/REFERENCE_MAP.md)

4. For integration changes in OmniClaw:
- Keep Nullclaw defaults secure (`workspace_only=true`, pairing required, sandbox backend set).
- Keep provider credentials out of git; inject at runtime.
- Validate with small smoke commands before enabling daemon/service mode.

5. If runtime smoke fails:
- Follow [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) before changing wider system settings.

## Verification Commands

```bash
nullclaw --version
nullclaw status
nullclaw doctor
nullclaw channel status
nullclaw service status
ls -la ~/.nullclaw/config.json ~/.nullclaw/workspace
```

## Related Skills

- `$deploy-new-claw-agent`: Provision Linux user + workspace + baseline Nullclaw install.
- `$authoring-skills`: Rules for writing and maintaining skills.
