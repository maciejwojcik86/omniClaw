# Nullclaw Configuration Guide

## Canonical Location

- `~/.nullclaw/config.json`

## Most Important Sections

- `models.providers`: provider credentials and endpoints.
- `agents.defaults.model.primary`: default model routing target.
- `agents.defaults.heartbeat`: heartbeat enablement and cadence (`every`, for example `"30m"`).
- `channels.*.accounts`: channel account definitions.
- `autonomy`: risk/permission behavior (`workspace_only`, action limits).
- `gateway`: bind host/port + pairing requirements.
- `security`: sandbox, resource, audit controls.
- `memory`: backend + retrieval behavior.

## Baseline Safe Defaults For OmniClaw Integration

- keep `autonomy.workspace_only = true`
- keep gateway pairing enabled (`gateway.require_pairing = true`)
- keep sandbox backend enabled (`security.sandbox.backend = "auto"` or explicit)
- keep provider map present but allow empty providers during bootstrap phase
- enable heartbeat explicitly for agent polling workflows:
  - `"agents": {"defaults": {"heartbeat": {"every": "30m"}}}`

## Validation Checklist

- config is valid JSON
- default model key exists (or intentionally empty for bootstrap)
- channels are only enabled when credentials are present
- no plaintext secrets committed to git

## Primary Sources

- https://github.com/nullclaw/nullclaw/blob/main/config.example.json
- https://github.com/nullclaw/nullclaw/blob/main/README.md#configuration
- https://github.com/nullclaw/nullclaw/blob/main/src/config_parse.zig
- https://github.com/nullclaw/nullclaw/blob/main/src/heartbeat.zig
- https://nullclaw.github.io/configuration.html
- https://nullclaw.github.io/providers.html
- https://nullclaw.github.io/channels.html
- https://docs.openclaw.ai/gateway/heartbeat.md
- https://docs.openclaw.ai/automation/cron-vs-heartbeat.md
